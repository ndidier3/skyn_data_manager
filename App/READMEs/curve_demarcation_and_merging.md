# Curve Demarcation and Merging

## Overview

This document describes how TAC (Transdermal Alcohol Concentration) curves are identified, filtered, and merged in the SDM analysis pipeline. The curve demarcation process involves detecting discrete curves above a threshold, filtering out brief or standalone curves, and intelligently merging nearby curves.

## Process Flow

### 1. Initial Curve Detection (`get_start_and_end_of_discrete_curves()`)

**Purpose**: Identify all consecutive sequences of TAC values above the determined threshold.

**Algorithm**:
1. Find all indices where `TAC > curve_threshold`
2. Identify gaps between consecutive indices (`gaps = np.diff(above_threshold)`)
3. Split sequences at gaps > 1 to create discrete curve segments
4. Return start and end indices for each consecutive sequence

**Filtering**: 
- **Blip curves (<5 minutes)**: Filtered out immediately as too brief to be meaningful
- **Short curves (5-15 minutes)**: Retained for potential merging with longer curves
- **Substantial curves (≥15 minutes)**: Always retained

### 2. Curve Merging (`merge_nearby_curves()`)

**Purpose**: Merge nearby curves that are likely part of the same drinking event.

**Configuration**:
- `merge_curves_within_duration`: 2 hours (default in test settings)
- `curve_minutes_limit`: 24 hours (maximum merged curve duration)

**Merging Logic**:
1. **Distance Check**: 
   - Uses **sum-based approach**: `most_recent_discrete_curve + current_curve`
   - Only considers the **two neighboring curves** on either side of the gap
   - Capped at `max_curve_separation_minutes` (default: 60 minutes when configured for 2 hours)
   - **Examples**:
     - [10 min] + [8 min] → 18 min merge distance allowed
     - [20 min] + [15 min] → 35 min merge distance allowed
     - [30 min] + [35 min] → 60 min merge distance (hits cap)
2. **Duration Check**: If merged curve would be < `curve_minutes_limit` minutes (24 hours)
3. **Merge**: Combine curves by extending the end time of the previous curve
4. **Anti-Accumulation**: Each merge decision only considers immediate neighbors, preventing quality degradation from distant curves

**Post-Merge Filtering**:
After merging, the system applies intelligent filtering:
- **Keep curves if**:
  - The merged curve itself is substantial (≥15 minutes), OR
  - The merged curve contains at least one substantial "anchor" curve (≥15 minutes)
- **Remove curves if**:
  - The curve is <15 minutes AND contains no substantial anchor curves

### 3. Final Processing

**When merging is disabled** (`merge_curves_within_duration = 0`):
- Simple filtering: Remove all curves <15 minutes
- Add curve_count = 1 to remaining curves

**When merging is enabled**:
- Apply sophisticated merging and filtering logic
- Track which original curves contributed to each merged curve
- Preserve short curves that merged with substantial anchors

## Curve Classification

### Blip Curves (<5 minutes)
- **Status**: Always filtered out
- **Rationale**: Too brief to represent meaningful drinking events
- **Processing**: Removed at initial detection stage

### Short Curves (5-15 minutes)
- **Status**: Conditionally kept
- **Keep if**: Merges with a substantial anchor curve (≥15 minutes)
- **Remove if**: Standalone or only merges with other short curves
- **Merge Distance**: Calculated as sum of the two neighboring curves (e.g., 10 min + 8 min = 18 min allowed)
- **Rationale**: May represent brief drinking episodes that are part of larger events

### Substantial Curves (≥15 minutes)
- **Status**: Always kept
- **Role**: Serve as "anchor curves" that can preserve nearby short curves

## Example Scenarios

### Scenario 1: Two Substantial Curves
```
Curve A: 25 minutes (substantial, ≥15 min)
Curve B: 30 minutes (substantial, ≥15 min)
Gap: 50 minutes

Merge distance allowed: 25 + 30 = 55 minutes
Gap (50) < Allowed (55) → MERGE ✓

Result: Merged into 105-minute curve (kept)
Reason: Both curves are substantial, gap within sum threshold
```

### Scenario 2: Short Curve Merged with Substantial Anchor
```
Curve A: 10 minutes (short, 5-15 min range)
Curve B: 20 minutes (substantial anchor, ≥15 min)
Gap: 25 minutes

Merge distance allowed: 10 + 20 = 30 minutes
Gap (25) < Allowed (30) → MERGE ✓

Result: Merged into single 55-minute curve (kept)
Reason: Short curve within sum threshold of substantial anchor
```

