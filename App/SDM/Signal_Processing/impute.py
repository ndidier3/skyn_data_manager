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

      # Calculate max positive difference between consecutive values for jumps
      consecutive_diffs = np.diff(recent_values)
      tac_change = np.max(consecutive_diffs)  # Only consider positive changes for jumps

      if (slope > rise_rate_threshold) or (tac_change > (rise_rate_threshold*2.25)):
        #jump i forward         
        #add indices in the future until TAC returns to a realistically lower TAC
        indices_to_add = set(df_indices[i:i + rolling_n])
        jump_indices.update(indices_to_add)
        #projection will start at value before jump occured
        projected_tac_upward = recent_values[0]
        count = 0  
        
        for count in range(max_jump_labeling_length):
          idx = i + rolling_n + count
          if idx >= len(tac_values):  # Prevent out-of-bounds error
            break
          if idx >= len(tac_values) or (tac_values[idx] < projected_tac_upward):
            break
          projected_tac_upward += projected_tac_change_rate

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

#review return to valid TAC
def get_plummet_indices(df, jump_indices_candidates = (), rolling_n = 5, fall_rate_threshold = -40, projected_tac_change_rate = 3, max_plummet_labeling_length = (60*6)):
  plummet_indices_candidates = set()
  plummet_indices = set()
  tac_values = df["TAC"].values
  df_indices = df.index
  
  slopes = []
  for i in range(len(tac_values) - rolling_n + 1):
    recent_values = tac_values[i:i + rolling_n]
    recent_indices = df_indices[i:i + rolling_n]
    #only assess if at least 3 values are descending AND no values are associated with a TAC jump [such values should be taken care of by jump cleaning]
    if np.sum(np.diff(recent_values) < 0) >= 3 and not any([idx in jump_indices_candidates for idx in recent_indices]):
      slope = (recent_values[-1] - recent_values[0]) / rolling_n
      slopes.append(slope)
      
      # Calculate max negative difference between consecutive values for plummets
      consecutive_diffs = np.diff(recent_values)
      tac_change = np.min(consecutive_diffs)  # Only consider negative changes for plummets

      if (slope < fall_rate_threshold) or (tac_change < (fall_rate_threshold*2.25)):
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

def get_extreme_negative_indices(df, negative_threshold = -10):
  """
  Get indices where TAC values are below a negative threshold.
  These values are physically impossible since TAC should always be non-negative.
  
  Args:
    df: DataFrame containing TAC values
    negative_threshold: Threshold below which values are considered extreme negative (default: -10)
    
  Returns:
    Tuple of (extreme_negative_indices_candidates, extreme_negative_indices)
    - extreme_negative_indices_candidates: Indices that are candidates for imputation
    - extreme_negative_indices: All indices with extreme negative values
  """
  extreme_negative_indices = set()
  extreme_negative_indices_candidates = set()
  
  # Find all indices where TAC is below threshold
  negative_mask = df['TAC'] < negative_threshold
  extreme_negative_indices.update(df[negative_mask].index)
  extreme_negative_indices_candidates.update(df[negative_mask].index)
  
  # Sort indices to maintain order
  extreme_negative_indices = sorted(extreme_negative_indices, key=lambda idx: df.index.get_loc(idx))
  extreme_negative_indices_candidates = sorted(extreme_negative_indices_candidates, key=lambda idx: df.index.get_loc(idx))
  
  return extreme_negative_indices_candidates, extreme_negative_indices

