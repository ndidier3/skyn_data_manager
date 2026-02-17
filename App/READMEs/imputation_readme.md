TAC IMPUTATION PROCESS
======================

STEP ONE: EXPAND IMPUTATION CANDIDATES TO INCLUDE PROXIMAL LOW-QUALITY DATA
============================================================================
An imputation candidate is a slice of data considered for imputation. It consists of a low-quality interval (consecutive rows with any of: missing data, non-wear, jumps, plummets, or extreme negatives) plus data labeled *proximal low-quality* — data that may be affected by quality issues but are not themselves labeled low-quality (readings just before/after a low-quality interval, and between nearby adjacent low-quality intervals).

**Per low-quality region (indices n_start to n_end inclusive):**

1. **Region length:** Region Length = (n_end − n_start + 1) (number of readings, inclusive).

2. **Extension length:** Set Extension Length as follows:
   - If Region Length &lt; 4: Extension Length = 3 [min]
   - If Region Length &gt; 80: Extension Length = 15 [max]
   - Else: Extension Length = 3 + round(Region Length / 7) [linear scaling; implementation caps at 15, reached at region length ≥ 84]

3. **Proximal labeling (before/after):**
   - Label as *proximal low-quality* the readings from index (n_start − Extension Length) through (n_start − 1) — i.e., Extension Length readings before the region.
   - Label as *proximal low-quality* the readings from index (n_end + 1) through (n_end + Extension Length) — i.e., Extension Length readings after the region.

**Adjacent imputation candidates (after the above extensions):**

For each pair of adjacent imputation candidates (first region R1, second region R2), the lengths used below are the *extended* candidate lengths (including proximal extensions).

4. **Combined length:** Combined Region Length = (R1 length + R2 length) in number of readings.

5. **Gap between regions:** Region Distance = number of readings between the two regions = (R2 start index − R1 end index − 1).

6. **Region distance threshold:**
   - If Combined Region Length ≤ 10: Region Distance Threshold = 10 [min]
   - If Combined Region Length ≥ 60: Region Distance Threshold = 20 [max]
   - Else: Region Distance Threshold = 10 + (Combined Region Length − 10) × (10/50) [linear scaling from 10 to 20]

7. **Merge:** If Region Distance ≤ Region Distance Threshold, label all readings between the two low-quality regions as *proximal low-quality* (effectively merging the two candidates into one).

Proximal indices are never part of the original low-quality index sets (gaps, non-wear, jumps, plummets, extreme negatives); they are only the extended and between-region readings added by this step.

STEP TWO: EVALUATE WHETHER CONDITIONS ARE SUFFICIENT FOR CONDUCTING IMPUTATION
==============================================================================
Each low-quality region is a consecutive set of low-quality readings, which can include any mix of gap data, non-wear, jumps, plummets, extreme negatives, and proximal low-quality. For each such region, the data *before* and *after* the region are evaluated to decide whether and how to impute.

**Outcomes:**

1. **Sufficient high-quality data surrounding the region**  
   If there is enough high-quality data before and after the region (see IMPUTATION REQUIREMENTS below), a Gaussian Process model is fitted to that surrounding data and used to impute TAC throughout the low-quality region.

2. **Insufficient surrounding data, but region is only extreme negative and proximal low-quality**  
   If the region contains no gaps, non-wear, jumps, or plummets — only extreme negatives and/or proximal low-quality — then TAC is imputed with zero throughout the region.

3. **Otherwise**  
   The low-quality data is left uncorrected. If an uncorrected low-quality region overlaps with a TAC curve, the curve is likely flagged downstream.

Region length is also enforced: regions longer than 180 minutes are not imputed (see LIMITATIONS / IMPUTATION REQUIREMENTS). The detailed checks (training windows, minimum high-quality minutes, quality percent, and reason codes for no imputation) are given in the PSEUDOCODE and IMPUTATION REQUIREMENTS sections below.

**Pseudocode: determining whether training data is sufficient**

For a low-quality region from `region_start` to `region_end` (inclusive), training data is considered sufficient for GPR imputation if and only if *both* the before-window and the after-window pass the checks below.

    region_length = (region_end - region_start + 1)

    // Training windows (up to 60 minutes before and 60 minutes after the region)
    training_data_start = max(0, region_start - 60)
    training_data_end   = min(region_end + 60 + 1, len(df) - 1)

    train_data_before = df[training_data_start : region_start]           // exclusive of region_start
    train_data_after  = df[region_end + 1 : training_data_end]            // exclusive of region_end+1

    min_training_data = max(10, round(region_length / 6))

    // High-quality = readings not in any low-quality set (gaps, non-wear, jumps, plummets, extreme negatives, proximal low-quality)
    high_quality_before = train_data_before with all low-quality indices removed
    high_quality_after  = train_data_after  with all low-quality indices removed

    high_quality_minutes_before = len(high_quality_before)
    high_quality_minutes_after  = len(high_quality_after)

    high_quality_percent_before = high_quality_minutes_before / len(train_data_before)   // 0 if train_data_before is empty
    high_quality_percent_after  = high_quality_minutes_after  / len(train_data_after)    // 0 if train_data_after is empty

    training_data_before_valid = (high_quality_minutes_before > min_training_data) AND (high_quality_percent_before > 0.5)
    training_data_after_valid  = (high_quality_minutes_after  > min_training_data) AND (high_quality_percent_after  > 0.5)

    training_data_sufficient = training_data_before_valid AND training_data_after_valid

