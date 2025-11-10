from App.SDM.Feature_Engineering.tac_analyzer import TACAnalyzer
from App.SDM.Feature_Engineering.quality_analyzer import DataQualityAnalyzer
from App.SDM.Visualization.tac import *
from App.SDM.Visualization.device_non_wear import plot_device_removal
from App.SDM.Analysis.featureFlagger import featureFlagger
import pandas as pd

class Curve:
  def __init__(self, df: pd.DataFrame, subid, dataset_identifier, curve_id, curve_start, curve_end, curve_count, curve_threshold, flag_selections = {}, periphery_buffer_before = 2, periphery_buffer_after = 2, TAC_column = 'TAC'):
    
    self.df = df
    self.subid = subid
    self.dataset_identifier = dataset_identifier
    self.TAC_column = TAC_column

    self.curve_id = curve_id
    self.curve_count = curve_count
    self.curve = df.loc[curve_start:curve_end]
    self.valid = False

    self.curve_threshold = curve_threshold
    self.periphery_start_index = max(0, (int(self.curve.index[0]) - (periphery_buffer_before*60)))
    self.periphery_end_index = min(int(df.index[-1]), (int(self.curve.index[-1]) + (periphery_buffer_after*60)))
    self.periphery_before = df.loc[self.periphery_start_index:curve_start]
    self.periphery_after = df.loc[curve_end:self.periphery_end_index]
    self.periphery = pd.concat([
      self.periphery_before, 
      self.periphery_after
    ])
    
    self.region = df.loc[self.periphery_start_index:self.periphery_end_index]

    curve_minutes = int(curve_end) - int(curve_start)
    buffer = max(0, (24 * 60 - curve_minutes) // 2)
    day_region_start = max(0, int(curve_start) - buffer)
    day_region_end = min(int(df.index[-1]), int(curve_end) + buffer)
    self.day_region = df.loc[day_region_start:day_region_end]
    
    self.curve.reset_index(drop=True, inplace=True)
    self.periphery_before.reset_index(drop=True, inplace=True)
    self.periphery_after.reset_index(drop=True, inplace=True)
    self.periphery.reset_index(drop=True, inplace=True) 
    self.day_region.reset_index(drop=True, inplace=True)

    self.device_ids = self.region['device_id'].unique().tolist()
    self.device_info = {
      'device_one_REGION' : self.device_ids[0] if len(self.device_ids) > 0 else None,
      'device_two_REGION' : self.device_ids[1] if len(self.device_ids) > 1 else None,
      'device_count_REGION': len(self.device_ids),
    }

    # Create analyzers for each region to enable caching and efficient computation
    self.curve_tac_analyzer = TACAnalyzer(self.curve, self.TAC_column)
    self.curve_quality_analyzer = DataQualityAnalyzer(self.curve, self.TAC_column)
    self.periphery_before_quality_analyzer = DataQualityAnalyzer(self.periphery_before, self.TAC_column)
    self.periphery_after_quality_analyzer = DataQualityAnalyzer(self.periphery_after, self.TAC_column)
    self.region_quality_analyzer = DataQualityAnalyzer(self.region, self.TAC_column)
    self.region_tac_analyzer = TACAnalyzer(self.region, self.TAC_column)

    peak_index = self.curve_tac_analyzer.get_peak_index()
    
    # Get curve start index for time-windowed rise rate calculations
    curve_start_index = self.curve.index[0]
    
    # Calculate rise duration by counting rows (minutes) from curve start to peak
    rise_duration = (peak_index + 1) / 60.0  # +1 to include both start and peak
    
    # Calculate fall duration by counting rows (minutes) from peak to curve end
    fall_duration = (len(self.curve) - peak_index) / 60.0  # peak_index to end (inclusive)
    peak_tac = self.curve.loc[peak_index, self.TAC_column]
    first_tac = self.curve.iloc[0][self.TAC_column]
    last_tac = self.curve.iloc[-1][self.TAC_column]
    relative_peak = peak_tac - self.curve_threshold
    mean_tac, sd_tac, sem_tac = self.curve_tac_analyzer.get_mean_stdev_sem()

    # Calculate rise and fall portions
    rise_portion = self.curve.loc[:peak_index]
    fall_portion = self.curve.loc[peak_index:]

    self.curve_quality_features = {
      'started_curve_count_CURVE': self.curve_tac_analyzer.count_started_curves(threshold=self.curve_threshold, min_length=10),
      'complete_curve_count_CURVE': self.curve_tac_analyzer.count_complete_curves(threshold=self.curve_threshold, min_length=10),      
      'total_duration_CURVE': len(self.curve) / 60,
      'device_turned_on_duration_CURVE': (self.curve['device_turned_on'].sum()) / 60,
      'device_turned_on_percent_CURVE': (self.curve['device_turned_on'].sum()) / len(self.curve),
      'device_worn_duration_CURVE': (self.curve['device_worn_model'].sum()) / 60,
      'device_worn_percent_CURVE': (self.curve['device_worn_model'].sum()) / len(self.curve),
      'flatline_max_CURVE': self.curve_quality_analyzer.count_longest_tac_flatline(),
      'flatlined_percent_CURVE': (self.curve_quality_analyzer.count_longest_tac_flatline() / len(self.curve)),
      'imputed_duration_CURVE': 0 if self.TAC_column == 'TAC_pre_imputation' else self.curve['imputed'].sum() / 60,
      'imputed_percent_CURVE': 0 if self.TAC_column == 'TAC_pre_imputation' else self.curve['imputed'].sum() / len(self.curve),
      'imputed_low_quality_duration_CURVE': 0 if self.TAC_column == 'TAC_pre_imputation' else self.curve_quality_analyzer.get_imputed_low_quality_duration(),
      'imputed_low_quality_percent_CURVE': 0 if self.TAC_column == 'TAC_pre_imputation' else self.curve_quality_analyzer.get_imputed_low_quality_percent(),
      'unimputed_low_quality_duration_CURVE': self.curve_quality_analyzer.get_low_quality_duration() if self.TAC_column == 'TAC_pre_imputation' else self.curve_quality_analyzer.get_unimputed_low_quality_duration(),
      'unimputed_low_quality_percent_CURVE': self.curve_quality_analyzer.get_low_quality_percent() if self.TAC_column == 'TAC_pre_imputation' else self.curve_quality_analyzer.get_unimputed_low_quality_percent(),
      'total_low_quality_duration_CURVE': self.curve_quality_analyzer.get_low_quality_duration(),
      'total_low_quality_percent_CURVE': self.curve_quality_analyzer.get_low_quality_percent(),
      'imputed_gap_duration_CURVE': 0 if self.TAC_column == 'TAC_pre_imputation' else self.curve_quality_analyzer.get_imputed_gap_duration(),
      'imputed_gap_percent_CURVE': 0 if self.TAC_column == 'TAC_pre_imputation' else self.curve_quality_analyzer.get_imputed_gap_percent(),
      'unimputed_gap_duration_CURVE': (self.curve['gap'] == 1).sum() / 60 if self.TAC_column == 'TAC_pre_imputation' else self.curve_quality_analyzer.get_unimputed_gap_duration(),
      'unimputed_gap_percent_CURVE': (self.curve['gap'] == 1).sum() / len(self.curve) if self.TAC_column == 'TAC_pre_imputation' else self.curve_quality_analyzer.get_unimputed_gap_percent(),
      'total_gap_duration_CURVE': (self.curve['gap'] == 1).sum() / 60,
      'total_gap_percent_CURVE': (self.curve['gap'] == 1).sum() / len(self.curve),
      'gap_imputation_ratio_CURVE': self.curve_quality_analyzer.get_gap_imputation_ratio(),
      'imputed_non_wear_duration_CURVE': 0 if self.TAC_column == 'TAC_pre_imputation' else self.curve_quality_analyzer.get_imputed_non_wear_duration(),
      'imputed_non_wear_percent_CURVE': 0 if self.TAC_column == 'TAC_pre_imputation' else self.curve_quality_analyzer.get_imputed_non_wear_percent(),
      'unimputed_non_wear_duration_CURVE': (self.curve['non_wear'] == 1).sum() / 60 if self.TAC_column == 'TAC_pre_imputation' else self.curve_quality_analyzer.get_unimputed_non_wear_duration(),
      'unimputed_non_wear_percent_CURVE': (self.curve['non_wear'] == 1).sum() / len(self.curve) if self.TAC_column == 'TAC_pre_imputation' else self.curve_quality_analyzer.get_unimputed_non_wear_percent(),
      'total_non_wear_duration_CURVE': (self.curve['non_wear'] == 1).sum() / 60,
      'total_non_wear_percent_CURVE': (self.curve['non_wear'] == 1).sum() / len(self.curve),
      'non_wear_imputation_ratio_CURVE': self.curve_quality_analyzer.get_non_wear_imputation_ratio(),
      'imputed_jump_duration_CURVE': 0 if self.TAC_column == 'TAC_pre_imputation' else self.curve_quality_analyzer.get_imputed_jump_duration(),
      'imputed_jump_percent_CURVE': 0 if self.TAC_column == 'TAC_pre_imputation' else self.curve_quality_analyzer.get_imputed_jump_percent(),
      'unimputed_jump_duration_CURVE': (self.curve['jump'] == 1).sum() / 60 if self.TAC_column == 'TAC_pre_imputation' else self.curve_quality_analyzer.get_unimputed_jump_duration(),
      'unimputed_jump_percent_CURVE': (self.curve['jump'] == 1).sum() / len(self.curve) if self.TAC_column == 'TAC_pre_imputation' else self.curve_quality_analyzer.get_unimputed_jump_percent(),
      'total_jump_duration_CURVE': (self.curve['jump'] == 1).sum() / 60,
      'total_jump_percent_CURVE': (self.curve['jump'] == 1).sum() / len(self.curve),
      'jump_imputation_ratio_CURVE': self.curve_quality_analyzer.get_jump_imputation_ratio(),
      'imputed_plummet_duration_CURVE': 0 if self.TAC_column == 'TAC_pre_imputation' else self.curve_quality_analyzer.get_imputed_plummet_duration(),
      'imputed_plummet_percent_CURVE': 0 if self.TAC_column == 'TAC_pre_imputation' else self.curve_quality_analyzer.get_imputed_plummet_percent(),
      'unimputed_plummet_duration_CURVE': (self.curve['plummet'] == 1).sum() / 60 if self.TAC_column == 'TAC_pre_imputation' else self.curve_quality_analyzer.get_unimputed_plummet_duration(),
      'unimputed_plummet_percent_CURVE': (self.curve['plummet'] == 1).sum() / len(self.curve) if self.TAC_column == 'TAC_pre_imputation' else self.curve_quality_analyzer.get_unimputed_plummet_percent(),
      'total_plummet_duration_CURVE': (self.curve['plummet'] == 1).sum() / 60,
      'total_plummet_percent_CURVE': (self.curve['plummet'] == 1).sum() / len(self.curve),
      'plummet_imputation_ratio_CURVE': self.curve_quality_analyzer.get_plummet_imputation_ratio(),
      'imputed_extreme_negative_duration_CURVE': 0 if self.TAC_column == 'TAC_pre_imputation' else self.curve_quality_analyzer.get_imputed_extreme_negative_duration(),
      'imputed_extreme_negative_percent_CURVE': 0 if self.TAC_column == 'TAC_pre_imputation' else self.curve_quality_analyzer.get_imputed_extreme_negative_percent(),
      'unimputed_extreme_negative_duration_CURVE': (self.curve['extreme_negative'] == 1).sum() / 60 if self.TAC_column == 'TAC_pre_imputation' else self.curve_quality_analyzer.get_unimputed_extreme_negative_duration(),
      'unimputed_extreme_negative_percent_CURVE': (self.curve['extreme_negative'] == 1).sum() / len(self.curve) if self.TAC_column == 'TAC_pre_imputation' else self.curve_quality_analyzer.get_unimputed_extreme_negative_percent(),
      'total_extreme_negative_duration_CURVE': (self.curve['extreme_negative'] == 1).sum() / 60,
      'total_extreme_negative_percent_CURVE': (self.curve['extreme_negative'] == 1).sum() / len(self.curve),
      'sub_negative_10_sum_CURVE': self.curve.loc[self.curve['extreme_negative'] == 1, self.TAC_column].sum(),
      'extreme_negative_imputation_ratio_CURVE': self.curve_quality_analyzer.get_extreme_negative_imputation_ratio(),
      'low_quality_imputation_ratio_CURVE': self.curve_quality_analyzer.get_low_quality_imputation_ratio(),
      'get_start_to_peak_interval_CURVE': self.curve_quality_analyzer.get_start_to_peak_interval(),
      'total_gaps_and_non_wear_percent_CURVE' : self.curve_quality_analyzer.get_total_gaps_and_non_wear_percent(),
      'unimputed_gaps_and_non_wear_percent_CURVE': self.curve_quality_analyzer.get_unimputed_gaps_and_non_wear_percent(),
      'below_threshold_percent_CURVE' : self.curve_quality_analyzer.get_below_threshold_percent(self.curve_threshold),
      'rise_complete_percent_CURVE' : 1 if first_tac <= self.curve_threshold else (peak_tac - first_tac) / relative_peak,
      'rise_imputed_percent_CURVE': DataQualityAnalyzer(rise_portion, self.TAC_column).get_rise_imputed_percent(),
      'fall_complete_percent_CURVE' : 1 if last_tac <= self.curve_threshold else (peak_tac - last_tac) / relative_peak,
      'fall_imputed_percent_CURVE': DataQualityAnalyzer(fall_portion, self.TAC_column).get_fall_imputed_percent(),
      'ascending_imputed_percent_CURVE': self.curve_quality_analyzer.get_ascending_imputed_percent(),
      'descending_imputed_percent_CURVE': self.curve_quality_analyzer.get_descending_imputed_percent(),
      'high_quality_duration_CURVE': self.curve_quality_analyzer.get_high_quality_duration(),
      'high_quality_percent_CURVE': self.curve_quality_analyzer.get_high_quality_percent(),
      'high_quality_above_threshold_duration_CURVE': self.curve_quality_analyzer.get_high_quality_above_threshold_duration(self.curve_threshold),
    }

    self.periphery_before_quality_features = {
      'total_duration_PERIPHERY_BEFORE': len(self.periphery_before) / 60,
      'device_turned_on_duration_PERIPHERY_BEFORE': (self.periphery_before['device_turned_on'].sum()) / 60,
      'device_turned_on_percent_PERIPHERY_BEFORE': (self.periphery_before['device_turned_on'].sum()) / len(self.periphery_before) if len(self.periphery_before) > 0 else 0,
      'device_worn_duration_PERIPHERY_BEFORE': (self.periphery_before['device_worn_model'].sum()) / 60,
      'device_worn_percent_PERIPHERY_BEFORE': (self.periphery_before['device_worn_model'].sum()) / len(self.periphery_before) if len(self.periphery_before) > 0 else 0,
      'imputed_duration_PERIPHERY_BEFORE': 0 if self.TAC_column == 'TAC_pre_imputation' else self.periphery_before['imputed'].sum() / 60,
      'imputed_percent_PERIPHERY_BEFORE': 0 if self.TAC_column == 'TAC_pre_imputation' else (self.periphery_before['imputed'].sum() / len(self.periphery_before) if len(self.periphery_before) > 0 else 0),
      'imputed_low_quality_duration_PERIPHERY_BEFORE': 0 if self.TAC_column == 'TAC_pre_imputation' else self.periphery_before_quality_analyzer.get_imputed_low_quality_duration(),
      'imputed_low_quality_percent_PERIPHERY_BEFORE': 0 if self.TAC_column == 'TAC_pre_imputation' else self.periphery_before_quality_analyzer.get_imputed_low_quality_percent(),
      'unimputed_low_quality_duration_PERIPHERY_BEFORE': self.periphery_before_quality_analyzer.get_low_quality_duration() if self.TAC_column == 'TAC_pre_imputation' else self.periphery_before_quality_analyzer.get_unimputed_low_quality_duration(),
      'unimputed_low_quality_percent_PERIPHERY_BEFORE': self.periphery_before_quality_analyzer.get_low_quality_percent() if self.TAC_column == 'TAC_pre_imputation' else self.periphery_before_quality_analyzer.get_unimputed_low_quality_percent(),
      'total_low_quality_duration_PERIPHERY_BEFORE': self.periphery_before_quality_analyzer.get_low_quality_duration(),
      'total_low_quality_percent_PERIPHERY_BEFORE': self.periphery_before_quality_analyzer.get_low_quality_percent(),
      'imputed_gap_duration_PERIPHERY_BEFORE': 0 if self.TAC_column == 'TAC_pre_imputation' else self.periphery_before_quality_analyzer.get_imputed_gap_duration(),
      'imputed_gap_percent_PERIPHERY_BEFORE': 0 if self.TAC_column == 'TAC_pre_imputation' else self.periphery_before_quality_analyzer.get_imputed_gap_percent(),
      'unimputed_gap_duration_PERIPHERY_BEFORE': (self.periphery_before['gap'] == 1).sum() / 60 if self.TAC_column == 'TAC_pre_imputation' else self.periphery_before_quality_analyzer.get_unimputed_gap_duration(),
      'unimputed_gap_percent_PERIPHERY_BEFORE': (self.periphery_before['gap'] == 1).sum() / len(self.periphery_before) if self.TAC_column == 'TAC_pre_imputation' else self.periphery_before_quality_analyzer.get_unimputed_gap_percent(),
      'total_gap_duration_PERIPHERY_BEFORE': (self.periphery_before['gap'] == 1).sum() / 60,
      'total_gap_percent_PERIPHERY_BEFORE': (self.periphery_before['gap'] == 1).sum() / len(self.periphery_before) if len(self.periphery_before) > 0 else 0,
      'gap_imputation_ratio_PERIPHERY_BEFORE': self.periphery_before_quality_analyzer.get_gap_imputation_ratio(),
      'imputed_non_wear_duration_PERIPHERY_BEFORE': 0 if self.TAC_column == 'TAC_pre_imputation' else self.periphery_before_quality_analyzer.get_imputed_non_wear_duration(),
      'imputed_non_wear_percent_PERIPHERY_BEFORE': 0 if self.TAC_column == 'TAC_pre_imputation' else self.periphery_before_quality_analyzer.get_imputed_non_wear_percent(),
      'unimputed_non_wear_duration_PERIPHERY_BEFORE': (self.periphery_before['non_wear'] == 1).sum() / 60 if self.TAC_column == 'TAC_pre_imputation' else self.periphery_before_quality_analyzer.get_unimputed_non_wear_duration(),
      'unimputed_non_wear_percent_PERIPHERY_BEFORE': (self.periphery_before['non_wear'] == 1).sum() / len(self.periphery_before) if self.TAC_column == 'TAC_pre_imputation' else self.periphery_before_quality_analyzer.get_unimputed_non_wear_percent(),
      'total_non_wear_duration_PERIPHERY_BEFORE': (self.periphery_before['non_wear'] == 1).sum() / 60,
      'total_non_wear_percent_PERIPHERY_BEFORE': (self.periphery_before['non_wear'] == 1).sum() / len(self.periphery_before) if len(self.periphery_before) > 0 else 0,
      'non_wear_imputation_ratio_PERIPHERY_BEFORE': self.periphery_before_quality_analyzer.get_non_wear_imputation_ratio(),
      'imputed_jump_duration_PERIPHERY_BEFORE': 0 if self.TAC_column == 'TAC_pre_imputation' else self.periphery_before_quality_analyzer.get_imputed_jump_duration(),
      'imputed_jump_percent_PERIPHERY_BEFORE': 0 if self.TAC_column == 'TAC_pre_imputation' else self.periphery_before_quality_analyzer.get_imputed_jump_percent(),
      'unimputed_jump_duration_PERIPHERY_BEFORE': (self.periphery_before['jump'] == 1).sum() / 60 if self.TAC_column == 'TAC_pre_imputation' else self.periphery_before_quality_analyzer.get_unimputed_jump_duration(),
      'unimputed_jump_percent_PERIPHERY_BEFORE': (self.periphery_before['jump'] == 1).sum() / len(self.periphery_before) if self.TAC_column == 'TAC_pre_imputation' else self.periphery_before_quality_analyzer.get_unimputed_jump_percent(),
      'total_jump_duration_PERIPHERY_BEFORE': (self.periphery_before['jump'] == 1).sum() / 60,
      'total_jump_percent_PERIPHERY_BEFORE': (self.periphery_before['jump'] == 1).sum() / len(self.periphery_before) if len(self.periphery_before) > 0 else 0,
      'jump_imputation_ratio_PERIPHERY_BEFORE': self.periphery_before_quality_analyzer.get_jump_imputation_ratio(),
      'imputed_plummet_duration_PERIPHERY_BEFORE': 0 if self.TAC_column == 'TAC_pre_imputation' else self.periphery_before_quality_analyzer.get_imputed_plummet_duration(),
      'imputed_plummet_percent_PERIPHERY_BEFORE': 0 if self.TAC_column == 'TAC_pre_imputation' else self.periphery_before_quality_analyzer.get_imputed_plummet_percent(),
      'unimputed_plummet_duration_PERIPHERY_BEFORE': (self.periphery_before['plummet'] == 1).sum() / 60 if self.TAC_column == 'TAC_pre_imputation' else self.periphery_before_quality_analyzer.get_unimputed_plummet_duration(),
      'unimputed_plummet_percent_PERIPHERY_BEFORE': (self.periphery_before['plummet'] == 1).sum() / len(self.periphery_before) if self.TAC_column == 'TAC_pre_imputation' else self.periphery_before_quality_analyzer.get_unimputed_plummet_percent(),
      'total_plummet_duration_PERIPHERY_BEFORE': (self.periphery_before['plummet'] == 1).sum() / 60,
      'total_plummet_percent_PERIPHERY_BEFORE': (self.periphery_before['plummet'] == 1).sum() / len(self.periphery_before) if len(self.periphery_before) > 0 else 0,
      'plummet_imputation_ratio_PERIPHERY_BEFORE': self.periphery_before_quality_analyzer.get_plummet_imputation_ratio(),
      'imputed_extreme_negative_duration_PERIPHERY_BEFORE': 0 if self.TAC_column == 'TAC_pre_imputation' else self.periphery_before_quality_analyzer.get_imputed_extreme_negative_duration(),
      'imputed_extreme_negative_percent_PERIPHERY_BEFORE': 0 if self.TAC_column == 'TAC_pre_imputation' else self.periphery_before_quality_analyzer.get_imputed_extreme_negative_percent(),
      'unimputed_extreme_negative_duration_PERIPHERY_BEFORE': (self.periphery_before['extreme_negative'] == 1).sum() / 60 if self.TAC_column == 'TAC_pre_imputation' else self.periphery_before_quality_analyzer.get_unimputed_extreme_negative_duration(),
      'unimputed_extreme_negative_percent_PERIPHERY_BEFORE': (self.periphery_before['extreme_negative'] == 1).sum() / len(self.periphery_before) if self.TAC_column == 'TAC_pre_imputation' else self.periphery_before_quality_analyzer.get_unimputed_extreme_negative_percent(),
      'total_extreme_negative_duration_PERIPHERY_BEFORE': (self.periphery_before['extreme_negative'] == 1).sum() / 60,
      'total_extreme_negative_percent_PERIPHERY_BEFORE': (self.periphery_before['extreme_negative'] == 1).sum() / len(self.periphery_before) if len(self.periphery_before) > 0 else 0,
      'sub_negative_10_sum_PERIPHERY_BEFORE': self.periphery_before.loc[self.periphery_before['extreme_negative'] == 1, self.TAC_column].sum() if len(self.periphery_before) > 0 else 0,
      'extreme_negative_imputation_ratio_PERIPHERY_BEFORE': self.periphery_before_quality_analyzer.get_extreme_negative_imputation_ratio(),
      'low_quality_imputation_ratio_PERIPHERY_BEFORE': self.periphery_before_quality_analyzer.get_low_quality_imputation_ratio(),
      'total_gaps_and_non_wear_percent_PERIPHERY_BEFORE': self.periphery_before_quality_analyzer.get_total_gaps_and_non_wear_percent(),
      'unimputed_gaps_and_non_wear_percent_PERIPHERY_BEFORE': self.periphery_before_quality_analyzer.get_unimputed_gaps_and_non_wear_percent(),
    }

    self.periphery_after_quality_features = {
      'total_duration_PERIPHERY_AFTER': len(self.periphery_after) / 60,
      'device_turned_on_duration_PERIPHERY_AFTER': (self.periphery_after['device_turned_on'].sum()) / 60,
      'device_turned_on_percent_PERIPHERY_AFTER': (self.periphery_after['device_turned_on'].sum()) / len(self.periphery_after) if len(self.periphery_after) > 0 else 0,
      'device_worn_duration_PERIPHERY_AFTER': (self.periphery_after['device_worn_model'].sum()) / 60,
      'device_worn_percent_PERIPHERY_AFTER': (self.periphery_after['device_worn_model'].sum()) / len(self.periphery_after) if len(self.periphery_after) > 0 else 0,
      'imputed_duration_PERIPHERY_AFTER': 0 if self.TAC_column == 'TAC_pre_imputation' else self.periphery_after['imputed'].sum() / 60,
      'imputed_percent_PERIPHERY_AFTER': 0 if self.TAC_column == 'TAC_pre_imputation' else (self.periphery_after['imputed'].sum() / len(self.periphery_after) if len(self.periphery_after) > 0 else 0),
      'imputed_low_quality_duration_PERIPHERY_AFTER': 0 if self.TAC_column == 'TAC_pre_imputation' else self.periphery_after_quality_analyzer.get_imputed_low_quality_duration(),
      'imputed_low_quality_percent_PERIPHERY_AFTER': 0 if self.TAC_column == 'TAC_pre_imputation' else self.periphery_after_quality_analyzer.get_imputed_low_quality_percent(),
      'unimputed_low_quality_duration_PERIPHERY_AFTER': self.periphery_after_quality_analyzer.get_low_quality_duration() if self.TAC_column == 'TAC_pre_imputation' else self.periphery_after_quality_analyzer.get_unimputed_low_quality_duration(),
      'unimputed_low_quality_percent_PERIPHERY_AFTER': self.periphery_after_quality_analyzer.get_low_quality_percent() if self.TAC_column == 'TAC_pre_imputation' else self.periphery_after_quality_analyzer.get_unimputed_low_quality_percent(),
      'total_low_quality_duration_PERIPHERY_AFTER': self.periphery_after_quality_analyzer.get_low_quality_duration(),
      'total_low_quality_percent_PERIPHERY_AFTER': self.periphery_after_quality_analyzer.get_low_quality_percent(),
      'imputed_gap_duration_PERIPHERY_AFTER': 0 if self.TAC_column == 'TAC_pre_imputation' else self.periphery_after_quality_analyzer.get_imputed_gap_duration(),
      'imputed_gap_percent_PERIPHERY_AFTER': 0 if self.TAC_column == 'TAC_pre_imputation' else self.periphery_after_quality_analyzer.get_imputed_gap_percent(),
      'unimputed_gap_duration_PERIPHERY_AFTER': (self.periphery_after['gap'] == 1).sum() / 60 if self.TAC_column == 'TAC_pre_imputation' else self.periphery_after_quality_analyzer.get_unimputed_gap_duration(),
      'unimputed_gap_percent_PERIPHERY_AFTER': (self.periphery_after['gap'] == 1).sum() / len(self.periphery_after) if self.TAC_column == 'TAC_pre_imputation' else self.periphery_after_quality_analyzer.get_unimputed_gap_percent(),
      'total_gap_duration_PERIPHERY_AFTER': (self.periphery_after['gap'] == 1).sum() / 60,
      'total_gap_percent_PERIPHERY_AFTER': (self.periphery_after['gap'] == 1).sum() / len(self.periphery_after) if len(self.periphery_after) > 0 else 0,
      'gap_imputation_ratio_PERIPHERY_AFTER': self.periphery_after_quality_analyzer.get_gap_imputation_ratio(),
      'imputed_non_wear_duration_PERIPHERY_AFTER': 0 if self.TAC_column == 'TAC_pre_imputation' else self.periphery_after_quality_analyzer.get_imputed_non_wear_duration(),
      'imputed_non_wear_percent_PERIPHERY_AFTER': 0 if self.TAC_column == 'TAC_pre_imputation' else self.periphery_after_quality_analyzer.get_imputed_non_wear_percent(),
      'unimputed_non_wear_duration_PERIPHERY_AFTER': (self.periphery_after['non_wear'] == 1).sum() / 60 if self.TAC_column == 'TAC_pre_imputation' else self.periphery_after_quality_analyzer.get_unimputed_non_wear_duration(),
      'unimputed_non_wear_percent_PERIPHERY_AFTER': (self.periphery_after['non_wear'] == 1).sum() / len(self.periphery_after) if self.TAC_column == 'TAC_pre_imputation' else self.periphery_after_quality_analyzer.get_unimputed_non_wear_percent(),
      'total_non_wear_duration_PERIPHERY_AFTER': (self.periphery_after['non_wear'] == 1).sum() / 60,
      'total_non_wear_percent_PERIPHERY_AFTER': (self.periphery_after['non_wear'] == 1).sum() / len(self.periphery_after) if len(self.periphery_after) > 0 else 0,
      'non_wear_imputation_ratio_PERIPHERY_AFTER': self.periphery_after_quality_analyzer.get_non_wear_imputation_ratio(),
      'imputed_jump_duration_PERIPHERY_AFTER': 0 if self.TAC_column == 'TAC_pre_imputation' else self.periphery_after_quality_analyzer.get_imputed_jump_duration(),
      'imputed_jump_percent_PERIPHERY_AFTER': 0 if self.TAC_column == 'TAC_pre_imputation' else self.periphery_after_quality_analyzer.get_imputed_jump_percent(),
      'unimputed_jump_duration_PERIPHERY_AFTER': (self.periphery_after['jump'] == 1).sum() / 60 if self.TAC_column == 'TAC_pre_imputation' else self.periphery_after_quality_analyzer.get_unimputed_jump_duration(),
      'unimputed_jump_percent_PERIPHERY_AFTER': (self.periphery_after['jump'] == 1).sum() / len(self.periphery_after) if self.TAC_column == 'TAC_pre_imputation' else self.periphery_after_quality_analyzer.get_unimputed_jump_percent(),
      'total_jump_duration_PERIPHERY_AFTER': (self.periphery_after['jump'] == 1).sum() / 60,
      'total_jump_percent_PERIPHERY_AFTER': (self.periphery_after['jump'] == 1).sum() / len(self.periphery_after) if len(self.periphery_after) > 0 else 0,
      'jump_imputation_ratio_PERIPHERY_AFTER': self.periphery_after_quality_analyzer.get_jump_imputation_ratio(),
      'imputed_plummet_duration_PERIPHERY_AFTER': 0 if self.TAC_column == 'TAC_pre_imputation' else self.periphery_after_quality_analyzer.get_imputed_plummet_duration(),
      'imputed_plummet_percent_PERIPHERY_AFTER': 0 if self.TAC_column == 'TAC_pre_imputation' else self.periphery_after_quality_analyzer.get_imputed_plummet_percent(),
      'unimputed_plummet_duration_PERIPHERY_AFTER': (self.periphery_after['plummet'] == 1).sum() / 60 if self.TAC_column == 'TAC_pre_imputation' else self.periphery_after_quality_analyzer.get_unimputed_plummet_duration(),
      'unimputed_plummet_percent_PERIPHERY_AFTER': (self.periphery_after['plummet'] == 1).sum() / len(self.periphery_after) if self.TAC_column == 'TAC_pre_imputation' else self.periphery_after_quality_analyzer.get_unimputed_plummet_percent(),
      'total_plummet_duration_PERIPHERY_AFTER': (self.periphery_after['plummet'] == 1).sum() / 60,
      'total_plummet_percent_PERIPHERY_AFTER': (self.periphery_after['plummet'] == 1).sum() / len(self.periphery_after) if len(self.periphery_after) > 0 else 0,
      'plummet_imputation_ratio_PERIPHERY_AFTER': self.periphery_after_quality_analyzer.get_plummet_imputation_ratio(),
      'imputed_extreme_negative_duration_PERIPHERY_AFTER': 0 if self.TAC_column == 'TAC_pre_imputation' else self.periphery_after_quality_analyzer.get_imputed_extreme_negative_duration(),
      'imputed_extreme_negative_percent_PERIPHERY_AFTER': 0 if self.TAC_column == 'TAC_pre_imputation' else self.periphery_after_quality_analyzer.get_imputed_extreme_negative_percent(),
      'unimputed_extreme_negative_duration_PERIPHERY_AFTER': (self.periphery_after['extreme_negative'] == 1).sum() / 60 if self.TAC_column == 'TAC_pre_imputation' else self.periphery_after_quality_analyzer.get_unimputed_extreme_negative_duration(),
      'unimputed_extreme_negative_percent_PERIPHERY_AFTER': (self.periphery_after['extreme_negative'] == 1).sum() / len(self.periphery_after) if self.TAC_column == 'TAC_pre_imputation' else self.periphery_after_quality_analyzer.get_unimputed_extreme_negative_percent(),
      'total_extreme_negative_duration_PERIPHERY_AFTER': (self.periphery_after['extreme_negative'] == 1).sum() / 60,
      'total_extreme_negative_percent_PERIPHERY_AFTER': (self.periphery_after['extreme_negative'] == 1).sum() / len(self.periphery_after) if len(self.periphery_after) > 0 else 0,
      'sub_negative_10_sum_PERIPHERY_AFTER': self.periphery_after.loc[self.periphery_after['extreme_negative'] == 1, self.TAC_column].sum() if len(self.periphery_after) > 0 else 0,
      'extreme_negative_imputation_ratio_PERIPHERY_AFTER': self.periphery_after_quality_analyzer.get_extreme_negative_imputation_ratio(),
      'low_quality_imputation_ratio_PERIPHERY_AFTER': self.periphery_after_quality_analyzer.get_low_quality_imputation_ratio(),
      'total_gaps_and_non_wear_percent_PERIPHERY_AFTER': self.periphery_after_quality_analyzer.get_total_gaps_and_non_wear_percent(),
      'unimputed_gaps_and_non_wear_percent_PERIPHERY_AFTER': self.periphery_after_quality_analyzer.get_unimputed_gaps_and_non_wear_percent(),
    }

    self.region_quality_features = {
      'started_curve_count_REGION': self.region_tac_analyzer.count_started_curves(threshold=self.curve_threshold, min_length=10),
      'complete_curve_count_REGION': self.region_tac_analyzer.count_complete_curves(threshold=self.curve_threshold, min_length=10),      
      'total_duration_REGION': len(self.region) / 60,
      'device_turned_on_duration_REGION': (self.region['device_turned_on'].sum()) / 60,
      'device_turned_on_percent_REGION': (self.region['device_turned_on'].sum()) / len(self.region),
      'device_worn_duration_REGION': (self.region['device_worn_model'].sum()) / 60,
      'device_worn_percent_REGION': (self.region['device_worn_model'].sum()) / len(self.region),
      'flatline_max_REGION': self.region_quality_analyzer.count_longest_tac_flatline(),
      'flatlined_percent_REGION': (self.region_quality_analyzer.count_longest_tac_flatline() / len(self.region)),
      'imputed_duration_REGION': 0 if self.TAC_column == 'TAC_pre_imputation' else self.region['imputed'].sum() / 60,
      'imputed_percent_REGION': 0 if self.TAC_column == 'TAC_pre_imputation' else self.region['imputed'].sum() / len(self.region),
      'imputed_low_quality_duration_REGION': 0 if self.TAC_column == 'TAC_pre_imputation' else self.region_quality_analyzer.get_imputed_low_quality_duration(),
      'imputed_low_quality_percent_REGION': 0 if self.TAC_column == 'TAC_pre_imputation' else self.region_quality_analyzer.get_imputed_low_quality_percent(),
      'unimputed_low_quality_duration_REGION': self.region_quality_analyzer.get_low_quality_duration() if self.TAC_column == 'TAC_pre_imputation' else self.region_quality_analyzer.get_unimputed_low_quality_duration(),
      'unimputed_low_quality_percent_REGION': self.region_quality_analyzer.get_low_quality_percent() if self.TAC_column == 'TAC_pre_imputation' else self.region_quality_analyzer.get_unimputed_low_quality_percent(),
      'total_low_quality_duration_REGION': self.region_quality_analyzer.get_low_quality_duration(),
      'total_low_quality_percent_REGION': self.region_quality_analyzer.get_low_quality_percent(),
      'imputed_gap_duration_REGION': 0 if self.TAC_column == 'TAC_pre_imputation' else self.region_quality_analyzer.get_imputed_gap_duration(),
      'imputed_gap_percent_REGION': 0 if self.TAC_column == 'TAC_pre_imputation' else self.region_quality_analyzer.get_imputed_gap_percent(),
      'unimputed_gap_duration_REGION': (self.region['gap'] == 1).sum() / 60 if self.TAC_column == 'TAC_pre_imputation' else self.region_quality_analyzer.get_unimputed_gap_duration(),
      'unimputed_gap_percent_REGION': (self.region['gap'] == 1).sum() / len(self.region) if self.TAC_column == 'TAC_pre_imputation' else self.region_quality_analyzer.get_unimputed_gap_percent(),
      'total_gap_duration_REGION': (self.region['gap'] == 1).sum() / 60,
      'total_gap_percent_REGION': (self.region['gap'] == 1).sum() / len(self.region),
      'gap_imputation_ratio_REGION': self.region_quality_analyzer.get_gap_imputation_ratio(),
      'imputed_non_wear_duration_REGION': 0 if self.TAC_column == 'TAC_pre_imputation' else self.region_quality_analyzer.get_imputed_non_wear_duration(),
      'imputed_non_wear_percent_REGION': 0 if self.TAC_column == 'TAC_pre_imputation' else self.region_quality_analyzer.get_imputed_non_wear_percent(),
      'unimputed_non_wear_duration_REGION': (self.region['non_wear'] == 1).sum() / 60 if self.TAC_column == 'TAC_pre_imputation' else self.region_quality_analyzer.get_unimputed_non_wear_duration(),
      'unimputed_non_wear_percent_REGION': (self.region['non_wear'] == 1).sum() / len(self.region) if self.TAC_column == 'TAC_pre_imputation' else self.region_quality_analyzer.get_unimputed_non_wear_percent(),
      'total_non_wear_duration_REGION': (self.region['non_wear'] == 1).sum() / 60,
      'total_non_wear_percent_REGION': (self.region['non_wear'] == 1).sum() / len(self.region),
      'non_wear_imputation_ratio_REGION': self.region_quality_analyzer.get_non_wear_imputation_ratio(),
      'imputed_jump_duration_REGION': 0 if self.TAC_column == 'TAC_pre_imputation' else self.region_quality_analyzer.get_imputed_jump_duration(),
      'imputed_jump_percent_REGION': 0 if self.TAC_column == 'TAC_pre_imputation' else self.region_quality_analyzer.get_imputed_jump_percent(),
      'unimputed_jump_duration_REGION': (self.region['jump'] == 1).sum() / 60 if self.TAC_column == 'TAC_pre_imputation' else self.region_quality_analyzer.get_unimputed_jump_duration(),
      'unimputed_jump_percent_REGION': (self.region['jump'] == 1).sum() / len(self.region) if self.TAC_column == 'TAC_pre_imputation' else self.region_quality_analyzer.get_unimputed_jump_percent(),
      'total_jump_duration_REGION': (self.region['jump'] == 1).sum() / 60,
      'total_jump_percent_REGION': (self.region['jump'] == 1).sum() / len(self.region),
      'jump_imputation_ratio_REGION': self.region_quality_analyzer.get_jump_imputation_ratio(),
      'imputed_plummet_duration_REGION': 0 if self.TAC_column == 'TAC_pre_imputation' else self.region_quality_analyzer.get_imputed_plummet_duration(),
      'imputed_plummet_percent_REGION': 0 if self.TAC_column == 'TAC_pre_imputation' else self.region_quality_analyzer.get_imputed_plummet_percent(),
      'unimputed_plummet_duration_REGION': (self.region['plummet'] == 1).sum() / 60 if self.TAC_column == 'TAC_pre_imputation' else self.region_quality_analyzer.get_unimputed_plummet_duration(),
      'unimputed_plummet_percent_REGION': (self.region['plummet'] == 1).sum() / len(self.region) if self.TAC_column == 'TAC_pre_imputation' else self.region_quality_analyzer.get_unimputed_plummet_percent(),
      'total_plummet_duration_REGION': (self.region['plummet'] == 1).sum() / 60,
      'total_plummet_percent_REGION': (self.region['plummet'] == 1).sum() / len(self.region),
      'plummet_imputation_ratio_REGION': self.region_quality_analyzer.get_plummet_imputation_ratio(),
      'imputed_extreme_negative_duration_REGION': 0 if self.TAC_column == 'TAC_pre_imputation' else self.region_quality_analyzer.get_imputed_extreme_negative_duration(),
      'imputed_extreme_negative_percent_REGION': 0 if self.TAC_column == 'TAC_pre_imputation' else self.region_quality_analyzer.get_imputed_extreme_negative_percent(),
      'unimputed_extreme_negative_duration_REGION': (self.region['extreme_negative'] == 1).sum() / 60 if self.TAC_column == 'TAC_pre_imputation' else self.region_quality_analyzer.get_unimputed_extreme_negative_duration(),
      'unimputed_extreme_negative_percent_REGION': (self.region['extreme_negative'] == 1).sum() / len(self.region) if self.TAC_column == 'TAC_pre_imputation' else self.region_quality_analyzer.get_unimputed_extreme_negative_percent(),
      'total_extreme_negative_duration_REGION': (self.region['extreme_negative'] == 1).sum() / 60,
      'total_extreme_negative_percent_REGION': (self.region['extreme_negative'] == 1).sum() / len(self.region),
      'sub_negative_10_sum_REGION': self.region.loc[self.region['extreme_negative'] == 1, self.TAC_column].sum(),
      'extreme_negative_imputation_ratio_REGION': self.region_quality_analyzer.get_extreme_negative_imputation_ratio(),
      'low_quality_imputation_ratio_REGION': self.region_quality_analyzer.get_low_quality_imputation_ratio(),
      'total_gaps_and_non_wear_percent_REGION': self.region_quality_analyzer.get_total_gaps_and_non_wear_percent(),
      'unimputed_gaps_and_non_wear_percent_REGION': self.region_quality_analyzer.get_unimputed_gaps_and_non_wear_percent(),
    }

    self.curve_tac_features = {
      'begin_CURVE': self.curve['datetime'].iloc[0],
      'end_CURVE': self.curve['datetime'].iloc[-1],
      'duration_CURVE': ((self.curve['datetime'].iloc[-1] - self.curve['datetime'].iloc[0]).total_seconds() + 60) / 3600,
      'first_tac_CURVE': first_tac,
      'last_tac_CURVE': last_tac,
      'mean_tac_CURVE': mean_tac,
      'sd_tac_CURVE': sd_tac,
      'sem_tac_CURVE': sem_tac,
      'peak_CURVE': peak_tac,
      'auc_total_CURVE' : self.curve_tac_analyzer.get_auc(),
      'auc_relative_CURVE' : self.curve_tac_analyzer.get_curve_auc(self.curve_threshold),
      'rise_duration_CURVE' : rise_duration,
      'fall_duration_CURVE' : fall_duration,
      'relative_peak_CURVE' : relative_peak,
      'rise_fall_rate_CURVE': ((self.curve['datetime'].iloc[-1] - self.curve['datetime'].iloc[0]).total_seconds() + 60) / 3600 / relative_peak if relative_peak > 0 else None,
      'rise_rate_CURVE' : self.curve_tac_analyzer.get_rise_rate(rise_duration, relative_peak, self.curve_threshold),
      'rise_rate_point_to_point_CURVE': self.curve_tac_analyzer.get_point_to_point_rise_rate(curve_start_index),
      'rise_duration_point_to_point_CURVE': self.curve_tac_analyzer.get_point_to_point_rise_duration(curve_start_index),
      'rise_rate_1hr_CURVE': self.curve_tac_analyzer.get_rise_rate_1hr(curve_start_index, peak_index, self.curve_threshold),
      'rise_rate_2hr_CURVE': self.curve_tac_analyzer.get_rise_rate_2hr(curve_start_index, peak_index, self.curve_threshold),
      'fall_rate_CURVE' : self.curve_tac_analyzer.get_fall_rate(fall_duration, relative_peak),
      'fall_rate_point_to_point_CURVE': self.curve_tac_analyzer.get_point_to_point_fall_rate(peak_index),
      'fall_duration_point_to_point_CURVE': self.curve_tac_analyzer.get_point_to_point_fall_duration(peak_index),
      'fall_rate_1hr_CURVE': self.curve_tac_analyzer.get_fall_rate_1hr(peak_index, self.curve_threshold),
      'fall_rate_2hr_CURVE': self.curve_tac_analyzer.get_fall_rate_2hr(peak_index, self.curve_threshold),
      'smoothed_curve_plot': None,
      'signal_processing_plot': None,
      'device_removal_plot': None,
      'signal_processing_plot_wide': None,
    }

    self.all_features = {
      'subid': self.subid,
      'dataset_id': self.dataset_identifier,
      'curve_id': self.curve_id,
      'curve_count': self.curve_count,
      'curve_threshold': self.curve_threshold,
      **self.device_info,
      **self.periphery_before_quality_features,
      **self.periphery_after_quality_features,
      **self.curve_quality_features,
      **self.region_quality_features,
      **self.curve_tac_features
    }

    self.features = pd.DataFrame([self.all_features])
    self.flagger = featureFlagger(self.features, flag_selections=flag_selections)
    flags = self.flagger.run_flags_and_validation()
    self.periphery_flag_columns = flags['periphery_flags']
    self.curve_flag_columns = flags['curve_flags']
    self.features = self.flagger.ftrs
    self.row = self.features.loc[0]
    flag_columns = [col for col in self.row.index if col.startswith('FLAG_')]
    matching_flags = [col for col in flag_columns if self.row[col] == 1]
    self.flag_column = matching_flags[0] if len(matching_flags) == 1 else "None"
    self.flag_column = "Multiple" if len(matching_flags) > 1 else self.flag_column 
  
    self.curve_plot_annotations = {
      'Curve Start': self.curve.iloc[0]['datetime'],
      'Curve End': self.curve.iloc[-1]['datetime'],
    }

    self.day_plot_annotations = {
      'Curve Start': self.curve.iloc[0]['datetime'],
      'Curve End': self.curve.iloc[-1]['datetime'],
    }
  
  def update_plot_annotations(self, event_labels):
    curve_event_labels = event_labels[
      (event_labels['timestamp'] >= self.region.iloc[0]['datetime']) & 
      (event_labels['timestamp'] <= self.region.iloc[-1]['datetime'])
    ]
    for i, row in curve_event_labels.iterrows():
      self.curve_plot_annotations[row['label']] = row['timestamp']
      
    day_event_labels = event_labels[
      (event_labels['timestamp'] >= self.day_region.iloc[0]['datetime']) & 
      (event_labels['timestamp'] <= self.day_region.iloc[-1]['datetime'])
    ]
    for i, row in day_event_labels.iterrows():
      self.day_plot_annotations[row['label']] = row['timestamp']

  def create_graphs(self, plot_folder):
    plot_df = self.region
    date = self.curve.iloc[0]['datetime'].strftime('%B %d, %Y')
    subtitle_text = f'SubID: {self.subid} -- Date: {date} -- Curve: {self.curve_id} -- Dataset ID: {self.dataset_identifier} -- FLAG: {self.flag_column}'

    self.smoothed_curve_plot = plot_smoothed_curve(
      plot_df, plot_folder, self.subid, self.dataset_identifier, self.curve_id, 
      self.curve_tac_features['peak_CURVE'], self.curve_threshold,
      df_version = 'CURVE', event_timestamps = self.curve_plot_annotations,
      subtitle_text = subtitle_text,
      tac_column = self.TAC_column
    )

    self.device_removal_plot = plot_device_removal(
      plot_df, plot_folder, self.subid, self.curve_id, self.dataset_identifier, 
      'Temperature_C', 'datetime', motion_variable='Motion', add_color=True, 
      method = 'Model Predictions', prediction_column = 'device_worn_model', df_version = 'CURVE',
      event_timestamps = self.curve_plot_annotations,
      subtitle_text = subtitle_text
    )

    self.signal_processing_plot = plot_signal_processing(
      plot_df, plot_folder, self.subid, self.curve_id, self.dataset_identifier, 'CURVE',
      self.curve_threshold, time_variable='datetime', title = f'Signal Processing',
      event_timestamps = self.curve_plot_annotations,
      subtitle_text = subtitle_text,
      show_imputations = self.TAC_column != 'TAC_pre_imputation'
    )

    self.signal_processing_plot_wide = plot_signal_processing(
      self.day_region, plot_folder, self.subid, self.curve_id, self.dataset_identifier, 'CURVE_WIDE',
      self.curve_threshold, time_variable='datetime', title = f'Signal Processing',
      event_timestamps = self.day_plot_annotations,
      subtitle_text = subtitle_text,
      show_imputations = self.TAC_column != 'TAC_pre_imputation'
    )

    self.features['smoothed_curve_plot'] = self.smoothed_curve_plot
    self.features['signal_processing_plot'] = self.signal_processing_plot
    self.features['device_removal_plot'] = self.device_removal_plot
    self.features['signal_processing_plot_wide'] = self.signal_processing_plot_wide
    self.row = self.features.loc[0]
  