from App.SDM.Feature_Engineering.tac_features import *
from App.SDM.Visualization.tac import *
from App.SDM.Visualization.device_non_wear import plot_device_removal
from App.SDM.Configuration.configuration import get_closest_index_with_timestamp
import traceback
import pandas as pd

def get_first_index_above(dataset, threshold):
  above_threshold = dataset[dataset['TAC'] > threshold]
  if above_threshold.empty:
    starts_after_null = None 
    return None, starts_after_null
  
  first_index_above = above_threshold.index[0]
  if first_index_above > 0:
    starts_after_null = pd.isnull(dataset.loc[first_index_above - 1, 'TAC'])
  else:
    starts_after_null = False  # No row before the first index
  return first_index_above, starts_after_null

def get_first_index_below_threshold(dataset, threshold):
  """
  Finds the first index where TAC drops below the threshold or encounters a null value.
  If the value is null, returns the index before it. Starts evaluation at index 2.
  If no condition is met, returns the final index.

  Args:
      dataset (pd.DataFrame): DataFrame containing a 'TAC' column.
      threshold (float): The threshold to compare against.

  Returns:
      int or None: The first index below the threshold, the index before the first null,
                   or the final index if no conditions are met.
  """
  if dataset.empty or len(dataset) < 3:
    ends_before_null = None
    return None, ends_before_null

  for idx, row in dataset.iloc[2:].iterrows():  # Start from index 2
    value = row['TAC']
    if pd.isnull(value):  # Handle null case
      ends_before_null = True
      return idx - 1, ends_before_null  # Return the index before the null
    if value < threshold:  # Handle below threshold case
      ends_before_null = False
      return idx - 1, ends_before_null

  # If no condition is met, return the final index
  ends_before_null = False
  return dataset.index[-1], ends_before_null

def get_first_index_above_threshold_near_peak(dataset, threshold):
  """
  Identifies the index of the first valid value after:
  - A value drops below the threshold, or
  - A null value is encountered.

  Args:
      dataset (pd.DataFrame): DataFrame containing a 'TAC' column.
      threshold (float): The threshold to compare against.

  Returns:
      int or None: The index of the next valid value after the condition,
                   or None if no such value exists.
  """
  if dataset.empty:
    starts_after_null = None
    return None, starts_after_null

  # Start iterating backward through rows
  for idx, row in dataset.iloc[::-1].iterrows():  # Reverse iteration
    value = row['TAC']

    # If current value is null, return the next valid index
    if pd.isnull(value):
      starts_after_null = True
      return idx + 1, starts_after_null

    # If current value is below the threshold, return the value prior
    if value < threshold:
      starts_after_null = False
      return idx + 1, starts_after_null

  # If no stopping condition is met, return last index
  starts_after_null = False
  return dataset.index[0], starts_after_null 
        
def determine_searchability(self, df, curve_threshold):
  valid_length = df['TAC'].notna().sum() > 5
  if valid_length:
    result = df['TAC'].max() > curve_threshold
    if not result:
      self.curve_not_found_reason = f'no TAC above {curve_threshold}'
    return result
  else:
    self.curve_not_found_reason = f'not enough search data found'
    return False

