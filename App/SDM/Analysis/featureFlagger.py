import numpy as np
import pandas as pd

class featureFlagger():
  """
  Takes event features; adds flags (1=flagged) or validation (1=valid)
  """
  def __init__(self, features: pd.DataFrame, search_flag_selections = {}, periphery_flag_selections = {}, curve_flag_selections = {}):
    self.ftrs = features
    self.search_flag_selections = {
      'flag_sub_negative_10_search': {},
      'flag_sub_negative_20_search': {},
      'flag_sub_negative_40_search': {},
      'flag_non_wear_duration_search': {},
    }
    self.search_flag_selections.update(search_flag_selections)

    self.periphery_flag_selections = {
      'flag_sub_negative_10_periphery': {},
      'flag_sub_negative_20_periphery': {},
      'flag_sub_negative_40_periphery': {},
      'flag_non_wear_periphery': {},
    }
    self.periphery_flag_selections.update(periphery_flag_selections)

    self.curve_flag_selections = {
      'flag_device_non_wear_curve': {},
      'flag_device_worn_duration_curve': {},
      'flag_flatlined_peak': {},
      'flag_low_flat_curves': {},
      'flag_curve_start_too_late': {},
      'flag_sub_negative_10_curve': {},
      'flag_device_turned_on_percent_curve': {},
      'flag_starting_non_wear_perc_curve': {},
      'flag_incomplete_curve_start': {},
      'flag_extreme_rise_rate': {},
      'flag_ending_non_wear_perc_curve': {},
      'flag_incomplete_curve_end': {},
      'flag_low_quality': {}
    }
    self.curve_flag_selections.update(curve_flag_selections)

  
  """ Flags will be based on cutoffs for continuous quality features """
  def flag_data_above_cutoff(self, column, cutoff, flag_name):
    self.ftrs[flag_name] = np.where(self.ftrs[column].isna(), np.nan, (self.ftrs[column] > cutoff).astype(int))

  def flag_data_below_cutoff(self, column, cutoff, flag_name):
    self.ftrs[flag_name] = np.where(self.ftrs[column].isna(), np.nan, (self.ftrs[column] < cutoff).astype(int))
  
  def flag_data_above_cutoffs(self, column1, cutoff1, column2, cutoff2, flag_name):
    self.ftrs[flag_name] = np.where(
      self.ftrs[[column1, column2]].isna().any(axis=1), 
      np.nan, 
      ((self.ftrs[column1] > cutoff1) & (self.ftrs[column2] > cutoff2)).astype(int)
    )
  
  def flag_data_above_one_of_two_cutoffs(self, column1, cutoff1, column2, cutoff2, flag_name):
    self.ftrs[flag_name] = np.where(
        self.ftrs[[column1, column2]].isna().any(axis=1), 
        np.nan, 
        ((self.ftrs[column1] > cutoff1) | (self.ftrs[column2] > cutoff2)).astype(int)
    )

  def flag_data_below_cutoffs(self, column1, cutoff1, column2, cutoff2, flag_name):
    self.ftrs[flag_name] = np.where(
      self.ftrs[[column1, column2]].isna().any(axis=1), 
      np.nan, 
      ((self.ftrs[column1] < cutoff1) & (self.ftrs[column2] < cutoff2)).astype(int)
    )

  def flag_data_below_one_of_two_cutoffs(self, column1, cutoff1, column2, cutoff2, flag_name):
    self.ftrs[flag_name] = np.where(
        self.ftrs[[column1, column2]].isna().any(axis=1), 
        np.nan, 
        ((self.ftrs[column1] < cutoff1) | (self.ftrs[column2] < cutoff2)).astype(int)
    )

  def flag_data_below_or_above_cutoffs(self, column1, below_cutoff, column2, above_cutoff, flag_name):
    self.ftrs[flag_name] = np.where(
      self.ftrs[[column1, column2]].isna().any(axis=1), 
      np.nan, 
      ((self.ftrs[column1] < below_cutoff) | (self.ftrs[column2] > above_cutoff)).astype(int)
    )

  def flag_data_below_and_above_cutoffs(self, column1, below_cutoff, column2, above_cutoff, flag_name):
    self.ftrs[flag_name] = np.where(
      self.ftrs[[column1, column2]].isna().any(axis=1), 
      np.nan, 
      ((self.ftrs[column1] < below_cutoff) & (self.ftrs[column2] > above_cutoff)).astype(int)
    )
  """ Periphery Quality Assessment """
  def flag_sub_negative_10_periphery(self, percent_cutoff, duration_cutoff = None):
    if duration_cutoff:
      flag_column_name = f'FLAG_sub_negative_10_PERIPHERY_>{percent_cutoff*100}%_>{duration_cutoff}hrs'
      self.flag_data_above_one_of_two_cutoffs(
        'sub_negative_10_percent_PERIPHERY', percent_cutoff, 'sub_negative_10_duration_PERIPHERY', duration_cutoff, flag_column_name
      )
    else:
      flag_column_name = f'FLAG_sub_negative_10_PERIPHERY_>{percent_cutoff*100}%'
      self.flag_data_above_cutoff(
        'sub_negative_10_percent_PERIPHERY', percent_cutoff, flag_column_name
      )
    return flag_column_name

  def flag_sub_negative_20_periphery(self, percent_cutoff, duration_cutoff = None):
    if duration_cutoff:
      flag_column_name = f'FLAG_sub_negative_20_PERIPHERY_>{percent_cutoff*100}%_>{duration_cutoff}hrs'
      self.flag_data_above_one_of_two_cutoffs(
        'sub_negative_20_percent_PERIPHERY', percent_cutoff, 'sub_negative_20_duration_PERIPHERY', duration_cutoff, flag_column_name
      )
    else:
      flag_column_name = f'FLAG_sub_negative_20_PERIPHERY_>{percent_cutoff*100}%'
      self.flag_data_above_cutoff(
        'sub_negative_20_percent_PERIPHERY', percent_cutoff, flag_column_name
      )
    return flag_column_name

  def flag_sub_negative_40_periphery(self, percent_cutoff, duration_cutoff = None):
    if duration_cutoff:
      flag_column_name = f'FLAG_sub_negative_40_PERIPHERY_>{percent_cutoff*100}%_>{duration_cutoff}hrs'
      self.flag_data_above_one_of_two_cutoffs(
        'sub_negative_40_percent_PERIPHERY', percent_cutoff, 'sub_negative_40_duration_PERIPHERY', duration_cutoff, flag_column_name
      )
    else:
      flag_column_name = f'FLAG_sub_negative_40_PERIPHERY_>{percent_cutoff*100}%_'
      self.flag_data_above_cutoff(
        'sub_negative_40_percent_PERIPHERY', percent_cutoff, flag_column_name
      )
    return flag_column_name

  def flag_non_wear_periphery(self, percent_cutoff):
    flag_column_name = f'FLAG_non_wear_PERIPHERY_>{percent_cutoff*100}%'
    # percent of wear will be assessed, so percent of non-wear needs to be flipped
    percent_cutoff = 1-percent_cutoff 
    self.flag_data_below_cutoff(
      'device_worn_percent_PERIPHERY', percent_cutoff, flag_column_name
    )
    return flag_column_name

  """ Whole Curve Qaulity Assessment """
  def flag_device_non_wear_curve(self, percent_cutoff, percent_consecutive_cutoff):
    #if flagged, all curve features invalid
    flag_column_name = f'FLAG_device_non_wear_CURVE_>{(1-percent_cutoff)*100}%_>{percent_consecutive_cutoff*100}%'
    self.flag_data_below_or_above_cutoffs(
      'device_worn_percent_CURVE', percent_cutoff, 'consecutive_non_wear_percent_CURVE', percent_consecutive_cutoff,  flag_column_name
    )
    return flag_column_name

  def flag_device_worn_duration_curve(self, duration_cutoff):
    #if flagged, all curve features invalid
    flag_column_name = f'FLAG_device_worn_duration_CURVE_<{duration_cutoff}'
    self.flag_data_below_cutoff(
      'device_worn_percent_CURVE', duration_cutoff, flag_column_name
    )
    return flag_column_name

  def flag_flatlined_peak(self, flatline_percent_cutoff, peak_above):
    flag_column_name = f'FLAG_flatlined_peak>{flatline_percent_cutoff*100}%flatline_peak>{peak_above}'
    self.flag_data_above_cutoffs(
      'flatlined_percent_CURVE', flatline_percent_cutoff, 'peak_CURVE', peak_above, flag_column_name
    )
    return flag_column_name

  def flag_low_flat_curves(self, peak_below, peak_to_curve_duration_ratio):
    flag_column_name = f'FLAG_flat_low_peak<{peak_below}peak_to_curve_duration_ratio>{peak_to_curve_duration_ratio}'
    self.ftrs['peak_to_curve_duration_ratio'] = self.ftrs['peak_CURVE'] / self.ftrs['duration_CURVE']
    self.flag_data_below_and_above_cutoffs(
      'peak_CURVE', peak_below, 'peak_to_curve_duration_ratio', peak_to_curve_duration_ratio, flag_column_name
    )
    self.ftrs.drop(['peak_to_curve_duration_ratio'], inplace=True)

    return flag_column_name

  def flag_curve_start_too_late(self, search_and_curve_delay = 6, peak_below = 20):
    flag_column_name = f'FLAG_search_and_curve_delay>{search_and_curve_delay}hrs_peak<{peak_below}'
    self.ftrs['begin_CURVE'] = pd.to_datetime(self.ftrs['begin_CURVE'])
    self.ftrs['begin_SEARCH'] = pd.to_datetime(self.ftrs['begin_SEARCH'])
    self.ftrs['search_and_curve_delay'] = (
      (self.ftrs['begin_CURVE'] - self.ftrs['begin_SEARCH'])
      .dt.total_seconds()
      .div(3600)  # Equivalent to / 3600
      .where(self.ftrs[['begin_CURVE', 'begin_SEARCH']].notna().all(axis=1))  # Keep NaN if either is NaN
    )
    self.flag_data_below_and_above_cutoffs(
      'peak_CURVE', peak_below, 'search_and_curve_delay', search_and_curve_delay, flag_column_name
    )
    return flag_column_name
  
  def flag_sub_negative_10_curve(self, percent_cutoff, duration_cutoff):
    flag_column_name = f'FLAG_sub_negative_10_CURVE_>{percent_cutoff*100}%_>{duration_cutoff}'
    self.flag_data_above_one_of_two_cutoffs(
      'sub_negative_10_percent_CURVE', percent_cutoff, 'sub_negative_10_duration_CURVE', duration_cutoff, flag_column_name
    )
    return flag_column_name

  def flag_device_turned_on_percent_curve(self, percent_cutoff = 0.60):
    flag_column_name = f'FLAG_device_turned_on_percent_CURVE_<{percent_cutoff}'
    self.flag_data_below_cutoff(
      'device_turned_on_percent_CURVE', percent_cutoff, flag_column_name
    )
    return flag_column_name

  def flag_unimputed_low_quality_percent(self, percent_cutoff = 0.25):
    flag_column = f'FLAG_unimputed_low_quality_percent_CURVE_>{percent_cutoff}'
    self.flag_data_above_cutoff(
      'unimputed_low_quality_percent_CURVE', percent_cutoff, flag_column
    )
    return flag_column

  def flag_too_much_imputation(self, percent_cutoff = 0.6):
    flag_column = f'FLAG_imputed_percent_CURVE_>{percent_cutoff}'
    self.flag_data_above_cutoff(
      'imputed_percent_CURVE', percent_cutoff, flag_column
    )
    return flag_column

  def flag_low_quality(self, percent_cutoff = 0.4):
    flag_column = f'FLAG_low_quality_percent_CURVE_>{percent_cutoff}'
    self.flag_data_above_cutoff(
      'low_quality_percent_CURVE', percent_cutoff, flag_column
    )
    return flag_column

  """ Rise Quality Assessment """
  def flag_starting_non_wear_perc_curve(self, percent_cutoff = 0.5):
    flag_column_name = f'FLAG_non_wear_CURVE_start_>{percent_cutoff}'
    self.flag_data_above_cutoff(
      'starting_non_wear_perc_CURVE', percent_cutoff, flag_column_name
    )
    return flag_column_name

  def flag_incomplete_curve_start(self, percent_cutoff=0.5):
    flag_column_name = f'FLAG_rise_completion_CURVE_<{percent_cutoff}'
    self.flag_data_below_and_above_cutoffs(
      'rise_complete_perc_CURVE', percent_cutoff, 'peak_CURVE', 30, flag_column_name
    )
    return flag_column_name

  def flag_extreme_rise_rate(self, rise_rate_cutoff=430):
    flag_column_name = f'FLAG_rise_rate_CURVE_>{rise_rate_cutoff}'
    self.flag_data_above_cutoff(
      'rise_rate_CURVE', rise_rate_cutoff, flag_column_name
    )
    return flag_column_name

  """ Fall Quality Assessment """
  def flag_ending_non_wear_perc_curve(self, percent_cutoff = 0.5):
    flag_column_name = f'FLAG_non_wear_CURVE_end_>{percent_cutoff}'
    self.flag_data_above_cutoff(
      'ending_non_wear_perc_CURVE', percent_cutoff, flag_column_name
    )
    return flag_column_name

  def flag_incomplete_curve_end(self, percent_cutoff=0.5):
    flag_column_name = f'FLAG_fall_completion_CURVE_<{percent_cutoff}'
    self.flag_data_below_and_above_cutoffs(
      'fall_complete_perc_CURVE', percent_cutoff, 'peak_CURVE', 30, flag_column_name
    )
    return flag_column_name

  def validate_periphery(self, new_column, flag_columns):
    any_nan = self.ftrs[flag_columns].isna().any(axis=1)
    any_one = self.ftrs[flag_columns].eq(1).any(axis=1)
    all_zero = self.ftrs[flag_columns].fillna(0).eq(0).all(axis=1)
    self.ftrs[new_column] = np.where(
      any_nan, 0, np.where(
        any_one, 0, np.where(
          all_zero, 1, np.nan
    )))

  def validate_feature(self, new_column, flag_columns):
  
    search_valid = self.ftrs['PERIPHERY_VALID'] 

    any_nan = self.ftrs[flag_columns].isna().any(axis=1)
    any_one = self.ftrs[flag_columns].eq(1).any(axis=1)
    all_zero = self.ftrs[flag_columns].fillna(0).eq(0).all(axis=1)

    # Set new_column based on conditions and SEARCH_VALID
    self.ftrs[new_column] = np.where(
      search_valid,
        np.where(any_nan, np.nan, 
          np.where(any_one, 0, 
            np.where(all_zero, 1, 
              np.nan
        ))),
      np.nan #if search invalid
    )
  
  def run_periphery_flags_and_validation(self):
    self.periphery_flags = []
    
    if self.periphery_flag_selections['flag_sub_negative_10_periphery']:
      flag_sub_negative_10_periphery_column = self.flag_sub_negative_10_periphery(**self.periphery_flag_selections['flag_sub_negative_10_periphery'])
      self.periphery_flags.append(flag_sub_negative_10_periphery_column)

    if self.periphery_flag_selections['flag_sub_negative_20_periphery']:
      flag_sub_negative_20_periphery_column = self.flag_sub_negative_20_periphery(**self.periphery_flag_selections['flag_sub_negative_20_periphery'])
      self.periphery_flags.append(flag_sub_negative_20_periphery_column)

    if self.periphery_flag_selections['flag_sub_negative_40_periphery']:
      flag_sub_negative_40_periphery_column = self.flag_sub_negative_40_periphery(**self.periphery_flag_selections['flag_sub_negative_40_periphery'])
      self.periphery_flags.append(flag_sub_negative_40_periphery_column)

    if self.periphery_flag_selections['flag_non_wear_periphery']:
      flag_non_wear_periphery_column = self.flag_non_wear_periphery(**self.periphery_flag_selections['flag_non_wear_periphery'])
      self.periphery_flags.append(flag_non_wear_periphery_column)
    
    self.validate_periphery('PERIPHERY_VALID', self.periphery_flags)

    return self.periphery_flags

  def run_curve_flags_and_validation(self):
    if 'PERIPHERY_VALID' not in self.ftrs.columns:
      self.ftrs['PERIPHERY_VALID'] = 1

    self.curve_feature_flags = []

    if self.curve_flag_selections['flag_device_non_wear_curve']:
      flag_device_non_wear_curve_column = self.flag_device_non_wear_curve(**self.curve_flag_selections['flag_device_non_wear_curve'])
      self.curve_feature_flags.append(flag_device_non_wear_curve_column)

    if self.curve_flag_selections['flag_device_worn_duration_curve']:
      flag_device_worn_duration_curve_column = self.flag_device_worn_duration_curve(**self.curve_flag_selections['flag_device_worn_duration_curve'])
      self.curve_feature_flags.append(flag_device_worn_duration_curve_column)

    if self.curve_flag_selections['flag_flatlined_peak']:
      flag_flatlined_percent_curve_column = self.flag_flatlined_peak(**self.curve_flag_selections['flag_flatlined_peak'])
      self.curve_feature_flags.append(flag_flatlined_percent_curve_column)

    if self.curve_flag_selections['flag_sub_negative_10_curve']:
      flag_sub_negative_10_curve_column = self.flag_sub_negative_10_curve(**self.curve_flag_selections['flag_sub_negative_10_curve'])
      self.curve_feature_flags.append(flag_sub_negative_10_curve_column)

    if self.curve_flag_selections['flag_device_turned_on_percent_curve']:
      flag_device_turned_on_percent_curve_column = self.flag_device_turned_on_percent_curve(**self.curve_flag_selections['flag_device_turned_on_percent_curve'])
      self.curve_feature_flags.append(flag_device_turned_on_percent_curve_column)

    if self.curve_flag_selections['flag_starting_non_wear_perc_curve']:
      flag_starting_non_wear_perc_column = self.flag_starting_non_wear_perc_curve(**self.curve_flag_selections['flag_starting_non_wear_perc_curve'])
      self.curve_feature_flags.append(flag_starting_non_wear_perc_column)

    if self.curve_flag_selections['flag_incomplete_curve_start']:
      flag_incomplete_curve_start_column = self.flag_incomplete_curve_start(**self.curve_flag_selections['flag_incomplete_curve_start'])
      self.curve_feature_flags.append(flag_incomplete_curve_start_column)

    if self.curve_flag_selections['flag_extreme_rise_rate']:
      flag_extreme_rise_rates_column = self.flag_extreme_rise_rate(**self.curve_flag_selections['flag_extreme_rise_rate'])
      self.curve_feature_flags.append(flag_extreme_rise_rates_column)

    if self.curve_flag_selections['flag_ending_non_wear_perc_curve']:    
      flag_ending_non_wear_perc_curve_column = self.flag_ending_non_wear_perc_curve(**self.curve_flag_selections['flag_ending_non_wear_perc_curve'])
      self.curve_feature_flags.append(flag_ending_non_wear_perc_curve_column)
    
    if self.curve_flag_selections['flag_incomplete_curve_end']:
      flag_very_incomplete_curve_end_column = self.flag_incomplete_curve_end(**self.curve_flag_selections['flag_incomplete_curve_end'])
      self.curve_feature_flags.append(flag_very_incomplete_curve_end_column)
    
    if self.curve_flag_selections['flag_curve_start_too_late']:
      flag_curve_start_too_late_column = self.flag_curve_start_too_late(**self.curve_flag_selections['flag_curve_start_too_late'])
      self.curve_feature_flags.append(flag_curve_start_too_late_column)

    if self.curve_flag_selections['flag_unimputed_low_quality_percent']:
      flag_curve_unimputed_low_quality_column = self.flag_unimputed_low_quality_percent(**self.curve_flag_selections['flag_unimputed_low_quality_percent'])
      self.curve_feature_flags.append(flag_curve_unimputed_low_quality_column)
    
    if self.curve_flag_selections['flag_too_much_imputation']:
      flag_too_much_imputation_column = self.flag_too_much_imputation(**self.curve_flag_selections['flag_too_much_imputation'])
      self.curve_feature_flags.append(flag_too_much_imputation_column)
    
    if self.curve_flag_selections['flag_low_quality']:
      flag_low_quality_column = self.flag_low_quality(**self.curve_flag_selections['flag_low_quality'])
      self.curve_feature_flags.append(flag_low_quality_column)

    self.validate_feature('CURVE_VALID', self.curve_feature_flags)
    
    return self.curve_feature_flags

  # """ Search Quality Assessment """
  # def flag_sub_negative_10_search(self, duration_cutoff):
  #   flag_column_name = f'FLAG_sub_negative_10_SEARCH_>{duration_cutoff}hrs_total'
  #   self.flag_data_above_cutoff(
  #     'sub_negative_10_duration_SEARCH', duration_cutoff, flag_column_name
  #   )
  #   return flag_column_name

  # def flag_sub_negative_20_search(self, duration_cutoff):
  #   flag_column_name = f'FLAG_sub_negative_20_SEARCH_>{duration_cutoff}hrs_total'
  #   self.flag_data_above_cutoff(
  #     'sub_negative_20_duration_SEARCH', duration_cutoff, flag_column_name
  #   )
  #   return flag_column_name

  # def flag_sub_negative_40_search(self, duration_cutoff):
  #   flag_column_name = f'FLAG_sub_negative_40_SEARCH_>{duration_cutoff}hrs_total'
  #   self.flag_data_above_cutoff(
  #     'sub_negative_40_duration_SEARCH', duration_cutoff, flag_column_name
  #   )
  #   return flag_column_name

  # def flag_non_wear_percent_search(self, cutoff = 0.80):
  #   flag_column_name = f'FLAG_non_wear_percent_SEARCH_>{cutoff}'
  #   self.flag_data_below_cutoff(
  #     'device_worn_percent_SEARCH', cutoff, flag_column_name
  #   )
  #   return flag_column_name

