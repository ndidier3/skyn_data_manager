# Curve Demarcation and Merging

## Overview

This document describes how TAC (Transdermal Alcohol Concentration) curves are identified, filtered, and merged in the SDM analysis pipeline. The curve demarcation process involves detecting discrete **candidate curves** above a threshold, filtering out brief candidates, and intelligently merging nearby candidate curves into final accepted curves.

## Terminology

- **Candidate curve**: A TAC curve segment that has been initially detected but has not yet passed final filtering criteria
- **Blip curve**: Candidate curves <5 minutes (always rejected)
- **Short curve**: Candidate curves 5-15 minutes (conditionally accepted if merged)
- **Substantial curve**: Candidate curves ≥15 minutes (always accepted)
- **Anchor curve**: A substantial candidate curve (≥15 min) that can "anchor" nearby short curves through merging
- **Accepted curve**: Final curve that passes all filtering and is included in analysis

## Process Flow

### 1. Initial Curve Detection (`get_start_and_end_of_discrete_curves()`)

**Purpose**: Identify all consecutive sequences of TAC values above the determined threshold as candidate curves.

**Algorithm**:
1. Find all indices where `TAC > curve_threshold`
2. Identify gaps between consecutive indices (`gaps = np.diff(above_threshold)`)
3. Split sequences at gaps > 1 to create discrete candidate curve segments
4. Return start and end indices for each consecutive sequence

**Initial Filtering**: 
- **Blip curves (<5 minutes)**: Filtered out immediately as too brief to be meaningful
- **Short curves (5-15 minutes)**: Retained as candidates for potential merging with anchor curves
- **Substantial curves (≥15 minutes)**: Retained as candidates and serve as anchors for merging

### 2. Curve Merging (`merge_nearby_curves()`)

**Purpose**: Merge nearby candidate curves that are likely part of the same drinking event.

**Configuration**:
- `merge_curves_within_duration`: 2 hours (default in test settings)
- `curve_minutes_limit`: 24 hours (maximum merged curve duration)

**Merging Logic**:
1. **Distance Check**: 
   - Uses **sum-based approach**: `most_recent_discrete_curve + current_curve`
   - Only considers the **two neighboring candidate curves** on either side of the gap
   - Capped at `max_curve_separation_minutes` (default: 60 minutes when configured for 2 hours)
   - **Examples**:
     - [10 min] + [8 min] → 18 min merge distance allowed
     - [20 min] + [15 min] → 35 min merge distance allowed
     - [30 min] + [35 min] → 60 min merge distance (hits cap)
2. **Duration Check**: If merged curve would be < `curve_minutes_limit` minutes (24 hours)
3. **Merge**: Combine candidate curves by extending the end time of the previous curve
4. **Anti-Accumulation**: Each merge decision only considers immediate neighbors, preventing quality degradation from distant curves

**Post-Merge Filtering**:
After merging, the system applies final acceptance criteria to determine which merged candidates become accepted curves:
- **Accept if**: The merged candidate curve (including all gaps) is ≥15 minutes
- **Reject if**: The merged candidate curve (including all gaps) is <15 minutes

**Note**: If any anchor curve (≥15 min) was merged, the resulting merged curve will mathematically always be ≥15 minutes since the merged duration includes the anchor plus any gaps and additional curves. Therefore, only merged candidates formed entirely from short curves (<15 min) risk rejection.

### 3. Final Processing

**When merging is disabled** (`merge_curves_within_duration = 0`):
- Simple filtering: Remove all candidate curves <15 minutes
- Add curve_count = 1 to remaining accepted curves

**When merging is enabled**:
- Apply sophisticated merging and filtering logic
- Track which original candidate curves contributed to each merged curve (curve_count)
- Accept merged curves if total span ≥15 minutes

## Candidate Curve Classification

### Blip Curves (<5 minutes)
- **Status**: Always rejected
- **Rationale**: Too brief to represent meaningful drinking events
- **Processing**: Removed at initial detection stage before merging