def convert_index_sets_to_index_region_pairs(*args, merge_distance = 20):
  combined_indices = sorted(set().union(*args))
  grouped_regions = []
  between_low_quality_indices = set()  # New set to track between low quality indices
  
  if combined_indices:
    region_start = combined_indices[0]
    for i in range(1, len(combined_indices)):
      if combined_indices[i] != combined_indices[i - 1] + 1:
        region_end = combined_indices[i - 1]
        grouped_regions.append([region_start, region_end])  # Add the region
        region_start = combined_indices[i]  # Start a new region  
    grouped_regions.append([region_start, combined_indices[-1]])
  
  merged_regions = []
  for i, region in enumerate(grouped_regions):
    if not merged_regions: 
      merged_regions.append(region)
    elif region[0] > merged_regions[-1][1] + merge_distance:
      merged_regions.append(region)
    else:
      # Add indices between the regions to between_low_quality_indices
      between_indices = range(merged_regions[-1][1] + 1, region[0])
      between_low_quality_indices.update(between_indices)
      merged_regions[-1][1] = region[1]

  return merged_regions, sorted(between_low_quality_indices)  # Return both merged regions and between low quality indices

def label_imputation_reason(df, low_quality_region_start, low_quality_region_end, gap_indices, non_wear_indices, jump_indices_candidates, plummet_indices_candidates, extreme_negative_indices_candidates):
    imputation_dict = {
      'gap_imputed': [],
      'non_wear_imputed': [],
      'extreme_negative_imputed': [],
      'jump_imputed': [],
      'plummet_imputed': [],
      'between_low_quality_imputed': []
    }

    for idx in range(low_quality_region_start, low_quality_region_end + 1):
      if idx in gap_indices:
        imputation_dict['gap_imputed'].append(idx)
      elif idx in non_wear_indices:
        imputation_dict['non_wear_imputed'].append(idx)
      elif idx in extreme_negative_indices_candidates:
        imputation_dict['extreme_negative_imputed'].append(idx)
      elif idx in jump_indices_candidates:
        imputation_dict['jump_imputed'].append(idx)
      elif idx in plummet_indices_candidates:
        imputation_dict['plummet_imputed'].append(idx)
      else:
        imputation_dict['between_low_quality_imputed'].append(idx)

    for reason, indices in imputation_dict.items():
      df.loc[indices, reason] = 1 
    
    return df