class alcoholEvent:
  def __init__(self, dataset, subid, dataset_identifier, event_number, curve_search_start_index, curve_search_end_index, drink_total = None, day_id = None, curve_threshold = 10, search_method = 'peak', extra_info = {}, include_prior_curves = False, include_subsequent_curves = False):
    
    self.subid = subid
    self.dataset_identifier = dataset_identifier
    self.dataset = dataset
    
    self.curve_threshold = curve_threshold
    self.min_curve_length = 5
    self.curve_not_found_reason = None
    
    self.curve_search_start_index = curve_search_start_index
    self.curve_search_end_index = curve_search_end_index

    self.search_dataset = dataset.iloc[self.curve_search_start_index:]
    self.curve_search_start_time = self.search_dataset['datetime'].iloc[0]
    """ The latest a curve can begin is 14 hours past search start """
    self.curve_start_time_limit = self.curve_search_start_time + pd.Timedelta(hours=14) #MAKE THIS ADJUSTABLE
    self.curve_start_search_dataset = self.search_dataset[self.search_dataset['datetime'] <= self.curve_start_time_limit]
    """ The latest a curve can end is 24 hours past search start """
    self.curve_end_time_limit = self.curve_search_start_time + pd.Timedelta(hours=24) #MAKE THIS ADJUSTABLE
    self.curve_search_dataset = self.search_dataset[self.search_dataset['datetime'] <= self.curve_end_time_limit]

    self.search_dataset_searchable = determine_searchability(self, self.curve_start_search_dataset, self.curve_threshold)

    self.tac_event_start_index = None
    self.tac_event_end_index = None
    self.curve_starts_after_null = None
    self.curve_ends_before_null = None
    self.curve_not_found_reason = None
    # if search_method == 'first' and self.search_dataset_searchable:
      # start_time = self.search_dataset['datetime'].iloc[0]
      # # self.search_end_time = start_time + pd.Timedelta(hours=6)
      # curve_begin_search_dataset = self.search_dataset[self.search_dataset['datetime'] <= self.search_end_time]
      # #Find first row that goes above curve_threshold
      # self.tac_event_start_index, self.curve_starts_after_null = get_first_index_above(curve_begin_search_dataset, self.curve_threshold)
      # self.tac_event_start_index, self.curve_starts_after_null = get_first_index_above(self.curve_start_search_dataset, self.curve_threshold)
      # if self.tac_event_start_index:
      #   #Find first row (since TAC event started) that goes below Curve Threshold
      #   self.tac_event_end_index, self.curve_ends_before_null = get_first_index_below_threshold(self.curve_search_dataset, self.curve_threshold)
    if search_method == 'peak' and self.search_dataset_searchable:      
      peak_index = get_peak_index(self.curve_start_search_dataset, variable='TAC')
      peak = get_peak(self.curve_start_search_dataset, variable='TAC')
      if peak >= self.curve_threshold and self.dataset.loc[peak_index-2:peak_index+2, 'TAC'].notna().sum() == 5:
        #Find last row that is below curve_threshold prior to peak
        self.tac_event_start_index, self.curve_starts_after_null = get_first_index_above_threshold_near_peak(self.dataset[curve_search_start_index:peak_index], self.curve_threshold)
        #revise curve search end to be 24 hours since curve start
        self.curve_end_time_limit = self.dataset.loc[self.tac_event_start_index, 'datetime'] + pd.Timedelta(hours=24) #MAKE THIS ADJUSTABLE
        self.curve_search_dataset = self.search_dataset[self.search_dataset['datetime'] <= self.curve_end_time_limit]
        self.curve_search_end_index = self.curve_search_dataset.index[-1]
        #Find first row (since Peak) that goes below Curve Threshold - if never returns below threshold, last index of search will be used
        self.tac_event_end_index, self.curve_ends_before_null = get_first_index_below_threshold(self.dataset[peak_index:curve_search_end_index], self.curve_threshold)
      else:
        if peak < self.curve_threshold:
          self.curve_not_found_reason = f'TAC < {self.curve_threshold}'
        else:
          self.curve_not_found_reason = 'device turned off near peak'
    
    #Confirming Valid Curve Indices have been found
    try:
      self.alcohol_event_found = (
        self.tac_event_start_index is not None 
        and self.tac_event_end_index is not None 
        and (self.tac_event_end_index - self.tac_event_start_index) >= self.min_curve_length
      )
      
    except:
      self.tac_event_start_index = None
      self.tac_event_end_index = None
      self.curve_starts_after_null = None
      self.curve_ends_before_null = None
      self.alcohol_event_found = False
    
    print(f'Event: {event_number}')
    if self.alcohol_event_found and include_prior_curves and not self.curve_starts_after_null:
      self.include_prior_curves()

    if self.alcohol_event_found and include_subsequent_curves and not self.curve_ends_before_null:
      self.include_subsequent_curves()

    if self.alcohol_event_found:
      self.curve_dataset = self.dataset.iloc[self.tac_event_start_index: self.tac_event_end_index+1].reset_index(drop=True)
      self.peak_index = get_peak_index(self.curve_dataset, variable='TAC')
      self.curve_rise_dataset =  self.curve_dataset[:self.peak_index]
      self.curve_fall_dataset = self.curve_dataset[self.peak_index:]

      curve_start_quality_check_indices = (
        max(self.curve_search_dataset.index[0], (self.tac_event_start_index - 5)),  # Start index
        min(self.curve_search_dataset.index[-1], (self.tac_event_start_index + 4))  # End index
      )
      self.curve_start_slice = self.curve_search_dataset.iloc[curve_start_quality_check_indices[0]: curve_start_quality_check_indices[1]]
      
      curve_end_quality_check_indices = (
        max(self.curve_search_dataset.index[0], (self.tac_event_end_index - 4)),  # Start index
        min(self.curve_search_dataset.index[-1], (self.tac_event_end_index + 5))  # End index
      )
      self.curve_ending_slice = self.curve_search_dataset.iloc[curve_end_quality_check_indices[0]: curve_end_quality_check_indices[1]]
      self.curve_timestamps = {
        'Curve Start': self.curve_dataset.iloc[0]['datetime'],
        'Curve End': self.curve_dataset.iloc[-1]['datetime'],
        'Curve Limit': self.curve_end_time_limit,
      }
      self.search_timestamps = {
        'Search Start': self.curve_search_start_time,
        'Search End': self.curve_start_time_limit,
         **self.curve_timestamps
      }

    else:
      #if no curve found, set empty datasets
      self.curve_dataset = pd.DataFrame(columns=self.search_dataset.columns) #empty
      self.curve_start_slice = pd.DataFrame(columns=self.search_dataset.columns) #empty
      self.curve_ending_slice = pd.DataFrame(columns=self.search_dataset.columns) #empty
      self.curve_rise_dataset = pd.DataFrame(columns=self.search_dataset.columns) #empty
      self.curve_fall_dataset = pd.DataFrame(columns=self.search_dataset.columns) #empty
      self.curve_starts_after_null = None
      self.curve_ends_before_null = None
      self.curve_timestamps = {
        'Curve Start': None,
        'Curve End': None
      }
      self.search_timestamps = {
        'Search Start': self.curve_search_start_time,
        'Search End': self.curve_start_time_limit,
        'Curve Limit': self.curve_start_time_limit,
         **self.curve_timestamps
      }
      if self.tac_event_start_index is None or get_peak(self.curve_start_search_dataset, variable='TAC') < self.curve_threshold:
        self.curve_not_found_reason = 'never rose above threshold'
      elif self.tac_event_end_index is None:
        self.curve_not_found_reason = 'no valid data following peak'
      elif (self.tac_event_end_index - self.tac_event_start_index) < self.min_curve_length:
        self.curve_not_found_reason = 'curve duration too small'
      else:
        self.curve_not_found_reason = 'unclear'
      
    self.curve_dataset['event_number'] = event_number
    self.curve_dataset['drink_total'] = drink_total
    self.curve_dataset['day_id'] = day_id
    self.event_number = event_number
    self.drink_total = drink_total
    self.day_id = day_id
    self.extra_info = extra_info
    for key, value in extra_info.items():
      setattr(self, key, value)
      self.curve_dataset[key] = value

    self.quality_features_of_search = {
      'search_start_time': self.curve_search_start_time,
      'curve_start_time_limit': self.curve_start_time_limit, 
      'curve_end_time_limit':  self.curve_end_time_limit,
      'data_found_SEARCH': self.curve_start_search_dataset['TAC'].notna().sum() > 5,
      'started_curve_count_SEARCH': count_started_curves(self.curve_search_dataset, 'TAC', threshold=self.curve_threshold, min_length=self.min_curve_length),
      'complete_curve_count_SEARCH': count_complete_curves(self.curve_search_dataset, 'TAC', threshold=self.curve_threshold, min_length=self.min_curve_length),      
      'device_one_SEARCH': None,
      'device_two_SEARCH': None,
      'device_count_SEARCH': None,
      'device_turned_on_duration_SEARCH': None,
      'device_turned_on_percent_SEARCH': None,
      'device_worn_duration_SEARCH': None,
      'device_worn_percent_SEARCH': None,
      'negative_duration_SEARCH': None,
      'sub_negative_10_duration_SEARCH': None,
      'sub_negative_10_percent_SEARCH': (self.curve_start_search_dataset['TAC'] <= -10).sum() / len(self.curve_start_search_dataset),
      'consecutive_sub_negative_10_duration_SEARCH': (count_longest_consecutive_below(self.curve_start_search_dataset) / 60),
      'sub_negative_20_duration_SEARCH': (self.curve_start_search_dataset['TAC'] <= -20).sum() / 60,
      'sub_negative_20_percent_SEARCH': (self.curve_start_search_dataset['TAC'] <= -20).sum() / len(self.curve_start_search_dataset),
      'consecutive_sub_negative_20_duration_SEARCH': (count_longest_consecutive_below(self.curve_start_search_dataset, X=-20) / 60),
      'sub_negative_40_duration_SEARCH': (self.curve_start_search_dataset['TAC'] <= -40).sum() / 60,
      'sub_negative_40_percent_SEARCH': (self.curve_start_search_dataset['TAC'] <= -40).sum() / len(self.curve_start_search_dataset),
      'consecutive_sub_negative_40_duration_SEARCH': (count_longest_consecutive_below(self.curve_start_search_dataset, X=-40) / 60),
      'imputed_duration_SEARCH': (self.curve_start_search_dataset['imputed'].sum() / 60),
      'imputed_percent_SEARCH': (self.curve_start_search_dataset['imputed'].sum() / len(self.curve_start_search_dataset)),
    }

    self.tac_features_of_search = {
      'begin_SEARCH': None, 
      'end_SEARCH': None,
      'duration_SEARCH': None,
      'first_tac_SEARCH': None,
      'last_tac_SEARCH': None,
      'mean_tac_SEARCH': None, 
      'sd_tac_SEARCH': None, 
      'sem_tac_SEARCH': None, 
      'peak_SEARCH': None, 
      'auc_total_SEARCH': None,
      'min_tac_SEARCH': self.curve_search_dataset['TAC'].min(), 
    }

    self.quality_features_of_curve = {
      'data_found_CURVE': self.alcohol_event_found,
      'CURVE_threshold': self.curve_threshold,
      'starting_non_wear_perc_CURVE': (
        (self.curve_start_slice[self.curve_start_slice['device_worn_model'] == 0].shape[0] / len(self.curve_start_slice))
        if len(self.curve_start_slice) else None
      ),
      'curve_starts_after_null': self.curve_starts_after_null,
      'ending_non_wear_perc_CURVE': (
        (self.curve_ending_slice[self.curve_ending_slice['device_worn_model'] == 0].shape[0] / len(self.curve_ending_slice))
        if len(self.curve_ending_slice) else None
      ),
      'curve_ends_before_null': self.curve_ends_before_null,      
      'flatline_max_CURVE': count_longest_tac_flatline(self.curve_dataset) if self.alcohol_event_found else None,
      'flatlined_percent_CURVE': (count_longest_tac_flatline(self.curve_dataset) / len(self.curve_dataset)) if self.alcohol_event_found else None,
      'device_one_CURVE': None,
      'device_two_CURVE': None,
      'device_count_CURVE': None,
      'device_turned_on_duration_CURVE': None,
      'device_turned_on_percent_CURVE': None,
      'device_worn_duration_CURVE': None,
      'consecutive_non_wear_duration_CURVE': (count_longest_consecutive_non_wear(self.curve_dataset) / 60) if self.alcohol_event_found else None,
      'consecutive_non_wear_percent_CURVE': (count_longest_consecutive_non_wear(self.curve_dataset) / len(self.curve_dataset)) if self.alcohol_event_found else None,
      'device_worn_rise_duration_CURVE': (self.curve_rise_dataset['device_worn_model'].sum() / 60) if self.alcohol_event_found else None,
      'device_worn_rise_percent_CURVE': (self.curve_rise_dataset['device_worn_model'].sum() / len(self.curve_rise_dataset)) if self.alcohol_event_found else None,
      'device_worn_percent_CURVE': None,
      'device_worn_fall_duration_CURVE': (self.curve_fall_dataset['device_worn_model'].sum() / 60) if self.alcohol_event_found else None,
      'device_worn_fall_percent_CURVE': (self.curve_fall_dataset['device_worn_model'].sum() / len(self.curve_fall_dataset)) if self.alcohol_event_found else None,
      'imputed_duration_CURVE': (self.curve_dataset['imputed'].sum() / 60) if self.alcohol_event_found else None,
      'imputed_percent_CURVE': (self.curve_dataset['imputed'].sum() / len(self.curve_dataset)) if self.alcohol_event_found else None,
      'gap_imputed_duration_CURVE': (self.curve_dataset['gap_imputed'].sum() / 60) if self.alcohol_event_found else None,
      'gap_imputed_percent_CURVE': (self.curve_dataset['gap_imputed'].sum() / len(self.curve_dataset)) if self.alcohol_event_found else None,
      'non_wear_imputed_duration_CURVE': (self.curve_dataset['non_wear_imputed'].sum() / 60) if self.alcohol_event_found else None,
      'non_wear_imputed_percent_CURVE': (self.curve_dataset['non_wear_imputed'].sum() / len(self.curve_dataset)) if self.alcohol_event_found else None,
      'jump_imputed_duration_CURVE': (self.curve_dataset['jump_imputed'].sum() / 60) if self.alcohol_event_found else None,
      'jump_imputed_percent_CURVE': (self.curve_dataset['jump_imputed'].sum() / len(self.curve_dataset)) if self.alcohol_event_found else None,
      'plummet_imputed_duration_CURVE': (self.curve_dataset['plummet_imputed'].sum() / 60) if self.alcohol_event_found else None,
      'plummet_imputed_percent_CURVE': (self.curve_dataset['plummet_imputed'].sum() / len(self.curve_dataset)) if self.alcohol_event_found else None,
      'negative_duration_CURVE': None,
      'sub_negative_10_duration_CURVE': None,
    }

    self.tac_features_of_curve = {
      'begin_CURVE': None, 
      'end_CURVE': None, 
      'duration_CURVE': None,
      'first_tac_CURVE': None,
      'last_tac_CURVE': None,
      'mean_tac_CURVE': None, 
      'sd_tac_CURVE': None, 
      'sem_tac_CURVE': None, 
      'peak_CURVE': None, 
      'auc_total_CURVE': None
    }

    self.curve_specific_features = {
      'rise_duration_CURVE': None,
      'fall_duration_CURVE': None,
      'relative_peak_CURVE': None, 
      'rise_rate_CURVE': None,
      'fall_rate_CURVE': None, 
      'fall_complete_perc_CURVE': None,
      'rise_complete_perc_CURVE': None,
      'rise_auc_CURVE': get_auc(self.curve_rise_dataset, 'TAC') if self.alcohol_event_found else None,
      'fall_auc_CURVE': get_auc(self.curve_fall_dataset, 'TAC') if self.alcohol_event_found else None
    }

    self.all_features = {
      'quality_features_of_search': self.quality_features_of_search,
      'tac_features_of_search': self.tac_features_of_search,
      'quality_features_of_curve': self.quality_features_of_curve,
      'tac_features_of_curve': self.tac_features_of_curve,
      'curve_specific_features': self.curve_specific_features
    }

  def include_prior_curves(self, max_distance = 60, min_duration = 10, min_allowed_value = -50):
    #revises curve start to inclue nearby curves occuring before main curve
    pre_curve_dataset = self.dataset[self.curve_search_start_index:self.tac_event_start_index].dropna(subset=['TAC'])
    if pre_curve_dataset['TAC'].max() > self.curve_threshold:
      print(f'MINI CURVE FOUND')
      above_threshold = pre_curve_dataset[pre_curve_dataset['TAC'] > self.curve_threshold].copy()
      above_threshold['group'] = (above_threshold.index.to_series().diff() > 1).cumsum()
      #For each new candidate curve, store start index and end index
      curve_start_end_index_pairs = above_threshold.groupby('group').apply(lambda g: [g.index[0], g.index[-1]]).sort_index(ascending=False).tolist()

      for candidate_curve_start_index, candidate_curve_end_index in curve_start_end_index_pairs:
        print('Current Curve Start: ', self.tac_event_start_index)

        #curve must end within 60 minutes of main curve
        if candidate_curve_end_index < (self.tac_event_start_index - max_distance):
          print('start not reassigned - curve too far')

        #curve must be at least 10 minutes in duration
        elif (candidate_curve_end_index - candidate_curve_start_index) < min_duration:
          print('start not reassigned - curve too small')

        #break between curve must not contain negative values
        elif pre_curve_dataset.loc[candidate_curve_end_index:self.tac_event_start_index, 'TAC'].min() < min_allowed_value:
          """ ATTEMPT TO IMPUTE GAP ? """
          print('start not reassigned - negative value')

        #curve meets all quality conditions... include it  
        else:
          print('START REASSIGNED')
          self.tac_event_start_index = candidate_curve_start_index
    
  def include_subsequent_curves(self, max_distance = 60, min_duration = 10, min_allowed_value = -50):
    #revises curve start to inclue nearby curves occuring before main curve
    post_curve_dataset = self.dataset[self.tac_event_end_index+1:self.curve_search_end_index].dropna(subset=['TAC'])
    if post_curve_dataset['TAC'].max() > self.curve_threshold:
      print(f'MINI CURVE FOUND after EVENT')
      above_threshold = post_curve_dataset[post_curve_dataset['TAC'] > self.curve_threshold].copy()
      above_threshold['group'] = (above_threshold.index.to_series().diff() > 1).cumsum()
      #For each new candidate curve, store start index and end index
      curve_start_end_index_pairs = above_threshold.groupby('group').apply(lambda g: [g.index[0], g.index[-1]]).sort_index(ascending=True).tolist()

      for candidate_curve_start_index, candidate_curve_end_index in curve_start_end_index_pairs:
        print('Current Curve End: ', self.tac_event_end_index)

        #candidate curve must start within 60 minutes of main curve
        if candidate_curve_start_index > (self.tac_event_end_index + 1 + max_distance):
          print('end not reassigned - curve too far')

        #candidate curve must be at least 10 minutes in duration
        elif (candidate_curve_end_index - candidate_curve_start_index) < min_duration:
          print('end not reassigned - curve too small')

        #break between main and candidate curve must not contain negative values
        elif post_curve_dataset.loc[:candidate_curve_start_index, 'TAC'].min() < min_allowed_value:
          """ ATTEMPT TO IMPUTE GAP ? """
          print('end not reassigned - negative value')

        #curve meet all quality conditions... include it  
        else:
          print(f'END REASSIGNED: {candidate_curve_start_index}')
          self.tac_event_end_index = candidate_curve_end_index

  def get_quality_metrics(self, df, df_version = 'SEARCH'):
    """df_version can either be 'SEARCH' or 'CURVE' """
    try:
      device_ids = df['device_id'].unique().tolist()
      dataset_duration = len(df) / 60
      device_turned_on_duration = (df['device_turned_on'].sum()) / 60
      device_worn_duration = (df['device_worn_model'].sum()) / 60
      # signal_imputed_duration = df['imputed'].sum() / 60
      quality_features = {
        f'device_one_{df_version}' : device_ids[0] if len(device_ids) > 0 else None,
        f'device_two_{df_version}' : device_ids[1] if len(device_ids) > 1 else None,
        f'device_count_{df_version}' : len(device_ids),
        f'device_turned_on_duration_{df_version}': device_turned_on_duration,
        f'device_turned_on_percent_{df_version}': device_turned_on_duration / dataset_duration,
        f'device_worn_duration_{df_version}': device_worn_duration,
        f'device_worn_percent_{df_version}': device_worn_duration / dataset_duration,
        # f'imputed_duration_{df_version}': signal_imputed_duration,
        # f'imputed_percent_{df_version}': signal_imputed_duration / dataset_duration,
        f'negative_duration_{df_version}': (df['TAC'] <= 0).sum() / 60,
        f'sub_negative_10_duration_{df_version}': (df['TAC'] <= -10).sum() / 60
      }

      if df_version == 'SEARCH':
        self.quality_features_of_search.update(quality_features)
      elif df_version == 'CURVE':
        self.quality_features_of_curve.update(quality_features)
      else:
        print(f'No update make to quality features. Dataframe Version [ {df_version} ] not recognized.')
    except Exception:
      print(traceback.format_exc())
      print(f'Quality Features ({df_version}) not generated. See ERROR above.')

  def get_tac_features(self, df, time_var = 'Duration_Hrs', df_version = 'SEARCH'):
    """ df_version can be either 'SEARCH' or 'CURVE' """
    try:
      mean_tac, sd_tac, sem_tac = get_mean_stdev_sem(df, 'TAC')
      tac_features = {
        f'begin_{df_version}': df['datetime'].iloc[0],
        f'end_{df_version}': df['datetime'].iloc[-1],
        f'duration_{df_version}': ((df['datetime'].iloc[-1] - df['datetime'].iloc[0]).total_seconds() + 60) / 3600,
        f'first_tac_{df_version}': df['TAC'].iloc[0],
        f'last_tac_{df_version}': df['TAC'].iloc[-1],
        f'mean_tac_{df_version}': mean_tac,
        f'sd_tac_{df_version}': sd_tac,
        f'sem_tac_{df_version}': sem_tac,
        f'peak_{df_version}': get_peak(df, 'TAC'),
        f'auc_total_{df_version}' : get_auc(df, 'TAC')
      }

      if df_version == 'SEARCH':
        self.tac_features_of_search.update(tac_features)
      elif df_version == 'CURVE':
        self.tac_features_of_curve.update(tac_features)
      else:
        print(f'No update make to quality features. Dataframe Version [ {df_version} ] not recognized.')
    
    except Exception:
      print(traceback.format_exc())
      print(f'TAC Features ({df_version}) not generated. See ERROR above.')

  def get_curve_specific_features(self, df):
    tac_features = self.tac_features_of_curve
    try:
      #curve specific features
      peak_index = get_peak_index(df, 'TAC') if len(df) else None
      rise_duration = (df.loc[peak_index, 'Duration_Hrs'] - df.loc[0, 'Duration_Hrs']) + (1/60)
      fall_duration = (df.loc[len(df)-1, 'Duration_Hrs'] - df.loc[peak_index, 'Duration_Hrs']) + (1/60)
      relative_peak = (tac_features['peak_CURVE'] - self.curve_threshold)
      relative_rise = (tac_features['peak_CURVE'] - tac_features['first_tac_CURVE'])
      relative_fall = (tac_features['peak_CURVE'] - tac_features['last_tac_CURVE'])

      curve_specific_features = {
        'rise_duration_CURVE' : rise_duration,
        'fall_duration_CURVE' : fall_duration,
        'relative_peak_CURVE' : relative_peak,
        'rise_rate_CURVE' : get_rise_rate(rise_duration, relative_rise),
        'fall_rate_CURVE' : get_fall_rate(fall_duration, relative_fall),
        'rise_complete_perc_CURVE' : 1 if tac_features['first_tac_CURVE'] <= self.curve_threshold else (tac_features['peak_CURVE'] - tac_features['first_tac_CURVE']) / relative_peak,
        'fall_complete_perc_CURVE' : 1 if tac_features['last_tac_CURVE'] <= self.curve_threshold else (tac_features['peak_CURVE'] - tac_features['last_tac_CURVE']) / relative_peak
      }
      self.curve_specific_features.update(curve_specific_features)
    except Exception:
      print(traceback.format_exc())
      print(f'Curve-Specific Features not generated. See ERROR above.')
  
  def get_features_of_search_dataset(self):
    if self.quality_features_of_search['data_found_SEARCH']:
      self.get_quality_metrics(self.curve_start_search_dataset, df_version='SEARCH')
      self.get_tac_features(self.curve_start_search_dataset, df_version='SEARCH')
  
  def get_features_of_curve_dataset(self):
    if self.quality_features_of_curve['data_found_CURVE']:
      self.get_quality_metrics(self.curve_dataset, df_version='CURVE')
      self.get_tac_features(self.curve_dataset, df_version='CURVE')
      self.get_curve_specific_features(self.curve_dataset)
  
  def set_search_plot_dataset(self):
    try:
      search_plot_start = self.curve_search_start_time - pd.Timedelta(hours=1)
      start_index = get_closest_index_with_timestamp(self.dataset, search_plot_start)
      end_index = get_closest_index_with_timestamp(self.dataset, self.curve_end_time_limit)
      self.search_plot_dataset = self.dataset.iloc[start_index:end_index]
    except Exception:
      print('Failed to slice curve plot dataset.')
      print(traceback.format_exc())
      self.search_plot_dataset = pd.DataFrame(columns=self.dataset.columns)

  def set_curve_plot_dataset(self):
    try:
      start_curve_plot_time = pd.to_datetime(self.tac_features_of_curve['begin_CURVE']) - pd.Timedelta(hours=1)
      end_curve_plot_time = pd.to_datetime(self.tac_features_of_curve['end_CURVE']) + pd.Timedelta(hours=1)
      start_index = get_closest_index_with_timestamp(self.dataset, start_curve_plot_time)
      end_index = get_closest_index_with_timestamp(self.dataset, end_curve_plot_time)
      self.curve_plot_dataset = self.dataset.iloc[start_index:end_index]
    except Exception:
      print('Failed to slice curve plot dataset.')
      print(traceback.format_exc())
      self.curve_plot_dataset = pd.DataFrame(columns=self.dataset.columns)

  def save_plot_smooth_tac(self, plot_folder, df_version):
    try:
      df = self.search_plot_dataset if df_version == 'SEARCH' else self.curve_plot_dataset
      annotations = self.search_timestamps if df_version == 'SEARCH' else self.curve_timestamps 
      plot_path = plot_smoothed_curve(
        df, plot_folder, self.subid, self.dataset_identifier, self.event_number, 
        self.tac_features_of_curve['peak_CURVE'], self.curve_threshold, self.tac_event_start_index, 
        self.tac_event_end_index, df_version = df_version,
        event_timestamps = annotations,
        subtitle_text = f'{self.subid} -- Event: {self.event_number} -- Drinks: {self.drink_total} -- {df_version}'
      )
      return plot_path
    except Exception:
      print(traceback.format_exc())
  
  def save_plot_of_device_removal(self, plot_folder, df_version, prediction_column = 'device_worn_model'):
    try:
      df = self.search_plot_dataset if df_version == 'SEARCH' else self.curve_plot_dataset
      annotations = self.search_timestamps if df_version == 'SEARCH' else self.curve_timestamps 
      plot_path = plot_device_removal(
        df, plot_folder, self.subid, self.event_number, self.dataset_identifier, 
        'Temperature_C', 'datetime', motion_variable='Motion', add_color=True, 
        method = 'Model Predictions', prediction_column = prediction_column, df_version = df_version,
        event_timestamps = annotations,
        subtitle_text = f'SubID: {self.subid} -- Event: {self.event_number} -- {df_version} -- Algorithm Non-Wear Detection'
      )
      return plot_path
    except Exception:
      print(traceback.format_exc())

  def save_plot_of_signal_processing(self, plot_folder, df_version):

    try:
      df = self.search_plot_dataset if df_version == 'SEARCH' else self.curve_plot_dataset
      annotations = self.search_timestamps if df_version == 'SEARCH' else self.curve_timestamps 
      plot_path = plot_signal_processing(
        df, plot_folder, self.subid, self.event_number, self.dataset_identifier, df_version,
        self.curve_threshold, self.tac_event_start_index, self.tac_event_end_index,
        self.tac_features_of_curve[f'peak_CURVE'], time_variable='datetime', title = f'Signal Processing',
        event_timestamps = annotations,
        subtitle_text = f'{self.subid} -- Event: {self.event_number} -- Drinks: {self.drink_total} -- {df_version}'
      )
      return plot_path
    except Exception:
      print(traceback.format_exc())

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
    