### Short Curves (5-15 minutes)
- **Status**: Conditionally accepted
- **Accept if**: Merges with other candidate curves to form a ≥15 minute merged curve
- **Reject if**: Standalone or merges to form <15 minute total
- **Merge Distance**: Calculated as sum of the two neighboring curves (e.g., 10 min + 8 min = 18 min allowed)
- **Rationale**: May represent brief drinking episodes that are part of larger events

### Substantial Curves (≥15 minutes)
- **Status**: Always accepted
- **Role**: Serve as "anchor curves" that ensure any merged curve containing them will be ≥15 minutes
- **Impact**: Any curve merging with an anchor will automatically pass the ≥15 minute threshold

## Example Scenarios

### Scenario 1: Two Substantial Candidate Curves
```
Candidate A: 25 minutes (substantial, ≥15 min)
Candidate B: 30 minutes (substantial, ≥15 min)
Gap: 50 minutes

Merge distance allowed: 25 + 30 = 55 minutes
Gap (50) < Allowed (55) → MERGE ✓

Result: Merged into 105-minute accepted curve
Reason: Both candidates are substantial anchors, gap within sum threshold, 
        merged span (105 min) ≥15 min → ACCEPTED
```

### Scenario 2: Short Candidate Merged with Substantial Anchor
```
Candidate A: 10 minutes (short, 5-15 min range)
Candidate B: 20 minutes (substantial anchor, ≥15 min)
Gap: 25 minutes

Merge distance allowed: 10 + 20 = 30 minutes
Gap (25) < Allowed (30) → MERGE ✓

Result: Merged into 55-minute accepted curve
Reason: Short candidate within sum threshold of anchor,
        merged span (55 min) ≥15 min → ACCEPTED
```

### Scenario 3: Short Candidate Too Far from Substantial Anchor
```
Candidate A: 10 minutes (short, 5-15 min range)
Candidate B: 20 minutes (substantial anchor, ≥15 min)
Gap: 35 minutes

Merge distance allowed: 10 + 20 = 30 minutes
Gap (35) > Allowed (30) → DON'T MERGE ✗

Result: Candidate A rejected (10 min < 15 min threshold)
        Candidate B accepted as standalone (20 min ≥15 min threshold)
Reason: Gap exceeds sum threshold, no merging occurs
```

### Scenario 4: Multiple Short Candidates - Cannot Accumulate
```
Step 1: Candidate A: 8 min, Candidate B: 12 min, Gap: 18 min
  Allowed: 8 + 12 = 20 → MERGE ✓
  Result: [8] + [18 gap] + [12] = 38 min merged candidate

Step 2: Try to add Candidate C: 10 min, Gap from B: 25 min
  Allowed: 12 + 10 = 22 (only uses most recent discrete candidate B)
  Gap (25) > Allowed (22) → DON'T MERGE ✗
  
Result: Merged [A+B] accepted (38 min ≥15 min threshold)
        Candidate C rejected as standalone (10 min < 15 min threshold)
Reason: Anti-accumulation prevents progressive merging of weak signals,
        but merged A+B spans ≥15 min and passes acceptance
```

### Scenario 5: Short Standalone Candidate
```
Candidate A: 10 minutes (short, 5-15 min range)
Candidate B: 20 minutes (next curve)
Gap: 40 minutes

Merge distance allowed: 10 + 20 = 30 minutes
Gap (40) > Allowed (30) → DON'T MERGE ✗

Result: Candidate A rejected (10 min < 15 min threshold)
        Candidate B accepted (20 min ≥15 min threshold)
Reason: Gap exceeds sum threshold, no merging possible
```

### Scenario 6: Blip Curve (Always Rejected Before Merging)
```
Candidate A: 3 minutes (blip curve, <5 min)
Candidate B: 20 minutes (substantial anchor, ≥15 min)
Gap: 30 minutes

Result: Candidate A rejected immediately during initial filtering
        Candidate B accepted as standalone (20 min ≥15 min threshold)
Reason: Blip curves (<5 min) are filtered out before merging logic applies
```

