import pandas as pd
from App.SDM.Run.process_many import *
from App.SDM.Analysis.curveFeatures import curveFeatures
from App.SDM.Scripts.Test.test_settings import (
    smooth_and_impute_attrs,
    curve_attrs,
    day_attrs,
    gaps_and_non_wear_attrs
)

# Path settings
project_root = '/users/ndidier/SDM/skyn_data_manager'
data_input_folder = f'{project_root}/Inputs/Skyn_Data_RAW/TestData'
processed_data_folder = f'{project_root}/Inputs/Skyn_Data_PROCESSED/TestData'
cohort_name = 'Test'

process_and_analyze_data(
    project_root, data_input_folder, cohort_name,
    use_prior_save=False,
    adjust_for_gaps_and_non_wear=True,
    smooth_and_impute=True,
    analyze_days=True,
    analyze_events=False,
    identify_curves=True,
    match_events_to_curves=False,
    curve_attrs=curve_attrs,
    smooth_and_impute_attrs=smooth_and_impute_attrs,
    day_attrs=day_attrs,
    gaps_and_non_wear_attrs=gaps_and_non_wear_attrs
)

from datetime import datetime
today = datetime.today().strftime('%m.%d.%Y')

# Initialize curveFeatures with processed data and settings
features = curveFeatures(processed_data_folder,
                        smooth_and_impute_attrs=smooth_and_impute_attrs,
                        curve_attrs=curve_attrs)
features.run_stats()
features.export_workbook_curves(f'{project_root}/Results/{cohort_name}/{cohort_name}_curve_stats_{today}.xlsx')
