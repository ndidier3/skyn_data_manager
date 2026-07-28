"""
Phase 1 — Process (CohortExample skeleton)

Loop subjects, run process_and_analyze_data(), and save one pickle (.sdp)
per subject under Inputs/Skyn_Data_PROCESSED/{COHORT}/.

Copy this folder to App/SDM/Scripts/{YourCohort}/, rename settings, and
point paths at your raw data before running.
"""

from pathlib import Path

from App.SDM.Run.process_many import process_and_analyze_data
from App.SDM.Scripts.CohortExample.cohort_example_settings import (
    curve_attrs,
    day_attrs,
    event_attrs,
    gaps_and_non_wear_attrs,
    smooth_and_impute_attrs,
)

# ---------------------------------------------------------------------------
# Paths — resolved from this file so the script works locally and on cluster
# ---------------------------------------------------------------------------
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parents[4]  # .../Scripts/CohortExample/process → repo root

cohort_name = 'CohortExample'
data_input_folder = project_root / 'Inputs' / 'Skyn_Data_RAW' / cohort_name
# Processed .sdp files are written under:
#   Inputs/Skyn_Data_PROCESSED/{cohort_name}/

# Optional: restrict to specific subjects (None = all in data_input_folder)
# subids_to_process = None  # e.g. [1001, 1002]

print(f'Project root: {project_root}')
print(f'Raw input:    {data_input_folder}')
print(f'Cohort:       {cohort_name}')

# ---------------------------------------------------------------------------
# Process pipeline
# Toggle arguments to match the stage you are running.
# First pass from raw: gaps/non-wear + smooth/impute True, use_prior_save False.
# Later curve/day-only pass: those False, use_prior_save True, identify_curves True.
# ---------------------------------------------------------------------------
process_and_analyze_data(
    str(project_root),
    str(data_input_folder),
    cohort_name,
    use_prior_save=False,
    adjust_for_gaps_and_non_wear=True,
    smooth_and_impute=True,
    analyze_days=True,
    compute_curve_threshold=True,
    identify_curves=True,
    include_raw_curves=False,
    match_events_to_curves=False,  # set True and configure event_attrs if needed
    filter_by_study_dates=False,   # set True when study-date metadata is available
    gaps_and_non_wear_attrs=gaps_and_non_wear_attrs,
    smooth_and_impute_attrs=smooth_and_impute_attrs,
    day_attrs=day_attrs,
    curve_attrs=curve_attrs,
    event_attrs=event_attrs,
    # subids_to_process=subids_to_process,
)

print(f'\nProcess complete. Processed files: '
      f'{project_root / "Inputs" / "Skyn_Data_PROCESSED" / cohort_name}')
