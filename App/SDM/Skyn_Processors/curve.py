from App.SDM.Feature_Engineering.tac_features import *
from App.SDM.Feature_Engineering.quality_features import *
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
    self.periphery = pd.concat([
      df.loc[self.periphery_start_index:curve_start], 
      df.loc[curve_end:self.periphery_end_index]
    ])
    
    self.region = df.loc[self.periphery_start_index:self.periphery_end_index]

    curve_minutes = int(curve_end) - int(curve_start)
    buffer = max(0, (24 * 60 - curve_minutes) // 2)
    day_region_start = max(0, int(curve_start) - buffer)
    day_region_end = min(int(df.index[-1]), int(curve_end) + buffer)
    self.day_region = df.loc[day_region_start:day_region_end]
    
    self.curve.reset_index(drop=True, inplace=True)
    self.periphery.reset_index(drop=True, inplace=True) 
    self.day_region.reset_index(drop=True, inplace=True)

    self.device_ids = self.region['device_id'].unique().tolist()
    self.device_info = {
      'device_one_REGION' : self.device_ids[0] if len(self.device_ids) > 0 else None,
      'device_two_REGION' : self.device_ids[1] if len(self.device_ids) > 1 else None,
      'device_count_REGION': len(self.device_ids),
    }

    self.curve_quality_features = {
      'started_curve_count_CURVE': count_started_curves(self.curve, self.TAC_column, threshold=self.curve_threshold, min_length=10),
      'complete_curve_count_CURVE': count_complete_curves(self.curve, self.TAC_column, threshold=self.curve_threshold, min_length=10),      
      'total_duration_CURVE': len(self.curve) / 60,
      'device_turned_on_duration_CURVE': (self.curve['device_turned_on'].sum()) / 60,
      'device_turned_on_percent_CURVE': (self.curve['device_turned_on'].sum()) / len(self.curve),
      'device_worn_duration_CURVE': (self.curve['device_worn_model'].sum()) / 60,
      'device_worn_percent_CURVE': (self.curve['device_worn_model'].sum()) / len(self.curve),
      'flatline_max_CURVE': count_longest_tac_flatline(self.curve),
      'flatlined_percent_CURVE': (count_longest_tac_flatline(self.curve) / len(self.curve)),
      'imputed_duration_CURVE': 0 if self.TAC_column == 'TAC_pre_imputation' else self.curve['imputed'].sum() / 60,
      'imputed_percent_CURVE': 0 if self.TAC_column == 'TAC_pre_imputation' else self.curve['imputed'].sum() / len(self.curve),
      'imputed_low_quality_duration_CURVE': 0 if self.TAC_column == 'TAC_pre_imputation' else get_imputed_low_quality_duration(self.curve),
      'imputed_low_quality_percent_CURVE': 0 if self.TAC_column == 'TAC_pre_imputation' else get_imputed_low_quality_percent(self.curve),
      'unimputed_low_quality_duration_CURVE': get_low_quality_duration(self.curve) if self.TAC_column == 'TAC_pre_imputation' else get_unimputed_low_quality_duration(self.curve),
      'unimputed_low_quality_percent_CURVE': get_low_quality_percent(self.curve) if self.TAC_column == 'TAC_pre_imputation' else get_unimputed_low_quality_percent(self.curve),
      'total_low_quality_duration_CURVE': get_low_quality_duration(self.curve),
      'total_low_quality_percent_CURVE': get_low_quality_percent(self.curve),
      'imputed_gap_duration_CURVE': 0 if self.TAC_column == 'TAC_pre_imputation' else get_imputed_gap_duration(self.curve),
      'imputed_gap_percent_CURVE': 0 if self.TAC_column == 'TAC_pre_imputation' else get_imputed_gap_percent(self.curve),
      'unimputed_gap_duration_CURVE': (self.curve['gap_buffered'] == 1).sum() / 60 if self.TAC_column == 'TAC_pre_imputation' else get_unimputed_gap_duration(self.curve),
      'unimputed_gap_percent_CURVE': (self.curve['gap_buffered'] == 1).sum() / len(self.curve) if self.TAC_column == 'TAC_pre_imputation' else get_unimputed_gap_percent(self.curve),
      'total_gap_duration_CURVE': (self.curve['gap_buffered'] == 1).sum() / 60,
      'total_gap_percent_CURVE': (self.curve['gap_buffered'] == 1).sum() / len(self.curve),
      'gap_imputation_ratio_CURVE': get_gap_imputation_ratio(self.curve),
      'imputed_non_wear_duration_CURVE': 0 if self.TAC_column == 'TAC_pre_imputation' else get_imputed_non_wear_duration(self.curve),
      'imputed_non_wear_percent_CURVE': 0 if self.TAC_column == 'TAC_pre_imputation' else get_imputed_non_wear_percent(self.curve),
      'unimputed_non_wear_duration_CURVE': (self.curve['non_wear_buffered'] == 1).sum() / 60 if self.TAC_column == 'TAC_pre_imputation' else get_unimputed_non_wear_duration(self.curve),
      'unimputed_non_wear_percent_CURVE': (self.curve['non_wear_buffered'] == 1).sum() / len(self.curve) if self.TAC_column == 'TAC_pre_imputation' else get_unimputed_non_wear_percent(self.curve),
      'total_non_wear_duration_CURVE': (self.curve['non_wear_buffered'] == 1).sum() / 60,
      'total_non_wear_percent_CURVE': (self.curve['non_wear_buffered'] == 1).sum() / len(self.curve),
      'non_wear_imputation_ratio_CURVE': get_non_wear_imputation_ratio(self.curve),
      'imputed_jump_duration_CURVE': 0 if self.TAC_column == 'TAC_pre_imputation' else get_imputed_jump_duration(self.curve),
      'imputed_jump_percent_CURVE': 0 if self.TAC_column == 'TAC_pre_imputation' else get_imputed_jump_percent(self.curve),
      'unimputed_jump_duration_CURVE': (self.curve['jump'] == 1).sum() / 60 if self.TAC_column == 'TAC_pre_imputation' else get_unimputed_jump_duration(self.curve),
      'unimputed_jump_percent_CURVE': (self.curve['jump'] == 1).sum() / len(self.curve) if self.TAC_column == 'TAC_pre_imputation' else get_unimputed_jump_percent(self.curve),
      'total_jump_duration_CURVE': (self.curve['jump'] == 1).sum() / 60,
      'total_jump_percent_CURVE': (self.curve['jump'] == 1).sum() / len(self.curve),
      'jump_imputation_ratio_CURVE': get_jump_imputation_ratio(self.curve),
      'imputed_plummet_duration_CURVE': 0 if self.TAC_column == 'TAC_pre_imputation' else get_imputed_plummet_duration(self.curve),
      'imputed_plummet_percent_CURVE': 0 if self.TAC_column == 'TAC_pre_imputation' else get_imputed_plummet_percent(self.curve),
      'unimputed_plummet_duration_CURVE': (self.curve['plummet'] == 1).sum() / 60 if self.TAC_column == 'TAC_pre_imputation' else get_unimputed_plummet_duration(self.curve),
      'unimputed_plummet_percent_CURVE': (self.curve['plummet'] == 1).sum() / len(self.curve) if self.TAC_column == 'TAC_pre_imputation' else get_unimputed_plummet_percent(self.curve),
      'total_plummet_duration_CURVE': (self.curve['plummet'] == 1).sum() / 60,
      'total_plummet_percent_CURVE': (self.curve['plummet'] == 1).sum() / len(self.curve),
      'plummet_imputation_ratio_CURVE': get_plummet_imputation_ratio(self.curve),
      'imputed_extreme_negative_duration_CURVE': 0 if self.TAC_column == 'TAC_pre_imputation' else get_imputed_extreme_negative_duration(self.curve),
      'imputed_extreme_negative_percent_CURVE': 0 if self.TAC_column == 'TAC_pre_imputation' else get_imputed_extreme_negative_percent(self.curve),
      'unimputed_extreme_negative_duration_CURVE': (self.curve['extreme_negative'] == 1).sum() / 60 if self.TAC_column == 'TAC_pre_imputation' else get_unimputed_extreme_negative_duration(self.curve),
      'unimputed_extreme_negative_percent_CURVE': (self.curve['extreme_negative'] == 1).sum() / len(self.curve) if self.TAC_column == 'TAC_pre_imputation' else get_unimputed_extreme_negative_percent(self.curve),
      'total_extreme_negative_duration_CURVE': (self.curve['extreme_negative'] == 1).sum() / 60,
      'total_extreme_negative_percent_CURVE': (self.curve['extreme_negative'] == 1).sum() / len(self.curve),
      'sub_negative_10_sum_CURVE': self.curve.loc[self.curve['extreme_negative'] == 1, self.TAC_column].sum(),
      'extreme_negative_imputation_ratio_CURVE': get_extreme_negative_imputation_ratio(self.curve),
      'low_quality_imputation_ratio_CURVE': get_low_quality_imputation_ratio(self.curve),
      'start_to_peak_interval_CURVE': start_to_peak_interval(self.curve, self.TAC_column),
    }

    self.periphery_quality_features = {
      'total_duration_PERIPHERY': len(self.periphery) / 60,
      'device_turned_on_duration_PERIPHERY': (self.periphery['device_turned_on'].sum()) / 60,
      'device_turned_on_percent_PERIPHERY': (self.periphery['device_turned_on'].sum()) / len(self.periphery),
      'device_worn_duration_PERIPHERY': (self.periphery['device_worn_model'].sum()) / 60,
      'device_worn_percent_PERIPHERY': (self.periphery['device_worn_model'].sum()) / len(self.periphery),
      'imputed_duration_PERIPHERY': 0 if self.TAC_column == 'TAC_pre_imputation' else self.periphery['imputed'].sum() / 60,
      'imputed_percent_PERIPHERY': 0 if self.TAC_column == 'TAC_pre_imputation' else self.periphery['imputed'].sum() / len(self.periphery),
      'imputed_low_quality_duration_PERIPHERY': 0 if self.TAC_column == 'TAC_pre_imputation' else get_imputed_low_quality_duration(self.periphery),
      'imputed_low_quality_percent_PERIPHERY': 0 if self.TAC_column == 'TAC_pre_imputation' else get_imputed_low_quality_percent(self.periphery),
      'unimputed_low_quality_duration_PERIPHERY': get_low_quality_duration(self.periphery) if self.TAC_column == 'TAC_pre_imputation' else get_unimputed_low_quality_duration(self.periphery),
      'unimputed_low_quality_percent_PERIPHERY': get_low_quality_percent(self.periphery) if self.TAC_column == 'TAC_pre_imputation' else get_unimputed_low_quality_percent(self.periphery),
      'total_low_quality_duration_PERIPHERY': get_low_quality_duration(self.periphery),
      'total_low_quality_percent_PERIPHERY': get_low_quality_percent(self.periphery),
      'imputed_gap_duration_PERIPHERY': 0 if self.TAC_column == 'TAC_pre_imputation' else get_imputed_gap_duration(self.periphery),
      'imputed_gap_percent_PERIPHERY': 0 if self.TAC_column == 'TAC_pre_imputation' else get_imputed_gap_percent(self.periphery),
      'unimputed_gap_duration_PERIPHERY': (self.periphery['gap_buffered'] == 1).sum() / 60 if self.TAC_column == 'TAC_pre_imputation' else get_unimputed_gap_duration(self.periphery),
      'unimputed_gap_percent_PERIPHERY': (self.periphery['gap_buffered'] == 1).sum() / len(self.periphery) if self.TAC_column == 'TAC_pre_imputation' else get_unimputed_gap_percent(self.periphery),
      'total_gap_duration_PERIPHERY': (self.periphery['gap_buffered'] == 1).sum() / 60,
      'total_gap_percent_PERIPHERY': (self.periphery['gap_buffered'] == 1).sum() / len(self.periphery),
      'gap_imputation_ratio_PERIPHERY': get_gap_imputation_ratio(self.periphery),
      'imputed_non_wear_duration_PERIPHERY': 0 if self.TAC_column == 'TAC_pre_imputation' else get_imputed_non_wear_duration(self.periphery),
      'imputed_non_wear_percent_PERIPHERY': 0 if self.TAC_column == 'TAC_pre_imputation' else get_imputed_non_wear_percent(self.periphery),
      'unimputed_non_wear_duration_PERIPHERY': (self.periphery['non_wear_buffered'] == 1).sum() / 60 if self.TAC_column == 'TAC_pre_imputation' else get_unimputed_non_wear_duration(self.periphery),
      'unimputed_non_wear_percent_PERIPHERY': (self.periphery['non_wear_buffered'] == 1).sum() / len(self.periphery) if self.TAC_column == 'TAC_pre_imputation' else get_unimputed_non_wear_percent(self.periphery),
      'total_non_wear_duration_PERIPHERY': (self.periphery['non_wear_buffered'] == 1).sum() / 60,
      'total_non_wear_percent_PERIPHERY': (self.periphery['non_wear_buffered'] == 1).sum() / len(self.periphery),
      'non_wear_imputation_ratio_PERIPHERY': get_non_wear_imputation_ratio(self.periphery),
      'imputed_jump_duration_PERIPHERY': 0 if self.TAC_column == 'TAC_pre_imputation' else get_imputed_jump_duration(self.periphery),
      'imputed_jump_percent_PERIPHERY': 0 if self.TAC_column == 'TAC_pre_imputation' else get_imputed_jump_percent(self.periphery),
      'unimputed_jump_duration_PERIPHERY': (self.periphery['jump'] == 1).sum() / 60 if self.TAC_column == 'TAC_pre_imputation' else get_unimputed_jump_duration(self.periphery),
      'unimputed_jump_percent_PERIPHERY': (self.periphery['jump'] == 1).sum() / len(self.periphery) if self.TAC_column == 'TAC_pre_imputation' else get_unimputed_jump_percent(self.periphery),
      'total_jump_duration_PERIPHERY': (self.periphery['jump'] == 1).sum() / 60,
      'total_jump_percent_PERIPHERY': (self.periphery['jump'] == 1).sum() / len(self.periphery),
      'jump_imputation_ratio_PERIPHERY': get_jump_imputation_ratio(self.periphery),
      'imputed_plummet_duration_PERIPHERY': 0 if self.TAC_column == 'TAC_pre_imputation' else get_imputed_plummet_duration(self.periphery),
      'imputed_plummet_percent_PERIPHERY': 0 if self.TAC_column == 'TAC_pre_imputation' else get_imputed_plummet_percent(self.periphery),
      'unimputed_plummet_duration_PERIPHERY': (self.periphery['plummet'] == 1).sum() / 60 if self.TAC_column == 'TAC_pre_imputation' else get_unimputed_plummet_duration(self.periphery),
      'unimputed_plummet_percent_PERIPHERY': (self.periphery['plummet'] == 1).sum() / len(self.periphery) if self.TAC_column == 'TAC_pre_imputation' else get_unimputed_plummet_percent(self.periphery),
      'total_plummet_duration_PERIPHERY': (self.periphery['plummet'] == 1).sum() / 60,
      'total_plummet_percent_PERIPHERY': (self.periphery['plummet'] == 1).sum() / len(self.periphery),
      'plummet_imputation_ratio_PERIPHERY': get_plummet_imputation_ratio(self.periphery),
      'imputed_extreme_negative_duration_PERIPHERY': 0 if self.TAC_column == 'TAC_pre_imputation' else get_imputed_extreme_negative_duration(self.periphery),
      'imputed_extreme_negative_percent_PERIPHERY': 0 if self.TAC_column == 'TAC_pre_imputation' else get_imputed_extreme_negative_percent(self.periphery),
      'unimputed_extreme_negative_duration_PERIPHERY': (self.periphery['extreme_negative'] == 1).sum() / 60 if self.TAC_column == 'TAC_pre_imputation' else get_unimputed_extreme_negative_duration(self.periphery),
      'unimputed_extreme_negative_percent_PERIPHERY': (self.periphery['extreme_negative'] == 1).sum() / len(self.periphery) if self.TAC_column == 'TAC_pre_imputation' else get_unimputed_extreme_negative_percent(self.periphery),
      'total_extreme_negative_duration_PERIPHERY': (self.periphery['extreme_negative'] == 1).sum() / 60,
      'total_extreme_negative_percent_PERIPHERY': (self.periphery['extreme_negative'] == 1).sum() / len(self.periphery),
      'sub_negative_10_sum_PERIPHERY': self.periphery.loc[self.periphery['extreme_negative'] == 1, self.TAC_column].sum(),
      'extreme_negative_imputation_ratio_PERIPHERY': get_extreme_negative_imputation_ratio(self.periphery),
      'low_quality_imputation_ratio_PERIPHERY': get_low_quality_imputation_ratio(self.periphery),
    }

    self.region_quality_features = {
      'started_curve_count_REGION': count_started_curves(self.region, self.TAC_column, threshold=self.curve_threshold, min_length=10),
      'complete_curve_count_REGION': count_complete_curves(self.region, self.TAC_column, threshold=self.curve_threshold, min_length=10),      
      'total_duration_REGION': len(self.region) / 60,
      'device_turned_on_duration_REGION': (self.region['device_turned_on'].sum()) / 60,
      'device_turned_on_percent_REGION': (self.region['device_turned_on'].sum()) / len(self.region),
      'device_worn_duration_REGION': (self.region['device_worn_model'].sum()) / 60,
      'device_worn_percent_REGION': (self.region['device_worn_model'].sum()) / len(self.region),
      'flatline_max_REGION': count_longest_tac_flatline(self.region),
      'flatlined_percent_REGION': (count_longest_tac_flatline(self.region) / len(self.region)),
      'imputed_duration_REGION': 0 if self.TAC_column == 'TAC_pre_imputation' else self.region['imputed'].sum() / 60,
      'imputed_percent_REGION': 0 if self.TAC_column == 'TAC_pre_imputation' else self.region['imputed'].sum() / len(self.region),
      'imputed_low_quality_duration_REGION': 0 if self.TAC_column == 'TAC_pre_imputation' else get_imputed_low_quality_duration(self.region),
      'imputed_low_quality_percent_REGION': 0 if self.TAC_column == 'TAC_pre_imputation' else get_imputed_low_quality_percent(self.region),
      'unimputed_low_quality_duration_REGION': get_low_quality_duration(self.region) if self.TAC_column == 'TAC_pre_imputation' else get_unimputed_low_quality_duration(self.region),
      'unimputed_low_quality_percent_REGION': get_low_quality_percent(self.region) if self.TAC_column == 'TAC_pre_imputation' else get_unimputed_low_quality_percent(self.region),
      'total_low_quality_duration_REGION': get_low_quality_duration(self.region),
      'total_low_quality_percent_REGION': get_low_quality_percent(self.region),
      'imputed_gap_duration_REGION': 0 if self.TAC_column == 'TAC_pre_imputation' else get_imputed_gap_duration(self.region),
      'imputed_gap_percent_REGION': 0 if self.TAC_column == 'TAC_pre_imputation' else get_imputed_gap_percent(self.region),
      'unimputed_gap_duration_REGION': (self.region['gap_buffered'] == 1).sum() / 60 if self.TAC_column == 'TAC_pre_imputation' else get_unimputed_gap_duration(self.region),
      'unimputed_gap_percent_REGION': (self.region['gap_buffered'] == 1).sum() / len(self.region) if self.TAC_column == 'TAC_pre_imputation' else get_unimputed_gap_percent(self.region),
      'total_gap_duration_REGION': (self.region['gap_buffered'] == 1).sum() / 60,
      'total_gap_percent_REGION': (self.region['gap_buffered'] == 1).sum() / len(self.region),
      'gap_imputation_ratio_REGION': get_gap_imputation_ratio(self.region),
      'imputed_non_wear_duration_REGION': 0 if self.TAC_column == 'TAC_pre_imputation' else get_imputed_non_wear_duration(self.region),
      'imputed_non_wear_percent_REGION': 0 if self.TAC_column == 'TAC_pre_imputation' else get_imputed_non_wear_percent(self.region),
      'unimputed_non_wear_duration_REGION': (self.region['non_wear_buffered'] == 1).sum() / 60 if self.TAC_column == 'TAC_pre_imputation' else get_unimputed_non_wear_duration(self.region),
      'unimputed_non_wear_percent_REGION': (self.region['non_wear_buffered'] == 1).sum() / len(self.region) if self.TAC_column == 'TAC_pre_imputation' else get_unimputed_non_wear_percent(self.region),
      'total_non_wear_duration_REGION': (self.region['non_wear_buffered'] == 1).sum() / 60,
      'total_non_wear_percent_REGION': (self.region['non_wear_buffered'] == 1).sum() / len(self.region),
      'non_wear_imputation_ratio_REGION': get_non_wear_imputation_ratio(self.region),
      'imputed_jump_duration_REGION': 0 if self.TAC_column == 'TAC_pre_imputation' else get_imputed_jump_duration(self.region),
      'imputed_jump_percent_REGION': 0 if self.TAC_column == 'TAC_pre_imputation' else get_imputed_jump_percent(self.region),
      'unimputed_jump_duration_REGION': (self.region['jump'] == 1).sum() / 60 if self.TAC_column == 'TAC_pre_imputation' else get_unimputed_jump_duration(self.region),
      'unimputed_jump_percent_REGION': (self.region['jump'] == 1).sum() / len(self.region) if self.TAC_column == 'TAC_pre_imputation' else get_unimputed_jump_percent(self.region),
      'total_jump_duration_REGION': (self.region['jump'] == 1).sum() / 60,
      'total_jump_percent_REGION': (self.region['jump'] == 1).sum() / len(self.region),
      'jump_imputation_ratio_REGION': get_jump_imputation_ratio(self.region),
      'imputed_plummet_duration_REGION': 0 if self.TAC_column == 'TAC_pre_imputation' else get_imputed_plummet_duration(self.region),
      'imputed_plummet_percent_REGION': 0 if self.TAC_column == 'TAC_pre_imputation' else get_imputed_plummet_percent(self.region),
      'unimputed_plummet_duration_REGION': (self.region['plummet'] == 1).sum() / 60 if self.TAC_column == 'TAC_pre_imputation' else get_unimputed_plummet_duration(self.region),
      'unimputed_plummet_percent_REGION': (self.region['plummet'] == 1).sum() / len(self.region) if self.TAC_column == 'TAC_pre_imputation' else get_unimputed_plummet_percent(self.region),
      'total_plummet_duration_REGION': (self.region['plummet'] == 1).sum() / 60,
      'total_plummet_percent_REGION': (self.region['plummet'] == 1).sum() / len(self.region),
      'plummet_imputation_ratio_REGION': get_plummet_imputation_ratio(self.region),
      'imputed_extreme_negative_duration_REGION': 0 if self.TAC_column == 'TAC_pre_imputation' else get_imputed_extreme_negative_duration(self.region),
      'imputed_extreme_negative_percent_REGION': 0 if self.TAC_column == 'TAC_pre_imputation' else get_imputed_extreme_negative_percent(self.region),
      'unimputed_extreme_negative_duration_REGION': (self.region['extreme_negative'] == 1).sum() / 60 if self.TAC_column == 'TAC_pre_imputation' else get_unimputed_extreme_negative_duration(self.region),
      'unimputed_extreme_negative_percent_REGION': (self.region['extreme_negative'] == 1).sum() / len(self.region) if self.TAC_column == 'TAC_pre_imputation' else get_unimputed_extreme_negative_percent(self.region),
      'total_extreme_negative_duration_REGION': (self.region['extreme_negative'] == 1).sum() / 60,
      'total_extreme_negative_percent_REGION': (self.region['extreme_negative'] == 1).sum() / len(self.region),
      'sub_negative_10_sum_REGION': self.region.loc[self.region['extreme_negative'] == 1, self.TAC_column].sum(),
      'extreme_negative_imputation_ratio_REGION': get_extreme_negative_imputation_ratio(self.region),
      'low_quality_imputation_ratio_REGION': get_low_quality_imputation_ratio(self.region),
    }

    peak_index = get_peak_index(self.curve, self.TAC_column)
    rise_duration = (self.curve.loc[peak_index, 'Duration_Hrs'] - self.curve.loc[0, 'Duration_Hrs']) + (1/60)
    fall_duration = (self.curve.loc[len(self.curve)-1, 'Duration_Hrs'] - self.curve.loc[peak_index, 'Duration_Hrs']) + (1/60)
    peak_tac = self.curve.loc[peak_index, self.TAC_column]
    first_tac = self.curve.iloc[0][self.TAC_column]
    last_tac = self.curve.iloc[-1][self.TAC_column]
    relative_peak = peak_tac - self.curve_threshold
    relative_rise = (peak_tac - first_tac)
    relative_fall = (peak_tac - last_tac)
    mean_tac, sd_tac, sem_tac = get_mean_stdev_sem(self.curve, self.TAC_column)

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
      'auc_total_CURVE' : get_auc(self.curve, self.TAC_column),
      'auc_relative_CURVE' : get_curve_auc(self.curve, self.TAC_column, self.curve_threshold),
      'rise_duration_CURVE' : rise_duration,
      'fall_duration_CURVE' : fall_duration,
      'relative_peak_CURVE' : relative_peak,
      'rise_rate_CURVE' : get_rise_rate(rise_duration, relative_rise),
      'fall_rate_CURVE' : get_fall_rate(fall_duration, relative_fall),
      'rise_complete_perc_CURVE' : 1 if first_tac <= self.curve_threshold else (peak_tac - first_tac) / relative_peak,
      'fall_complete_perc_CURVE' : 1 if last_tac <= self.curve_threshold else (peak_tac - last_tac) / relative_peak,
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
      **self.periphery_quality_features,
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
    self.valid = self.row['CURVE_VALID']
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
  
  # def match_curve_to_event(self, subid_column, self_report_start_time_column, ema_id_column):
  #   print('REACHED SELF REPORT MATCHING')
  #   self.event_matched = False
  #   curve_start = self.curve_tac_features['begin_CURVE']
    
  #   self.event_data_subid_match = self.event_data[
  #     (self.event_data[subid_column] == str(self.subid)) | (self.event_data[subid_column] == int(self.subid))
  #   ]
  #   print(len(self.event_data_subid_match))

  #   if not self.event_data_subid_match.empty:
  #     self.event_data_subid_match[self_report_start_time_column] = pd.to_datetime(self.event_data_subid_match[self_report_start_time_column])
  #     curve_start = pd.to_datetime(curve_start)
  #     print(curve_start)
  #     # Find the closest self report event
  #     closest_index = (self.event_data_subid_match[self_report_start_time_column] - curve_start).abs().idxmin()
  #     closest_row = self.event_data_subid_match.loc[closest_index].copy()
  #     self.self_report_start_time = closest_row[self_report_start_time_column]
  #     print(self.self_report_start_time)
  #     self.time_diff_to_self_report = (self.self_report_start_time - curve_start).total_seconds() / 3600
  #     closest_row['curve_vs_self_report_time_diff'] = self.time_diff_to_self_report
  #     self.event_matched = True
  #     print('FOUND MATCH')

  #   else:
  #     # If no matching data for the subid, create an empty row with NaN values
  #     closest_row = pd.Series(dtype='object', index=self.event_data.columns)
  #     closest_row['curve_vs_self_report_time_diff'] = np.nan
    
  #   # Ensure all columns from closest_row exist in self.features
  #   self.ema_id = closest_row[ema_id_column]
  #   self.features = self.features.reindex(columns=self.features.columns.union(closest_row.index, sort=False))
  #   self.features.iloc[0] = self.features.iloc[0].fillna(closest_row)
  #   self.row = self.features.loc[0]
  
  # def evaluate_self_report_region(self, plot_folder, drink_total_column, extend_before_hours = 2, extend_after_hours = 10):
  #   if self.event_matched:
  #     self.ema_region = emaRegion(self.df, self.subid, self.dataset_identifier, self.ema_id, self.self_report_start_time, extend_before_hours=extend_before_hours, extend_after_hours=extend_after_hours)
  #     self.ema_region.make_device_removal_plot(plot_folder)
  #     self.ema_region.make_signal_processing_plot(plot_folder, self.curve_threshold, self.features.loc[0, drink_total_column])
  #     self.self_report_region_quality_features = self.ema_region.self_report_region_quality_features
  #   else:
  #     self.ema_region = emaRegion(pd.DataFrame(), self.subid, self.dataset_identifier, self.ema_id, self.self_report_start_time)
  #     self.self_report_region_quality_features = self.ema_region.self_report_region_quality_features

  #   self.features = self.features.assign(**self.self_report_region_quality_features)
  #   self.row = self.features.loc[0]
  