TAC IMPUTATION PROCESS
======================

OVERVIEW:
Following proximal low-quality labeling, all low-quality regions have been identified. Each low-quality region consist of a consecutive set of low-quality readings, which can include a mix of gap data, non-wear, jumps, plummets, extreme negative, and proximal low-quality. For each low-quality region, the data before and after it are evaluated. If there is sufficient high-quality data surrounding the low-quality region, a Gaussian Process model will be fitted to the surrounding data and used to impute TAC throughout the low-quality region. If there is insufficient data but the low-quality region consists of only extreme negative data and proximal low-quality, then TAC is imputed with zero throughout the region. Otherwise, the low-quality data is left uncorrected; if an uncorrected low-quality region overlaps with a TAC curve, the curve is likely flagged.

LOW-QUALITY REGION DEFINITION:
==============================
A low-quality region consists of consecutive stretches of data containing one or more of the 6 types of low-quality data.

Low-Quality Data Types Identified:
==============================

1. Recording GAPS (Null Values)
2. NON-WEAR PERIODS
3. JUMPS (Signal Artifacts)
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

