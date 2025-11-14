"""
Test Analysis Script with Drinking Detection

This script processes SKYN data and performs curve-level and day-level analysis
with automated drinking curve identification based on quality and shape criteria.

Drinking Detection Implementation:
- Identifies curves likely to represent drinking events using:
  1. Two-phase high-quality duration threshold:
     Phase 1 (30-60 min): 9 non-HQ minutes allowed per 15-min block
     Phase 2 (60+ min): 5 additional HQ minutes required per 15-min block
  2. Not flagged as flat curve (FLAG_flat_curve == 0)
  3. Has complete rise phase (FLAG_incomplete_curve_start_curve == 0) - ONLY for curves < 1 hour
- Creates DRINKING_PRED column for curves
- Creates predicted_drinking_day_by_curve_start column for days (1 if drinking curve starts in day)
- Exports separate visualization tabs for drinking vs. non-drinking curves/days
"""

import pandas as pd
import os
from pathlib import Path
from App.SDM.Run.process_many import *
from App.SDM.Analysis.curveFeatures import curveFeatures
from App.SDM.Analysis.dayFeatures import dayFeatures
from App.SDM.Scripts.Test.test_settings import (
    smooth_and_impute_attrs,
    curve_attrs,
    day_attrs,
    gaps_and_non_wear_attrs,
    event_attrs
)

# gaps_and_non_wear_attrs['export_excel'] = True
smooth_and_impute_attrs['export_excel'] = False

# Dynamic path resolution - works regardless of where project is cloned
# Get the project root by going up from this script's location
script_dir = Path(__file__).parent.absolute()
project_root = script_dir.parent.parent.parent.parent.absolute()

# Alternative method using os.path (more compatible with older Python versions)
# script_dir = os.path.dirname(os.path.abspath(__file__))
# project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(script_dir))))

print(f"Script directory: {script_dir}")
print(f"Project root: {project_root}")

# Path settings
data_input_folder = project_root / 'Inputs' / 'Skyn_Data_RAW' / 'TestData'
processed_data_folder = project_root / 'Inputs' / 'Skyn_Data_PROCESSED' / 'TestData'
cohort_name = 'Test'

# Process and analyze data with enhanced settings matching ARC analysis approach
process_and_analyze_data(
    project_root, data_input_folder, cohort_name,
    use_prior_save=False,  # Load previously processed data if available
    adjust_for_gaps_and_non_wear=True,  # Remove gaps and non-wear periods
    smooth_and_impute=True,  # Smooth signals and impute missing values
    analyze_days=True,  # Perform day-level analysis
    compute_curve_threshold=True,  # Auto-compute curve detection threshold
    identify_curves=True,  # Detect drinking curves in the data
    include_raw_curves=False,  # Compute curve features made from non-corrected data
    match_events_to_curves=False,  # Match drinking events to detected curves
    gaps_and_non_wear_attrs=gaps_and_non_wear_attrs,
    smooth_and_impute_attrs=smooth_and_impute_attrs,
    day_attrs=day_attrs,
    curve_attrs=curve_attrs,
    event_attrs=event_attrs
)

from datetime import datetime
today = datetime.today().strftime('%m.%d.%Y')

# Initialize curveFeatures with processed data and settings
curves = curveFeatures(processed_data_folder,
                        smooth_and_impute_attrs=smooth_and_impute_attrs,
                        curve_attrs=curve_attrs)
output_dir = project_root / 'Results' / cohort_name

# Identify drinking curves using quality and shape criteria
print(f"\nIdentifying drinking curves...")
curves.identify_drinking_curves()

# Run statistics
curves.run_stats()
curves.count_curve_flags()
curves.compute_imputation_stats()

# Export curve workbook with drinking prediction splits
curves.export_workbook_curves(
    str(project_root / 'Results' / cohort_name / f'{cohort_name}_curve_stats_{today}.xlsx'),
    split_plots_by='drinking_pred'  # Split plots by drinking prediction
)

# Day-level analysis using dayFeatures
print(f"\nRunning day-level analysis...")
day_features_calculator = dayFeatures(processed_data_folder)
day_features_calculator.compute_low_quality_stats()  # Computes stats and adds to day_stat_frames

# Add curve overlap detection using curve features from the curves object
# This uses the DRINKING_PRED column to create:
#   - predicted_drinking_curve_overlap (any overlap)
#   - predicted_drinking_day_by_curve_start (curve starts in day)
day_features_calculator.add_curve_overlap_detection(curves.curve_features)

# Export day workbook with drinking day splits
day_features_calculator.export_workbook_days(
    str(project_root / 'Results' / cohort_name / f'{cohort_name}_day_stats_{today}.xlsx'),
    split_plots_by='drinking_by_start'  # Split plots by days where drinking curves start
)

print(f"\nTest analysis complete!")
print(f"Results exported to: {project_root / 'Results' / cohort_name}")
print(f"- {cohort_name}_curve_stats_{today}.xlsx (curve-level stats with 'Drinking Curves' and 'Non-Drinking Curves' tabs)")
print(f"- {cohort_name}_day_stats_{today}.xlsx (day-level stats with 'Drinking Days (by start)' and 'Non-Drinking Days (by start)' tabs)")
print(f"\nDrinking day classification:")
print(f"  - Days classified as 'Drinking Days' if a predicted drinking curve STARTS within the day")
print(f"\nDrinking detection criteria:")
print(f"  - High-quality duration > required threshold (two-phase algorithm):")
print(f"    Phase 1 (30-60 min): 9 non-HQ minutes allowed per 15-min block")
print(f"    Phase 2 (60+ min): 5 additional HQ minutes required per 15-min block")
print(f"  - FLAG_flat_curve == 0 (not flat)")
print(f"  - FLAG_incomplete_curve_start_curve == 0 (complete rise phase) - ONLY for curves < 1 hour")
