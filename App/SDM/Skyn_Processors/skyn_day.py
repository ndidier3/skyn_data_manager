from App.SDM.Feature_Engineering.quality_analyzer import DataQualityAnalyzer
import pandas as pd

class skynDay:
  def __init__(self, dataset, start_index, end_index, non_wear_self_report_column = '', compare_non_wear_methods = False, day_start_hour = 0):
    self.day_dataset = dataset.loc[start_index:end_index]

    # Set social day boundaries based on day_start_hour (default 0 = midnight)
    # This ensures day_hours is always 24.0 for complete days
    first_data_time = self.day_dataset['datetime'].iloc[0] if not self.day_dataset.empty else None
    last_data_time = self.day_dataset['datetime'].iloc[-1] if not self.day_dataset.empty else None
    
    if first_data_time is not None:
      # Determine which social day this data belongs to
      # If data is before day_start_hour, it belongs to the previous day's period
      if first_data_time.hour < day_start_hour:
        # Data is before day_start_hour, so it belongs to the previous day's period
        social_begin = first_data_time.replace(hour=day_start_hour, minute=0, second=0, microsecond=0) - pd.Timedelta(days=1)
      else:
        # Data is at or after day_start_hour, so it belongs to the current day's period
        social_begin = first_data_time.replace(hour=day_start_hour, minute=0, second=0, microsecond=0)
      
      # Calculate social end_day: next day at day_start_hour
      social_end = social_begin + pd.Timedelta(days=1)
      
      self.begin_day = social_begin
      self.end_day = social_end
    else:
      self.begin_day = None
      self.end_day = None

    self.device_ids = self.day_dataset['device_id'].unique().tolist()
    self.device_one = self.device_ids[0]
    self.device_two = self.device_ids[1] if len(self.device_ids) > 1 else None
    self.device_count = len(self.device_ids)
    
    # More robust firmware extraction
    if 'Firmware Version' in self.day_dataset.columns and not self.day_dataset.empty:
        # Get first non-null firmware value
        firmware_values = self.day_dataset['Firmware Version'].dropna()
        self.firmware = firmware_values.iloc[0] if not firmware_values.empty else None
    else:
        self.firmware = None

    self.day_hours = 24  # Always 24 hours with social day boundaries
    self.device_turned_on_duration = self.day_dataset['device_turned_on'].sum() / 60
    self.device_turned_on_percentage_of_day = self.device_turned_on_duration / self.day_hours

    """
    device_worn_duration will always be equal or less than device_turned_on_duration.
    This is because values for device_worn is null whenever device is not turned on.
    Therefore, device_worn_duration will be the duration when device is turned on AND worn.
    """
    self.device_worn_duration = self.day_dataset['device_worn_model'].sum() / 60
    self.device_worn_percent_of_device_on = (self.device_worn_duration / self.device_turned_on_duration) if self.device_turned_on_duration > 0 else 0
    self.device_worn_percent_of_day = self.device_worn_duration / 24

    self.device_worn_duration_cutoff = self.day_dataset['device_worn_temp_cutoff'].sum() / 60
    self.device_worn_cutoff_percent_of_device_on = (self.device_worn_duration_cutoff / self.device_turned_on_duration) if self.device_turned_on_duration > 0 else 0
    self.device_worn_cutoff_percent_of_day = self.device_worn_duration_cutoff / 24

    # Quality metrics
    self.imputed_duration = self.day_dataset['imputed'].sum() / 60
    self.imputed_percent = self.day_dataset['imputed'].sum() / len(self.day_dataset)
    
    # Create quality analyzer for efficient computation
    self.quality_analyzer = DataQualityAnalyzer(self.day_dataset, 'TAC')
    
    # Low quality metrics
    self.low_quality_duration = self.quality_analyzer.get_low_quality_duration()
    self.low_quality_percent = self.quality_analyzer.get_low_quality_percent()
    self.unimputed_low_quality_duration = self.quality_analyzer.get_unimputed_low_quality_duration()
    self.unimputed_low_quality_percent = self.quality_analyzer.get_unimputed_low_quality_percent()
    self.imputed_low_quality_duration = self.quality_analyzer.get_imputed_low_quality_duration()
    self.imputed_low_quality_percent = self.quality_analyzer.get_imputed_low_quality_percent()
    
    # Gap metrics
    self.gap_duration = (self.day_dataset['gap'] == 1).sum() / 60
    self.gap_percent = (self.day_dataset['gap'] == 1).sum() / len(self.day_dataset)
    self.imputed_gap_duration = self.quality_analyzer.get_imputed_gap_duration()
    self.imputed_gap_percent = self.quality_analyzer.get_imputed_gap_percent()
    self.unimputed_gap_duration = self.quality_analyzer.get_unimputed_gap_duration()
    self.unimputed_gap_percent = self.quality_analyzer.get_unimputed_gap_percent()
    self.gap_imputation_ratio = self.quality_analyzer.get_gap_imputation_ratio()
    
    # Non-wear metrics
    self.non_wear_duration = (self.day_dataset['non_wear'] == 1).sum() / 60
    self.non_wear_percent = (self.day_dataset['non_wear'] == 1).sum() / len(self.day_dataset)
    self.imputed_non_wear_duration = self.quality_analyzer.get_imputed_non_wear_duration()
    self.imputed_non_wear_percent = self.quality_analyzer.get_imputed_non_wear_percent()
    self.unimputed_non_wear_duration = self.quality_analyzer.get_unimputed_non_wear_duration()
    self.unimputed_non_wear_percent = self.quality_analyzer.get_unimputed_non_wear_percent()
    self.non_wear_imputation_ratio = self.quality_analyzer.get_non_wear_imputation_ratio()
    
    # Jump metrics
    self.jump_duration = (self.day_dataset['jump'] == 1).sum() / 60
    self.jump_percent = (self.day_dataset['jump'] == 1).sum() / len(self.day_dataset)
    self.imputed_jump_duration = self.quality_analyzer.get_imputed_jump_duration()
    self.imputed_jump_percent = self.quality_analyzer.get_imputed_jump_percent()
    self.unimputed_jump_duration = self.quality_analyzer.get_unimputed_jump_duration()
    self.unimputed_jump_percent = self.quality_analyzer.get_unimputed_jump_percent()
    self.jump_imputation_ratio = self.quality_analyzer.get_jump_imputation_ratio()
    
    # Plummet metrics
    self.plummet_duration = (self.day_dataset['plummet'] == 1).sum() / 60
    self.plummet_percent = (self.day_dataset['plummet'] == 1).sum() / len(self.day_dataset)
    self.imputed_plummet_duration = self.quality_analyzer.get_imputed_plummet_duration()
    self.imputed_plummet_percent = self.quality_analyzer.get_imputed_plummet_percent()
    self.unimputed_plummet_duration = self.quality_analyzer.get_unimputed_plummet_duration()
    self.unimputed_plummet_percent = self.quality_analyzer.get_unimputed_plummet_percent()
    self.plummet_imputation_ratio = self.quality_analyzer.get_plummet_imputation_ratio()
    
    # Negative value metrics
    self.negative_duration = (self.day_dataset['TAC'] <= 0).sum() / 60
    self.negative_percent = (self.day_dataset['TAC'] <= 0).sum() / len(self.day_dataset)
    
    # Extreme negative metrics
    self.extreme_negative_duration = (self.day_dataset['extreme_negative'] == 1).sum() / 60
    self.extreme_negative_percent = (self.day_dataset['extreme_negative'] == 1).sum() / len(self.day_dataset)
    self.extreme_negative_sum = self.day_dataset.loc[self.day_dataset['extreme_negative'] == 1, 'TAC'].sum()
    self.imputed_extreme_negative_duration = self.quality_analyzer.get_imputed_extreme_negative_duration()
    self.imputed_extreme_negative_percent = self.quality_analyzer.get_imputed_extreme_negative_percent()
    self.unimputed_extreme_negative_duration = self.quality_analyzer.get_unimputed_extreme_negative_duration()
    self.unimputed_extreme_negative_percent = self.quality_analyzer.get_unimputed_extreme_negative_percent()
    self.extreme_negative_imputation_ratio = self.quality_analyzer.get_extreme_negative_imputation_ratio()
    
    # Additional quality metrics
    self.low_quality_imputation_ratio = self.quality_analyzer.get_low_quality_imputation_ratio()
    self.total_gaps_and_non_wear_percent = self.quality_analyzer.get_total_gaps_and_non_wear_percent()
    self.below_threshold_percent = self.quality_analyzer.get_below_threshold_percent(0)
    self.flatline_max = self.quality_analyzer.count_longest_tac_flatline()
    self.flatlined_percent = self.quality_analyzer.count_longest_tac_flatline() / len(self.day_dataset) if len(self.day_dataset) > 0 else 0

    if compare_non_wear_methods:
      self.FP_cutoff_vs_model_duration = self.day_dataset['FP_cutoff_vs_model'].sum() / 60
      self.FN_cutoff_vs_model_duration = self.day_dataset['FN_cutoff_vs_model'].sum() / 60
      self.DISAGREE_cutoff_vs_model_duration = self.day_dataset['DISAGREE_cutoff_vs_model'].sum() / 60

    if non_wear_self_report_column:
      self.device_worn_duration_self_report = self.day_dataset[non_wear_self_report_column].sum() / 60
      self.device_worn_self_report_percent_of_device_on = (self.device_worn_duration_self_report / self.device_turned_on_duration) if self.device_turned_on_duration > 0 else 0
      self.device_worn_self_report_percent_of_day = self.device_worn_duration_self_report / 24

      if compare_non_wear_methods:
        self.FP_self_report_vs_model_duration = self.day_dataset['FP_self_report_vs_model'].sum() / 60
        self.FN_self_report_vs_model_duration = self.day_dataset['FN_self_report_vs_model'].sum() / 60
        self.DISAGREE_self_report_vs_model_duration = self.day_dataset['DISAGREE_self_report_vs_model'].sum() / 60
        self.FP_self_report_vs_cutoff_duration = self.day_dataset['FP_self_report_vs_cutoff'].sum() / 60
        self.FN_self_report_vs_cutoff_duration = self.day_dataset['FN_self_report_vs_cutoff'].sum() / 60
        self.DISAGREE_self_report_vs_cutoff_duration = self.day_dataset['DISAGREE_self_report_vs_cutoff'].sum() / 60
    
    self.temp_mean = self.day_dataset['Temperature_C'].mean()
    self.temp_sd = self.day_dataset['Temperature_C'].std()
    self.temp_min = self.day_dataset['Temperature_C'].min()
    self.temp_max = self.day_dataset['Temperature_C'].max()

    self.motion_mean = self.day_dataset['Motion'].mean()
    self.motion_sd = self.day_dataset['Motion'].std()
    self.motion_min = self.day_dataset['Motion'].min()
    self.motion_max = self.day_dataset['Motion'].max()