### Scenario 7: Multiple Short Candidates Form Substantial Merged Curve
```
Candidate A: 8 minutes (short)
Candidate B: 10 minutes (short)
Gap: 15 minutes

Merge distance allowed: 8 + 10 = 18 minutes
Gap (15) < Allowed (18) → MERGE ✓

Result: Merged into 33-minute accepted curve (8 + 15 + 10)
Reason: Neither candidate is an anchor, but merged span (33 min) ≥15 min → ACCEPTED
```

## Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `merge_curves_within_duration` | 2 hours | Converted to `max_curve_separation_minutes` (60 min cap) |
| `max_curve_separation_minutes` | 60 minutes | Hard cap on merge distance regardless of candidate curve sizes |
| `curve_minutes_limit` | 24 hours | Maximum duration for a merged candidate curve |
| Blip curve threshold | 5 minutes | Minimum candidate curve duration to consider for merging |
| Acceptance threshold | 15 minutes | Minimum total span for final curve acceptance |
| Merge distance formula | `min(candidate_A + candidate_B, 60)` | Sum of neighboring candidates, capped at 60 minutes |

## Sum-Based Merge Distance Algorithm

### Key Innovation: Anti-Accumulation Design

The merge distance calculation uses a **sum-based approach** that prevents quality degradation:

```python
most_recent_discrete_candidate + current_incoming_candidate = effective_merge_distance
```

**Why this matters:**
- **Local decisions only**: Each merge considers only the two candidate curves immediately adjacent to the gap
- **Prevents accumulation**: Old distant candidates don't inflate the merge allowance
- **Natural quality control**: Long merged segments don't automatically gain more "merge power"

### Example: Anti-Accumulation in Action

```
Step 1: Candidate [10 min] + Candidate [8 min], gap = 15 min
  Allowed: 10 + 8 = 18 → MERGE ✓
  Result: Merged candidate [10] + [15 gap] + [8] = 33 min

Step 2: Try to add Candidate [12 min], gap from [8] = 25 min
  Allowed: 8 + 12 = 20 (only uses most recent candidate [8], not [10])
  Gap (25) > Allowed (20) → DON'T MERGE ✗
```

**Without anti-accumulation**, step 2 would calculate: 10 + 8 + 12 = 30, allowing the merge and creating a curve that's 57% gap (25/44).

**With anti-accumulation**, step 2 only considers: 8 + 12 = 20, preventing the low-quality merge.

### Benefits

✅ Prevents merged candidate curves from becoming mostly gaps  
✅ Each gap evaluated against its immediate neighbors  
✅ Simple, transparent calculation  
✅ Scales naturally with candidate curve quality  

## Integration with Threshold Detection

The curve demarcation process works in conjunction with the automatic threshold detection system:

1. **Threshold Determination**: Uses k-means clustering to identify baseline vs. elevated TAC levels
2. **Candidate Curve Detection**: Applies the determined threshold to identify discrete candidate curves
3. **Filtering and Merging**: Applies the intelligent filtering and merging logic described above
4. **Final Acceptance**: Candidate curves passing the ≥15 minute threshold become accepted curves

See `README_curve_threshold_auto.md` for details on threshold computation.

## Technical Implementation

### Key Functions

- `get_start_and_end_of_discrete_curves()`: Initial candidate curve detection with blip filtering (<5 min)
- `merge_nearby_curves()`: Merging logic with final acceptance filtering (≥15 min total span)
- `adjust_curve_demarcation_for_raw_tac()`: Additional adjustment for raw TAC data

### Data Flow

```
TAC Data → Threshold Detection → Candidate Curve Detection → Blip Filtering (<5 min) → 
Merging Logic → Final Acceptance (≥15 min) → Accepted Curve List
```

### Processing Pipeline Summary

1. **Input**: TAC time series data with determined threshold
2. **Stage 1**: Detect all consecutive sequences above threshold → **Candidate curves**
3. **Stage 2**: Filter out blips (<5 min) → **Mergeable candidates**
4. **Stage 3**: Apply sum-based merging with anti-accumulation → **Merged candidates**
5. **Stage 4**: Accept candidates with total span ≥15 min → **Final accepted curves**
6. **Output**: List of accepted curves with start/end indices and curve_count

