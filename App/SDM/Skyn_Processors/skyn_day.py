from App.SDM.Feature_Engineering.quality_features import (
    get_low_quality_duration,
    get_low_quality_percent,
    get_unimputed_low_quality_duration,
    get_unimputed_low_quality_percent
)

class skynDay:
  def __init__(self, dataset, start_index, end_index, non_wear_self_report_column = '', compare_non_wear_methods = False):
    self.day_dataset = dataset.loc[start_index:end_index]

    self.begin_day = self.day_dataset['datetime'].iloc[0] if not self.day_dataset.empty else None
    self.end_day = self.day_dataset['datetime'].iloc[-1] if not self.day_dataset.empty else None

    self.device_ids = self.day_dataset['device_id'].unique().tolist()
    self.device_one = self.device_ids[0]
    self.device_two = self.device_ids[1] if len(self.device_ids) > 1 else None
    self.device_count = len(self.device_ids)
    self.firmware = self.day_dataset['Firmware Version'].iloc[0] if 'Firmware Version' in self.day_dataset.columns else None

    self.day_hours = (self.end_day - self.begin_day).total_seconds() / 3600
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
    
    # Low quality metrics
    self.low_quality_duration = get_low_quality_duration(self.day_dataset)
    self.low_quality_percent = get_low_quality_percent(self.day_dataset)
    self.unimputed_low_quality_duration = get_unimputed_low_quality_duration(self.day_dataset)
    self.unimputed_low_quality_percent = get_unimputed_low_quality_percent(self.day_dataset)
    
    # Negative value metrics
    self.negative_duration = (self.day_dataset['TAC'] <= 0).sum() / 60
    self.negative_percent = (self.day_dataset['TAC'] <= 0).sum() / len(self.day_dataset)
    
    # Extreme negative metrics
    self.extreme_negative_duration = (self.day_dataset['extreme_negative'] == 1).sum() / 60
    self.extreme_negative_percent = (self.day_dataset['extreme_negative'] == 1).sum() / len(self.day_dataset)
    self.extreme_negative_sum = self.day_dataset.loc[self.day_dataset['extreme_negative'] == 1, 'TAC'].sum()
    
    # Jump and plummet metrics
    self.jump_duration = (self.day_dataset['jump'] == 1).sum() / 60
    self.jump_percent = (self.day_dataset['jump'] == 1).sum() / len(self.day_dataset)
    self.plummet_duration = (self.day_dataset['plummet'] == 1).sum() / 60
    self.plummet_percent = (self.day_dataset['plummet'] == 1).sum() / len(self.day_dataset)

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