If `training_data_sufficient` is true, the region is eligible for Gaussian Process imputation (subject to the 180-minute length check). If false, the region may still receive zero imputation when it contains only extreme negative and proximal low-quality data; otherwise it is not imputed.

LOW-QUALITY REGION DEFINITION:
==============================
A low-quality region consists of consecutive stretches of data containing one or more of the 6 types of low-quality data.

Low-Quality Data Types Identified:
==============================

1. Recording GAPS (Null Values)
2. NON-WEAR PERIODS
3. JUMPS (Signal Artifacts)  
   • Rule Set: Detects >100 μg/L single-minute increases, relative surges >90% of the local 2-hour peak (when ≥40 μg/L), and multi-minute spikes where a 10-minute window shares the hour-peak, rises >30 μg/L per minute from its start, and is followed by a pronounced post-peak drop. The 10-minute check tolerates up to eight NaNs provided at least two readings remain.
4. PLUMMETS (Signal Artifacts)
5. EXTREME NEGATIVE VALUES
6. PROXIMAL LOW-QUALITY

PSEUDOCODE:
===========

For each low-quality region:
    Calculate Region Length = (region_end - region_start + 1)
    
    If region_length > 180:
        Record imputation attempt (was_imputed=False, reason="region_too_long")
        Continue to next region
    
    Calculate training data windows:
        training_data_start = max(0, region_start - 60)
        training_data_end = min(region_end + 60 + 1, len(df) - 1)
    
    Extract training data:
        train_data_before = df[training_data_start:region_start]
        train_data_after = df[region_end+1:training_data_end]
    
    Calculate minimum training data required:
        min_training_data = max(10, round(region_length / 6))
    
    Assess training data quality:
        high_quality_before = filter_high_quality_data(train_data_before)
        high_quality_after = filter_high_quality_data(train_data_after)
        
        high_quality_minutes_before = len(high_quality_before)
        high_quality_minutes_after = len(high_quality_after)
        
        high_quality_percent_before = high_quality_minutes_before / len(train_data_before)
        high_quality_percent_after = high_quality_minutes_after / len(train_data_after)
    
    Check training data validity:
        training_data_before_valid = (high_quality_minutes_before > min_training_data) AND (high_quality_percent_before > 0.5)
        training_data_after_valid = (high_quality_minutes_after > min_training_data) AND (high_quality_percent_after > 0.5)
    
    Decision: Impute or not?
        If training_data_before_valid AND training_data_after_valid:
            Strategy A: Gaussian Process Regression
                Generate predictions using GPR model
                Apply imputation: df[region_start:region_end+1, 'TAC'] = predictions
                Set imputed flag: df[region_start:region_end+1, 'imputed'] = 1
                Label imputation reasons
                Record imputation attempt (was_imputed=True)
                Print "IMPUTED (Using Gaussian Process for low-quality region)"
        
        Else:
            Check if region contains only extreme negative and proximal low quality:
                If NOT has_other_low_quality:
                    Strategy B: Zero Imputation
                        Set TAC = 0: df[region_start:region_end+1, 'TAC'] = 0
                        Set imputed flag: df[region_start:region_end+1, 'imputed'] = 1
                        Label imputation reasons
                        Record imputation attempt (was_imputed=True)
                        Print "IMPUTED (Zeros during all-negative region)"
                
                Else:
                    Strategy C: No Imputation
                        Determine reason for no imputation
                        Record imputation attempt (was_imputed=False, reason=reason)
                        Print "NOT IMPUTED"
    

LIMITATIONS:
============
- Maximum imputation region length: 180 minutes
- Requires sufficient high-quality training data (minimum 10 minutes, 50% quality)
- GPR imputation may not capture complex temporal patterns
- Zero imputation for extreme negative values assumes no alcohol consumption

IMPUTATION REQUIREMENTS:
==========================
- Low-Quality Region length: ≤ 180 minutes (3 hours) maximum
- Training data before region: minimum 10 minutes of high-quality data, ≥50% quality
  * High-quality data excludes all 6 types of low-quality data (gaps, non-wear, jumps, plummets, extreme negatives, proximal low-quality)
  * Quality percentage calculated as: (high_quality_minutes / total_training_window_minutes) ≥ 0.5
  * Training window extends 60 minutes before the low-quality region start
- Training data after region: minimum 10 minutes of high-quality data, ≥50% quality
  * Same criteria as before region
  * Training window extends 60 minutes after the low-quality region end
- Training window: 60 minutes before and 60 minutes after each low-quality region
  * Total training window = 120 minutes (60 before + 60 after)
  * If region is near dataset boundaries, training window adjusts accordingly
- Minimum training data scales with region length: max(10, round(region_length / 6))
  * Base requirement: 10 minutes minimum
  * For longer regions: additional training data required proportionally
  * Example: 60-minute region requires max(10, round(60/6)) = max(10, 10) = 10 minutes
  * Example: 120-minute region requires max(10, round(120/6)) = max(10, 20) = 20 minutes