# def run_search_flags_and_validation(self):
#     self.search_flags = []
    
#     if self.search_flag_selections['flag_sub_negative_10_search']:
#       flag_sub_negative_10_search_column = self.flag_sub_negative_10_search(**self.search_flag_selections['flag_sub_negative_10_search'])
#       self.search_flags.append(flag_sub_negative_10_search_column)

#     if self.search_flag_selections['flag_sub_negative_20_search']:
#       flag_sub_negative_20_search_column = self.flag_sub_negative_20_search(**self.search_flag_selections['flag_sub_negative_20_search'])
#       self.search_flags.append(flag_sub_negative_20_search_column)

#     if self.search_flag_selections['flag_sub_negative_40_search']:
#       flag_sub_negative_40_search_column = self.flag_sub_negative_40_search(**self.search_flag_selections['flag_sub_negative_40_search'])
#       self.search_flags.append(flag_sub_negative_40_search_column)

#     if self.search_flag_selections['flag_non_wear_duration_search']:
#       flag_non_wear_duration_search_column = self.flag_non_wear_duration_search(**self.search_flag_selections['flag_non_wear_duration_search'])
#       self.search_flags.append(flag_non_wear_duration_search_column)

#     self.validate_periphery('SEARCH_VALID', self.search_flags)

#     return self.search_flags

# def flag_non_wear_duration_search(self, duration_cutoff):
#     flag_column_name = f'FLAG_non_wear_duration_SEARCH_<{duration_cutoff}hrs'
#     self.flag_data_below_cutoff(
#       'device_worn_duration_SEARCH', duration_cutoff, flag_column_name
#     )
#     return flag_column_name

""" FEATURE SPECIFIC VALIDATION TO COME """