def impute_low_quality_data(df: pd.DataFrame, impute_gaps = True, impute_non_wear = True, impute_jumps = True, impute_plummets = True, impute_extreme_negative = True):
  df['imputed'] = 0
  df['between_low_quality_imputed'] = 0
  df['between_low_quality'] = 0  # New column for between low quality indices

  # Create DataFrame to store imputation information
  imputation_info = pd.DataFrame(columns=[
    'region_start',
    'region_end',
    'region_length',
    'worn_minutes_before',
    'worn_percent_before',
    'worn_minutes_after',
    'worn_percent_after',
    'min_training_data_required',
    'was_imputed',
    'reason_not_imputed',
    'high_quality_before',
    'low_quality_before',
    'high_quality_after',
    'low_quality_after',
    'total_training_before',
    'total_training_after'
  ])

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

  # Add extreme negative values detection
  df['extreme_negative'] = 0
  df['extreme_negative_imputed'] = 0
  extreme_negative_indices_candidates, extreme_negative_indices = get_extreme_negative_indices(df) if impute_extreme_negative else ()
  df.loc[extreme_negative_indices, 'extreme_negative'] = 1

  df['jump'] = 0
  df['jump_imputed'] = 0
  jump_indices_candidates, jump_indices = get_jump_indices(df) if impute_jumps else ()
  df.loc[jump_indices, 'jump'] = 1

  df['plummet'] = 0
  df['plummet_imputed'] = 0
  plummet_indices_candidates, plummet_indices = get_plummet_indices(df, jump_indices_candidates=jump_indices_candidates) if impute_plummets else ()
  df.loc[plummet_indices, 'plummet'] = 1

  low_quality_regions, between_low_quality_indices = convert_index_sets_to_index_region_pairs(
    gap_indices, 
    non_wear_indices, 
    jump_indices_candidates, 
    plummet_indices_candidates,
    extreme_negative_indices_candidates
  )
  df.loc[between_low_quality_indices, 'between_low_quality'] = 1  # Mark between low quality indices

  for low_quality_region_start, low_quality_region_end in low_quality_regions:
    
    low_quality_region_length = low_quality_region_end - low_quality_region_start
    low_quality_region_data = df.iloc[low_quality_region_start: low_quality_region_end+1]

    training_data_start = max(0, low_quality_region_start - 60)
    training_data_end = min(low_quality_region_end + 60 + 1, len(df) - 1)
    train_data_before = df.iloc[training_data_start:low_quality_region_start]
    train_data_after = df.iloc[low_quality_region_end+1:training_data_end]

    min_training_data = max(10, round(low_quality_region_length / 6))
    print("MIN TRAING DATA REQUIRED:", min_training_data)

    # Calculate high and low quality values in training regions
    high_quality_before = train_data_before[(~train_data_before['TAC'].isnull()) & (train_data_before['device_worn_model']==1)]
    low_quality_before = train_data_before[(train_data_before['TAC'].isnull()) | (train_data_before['device_worn_model']==0)]
    high_quality_after = train_data_after[(~train_data_after['TAC'].isnull()) & (train_data_after['device_worn_model']==1)]
    low_quality_after = train_data_after[(train_data_after['TAC'].isnull()) | (train_data_after['device_worn_model']==0)]

    worn_minutes_before = len(high_quality_before)
    worn_percent_before = (worn_minutes_before / len(train_data_before)) if not train_data_before.empty else 0
    training_data_before_valid = (worn_minutes_before > min_training_data) and (worn_percent_before > 0.5)

    worn_minutes_after = len(high_quality_after)
    worn_percent_after = (worn_minutes_after / len(train_data_after)) if not train_data_after.empty else 0
    training_data_after_valid = (worn_minutes_after > min_training_data) and (worn_percent_after > 0.5)

    non_wear_region_too_long = low_quality_region_length > 180

    # Record imputation attempt information
    imputation_attempt = {
      'region_start': low_quality_region_start,
      'region_end': low_quality_region_end,
      'region_length': low_quality_region_length,
      'worn_minutes_before': worn_minutes_before,
      'worn_percent_before': worn_percent_before,
      'worn_minutes_after': worn_minutes_after,
      'worn_percent_after': worn_percent_after,
      'min_training_data_required': min_training_data,
      'was_imputed': False,
      'reason_not_imputed': None,
      'high_quality_before': len(high_quality_before),
      'low_quality_before': len(low_quality_before),
      'high_quality_after': len(high_quality_after),
      'low_quality_after': len(low_quality_after),
      'total_training_before': len(train_data_before),
      'total_training_after': len(train_data_after)
    }

    if (not non_wear_region_too_long) and training_data_before_valid and training_data_after_valid:
      print('REACHED TRAINING & IMPUTING')
      t_all = pd.concat([high_quality_before, high_quality_after])

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
      df = label_imputation_reason(df, low_quality_region_start, low_quality_region_end, gap_indices, non_wear_indices, jump_indices_candidates, plummet_indices_candidates, extreme_negative_indices_candidates)
      
      imputation_attempt['was_imputed'] = True
    else:
      print('NOT IMPUTED')
      if non_wear_region_too_long:
        imputation_attempt['reason_not_imputed'] = 'region_too_long'
      elif not training_data_before_valid:
        if len(train_data_before) < min_training_data:
          imputation_attempt['reason_not_imputed'] = 'insufficient_quantity_before'
        else:
          imputation_attempt['reason_not_imputed'] = 'insufficient_quality_before'
      elif not training_data_after_valid:
        if len(train_data_after) < min_training_data:
          imputation_attempt['reason_not_imputed'] = 'insufficient_quantity_after'
        else:
          imputation_attempt['reason_not_imputed'] = 'insufficient_quality_after'
    
    imputation_info = pd.concat([imputation_info, pd.DataFrame([imputation_attempt])], ignore_index=True)
  
  # Store imputation info in the dataframe for later access
  df.attrs['imputation_info'] = imputation_info
  
  return df, imputation_info
