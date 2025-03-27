import pandas as pd
import numpy as np
from App.SDM.Feature_Engineering.tac_features import *
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.linear_model import LinearRegression
import scipy.interpolate
from sklearn.gaussian_process.kernels import DotProduct, Matern, ConstantKernel
import math  

"""
Separate functions for retrieving indices of
  -null values (device turned off) [buffered 1 value on either side]
  -non-wear [buffered half the length of non-wear duration on either side]
  -tac jump values (cleaning out extreme jumps based on rolling 5-value rise rate)
  -tac plummet values (cleaning out extreme drops based on rolling 5-value fall rate)

Then impute_low_quality_data() retrieves all of these indices, combines the regions if low quality occurences are within 20 minutes.
then imputes if the training data has enough device worn

"""
def get_gap_indices(df):
  gap_indices = df[df['TAC'].isnull()].index.tolist()
  gap_indices_with_buffer = set()
  
  i = 0
  while i < len(gap_indices):
    region_start = gap_indices[i]
    region_end = region_start
    while i + 1 < len(gap_indices) and gap_indices[i + 1] == gap_indices[i] + 1:
      i += 1
      region_end = gap_indices[i]
    
    start_idx = max(region_start - 1, gap_indices[0])
    end_idx = min(region_end + 1, gap_indices[-1])
    
    gap_indices_with_buffer.update(range(start_idx, end_idx + 1))
    i += 1

  return sorted(gap_indices_with_buffer)

