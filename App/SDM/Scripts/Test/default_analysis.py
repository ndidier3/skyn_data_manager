import pandas as pd
from SDM.Run.process_many import *
from SDM.Analysis.curveFeatures import curveFeatures

user_root = '/Users/nathandidier/Desktop/Repositories/'
project_root = f'{user_root}/skyn_data_manager' 
data_input_folder = f'{project_root}/Inputs/Skyn_Data_RAW/TestData'
processed_data_folder = f'{project_root}/Inputs/Skyn_Data_PROCESSED/TestData'
cohort_name = 'Test'

smooth_and_impute_attrs={
  'reset_tac': True,
  'median_smooth': True,
  'impute_gaps': True,
  'impute_non_wear': True,
  'impute_jumps': True,
  'impute_plummets': True,
  'savgol_smooth': False,
  'export_excel': False #if you want to export the processed biosensor data 
}

curve_attrs = {
  'curve_flags': {
    'flag_extreme_rise_rate': {
      'rise_rate_cutoff': 430
    },
    'flag_incomplete_curve_start': {
      'percent_cutoff': 0.5
    },
    'flag_incomplete_curve_end': {
      'percent_cutoff': 0.5
    },
    'flag_flatlined_peak': {
      'flatline_percent_cutoff': 0.20,
      'peak_above': 350
    },
    'flag_sub_negative_10_curve': {
      'percent_cutoff': 0.20,
      'duration_cutoff': 1.0,
    },
    'flag_unimputed_low_quality_percent': {
      'percent_cutoff': 0.20 #maybe raise this
    },
    'flag_too_much_imputation': { 
      'percent_cutoff': 0.4 #maybe raise this
    },
    'flag_low_quality': {},
    'flag_device_non_wear_curve': {},
    'flag_device_worn_duration_curve': {},
    'flag_low_flat_curves': {},
    'flag_curve_start_too_late': {},
    'flag_device_turned_on_percent_curve': {},
    'flag_starting_non_wear_perc_curve': {},
    'flag_ending_non_wear_perc_curve': {}
  }, 
  'periphery_flags': { #maybe raise these
    'flag_sub_negative_10_periphery': {'percent_cutoff': 0.80, 'duration_cutoff': 2},
    'flag_sub_negative_20_periphery': {'percent_cutoff': 0.40, 'duration_cutoff': 1.5},
    'flag_sub_negative_40_periphery': {'percent_cutoff': 0.20, 'duration_cutoff': 0.5},
    'flag_non_wear_periphery': {'percent_cutoff': 0.40}, #maybe raise
  },
  'periphery_buffer_before': 2, 
  'periphery_buffer_after': 2,
  'merge_curves_within_duration': 1 #set to 0 to not merge
}

# dictionary for determining day level times
day_attrs = {
  'day_start_hour': 10, 
  'make_graphs': True
}

process_and_analyze_data(
  project_root, data_input_folder, cohort_name,
  curve_threshold = 'auto', #if you want to set this at a constant number, change this to the number of your choice (e.g., 5 or 10)
  use_prior_save = False,
  adjust_for_gaps_and_non_wear = True, 
  smooth_and_impute = True, 
  analyze_days = True, 
  analyze_events = False,
  identify_curves = True,
  match_events_to_curves=False,
  curve_attrs=curve_attrs,
  smooth_and_impute_attrs=smooth_and_impute_attrs,
  day_attrs=day_attrs
)

from datetime import datetime
today = datetime.today().strftime('%m.%d.%Y')

features = curveFeatures(processed_data_folder)
features.run_stats()
features.export_workbook_curves(f'{project_root}/Results/{cohort_name}/{cohort_name}_curve_stats_{today}.xlsx')