### Scenario 3: Short Curve Too Far from Substantial Anchor
```
Curve A: 10 minutes (short, 5-15 min range)
Curve B: 20 minutes (substantial anchor, ≥15 min)
Gap: 35 minutes

Merge distance allowed: 10 + 20 = 30 minutes
Gap (35) > Allowed (30) → DON'T MERGE ✗

Result: Curve A filtered out, Curve B kept as standalone
Reason: Gap exceeds sum threshold, no merging occurs
```

### Scenario 4: Multiple Short Curves - Cannot Accumulate
```
Step 1: Curve A: 8 min, Curve B: 12 min, Gap: 18 min
  Allowed: 8 + 12 = 20 → MERGE ✓
  Result: [8] + [18 gap] + [12]

Step 2: Curve C: 10 min, Gap from B: 25 min
  Allowed: 12 + 10 = 22 (only uses most recent discrete curve B)
  Gap (25) > Allowed (22) → DON'T MERGE ✗
  
Result: [8]+[18]+[12] merged (38 min total), but filtered out (no ≥15 min anchor)
        Curve C kept separately (10 min → filtered out if standalone)
Reason: Anti-accumulation prevents progressive merging of weak signals
```

### Scenario 5: Short Standalone Curve
```
Curve A: 10 minutes (short, 5-15 min range)
Curve B: 20 minutes (next curve)
Gap: 40 minutes

Merge distance allowed: 10 + 20 = 30 minutes
Gap (40) > Allowed (30) → DON'T MERGE ✗

Result: Curve A filtered out (no merging possible)
Reason: Gap exceeds sum threshold, no anchor available
```

### Scenario 6: Blip Curve (Always Filtered)
```
Curve A: 3 minutes (blip curve, <5 min)
Curve B: 20 minutes (substantial anchor, ≥15 min)
Gap: 30 minutes (0.5 hours, within merge distance)

Result: Curve A filtered out immediately, Curve B kept
Reason: Blip curves are filtered out before merging logic applies
```

## Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `merge_curves_within_duration` | 2 hours | Converted to `max_curve_separation_minutes` (60 min cap) |
| `max_curve_separation_minutes` | 60 minutes | Hard cap on merge distance regardless of curve sizes |
| `curve_minutes_limit` | 24 hours | Maximum duration for a merged curve |
| Blip curve threshold | 5 minutes | Minimum curve duration to consider |
| Short curve threshold | 15 minutes | Minimum duration for standalone curves |
| Merge distance formula | `min(curve_A + curve_B, 60)` | Sum of neighboring curves, capped at 60 minutes |

## Sum-Based Merge Distance Algorithm

### Key Innovation: Anti-Accumulation Design

The merge distance calculation uses a **sum-based approach** that prevents quality degradation:

```python
most_recent_discrete_curve + current_incoming_curve = effective_merge_distance
```

**Why this matters:**
- **Local decisions only**: Each merge considers only the two curves immediately adjacent to the gap
- **Prevents accumulation**: Old distant curves don't inflate the merge allowance
- **Natural quality control**: Long merged segments don't automatically gain more "merge power"

### Example: Anti-Accumulation in Action

```
Step 1: [10 min] + [8 min], gap = 15 min
  Allowed: 10 + 8 = 18 → MERGE ✓
  Result: [10] + [15 gap] + [8]

Step 2: Try to add [12 min], gap from [8] = 25 min
  Allowed: 8 + 12 = 20 (only uses most recent [8], not [10])
  Gap (25) > Allowed (20) → DON'T MERGE ✗
```

**Without anti-accumulation**, step 2 would calculate: 10 + 8 + 12 = 30, allowing the merge and creating a curve that's 57% gap.

**With anti-accumulation**, step 2 only considers: 8 + 12 = 20, preventing the low-quality merge.

### Benefits

✅ Prevents merged curves from becoming mostly gaps  
✅ Each gap evaluated against its immediate neighbors  
✅ Simple, transparent calculation  
✅ Scales naturally with curve quality  

## Integration with Threshold Detection

The curve demarcation process works in conjunction with the automatic threshold detection system:

1. **Threshold Determination**: Uses k-means clustering to identify baseline vs. elevated TAC levels
2. **Curve Detection**: Applies the determined threshold to identify discrete curves
3. **Filtering and Merging**: Applies the intelligent filtering logic described above

See `README_curve_threshold_auto.md` for details on threshold computation.

## Technical Implementation

### Key Functions

- `get_start_and_end_of_discrete_curves()`: Initial curve detection with mini-curve filtering
- `merge_nearby_curves()`: Merging logic with post-merge filtering
- `adjust_curve_demarcation_for_raw_tac()`: Additional adjustment for raw TAC data

### Data Flow

```
TAC Data → Threshold Detection → Curve Detection → Mini-Curve Filtering → 
Merging → Anchor-Based Filtering → Final Curve List
```