def get_non_wear_indices(df):
  non_wear_indices = df[df['device_worn_model'] == 0].index.tolist()
  non_wear_indices_with_buffer = set()

  i = 0
  while i < len(non_wear_indices):
    region_start = non_wear_indices[i]
    region_end = region_start 
    while i + 1 < len(non_wear_indices) and non_wear_indices[i + 1] == non_wear_indices[i] + 1:
      i += 1
      region_end = non_wear_indices[i]
    
    region_length = region_end - region_start + 1
    buffer = min(region_length // 2, 10) if region_length >= 2 else 1
    
    start_idx = max(region_start - buffer, non_wear_indices[0])
    end_idx = min(region_end + buffer, non_wear_indices[-1])
    
    non_wear_indices_with_buffer.update(range(start_idx, end_idx + 1))
    i += 1
  
  return sorted(non_wear_indices_with_buffer)

def get_non_wear_indices(df):
  non_wear_indices = df[df['device_worn_model'] == 0].index.tolist()
  non_wear_indices_with_buffer = set()

  i = 0
  while i < len(non_wear_indices):
    region_start = non_wear_indices[i]
    region_end = region_start 
    while i + 1 < len(non_wear_indices) and non_wear_indices[i + 1] == non_wear_indices[i] + 1:
      i += 1
      region_end = non_wear_indices[i]
    
    region_length = region_end - region_start + 1
    buffer = min(region_length // 2, 10) if region_length >= 2 else 1
    
    start_idx = max(region_start - buffer, non_wear_indices[0])
    end_idx = min(region_end + buffer, non_wear_indices[-1])
    
    non_wear_indices_with_buffer.update(range(start_idx, end_idx + 1))
    i += 1
  
  return sorted(non_wear_indices_with_buffer)

def get_jump_indices(df, rolling_n=5, rise_rate_threshold=40, projected_tac_change_rate=1.2, max_jump_labeling_length = (60*6)):
  """ rise is based on change in tac per minute """
  jump_indices_candidates = set()
  jump_indices = set()
  tac_values = df["TAC"].values
  df_indices = df.index
  
  slopes = []
  for i in range(len(tac_values) - rolling_n + 1):
    recent_values = tac_values[i:i + rolling_n]
    #only assess if at least 3 of the values are descending
    if np.sum(np.diff(recent_values) > 0) >= 3:
      slope = (recent_values[-1] - recent_values[0]) / rolling_n
      slopes.append(slope)

      min_tac = min(recent_values)
      max_tac = max(recent_values)
      min_tac_index = np.argmin(recent_values)
      max_tac_index = np.argmax(recent_values)
      max_occurs_after_min = (min_tac_index - max_tac_index) > 0
      tac_change = max_tac - min_tac

      if (slope > rise_rate_threshold) or ((tac_change > (rise_rate_threshold*2)) and (max_occurs_after_min)):
        #jump i forward 
        print(f'JUMP: {slope} per minute')
        
        #add indices in the future until TAC returns to a realistically lower TAC
        indices_to_add = set(df_indices[i:i + rolling_n])
        jump_indices.update(indices_to_add)
        #projection will start at value before jump occured
        projected_tac_upward = recent_values[0]
        projected_tac_downward = recent_values[0]
        count = 0  
        
        for count in range(max_jump_labeling_length):
          idx = i + rolling_n + count
          if idx >= len(tac_values):  # Prevent out-of-bounds error
            break
          distance_to_projected_tac = min(abs(projected_tac_upward - tac_values[idx]), abs(projected_tac_downward - tac_values[idx]))
          if idx >= len(tac_values) or (distance_to_projected_tac < 10):
            break
          projected_tac_upward += projected_tac_change_rate
          projected_tac_downward -= projected_tac_change_rate

          indices_to_add.add(df_indices[idx])
          #for jumps but not plummets
          jump_indices_candidates.update(indices_to_add)
          jump_indices.update(indices_to_add)
        
  if len(slopes):
    print('Max SLOPE:')
    print(max(slopes))
  jump_indices_candidates = sorted(jump_indices_candidates, key=lambda idx: df.index.get_loc(idx))
  jump_indices = sorted(jump_indices, key=lambda idx: df.index.get_loc(idx))

  return  jump_indices_candidates, jump_indices

def get_plummet_indices(df, jump_indices_candidates = (), rolling_n = 5, fall_rate_threshold = -40, projected_tac_change_rate = 3, max_plummet_labeling_length = (60*6)):
  plummet_indices_candidates = set()
  plummet_indices = set()
  tac_values = df["TAC"].values
  df_indices = df.index
  
  slopes = []
  for i in range(len(tac_values) - rolling_n + 1):
    recent_values = tac_values[i:i + rolling_n]
    #only assess if at least 3 values are descending AND no values are associated with a TAC jump [such values should be taken care of by jump cleaning]
    if np.sum(np.diff(recent_values) < 0) >= 3 and not any([tac in jump_indices_candidates for tac in recent_values]):
      slope = (recent_values[-1] - recent_values[0]) / rolling_n
      slopes.append(slope)

      min_tac = min(recent_values)
      max_tac = max(recent_values)
      min_tac_index = np.argmin(recent_values)
      max_tac_index = np.argmax(recent_values)
      min_occurs_after_max = (max_tac_index - min_tac_index) > 0
      tac_change = min_tac - max_tac

      if (slope < fall_rate_threshold) or ((tac_change < (fall_rate_threshold*2) and (min_occurs_after_max))):
        print(f'PLUMMET: {slope} per minute / {tac_change}')
        
        projected_tac = recent_values[0]
        count = 0  

        #add slope indices and indices in the future until TAC returns to a realistically lower TAC
        indices_to_add = set(df_indices[i:i + rolling_n])
        plummet_indices.update(indices_to_add) #capture the plumetting slope even if slope wont be candidate for imputation
        for count in range(max_plummet_labeling_length):  # Limit flagging up to 90 indices
          idx = i + rolling_n + count
          if idx >= len(tac_values) or tac_values[idx] >= projected_tac:
            plummet_indices_candidates.update(indices_to_add)
            plummet_indices.update(indices_to_add)
            break
          #projected_tac always trends downward, because if tac plummeted, we arent expecting any values above
          projected_tac -= projected_tac_change_rate
          indices_to_add.add(df_indices[idx])
  
  if len(slopes):
    print('MIN SLOPE:')
    print(min(slopes)) 
    
  plummet_indices_candidates = sorted(plummet_indices_candidates, key=lambda idx: df.index.get_loc(idx))   
  plummet_indices = sorted(plummet_indices, key=lambda idx: df.index.get_loc(idx))
  return plummet_indices_candidates, plummet_indices

def convert_index_sets_to_index_region_pairs(*args, merge_distance = 20):
  combined_indices = sorted(set().union(*args))
  grouped_regions = []
  if combined_indices:
    region_start = combined_indices[0]
    for i in range(1, len(combined_indices)):
      if combined_indices[i] != combined_indices[i - 1] + 1:
        region_end = combined_indices[i - 1]
        grouped_regions.append([region_start, region_end])  # Add the region
        region_start = combined_indices[i]  # Start a new region  
    grouped_regions.append([region_start, combined_indices[-1]])
  
  merged_regions = []
  for region in grouped_regions:
    if not merged_regions: 
      merged_regions.append(region)
    elif region[0] > merged_regions[-1][1] + merge_distance:
      merged_regions.append(region)
    else:
      merged_regions[-1][1] = region[1]

  return merged_regions

def label_imputation_reason(df, low_quality_region_start, low_quality_region_end, gap_indices, non_wear_indices, jump_indices_candidates, plummet_indices_candidates):
    imputation_dict = {
      'gap_imputed': [],
      'non_wear_imputed': [],
      'jump_imputed': [],
      'plummet_imputed': [],
      'between_low_quality_imputed': []
    }

    for idx in range(low_quality_region_start, low_quality_region_end + 1):
      if idx in gap_indices:
        imputation_dict['gap_imputed'].append(idx)
      elif idx in non_wear_indices:
        imputation_dict['non_wear_imputed'].append(idx)
      elif idx in jump_indices_candidates:
        imputation_dict['jump_imputed'].append(idx)
      elif idx in plummet_indices_candidates:
        imputation_dict['plummet_imputed'].append(idx)
      else:
        imputation_dict['between_low_quality_imputed'].append(idx)

    for reason, indices in imputation_dict.items():
      df.loc[indices, reason] = 1 
    
    return df

def impute_low_quality_data(df: pd.DataFrame, impute_gaps = True, impute_non_wear = True, impute_jumps = True, impute_plummets = True):
  df['TAC_pre_imputation'] = df['TAC'].copy()
  df['imputed'] = 0
  df['between_low_quality_imputed'] = 0

  # gap [unbuffered] is device_turned_on == 0
  df['gap_buffered'] = 0
  df['gap_imputed'] = 0
  gap_indices = get_gap_indices(df) if impute_gaps else ()
  df.loc[gap_indices, 'gap_buffered'] = 1

  # non wear [unbuffered] is device_turned_on == 0
  df['non_wear_buffered'] = 0
  df['non_wear_imputed'] = 0
  non_wear_indices = get_non_wear_indices(df) if impute_non_wear else ()
  df.loc[non_wear_indices, 'non_wear_buffered'] = 1

  df['jump'] = 0
  df['jump_imputed'] = 0
  jump_indices_candidates, jump_indices = get_jump_indices(df) if impute_jumps else ()
  df.loc[jump_indices, 'jump'] = 1

  df['plummet'] = 0
  df['plummet_imputed'] = 0
  plummet_indices_candidates, plummet_indices = get_plummet_indices(df, jump_indices_candidates=jump_indices_candidates) if impute_plummets else ()
  df.loc[plummet_indices, 'plummet'] = 1

  low_quality_regions = convert_index_sets_to_index_region_pairs(gap_indices, non_wear_indices, jump_indices_candidates, plummet_indices_candidates)

  for low_quality_region_start, low_quality_region_end in low_quality_regions:
    
    low_quality_region_length = low_quality_region_end - low_quality_region_start
    low_quality_region_data = df.iloc[low_quality_region_start: low_quality_region_end+1]

    training_data_start = max(0, low_quality_region_start - 60)
    training_data_end = min(low_quality_region_end + 60 + 1, len(df) - 1)
    train_data_before = df.iloc[training_data_start:low_quality_region_start]
    train_data_after = df.iloc[low_quality_region_end+1:training_data_end]

    min_training_data = max(10, round(low_quality_region_length / 6))
    print("MIN TRAING DATA REQUIRED:", min_training_data)

    worn_minutes_before = train_data_before['device_worn_model'].sum()
    worn_percent_before = (worn_minutes_before / len(train_data_before)) if not train_data_before.empty else 0
    training_data_before_valid = (worn_minutes_before > min_training_data) and (worn_percent_before > 0.5)

    worn_minutes_after = train_data_after['device_worn_model'].sum()
    worn_percent_after = (worn_minutes_after / len(train_data_after)) if not train_data_after.empty else 0
    training_data_after_valid = (worn_minutes_after > min_training_data) and (worn_percent_after > 0.5)

    non_wear_region_too_long = low_quality_region_length > 180

    if (not non_wear_region_too_long) and training_data_before_valid and training_data_after_valid:
      print('REACHED TRAINING & IMPUTING')
      t_before = train_data_before[(~train_data_before['TAC'].isnull()) & (train_data_before['device_worn_model']==1)]
      t_after = train_data_after[(~train_data_after['TAC'].isnull()) & (train_data_after['device_worn_model']==1)]
      t_all = pd.concat([t_before, t_after])

      x = t_all['Duration_Hrs']
      y = t_all['TAC']
      x_non_wear = low_quality_region_data['Duration_Hrs']      

      kernel = Matern(length_scale=0.4, nu=0.3, length_scale_bounds=(1e-3, 1e3)) * ConstantKernel(constant_value=5)
      model = GaussianProcessRegressor(kernel=kernel, random_state=0)
      model.fit(x.to_numpy().reshape(-1, 1), y)
      predictions = model.predict(x_non_wear.to_numpy().reshape(-1, 1))
      predictions = predictions.flatten()  # Ensures it's always 1D
      df.iloc[x_non_wear.index, df.columns.get_loc('TAC')] = predictions
      df.iloc[x_non_wear.index, df.columns.get_loc('imputed')] = 1
      df = label_imputation_reason(df, low_quality_region_start, low_quality_region_end, gap_indices, non_wear_indices, jump_indices_candidates, plummet_indices_candidates)

    else:
      print('NOT IMPUTED')
    
  return df



def impute_device_off_gaps(df: pd.DataFrame, null_duration_minutes_max = 120):
  """
  if device off found, take an half-hour portion (30 min before and after)
  to make quality determination (i.e., can we use data to compute), get 
  counts of: 
    > before: 
      > device_worn == 1 
      > pass > 80%  
    > 
   
  """
  df['TAC_pre_gap_imputation'] = df['TAC'].copy()
  # df['Temp_pre_imputation'] = df['Temp'].copy()
  # df['Motion_pre_imputation'] = df['Motion'].copy()
  
  null_regions = []
  gap_indices = df[df['TAC'].isnull()].index
  if not gap_indices.empty:
    diff = gap_indices.to_series().diff().ne(1)  # Identify breaks in sequence
    groups = diff.cumsum()  # Group consecutive nulls together
    for group, group_indices in gap_indices.to_series().groupby(groups):
      null_regions.append([group_indices.iloc[0], group_indices.iloc[-1]])
  
  print(null_regions)
  
  # Combine null regions if the end of one region is within 5 indices of the next region's start
  merged_null_regions = []
  for region in null_regions:
    if not merged_null_regions: 
      merged_null_regions.append(region)
    elif region[0] > merged_null_regions[-1][1] + 5:
      merged_null_regions.append(region)
    else:
      merged_null_regions[-1][1] = region[1]

  print(merged_null_regions)

  for null_start, null_end in merged_null_regions:
    print('FOUND NULLS')
    null_start = max(0, null_start - 1)
    null_end = min(null_end + 1, len(df) - 1)  # Ensure it doesn't exceed index range
    null_data = df.iloc[null_start:null_end + 1]  # Safe slicing

    train_data_before_idx = max(0, null_start - 30)
    train_data_after_idx = min(len(df), null_end + 30 + 1)
    train_data_before = df.iloc[train_data_before_idx:null_start]
    train_data_after = df.iloc[null_end+1:train_data_after_idx]
    print('length of train before, ', len(train_data_before))
    print('length of train after, ', len(train_data_after))

    #Quality Checks
    null_data_too_long = len(null_data) > null_duration_minutes_max
    # minimum_values_before = max(min(len(null_data), 30), 10) 

    minimum_values_before = 10
    # minimum_values_after = max(min(round(len(null_data)*0.8), 30), 8) 
    minimum_values_after = 10
    print('min before', minimum_values_before)
    print('min after', minimum_values_after)

    worn_minutes_before = train_data_before['device_worn_model'].sum()
    worn_percent_before = (worn_minutes_before / len(train_data_before)) if not train_data_before.empty else 0
    training_data_before_valid = (worn_minutes_before > minimum_values_before) and (worn_percent_before > 0.5)

    worn_minutes_after = train_data_after['device_worn_model'].sum()
    worn_percent_after = (worn_minutes_after / len(train_data_after)) if not train_data_after.empty else 0
    training_data_after_valid = (worn_minutes_after > minimum_values_after) and (worn_percent_after > 0.5)

    if (not null_data_too_long) and training_data_before_valid and training_data_after_valid:
      print('REACHED TRAINING & IMPUTING')
      t_before = train_data_before[(~train_data_before['TAC'].isnull()) & (train_data_before['device_worn_model']==1)]
      t_after = train_data_after[(~train_data_after['TAC'].isnull()) & (train_data_after['device_worn_model']==1)]
      t_all = pd.concat([t_before, t_after])
      
      x = t_all['Duration_Hrs']
      y = t_all['TAC']
      x_null = null_data['Duration_Hrs']      

      kernel = Matern(length_scale=0.4, nu=0.3, length_scale_bounds=(1e-3, 1e3)) * ConstantKernel(constant_value=5)
      model = GaussianProcessRegressor(kernel=kernel, random_state=0)
      model.fit(x.to_numpy().reshape(-1, 1), y)
      predictions = model.predict(x_null.to_numpy().reshape(-1, 1))
      predictions = predictions.flatten()  # Ensures it's always 1D
      df.iloc[null_start:null_end+1, df.columns.get_loc('TAC')] = predictions
      df.iloc[null_start:null_end+1, df.columns.get_loc('gap_imputed')] = 1
    else:
      print('NOT IMPUTED')
      print('null too long? ', null_data_too_long)
      print('valid training data before: ', training_data_before_valid)
      print('valid training data after: ', training_data_after_valid)

  return df

def impute_non_wear(df: pd.DataFrame, non_wear_duration_max = 120, min_training_before = 15):
  
  non_wear_regions = []
  non_wear_indices = df[df['device_worn_model'] == 0].index
  if not non_wear_indices.empty:
    diff = non_wear_indices.to_series().diff().ne(1)  # Identify breaks in sequence
    groups = diff.cumsum()  # Group consecutive nulls together
    for group, group_indices in non_wear_indices.to_series().groupby(groups):
      # non-wear must be at least 5 minutes consecutively
      if (group_indices.iloc[-1] - group_indices.iloc[0]) >= 5:
        #extend imputation region 10 minute before and after
        non_wear_regions.append([group_indices.iloc[0], group_indices.iloc[-1]])
  
  merged_non_wear_regions = []
  for region in non_wear_regions:
    if not merged_non_wear_regions: 
      merged_non_wear_regions.append(region)
    elif region[0] > merged_non_wear_regions[-1][1] + 20:
      merged_non_wear_regions.append(region)
    else:
      merged_non_wear_regions[-1][1] = region[1]

  for non_wear_region in merged_non_wear_regions:
    non_wear_region_start = max(0, non_wear_region[0] - 8)
    non_wear_region_end = min(non_wear_region[1] + 8, len(df) - 1)
    # non_wear_region_indices = [idx for idx in range(non_wear_region_start, non_wear_region_end + 1)]
    non_wear_region_length = non_wear_region_end - non_wear_region_start
    non_wear_region_data = df.iloc[non_wear_region_start: non_wear_region_end+1]

    training_data_start = max(0, non_wear_region_start - 30)
    training_data_end = min(non_wear_region_end + 30 + 1, len(df) - 1)
    train_data_before = df.iloc[training_data_start:non_wear_region_start]
    train_data_after = df.iloc[non_wear_region_end+1:training_data_end]

    min_training_data = max(10, round(non_wear_region_length / 6))

    worn_minutes_before = train_data_before['device_worn_model'].sum()
    worn_percent_before = (worn_minutes_before / len(train_data_before)) if not train_data_before.empty else 0
    training_data_before_valid = (worn_minutes_before > min_training_data) and (worn_percent_before > 0.5)

    worn_minutes_after = train_data_after['device_worn_model'].sum()
    worn_percent_after = (worn_minutes_after / len(train_data_after)) if not train_data_after.empty else 0
    training_data_after_valid = (worn_minutes_after > min_training_data) and (worn_percent_after > 0.5)

    non_wear_region_too_long = non_wear_region_length > non_wear_duration_max

    if (not non_wear_region_too_long) and training_data_before_valid and training_data_after_valid:
      print('REACHED TRAINING & IMPUTING')
      t_before = train_data_before[(~train_data_before['TAC'].isnull()) & (train_data_before['device_worn_model']==1)]
      t_after = train_data_after[(~train_data_after['TAC'].isnull()) & (train_data_after['device_worn_model']==1)]
      t_all = pd.concat([t_before, t_after])

      x = t_all['Duration_Hrs']
      y = t_all['TAC']
      x_non_wear = non_wear_region_data['Duration_Hrs']      

      kernel = Matern(length_scale=0.4, nu=0.3, length_scale_bounds=(1e-3, 1e3)) * ConstantKernel(constant_value=5)
      model = GaussianProcessRegressor(kernel=kernel, random_state=0)
      model.fit(x.to_numpy().reshape(-1, 1), y)
      predictions = model.predict(x_non_wear.to_numpy().reshape(-1, 1))
      predictions = predictions.flatten()  # Ensures it's always 1D
      df.iloc[x_non_wear.index, df.columns.get_loc('TAC')] = predictions
      df.iloc[x_non_wear.index, df.columns.get_loc('non_wear_imputed')] = 1
    else:
      print('NOT IMPUTED')
    
  return df

""" RETIRED """  
def impute_tac_in_gaps(df, tac_variable, time_elapsed_variable, sampling_rate, hours_elapsed_threshold):
  gaps_filled_df = df.copy()
  gap_rows_filled = 0
  for idx, row in df.iterrows():
    if idx > 0:
      hours_elapsed_between_readings = row[time_elapsed_variable] - df.loc[idx-1, time_elapsed_variable]
      if hours_elapsed_between_readings > hours_elapsed_threshold:
        rows_to_add = math.floor(((hours_elapsed_between_readings * 60) / sampling_rate))
        gap_rows = pd.DataFrame(dict(zip(gaps_filled_df.columns.tolist(), [[None for i in range(0, rows_to_add)] for col_n in range(0, len(gaps_filled_df.columns))])))
        gap_rows['Duration_Hrs'] = [gaps_filled_df.loc[gap_rows_filled+idx-1,'Duration_Hrs'] + ((sampling_rate * (i+1)) / 60) for i in range(0, rows_to_add)]
        gap_rows['datetime'] = [gaps_filled_df.loc[gap_rows_filled+idx-1,'datetime'] + pd.Timedelta(minutes = (sampling_rate * (i+1))) for i in range(0, rows_to_add)]
        gap_rows[tac_variable] = [np.nan for i in range(0, rows_to_add)]
        gap_rows['device_id'] = [row['device_id'] for i in range(0, rows_to_add)]
        gap_rows['Firmware Version'] = [row['Firmware Version'] for i in range(0, rows_to_add)]
        if 'app version' in df.columns:
          gap_rows['app version'] = [row['app version'] for i in range(0, rows_to_add)]
        if 'device time zone' in df.columns:
          gap_rows['device time zone'] = [row['device time zone'] for i in range(0, rows_to_add)]
        gap_rows['gap_imputed'] = [1 for i in range(0, rows_to_add)]
        if 'gap_imputed' not in gaps_filled_df.columns:
          gaps_filled_df['gap_imputed'] = [0 for i in range(0, len(gaps_filled_df))]

        before_gap = gaps_filled_df.iloc[:idx+gap_rows_filled]
        after_gap = gaps_filled_df.iloc[idx+gap_rows_filled:]
        gaps_filled_df = pd.concat([before_gap, gap_rows, after_gap], ignore_index=True)
        gaps_filled_df.reset_index(inplace=True, drop=True)

        imputed_tac_list, not_imputable = impute(gaps_filled_df, gaps_filled_df[tac_variable].tolist(), 'Duration_Hrs', {}, gap_proportional_limit=0.7, override_index_check_count=True)
        gaps_filled_df['TAC_gaps_filled'] = imputed_tac_list
        gaps_filled_df[tac_variable] = gaps_filled_df['TAC_gaps_filled']
        gap_rows_filled += rows_to_add
  
  return gaps_filled_df

def impute(df_prior, tac_list, time_variable, index_check_count, knot_proportion = 0.10, variable='TAC', how='both', threshold=False, gap_proportional_limit = 0.40, override_index_check_count=False, extend_missing_idx = 0):

  df = df_prior.copy()
  cannot_impute = []

  #get a list of indices where artifacts have been removed
  missing_idx = [i for (i, tac) in enumerate(tac_list) if np.isnan([tac])]

  #artifact gap cannot take more than X% of dataset
  gap_limit = len(df) * gap_proportional_limit

  #create a list of each gap
  gaps = [[]]
  gap_count = 0
  for i, missing_tac_idx in enumerate(missing_idx):
    gaps[gap_count].append(missing_tac_idx)
    if i + 1 < len(missing_idx):
      #if there is a gap between the current missing_idx and the next
      if (missing_tac_idx + 1) != missing_idx[i+1]:
        missing_idx_to_add = [n for n in range(missing_tac_idx + 1, missing_tac_idx + 1 + extend_missing_idx) if (n < len(df)) and (n < missing_idx[i+1])]
        if len(missing_idx_to_add):
          for idx in missing_idx_to_add:
            gaps[gap_count].append(idx)
          #if the newly added idx still leaves a gap until the next missing idx
          if max(missing_idx_to_add) + 1 != missing_idx[i+1]:
            gap_count += 1
            gaps.append([])
    else:
      missing_idx_to_add = [n for n in range(missing_tac_idx + 1, missing_tac_idx + 1 + round(extend_missing_idx/3)) if (n < len(df))]
      if len(missing_idx_to_add):
        for idx in missing_idx_to_add:
          gaps[gap_count].append(idx)
  
  #If artifacts/device off gaps are less than 15 values apart, then take those two smaller gaps and combine to make large gap
  i=0
  while i < len(gaps) - 1:
    current_gap = gaps[i]
    next_gap = gaps[i + 1]
    gap_distance = next_gap[0] - current_gap[-1]
    #if gap is less than or equal to 15, then combine lists
    if 0 < gap_distance <= 15:
        filled_gap = list(range(current_gap[-1] + 1, next_gap[0]))
        combined_list = current_gap + filled_gap + next_gap
        gaps[i] = combined_list
        gaps.pop(i + 1)
    else:
        i += 1
    
  if len(missing_idx) > 0:
    for gap in gaps:
      if len(gap) < gap_limit:   
        if len(index_check_count) > 0:
          gap_index_check_count = {k: index_check_count[k] for k in gap}
          max_impute_attempts = max(gap_index_check_count.values())
        elif override_index_check_count:
          max_impute_attempts = 1
        else:
          max_impute_attempts = 0    
        #how many data points to use for building spline? X % of the dataset.
        #for front of gap
        first_missing_id = gap[0]
        data_limit = (int(len(df) * knot_proportion)) if (len(df) * knot_proportion) > 30 else 30
        front_ticker = 0
          #while the index is not beyond the length of df or greater than our local data limit
        while (first_missing_id - front_ticker > 0) and (front_ticker <= data_limit):
          front_ticker += 1
        front_index = first_missing_id - front_ticker
        data_before_gap = df.loc[front_index:first_missing_id-1]
        data_before_gap.reset_index(inplace=True)

        #for behind the gap
        last_missing_id = gap[-1]
        data_limit = (int(gap_limit / 2)) if gap_limit > 75 else 30
        back_ticker = 0
          #while the index is not beyond the length of df or greater than our local data limit
        while (last_missing_id + back_ticker < len(df)) and (back_ticker <= data_limit):
          back_ticker += 1
        back_index = last_missing_id + back_ticker
        data_after_gap = df.loc[last_missing_id+1:back_index]
        data_after_gap.reset_index(inplace=True)
        #before and after gap
        

        """
        sometimes the data after gap has values that are artifacts. while we do not want to impute for those now, 
        we do not want those to be used to train the imputation model. 
        this below loop detects those artifacts for removal
        """
        outlier_indices = {'before': [], 'after': []}
        if threshold:
          for position, dataset in {'before': data_before_gap, 'after': data_after_gap}.items():
            local_peak = get_peak(dataset, 'TAC')
            for i, row in dataset.iterrows():
              if i > 0:
                tac_difference = abs(row['TAC'] - dataset.loc[i - 1, 'TAC'])
                if (local_peak > 1) and (tac_difference > 1):
                  if ((np.log(tac_difference) / (np.log(local_peak) + 0.0001)) > threshold) and (local_peak > 3):
                    outlier_indices[position].append(i)
        data_before_gap.loc[outlier_indices['before'], 'TAC'] = np.nan
        data_after_gap.loc[outlier_indices['after'], 'TAC'] = np.nan
        data_around_gap = pd.concat([data_before_gap, data_after_gap])
        
        if len(data_after_gap) == 0:
          how = 'left'
        elif how == 'flex':
          remaining_duration = df_prior['Duration_Hrs'].max() - data_after_gap['Duration_Hrs'].min()
          TAC_diff_gap = data_after_gap.loc[min(data_after_gap.index.tolist()), 'TAC']  - data_before_gap.loc[max(data_before_gap.index.tolist()), 'TAC']
          local_peak = get_peak(df, 'TAC', window={'index': max(data_before_gap.index.tolist()), 'window': 100})
          TAC_diff_gap_too_big = (abs(TAC_diff_gap) / local_peak) > 0.5 and TAC_diff_gap > 10
          if remaining_duration < 1 or TAC_diff_gap_too_big:
            training_data = data_before_gap
          else:
            training_data = data_around_gap

        if how != 'flex':
          key = {
            'left': data_before_gap,
            'right': data_after_gap,
            'both': data_around_gap
          }
          training_data = key[how]
        x = training_data[~pd.isna(training_data[variable])][time_variable]
        y = training_data[~pd.isna(training_data[variable])][variable]
        x_with_gap = df[front_index:back_index][time_variable]      

        # 4 models can be attempted
        # if model fails to bring value below artifact threshold, then next model will be attempted
        
        if max_impute_attempts == 1:
          kernel = Matern(length_scale=0.4, nu=0.3, length_scale_bounds=(1e-3, 1e3)) * ConstantKernel(constant_value=5)
          model = GaussianProcessRegressor(kernel = kernel, random_state=0).fit(x.to_numpy().reshape(-1, 1), y)
          predictions = model.predict(x_with_gap.to_numpy().reshape(-1, 1))
          data_to_insert = predictions[front_ticker:front_ticker+(last_missing_id-first_missing_id+1)]
          tac_list[first_missing_id:last_missing_id+1] = data_to_insert
        elif max_impute_attempts == 2:
          model = LinearRegression().fit(x.to_numpy().reshape(-1, 1), y)
          predictions = model.predict(x_with_gap.to_numpy().reshape(-1, 1))
          data_to_insert = predictions[front_ticker:front_ticker+(last_missing_id-first_missing_id+1)]
          tac_list[first_missing_id:last_missing_id+1] = data_to_insert
        elif (max_impute_attempts == 3) and (how=='both'):
          y_interp = scipy.interpolate.interp1d(x.tolist(), y.tolist())
          predictions = y_interp(x_with_gap)
          data_to_insert = predictions[front_ticker:front_ticker+(last_missing_id-first_missing_id+1)]
          tac_list[first_missing_id:last_missing_id+1] = data_to_insert
        else:
          model = GaussianProcessRegressor(kernel = DotProduct(), random_state=0).fit(x.to_numpy().reshape(-1, 1), y)
          predictions = model.predict(x_with_gap.to_numpy().reshape(-1, 1))
          data_to_insert = predictions[front_ticker:front_ticker+(last_missing_id-first_missing_id+1)]
          tac_list[first_missing_id:last_missing_id+1] = data_to_insert
          for i in gap:
            cannot_impute.append(i)
      
      else:
        for i in gap:
          cannot_impute.append(i)

  tac_list = [tac if tac >= 0 else 0 for tac in tac_list]

  return tac_list, cannot_impute
  

        # import matplotlib.pyplot as plt
        # plt.figure()
        # plt.plot(x, y)
        # plt.title('interpolation')
        # plt.show()