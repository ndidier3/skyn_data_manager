import numpy as np

class featureFlagger():
  """
  Takes event features; adds flags (1=flagged) or validation (1=valid)
  """
  def __init__(self, features):
    self.ftrs = features
  
  """ Flags will be based on cutoffs for continuous quality features """
  def flag_data_above_cutoff(self, column, cutoff, flag_name):
    self.ftrs[flag_name] = np.where(self.ftrs[column].isna(), np.nan, (self.ftrs[column] > cutoff).astype(int))

  def flag_data_below_cutoff(self, column, cutoff, flag_name):
    self.ftrs[flag_name] = np.where(self.ftrs[column].isna(), np.nan, (self.ftrs[column] < cutoff).astype(int))

  """ Search Quality Assessment """
  # def flag_extreme_values_search(self, cutoff = 40):
  #   #If flagged, all features invalid
  #   flag_column_name = f'FLAG_extreme_values_SEARCH_>{cutoff}'
  #   self.flag_data_above_cutoff(
  #     'consecutive_extreme_values_SEARCH', cutoff, flag_column_name
  #   )
  #   return flag_column_name

  def flag_very_negative_duration_search(self, cutoff = 1.0):
    #If flagged, all features invalid
    flag_column_name = f'FLAG_very_negative_SEARCH_>{cutoff}'
    self.flag_data_above_cutoff(
      'very_negative_duration_SEARCH', cutoff, flag_column_name
    )
    return flag_column_name

  def flag_non_wear_percent_search(self, cutoff = 0.80):
    flag_column_name = f'FLAG_non_wear_percent_SEARCH_>{cutoff}'
    self.flag_data_below_cutoff(
      'device_worn_percent_SEARCH', cutoff, flag_column_name
    )
    return flag_column_name

  """ Whole Curve Qaulity Assessment """
  def flag_device_worn_percent_curve(self, cutoff = 0.90):
    #if flagged, all curve features invalid
    flag_column_name = f'FLAG_device_worn_percent_CURVE_<{cutoff}'
    self.flag_data_below_cutoff(
      'device_worn_percent_CURVE', cutoff, flag_column_name
    )
    return flag_column_name

  def flag_device_worn_duration_curve(self, cutoff = (6/60)):
    #if flagged, all curve features invalid
    flag_column_name = f'FLAG_device_worn_duration_CURVE_<{cutoff}'
    self.flag_data_below_cutoff(
      'device_worn_percent_CURVE', cutoff, flag_column_name
    )
    return flag_column_name

  def flag_extreme_percent_curve(self, cutoff = 0.05):
    flag_column_name = f'FLAG_extreme_percent_CURVE_>{cutoff}'
    self.flag_data_above_cutoff(
      'consecutive_extreme_percent_CURVE', cutoff, flag_column_name
    )
    return flag_column_name

  #Flags should never occur here, because a curve ends when TAC is below threshold (which is 10 as of 12.3.24)
  def flag_very_negative_duration_curve(self, cutoff = 0.1):
    flag_column_name = f'FLAG_very_negative_CURVE_<{cutoff}'
    self.flag_data_above_cutoff(
      'very_negative_duration_CURVE', cutoff, flag_column_name
    )
    return flag_column_name

  # Flags should never occur here, because when device is turned off curve automatically ends (as of 12.3.24)
  def flag_device_turned_on_percent_curve(self, cutoff = 0.999):
    flag_column_name = f'FLAG_device_turned_on_percent_CURVE_<{cutoff}'
    self.flag_data_below_cutoff(
      'device_turned_on_percent_CURVE', cutoff, flag_column_name
    )
    return flag_column_name

  """ Rise Quality Assessment """
  def flag_starting_non_wear_perc_curve(self, cutoff = 0.5):
    flag_column_name = f'FLAG_non_wear_CURVE_start_>{cutoff}'
    self.flag_data_above_cutoff(
      'starting_non_wear_perc_CURVE', cutoff, flag_column_name
    )
    return flag_column_name

  def flag_incomplete_curve_start(self, cutoff=0.75):
    flag_column_name = f'FLAG_rise_completion_CURVE_<{cutoff}'
    self.flag_data_below_cutoff(
      'rise_complete_perc_CURVE', cutoff, flag_column_name
    )
    return flag_column_name

  """ Fall Quality Assessment """
  def flag_ending_non_wear_perc_curve(self, cutoff = 0.5):
    flag_column_name = f'FLAG_non_wear_CURVE_end_>{cutoff}'
    self.flag_data_above_cutoff(
      'ending_non_wear_perc_CURVE', cutoff, flag_column_name
    )
    return flag_column_name

  def flag_incomplete_curve_end(self, cutoff=0.75):
    flag_column_name = f'FLAG_fall_completion_CURVE_<{cutoff}'
    self.flag_data_below_cutoff(
      'fall_complete_perc_CURVE', cutoff, flag_column_name
    )
    return flag_column_name

  def run_flags(self):
    self.search_flags = []
    self.all_feature_flags = []
    self.curve_duration_flags = []
    self.curve_auc_flags = []
    self.rise_flags = []
    self.fall_flags = []

    # flag_extreme_values_search_column = self.flag_extreme_values_search()
    # self.all_feature_flags.append(flag_extreme_values_search_column)
    # self.search_flags.append(flag_extreme_values_search_column)

    flag_very_negative_duration_search_column = self.flag_very_negative_duration_search()
    self.all_feature_flags.append(flag_very_negative_duration_search_column)
    self.search_flags.append(flag_very_negative_duration_search_column)

    flag_non_wear_percent_search_column = self.flag_non_wear_percent_search()
    self.all_feature_flags.append(flag_non_wear_percent_search_column)
    self.search_flags.append(flag_non_wear_percent_search_column)

    flag_device_worn_percent_curve_column = self.flag_device_worn_percent_curve()
    self.all_feature_flags.append(flag_device_worn_percent_curve_column)

    flag_device_worn_duration_curve_column = self.flag_device_worn_duration_curve()
    self.all_feature_flags.append(flag_device_worn_duration_curve_column)

    flag_extreme_percent_curve_column = self.flag_extreme_percent_curve()
    self.all_feature_flags.append(flag_extreme_percent_curve_column)

    flag_very_negative_duration_curve_column = self.flag_very_negative_duration_curve()
    self.all_feature_flags.append(flag_very_negative_duration_curve_column)

    flag_device_turned_on_percent_curve_column = self.flag_device_turned_on_percent_curve()
    self.all_feature_flags.append(flag_device_turned_on_percent_curve_column)

    flag_starting_non_wear_perc_column = self.flag_starting_non_wear_perc_curve()
    self.rise_flags.append(flag_starting_non_wear_perc_column)
    self.curve_duration_flags.append(flag_starting_non_wear_perc_column)
    self.curve_auc_flags.append(flag_starting_non_wear_perc_column)

    flag_incomplete_curve_start_column = self.flag_incomplete_curve_start()
    self.rise_flags.append(flag_incomplete_curve_start_column)
    self.curve_duration_flags.append(flag_incomplete_curve_start_column)
    self.curve_auc_flags.append(flag_incomplete_curve_start_column)

    flag_very_incomplete_curve_start_column = self.flag_incomplete_curve_start(cutoff=0.5)
    self.all_feature_flags.append(flag_very_incomplete_curve_start_column)

    flag_ending_non_wear_perc_curve_column = self.flag_ending_non_wear_perc_curve()
    self.fall_flags.append(flag_ending_non_wear_perc_curve_column)
    self.curve_duration_flags.append(flag_ending_non_wear_perc_curve_column)
    self.curve_auc_flags.append(flag_ending_non_wear_perc_curve_column)

    flag_incomplete_curve_end_column = self.flag_incomplete_curve_end()
    self.fall_flags.append(flag_incomplete_curve_end_column)
    self.curve_duration_flags.append(flag_incomplete_curve_end_column)
    self.curve_auc_flags.append(flag_incomplete_curve_end_column)

    flag_very_incomplete_curve_end_column = self.flag_incomplete_curve_end(cutoff=0.5)
    self.all_feature_flags.append(flag_very_incomplete_curve_end_column)

  """ Validation of TAC Features"""

  def validate_search(self, new_column, flag_columns):
    any_nan = self.ftrs[flag_columns].isna().any(axis=1)
    any_one = self.ftrs[flag_columns].eq(1).any(axis=1)
    all_zero = self.ftrs[flag_columns].fillna(0).eq(0).all(axis=1)
    self.ftrs[new_column] = np.where(
      any_nan, 0, np.where(
        any_one, 0, np.where(
          all_zero, 1, np.nan
    )))

  def validate(self, new_column, flag_columns):
    any_nan = self.ftrs[flag_columns].isna().any(axis=1)
    any_one = self.ftrs[flag_columns].eq(1).any(axis=1)
    all_zero = self.ftrs[flag_columns].fillna(0).eq(0).all(axis=1)
    self.ftrs[new_column] = np.where(
      any_nan, np.nan, np.where(
        any_one, 0, np.where(
          all_zero, 1, np.nan
    )))
  
  def validate_features(self):
    self.validate_search('SEARCH_VALID', self.search_flags)
    self.validate('peak_CURVE_VALID', self.all_feature_flags)
    self.validate('duration_CURVE_VALID', self.all_feature_flags + self.curve_duration_flags)
    self.validate('auc_total_CURVE_VALID', self.all_feature_flags + self.curve_auc_flags)
    self.validate('rise_rate_CURVE_VALID', self.all_feature_flags + self.rise_flags)
    self.validate('rise_duration_CURVE_VALID', self.all_feature_flags + self.rise_flags)
    self.validate('rise_auc_CURVE_VALID', self.all_feature_flags + self.rise_flags)
    self.validate('fall_rate_CURVE_VALID', self.all_feature_flags + self.fall_flags)
    self.validate('fall_duration_CURVE_VALID', self.all_feature_flags + self.fall_flags)
    self.validate('fall_auc_CURVE_VALID', self.all_feature_flags + self.fall_flags)
    
  def run_all_flags_and_validations(self):
    self.run_flags()
    self.validate_features()
