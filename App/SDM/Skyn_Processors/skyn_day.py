from App.SDM.Feature_Engineering.quality_analyzer import DataQualityAnalyzer
from App.SDM.Feature_Engineering.tac_analyzer import TACAnalyzer
import pandas as pd


class skynDay:
  def __init__(self, dataset, start_index, end_index, curve_threshold, non_wear_self_report_column = '', compare_non_wear_methods = False, day_start_hour = 0):
    self.day_dataset = dataset.loc[start_index:end_index]
    n = len(self.day_dataset)
    self.curve_threshold = curve_threshold

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
    self.imputed_percent = (self.day_dataset['imputed'].sum() / n) if n > 0 else 0.0
    
    # Create quality analyzer for efficient computation
    self.quality_analyzer = DataQualityAnalyzer(self.day_dataset, 'TAC')
    
    # Low quality metrics
    self.low_quality_duration = self.quality_analyzer.get_low_quality_duration()
    self.low_quality_percent = self.quality_analyzer.get_low_quality_percent()
    self.unimputed_low_quality_duration = self.quality_analyzer.get_unimputed_low_quality_duration()
    self.unimputed_low_quality_percent = self.quality_analyzer.get_unimputed_low_quality_percent()
    self.imputed_low_quality_duration = self.quality_analyzer.get_imputed_low_quality_duration()
    self.imputed_low_quality_percent = self.quality_analyzer.get_imputed_low_quality_percent()

    # Percent-of-day variants (denominator fixed at 24 hours)
    self.low_quality_percent_of_day = self.low_quality_duration / 24
    self.unimputed_low_quality_percent_of_day = self.unimputed_low_quality_duration / 24
    self.imputed_low_quality_percent_of_day = self.imputed_low_quality_duration / 24
    
    # Gap metrics
    # Exclusive totals (mutually exclusive; consistent with Curve feature computation)
    self.gap_duration = self.quality_analyzer.get_total_gap_duration()
    self.gap_percent = self.quality_analyzer.get_total_gap_percent()
    # Inclusive totals (raw flags; no mutual exclusivity)
    self.gap_duration_inclusive = self.quality_analyzer.get_total_gap_duration_inclusive()
    self.gap_percent_inclusive = self.quality_analyzer.get_total_gap_percent_inclusive()
    self.imputed_gap_duration = self.quality_analyzer.get_imputed_gap_duration()
    self.imputed_gap_percent = self.quality_analyzer.get_imputed_gap_percent()
    self.unimputed_gap_duration = self.quality_analyzer.get_unimputed_gap_duration()
    self.unimputed_gap_percent = self.quality_analyzer.get_unimputed_gap_percent()
    self.gap_imputation_ratio = self.quality_analyzer.get_gap_imputation_ratio()
    
    # Non-wear metrics
    # Exclusive totals
    self.non_wear_duration = self.quality_analyzer.get_total_non_wear_duration()
    self.non_wear_percent = self.quality_analyzer.get_total_non_wear_percent()
    # Inclusive totals
    self.non_wear_duration_inclusive = self.quality_analyzer.get_total_non_wear_duration_inclusive()
    self.non_wear_percent_inclusive = self.quality_analyzer.get_total_non_wear_percent_inclusive()
    self.imputed_non_wear_duration = self.quality_analyzer.get_imputed_non_wear_duration()
    self.imputed_non_wear_percent = self.quality_analyzer.get_imputed_non_wear_percent()
    self.unimputed_non_wear_duration = self.quality_analyzer.get_unimputed_non_wear_duration()
    self.unimputed_non_wear_percent = self.quality_analyzer.get_unimputed_non_wear_percent()
    self.non_wear_imputation_ratio = self.quality_analyzer.get_non_wear_imputation_ratio()
    
    # Jump metrics
    # Exclusive totals
    self.jump_duration = self.quality_analyzer.get_total_jump_duration()
    self.jump_percent = self.quality_analyzer.get_total_jump_percent()
    # Inclusive totals
    self.jump_duration_inclusive = self.quality_analyzer.get_total_jump_duration_inclusive()
    self.jump_percent_inclusive = self.quality_analyzer.get_total_jump_percent_inclusive()
    self.imputed_jump_duration = self.quality_analyzer.get_imputed_jump_duration()
    self.imputed_jump_percent = self.quality_analyzer.get_imputed_jump_percent()
    self.unimputed_jump_duration = self.quality_analyzer.get_unimputed_jump_duration()
    self.unimputed_jump_percent = self.quality_analyzer.get_unimputed_jump_percent()
    self.jump_imputation_ratio = self.quality_analyzer.get_jump_imputation_ratio()
    
    # Plummet metrics
    # Exclusive totals
    self.plummet_duration = self.quality_analyzer.get_total_plummet_duration()
    self.plummet_percent = self.quality_analyzer.get_total_plummet_percent()
    # Inclusive totals
    self.plummet_duration_inclusive = self.quality_analyzer.get_total_plummet_duration_inclusive()
    self.plummet_percent_inclusive = self.quality_analyzer.get_total_plummet_percent_inclusive()
    self.imputed_plummet_duration = self.quality_analyzer.get_imputed_plummet_duration()
    self.imputed_plummet_percent = self.quality_analyzer.get_imputed_plummet_percent()
    self.unimputed_plummet_duration = self.quality_analyzer.get_unimputed_plummet_duration()
    self.unimputed_plummet_percent = self.quality_analyzer.get_unimputed_plummet_percent()
    self.plummet_imputation_ratio = self.quality_analyzer.get_plummet_imputation_ratio()
    
    # Negative value metrics
    self.negative_duration = (self.day_dataset['TAC'] <= 0).sum() / 60
    self.negative_percent = ((self.day_dataset['TAC'] <= 0).sum() / n) if n > 0 else 0.0
    
    # Extreme negative metrics
    # Exclusive totals
    self.extreme_negative_duration = self.quality_analyzer.get_total_extreme_negative_duration()
    self.extreme_negative_percent = self.quality_analyzer.get_total_extreme_negative_percent()
    self.extreme_negative_sum = self.quality_analyzer.get_sub_negative_10_sum()
    # Inclusive totals
    self.extreme_negative_duration_inclusive = self.quality_analyzer.get_total_extreme_negative_duration_inclusive()
    self.extreme_negative_percent_inclusive = self.quality_analyzer.get_total_extreme_negative_percent_inclusive()
    self.extreme_negative_sum_inclusive = self.day_dataset.loc[self.day_dataset['extreme_negative'] == 1, 'TAC'].sum() if n > 0 else 0.0
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

    # Above-threshold metrics (relative to curve threshold)
    if n > 0:
      above_mask = self.day_dataset['TAC'] >= self.curve_threshold
      self.above_threshold_duration = above_mask.sum() / 60
      self.above_threshold_percent_of_day = self.above_threshold_duration / self.day_hours

      high_quality_mask = ~self.quality_analyzer.low_quality_mask
      above_and_hq_count = (above_mask & high_quality_mask).sum()

      if above_mask.any():
        self.above_threshold_high_quality_percent = above_and_hq_count / above_mask.sum()
      else:
        self.above_threshold_high_quality_percent = None

      self.above_threshold_high_quality_percent_of_day = (above_and_hq_count / 60) / self.day_hours
    else:
      self.above_threshold_duration = 0.0
      self.above_threshold_percent_of_day = 0.0
      self.above_threshold_high_quality_percent = None
      self.above_threshold_high_quality_percent_of_day = 0.0

    # Day-level TAC summaries (minute rows in the social day window). Exploratory only — coverage can be
    # incomplete; primary workflows use curve-level / merged features instead.
    _tac_nan = float('nan')
    if n > 0 and 'TAC' in self.day_dataset.columns:
      tac = pd.to_numeric(self.day_dataset['TAC'], errors='coerce')
      self.tac_day_mean = tac.mean()
      self.tac_day_median = tac.median()
      self.tac_day_sd = tac.std()
      self.tac_day_min = tac.min()
      self.tac_day_max = tac.max()
      self.tac_day_q25 = tac.quantile(0.25)
      self.tac_day_q75 = tac.quantile(0.75)
      nn = int(tac.notna().sum())
      self.tac_non_missing_minute_count = nn
      self.tac_non_missing_fraction_of_rows = float(nn) / float(n)
    else:
      self.tac_day_mean = _tac_nan
      self.tac_day_median = _tac_nan
      self.tac_day_sd = _tac_nan
      self.tac_day_min = _tac_nan
      self.tac_day_max = _tac_nan
      self.tac_day_q25 = _tac_nan
      self.tac_day_q75 = _tac_nan
      self.tac_non_missing_minute_count = 0
      self.tac_non_missing_fraction_of_rows = 0.0

    # Time-region TAC features: Q1 (0–6h) and Q2_Q4 (6–24h).
    # Q1 captures prior-day curve tail; Q2_Q4 captures same-day activity.
    _region_defs = (
        ('q1', 0, 6),
        ('q2_q4', 6, 24),
    )
    _region_attr_suffixes = (
        'mean', 'max', 'above_threshold_percent', 'auc',
        'rise_rate_point_to_point', 'fall_rate_point_to_point',
        'ascending_duration', 'descending_duration',
    )
    for rlabel, h_start, h_end in _region_defs:
      if n > 0 and 'TAC' in self.day_dataset.columns and self.begin_day is not None:
        r_start = self.begin_day + pd.Timedelta(hours=h_start)
        r_end = self.begin_day + pd.Timedelta(hours=h_end)
        r_slice = self.day_dataset[
            (self.day_dataset['datetime'] >= r_start) & (self.day_dataset['datetime'] < r_end)
        ].copy()
        r_tac = pd.to_numeric(r_slice['TAC'], errors='coerce') if not r_slice.empty else pd.Series(dtype=float)
        r_n = int(r_tac.notna().sum())

        if r_n > 0:
          setattr(self, f'tac_{rlabel}_mean', r_tac.mean())
          setattr(self, f'tac_{rlabel}_max', r_tac.max())
          r_above = (r_tac >= self.curve_threshold)
          setattr(self, f'tac_{rlabel}_above_threshold_percent', float(r_above.sum()) / float(len(r_slice)))

          r_analyzer = TACAnalyzer(r_slice, tac_column='TAC')
          setattr(self, f'tac_{rlabel}_auc', r_analyzer.get_auc())
          setattr(self, f'tac_{rlabel}_rise_rate_point_to_point', r_analyzer.get_point_to_point_rise_rate(0))
          setattr(self, f'tac_{rlabel}_fall_rate_point_to_point', r_analyzer.get_point_to_point_fall_rate(0))
          setattr(self, f'tac_{rlabel}_ascending_duration', r_analyzer.get_point_to_point_rise_duration(0))
          setattr(self, f'tac_{rlabel}_descending_duration', r_analyzer.get_point_to_point_fall_duration(0))
        else:
          for sfx in _region_attr_suffixes:
            setattr(self, f'tac_{rlabel}_{sfx}', _tac_nan)
      else:
        for sfx in _region_attr_suffixes:
          setattr(self, f'tac_{rlabel}_{sfx}', _tac_nan)

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
