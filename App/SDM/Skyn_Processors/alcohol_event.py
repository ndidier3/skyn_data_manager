from Feature_Engineering.tac_features import *

class alcoholEvent:
  def __init__(self, dataset, starting_index, ending_index, event_detection_method, curve_threshold = None):
    self.event_dataset = dataset.loc[starting_index:ending_index].reset_index(drop=True)
    self.event_detection_method = event_detection_method #self-report or threshold?

    self.begin_day = self.event_dataset['datetime'].iloc[0] if not self.event_dataset.empty else None
    self.end_day = self.event_dataset['datetime'].iloc[-1] if not self.event_dataset.empty else None

    self.device_id_begin = self.event_dataset['device_id'].iloc[0] if not self.event_dataset.empty else None
    self.device_id_end = self.event_dataset['device_id'].iloc[-1] if not self.event_dataset.empty else None

    self.device_turned_on_duration = self.event_dataset['device_turned_on'].sum() / 60
    self.device_turned_on_percentage_of_day = self.device_turned_on_duration / 24
  
    """
    device_worn_duration will always be equal or less than device_turned_on_duration.
    This is because values for device_worn are null whenever device is not turned on.
    Therefore, device_worn_duration will be the duration when device is turned on AND worn.
    """
    self.device_worn_duration = self.event_dataset['device_worn'].sum() / 60
    self.device_worn_percentage_of_device_on = (self.device_worn_duration / self.device_turned_on_duration) if self.device_turned_on_duration > 0 else 0
    self.device_worn_percentage_of_day = self.device_worn_duration / 24

    self.negative_duration = self.event_dataset['negative_tac'].sum() / 60
    self.very_negative_duration = self.event_dataset['below_neg10_tac'].sum() / 60

    self.curve_threshold = 10 if curve_threshold == None else curve_threshold

  def get_tac_features(self, tac_var = 'TAC', time_var = 'Duration_Hrs'):
    df = self.event_dataset
    self.mean_tac, self.sd_tac, self.sem_tac = get_mean_stdev_sem(df, tac_var)
    self.peak = get_peak(df, 'TAC')
    peak_index = get_peak_index(df, tac_var)
    self.rise_duration = get_rise_duration(df, tac_var, time_var, peak_index, self.curve_threshold)
    self.fall_duration = get_fall_duration(df, tac_var, time_var, peak_index, self.curve_threshold)
    self.rise_rate = get_rise_rate(df, tac_var, time_var)
    self.fall_rate = get_fall_rate(df, tac_var, time_var)
    self.duration =  get_curve_duration(self.rise_duration, self.fall_duration)
    self.auc_total = get_auc(df, tac_var, time_var)
    
    # self.relative_peak = self.peak - self.curve_threshold

"""
#MOTION 
self.stats[f'no_motion_{dataset_version}'] = get_value_proportion(df, 0, 'Motion')
self.stats[f'mean_motion_{dataset_version}'], self.stats[f'stdev_motion_{dataset_version}'], self.stats[f'sem_motion_{dataset_version}'] = get_mean_stdev_sem(df, 'Motion')

#TEMPERATURE
self.stats[f'mean_temp_{dataset_version}'], self.stats[f'stdev_temp_{dataset_version}'], self.stats[f'sem_temp_{dataset_version}'] = get_mean_stdev_sem(df, 'Temperature_C')

#SIGNAL VARIABILITY
self.stats[f'avg_tac_diff_{dataset_version}'], differences = get_avg_tac_diff(df, tac_variable) 
self.stats[f'tac_alt_perc_{dataset_version}'] = get_tac_directional_alteration_percent(df, tac_variable) 
self.stats[f'curve_alterations_{dataset_version}'], total_n = get_tac_directional_alterations(df.loc[curve_begins_index:curve_ends_index], tac_variable)
self.stats[f'completed_curve_count_{dataset_version}'] = get_discrete_curve_count(df, tac_variable, self.sampling_rate, self.stats[f'curve_threshold_{dataset_version}'], min_curve_duration_hours=0.5)

self.stats[f'curve_begins_index_{dataset_version}'] = curve_begins_index
self.stats[f'curve_ends_index_{dataset_version}'] = curve_ends_index

if dataset_version == 'CLN':
  #OUTLIERS AND CLEANING
  self.stats[f'subzero_reassigned_zero_count'] = len(df[df['negative_reassigned_zero']==0])
  self.stats[f'device_off_N'] = len(df[df['device_on_pred']==0])
  self.stats[f'extreme_outlier_N'] = len(df[df['extreme_outlier']==1])
  self.stats[f'major_outlier_N'] = len(df[df['major_outlier']==1])
  self.stats[f'minor_outlier_N'] = len(df[df['minor_outlier']==1])
  
  
  #proportion of how much of the tac falls towards baseline
  self.stats['fall_completion']  = get_fall_completion(self.dataset, tac_variable, curve_ends_index, self.stats['relative_peak_CLN'], curve_fall_threshold)
  self.rise_completion = get_rise_completion(self.dataset, tac_variable, curve_begins_index, self.stats['relative_peak_CLN'], self.stats['curve_threshold_CLN'])

  #Reassign null stats to their raw stat; if raw stat is also null, the dataset is invalid
  for variable in ['auc_total', 'auc_per_hour', 'curve_auc', 'curve_auc_per_hour', 'avg_tac_diff']:
    if not self.stats[f'{variable}_CLN']: 
      if self.stats[f'{variable}_RAW']:
        self.stats[f'{variable}_CLN'] = self.stats[f'{variable}_RAW']
      else:
        self.valid_occasion = 0
        self.invalid_reason = 'feature engineering failed'
  

"""
    
