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
   - **Short curves (5-15 min)**: Use half the merge distance (e.g., 1 hour if configured for 2 hours)
   - **Substantial curves (≥15 min)**: Use full merge distance
2. **Duration Check**: If merged curve would be < `curve_minutes_limit` minutes
3. **Merge**: Combine curves by extending the end time of the previous curve

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
- **Merge Distance**: Uses half the configured merge distance (e.g., 1 hour instead of 2 hours)
- **Rationale**: May represent brief drinking episodes that are part of larger events

### Substantial Curves (≥15 minutes)
- **Status**: Always kept
- **Role**: Serve as "anchor curves" that can preserve nearby short curves

## Example Scenarios

### Scenario 1: Two Substantial Curves (Most Obvious Success)
```
Curve A: 25 minutes (substantial, ≥15 min)
Curve B: 30 minutes (substantial, ≥15 min)
Gap: 90 minutes (1.5 hours, < 2 hours full merge distance)

Result: Merged into 145-minute curve (kept)
Reason: Both curves are substantial, gap is within full merge distance
```

### Scenario 2: Short Curve Merged with Substantial Anchor
```
Curve A: 10 minutes (short, 5-15 min range)
Curve B: 20 minutes (substantial anchor, ≥15 min)
Gap: 30 minutes (0.5 hours, < 1 hour half merge distance)

Result: Merged into single 60-minute curve (kept)
Reason: Short curve within half merge distance of substantial anchor
```

### Scenario 3: Short Curve Too Far from Substantial Anchor
```
Curve A: 10 minutes (short, 5-15 min range)
Curve B: 20 minutes (substantial anchor, ≥15 min)
Gap: 90 minutes (1.5 hours, > 1 hour half merge distance)

Result: Curve A filtered out, Curve B kept as standalone
Reason: Short curve beyond half merge distance, no merging occurs
```

### Scenario 4: Multiple Short Curves Merged Together
```
Curve A: 8 minutes (short, 5-15 min range)
Curve B: 12 minutes (short, 5-15 min range)
Gap: 45 minutes (0.75 hours, < 1 hour half merge distance)

Result: Merged into 65-minute curve, but filtered out
Reason: No substantial anchor curve present (both <15 min)
```

### Scenario 5: Short Standalone Curve
```
Curve A: 10 minutes (short, 5-15 min range)
Nearest curve: 90 minutes away (1.5 hours, > 1 hour half merge distance)

Result: Filtered out (no merging possible)
Reason: Beyond half merge distance for short curves, no anchor available
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
| `merge_curves_within_duration` | 2 hours | Maximum gap between substantial curves (≥15 min) to consider for merging |
| `curve_minutes_limit` | 24 hours | Maximum duration for a merged curve |
| Blip curve threshold | 5 minutes | Minimum curve duration to consider |
| Short curve threshold | 15 minutes | Minimum duration for standalone curves |
| Short curve merge distance | 1 hour | Half the configured merge distance for curves 5-15 minutes |

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

