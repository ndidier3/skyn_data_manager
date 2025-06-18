import pandas as pd
import numpy as np
from App.SDM.Feature_Engineering.tac_features import *
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.linear_model import LinearRegression
import scipy.interpolate
from sklearn.gaussian_process.kernels import DotProduct, Matern, ConstantKernel
import math  
import logging

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
    """
    Returns:
        Tuple of (set of gap indices, set of gap+buffer indices)
    """
    gap_indices = set(df[df['TAC'].isnull()].index.tolist())
    gap_indices_with_buffer = set()

    sorted_indices = sorted(gap_indices)
    i = 0
    while i < len(sorted_indices):
        region_start = sorted_indices[i]
        region_end = region_start
        while i + 1 < len(sorted_indices) and sorted_indices[i + 1] == sorted_indices[i] + 1:
            i += 1
            region_end = sorted_indices[i]
        start_idx = max(region_start - 1, sorted_indices[0])
        end_idx = min(region_end + 1, sorted_indices[-1])
        gap_indices_with_buffer.update(range(start_idx, end_idx + 1))
        i += 1
    return gap_indices, gap_indices_with_buffer

def get_non_wear_indices(df):
    """
    Returns:
        Tuple of (set of non-wear indices, set of non-wear+buffer indices)
    """
    non_wear_indices = set(df[df['device_worn_model'] == 0].index.tolist())
    non_wear_indices_with_buffer = set()

    sorted_indices = sorted(non_wear_indices)
    i = 0
    while i < len(sorted_indices):
        region_start = sorted_indices[i]
        region_end = region_start
        while i + 1 < len(sorted_indices) and sorted_indices[i + 1] == sorted_indices[i] + 1:
            i += 1
            region_end = sorted_indices[i]
        region_length = region_end - region_start + 1
        buffer = min(region_length // 2, 10) if region_length >= 2 else 1
        start_idx = max(region_start - buffer, sorted_indices[0])
        end_idx = min(region_end + buffer, sorted_indices[-1])
        non_wear_indices_with_buffer.update(range(start_idx, end_idx + 1))
        i += 1
    return non_wear_indices, non_wear_indices_with_buffer

def get_artifact_indices(df, max_labeling_length=(60*6)):
    """
    Detect both jumps (sudden increases) and plummets (sudden decreases) in TAC values
    based on consecutive value differences and max TAC within an hour.
    
    Args:
        df: DataFrame containing TAC values
        max_labeling_length: Maximum number of indices to label after the anomaly
    
    Returns:
        Tuple of (jump_indices, plummet_indices)
    """

    jump_indices = set()
    plummet_indices = set()
    
    # Compute max TAC within an hour window using pandas rolling
    max_tac_in_hour = df['TAC'].rolling(window=60*2+1, center=True, min_periods=1).max()
    
    tac_values = df["TAC"].values
    df_indices = df.index
    
    i = 0
    total_processed = 0
    jumps_detected = 0
    plummets_detected = 0
    
    
    while i < len(tac_values) - 1:
        total_processed += 1
        
        current_value = tac_values[i]
        next_value = tac_values[i + 1]
        
        # Skip if either value is NaN
        if np.isnan(current_value) or np.isnan(next_value):
            i += 1
            continue
            
        value_diff = next_value - current_value
        current_max_tac = max_tac_in_hour.iloc[i]
        
        # Calculate actual max labeling length that won't exceed DataFrame boundaries
        actual_max_labeling_length = min(max_labeling_length, len(tac_values) - (i + 2))
        
        # Check for jump (sudden increase)
        if value_diff > 100 or (current_max_tac >= 40 and value_diff > 0.9 * current_max_tac):
            jumps_detected += 1
            
            # Add the current and next indices
            indices_to_add = {df_indices[i], df_indices[i + 1]}
            jump_indices.update(indices_to_add)
            
            # Project forward
            projected_tac = current_value
            last_processed_idx = i  # Track the last index we process
            for count in range(actual_max_labeling_length):
                idx = i + 2 + count  # Start from the value after next
                if idx >= len(tac_values):
                    break
                    
                if tac_values[idx] < projected_tac:
                    jump_indices.update(indices_to_add)
                    break
                    
                projected_tac += 1.0  # Slightly increase acceptable TAC values
                indices_to_add.add(df_indices[idx])
                last_processed_idx = idx
            
            # Safety check to ensure we always move forward
            if last_processed_idx <= i:
                last_processed_idx = i + 1
            i = last_processed_idx  # Skip to the last processed index
                
        # Check for plummet (sudden decrease) - only if neither value is part of a jump
        elif (value_diff < -100 or (current_max_tac >= 40 and value_diff < -0.9 * current_max_tac)) and \
             df_indices[i] not in jump_indices and df_indices[i + 1] not in jump_indices:
            plummets_detected += 1
            
            # Add the current and next indices
            indices_to_add = {df_indices[i], df_indices[i + 1]}
            plummet_indices.update(indices_to_add)
            
            # Project forward
            projected_tac = current_value
            last_processed_idx = i + 1  # Track the last index we process
            for count in range(actual_max_labeling_length):
                idx = i + 2 + count  # Start from the value after next
                if idx >= len(tac_values):
                    break
                    
                if tac_values[idx] >= projected_tac:
                    plummet_indices.update(indices_to_add)
                    break
                    
                projected_tac -= 1.0  # Slightly decrease acceptable TAC values
                indices_to_add.add(df_indices[idx])
                last_processed_idx = idx
            
            # Safety check to ensure we always move forward
            if last_processed_idx <= i:
                last_processed_idx = i + 1
            i = last_processed_idx  # Skip to the last processed index
        else:
            i += 1  # Move to next value if no jump/plummet detected
    
    # Sort all index sets
    jump_indices = sorted(jump_indices, key=lambda idx: df.index.get_loc(idx))
    plummet_indices = sorted(plummet_indices, key=lambda idx: df.index.get_loc(idx))
    
    return jump_indices, plummet_indices

def get_extreme_negative_indices(df, negative_threshold = -10):
  """
  Get indices where TAC values are below a negative threshold.
  These values are physically impossible since TAC should always be non-negative.
  
  Args:
    df: DataFrame containing TAC values
    negative_threshold: Threshold below which values are considered extreme negative (default: -10)
    
  Returns:
    List of indices with extreme negative values
  """
  extreme_negative_indices = set()
  
  # Find all indices where TAC is below threshold
  negative_mask = df['TAC'] < negative_threshold
  extreme_negative_indices.update(df[negative_mask].index)
  
  # Sort indices to maintain order
  extreme_negative_indices = sorted(extreme_negative_indices, key=lambda idx: df.index.get_loc(idx))
  
  return extreme_negative_indices

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

def label_imputation_reason(df, low_quality_region_start, low_quality_region_end, gap_indices, non_wear_indices, jump_indices, plummet_indices, extreme_negative_indices_candidates):
    imputation_dict = {
      'gap_imputed': [],
      'non_wear_imputed': [],
      'jump_imputed': [],
      'plummet_imputed': [],
      'extreme_negative_imputed': [],
      'between_low_quality_imputed': []
    }

    for idx in range(low_quality_region_start, low_quality_region_end + 1):
      if idx in gap_indices:
        imputation_dict['gap_imputed'].append(idx)
      elif idx in non_wear_indices:
        imputation_dict['non_wear_imputed'].append(idx)
      elif idx in jump_indices:
        imputation_dict['jump_imputed'].append(idx)
      elif idx in plummet_indices:
        imputation_dict['plummet_imputed'].append(idx)
      elif idx in extreme_negative_indices_candidates:
        imputation_dict['extreme_negative_imputed'].append(idx)
      else:
        imputation_dict['between_low_quality_imputed'].append(idx)

    for reason, indices in imputation_dict.items():
      df.loc[indices, reason] = 1 
    
    return df

def impute_low_quality_data(df: pd.DataFrame):
  df['imputed'] = 0
  df['imp_cand'] = 0
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

  # gaps
  df['gap'] = 0
  df['gap_imp_cand'] = 0
  df['gap_imputed'] = 0
  gap_indices, gap_indices_with_buffer = get_gap_indices(df)
  #df already has 'gap' column
  df.loc[gap_indices, 'gap'] = 1
  df.loc[gap_indices_with_buffer, 'gap_imp_cand'] = 1

  # non wear
  df['non_wear'] = 0
  df['non_wear_imp_cand'] = 0
  df['non_wear_imputed'] = 0
  non_wear_indices, non_wear_indices_with_buffer = get_non_wear_indices(df)
  df.loc[non_wear_indices, 'non_wear'] = 1
  non_wear_indices_with_buffer = [idx for idx in non_wear_indices_with_buffer if idx not in gap_indices_with_buffer]
  df.loc[non_wear_indices_with_buffer, 'non_wear_imp_cand'] = 1

  # jumps and plummets
  df['jump'] = 0
  df['plummet'] = 0
  df['jump_imp_cand'] = 0
  df['jump_imputed'] = 0
  df['plummet_imp_cand'] = 0
  df['plummet_imputed'] = 0
  jump_indices, plummet_indices = get_artifact_indices(df)
  df.loc[jump_indices, 'jump'] = 1
  df.loc[plummet_indices, 'plummet'] = 1
  already_indexed = set(gap_indices_with_buffer) | set(non_wear_indices_with_buffer)
  jump_indices_filtered = [idx for idx in jump_indices if idx not in already_indexed]
  plummet_indices_filtered = [idx for idx in plummet_indices if idx not in already_indexed]
  df.loc[jump_indices_filtered, 'jump_imp_cand'] = 1
  df.loc[plummet_indices_filtered, 'plummet_imp_cand'] = 1
  
  # extreme negative values detection
  df['extreme_negative'] = 0
  df['extreme_negative_imp_cand'] = 0
  df['extreme_negative_imputed'] = 0
  extreme_negative_indices = get_extreme_negative_indices(df)
  df.loc[extreme_negative_indices, 'extreme_negative'] = 1
  already_indexed = already_indexed | set(jump_indices_filtered) | set(plummet_indices_filtered)
  extreme_negative_indices_filtered = [idx for idx in extreme_negative_indices if idx not in already_indexed]
  df.loc[extreme_negative_indices_filtered, 'extreme_negative_imp_cand'] = 1
  
  #get low-quality regions as pairs of start/end indices, which includes indices between low-quality regions
  low_quality_regions, between_low_quality_indices = convert_index_sets_to_index_region_pairs(
    gap_indices_with_buffer, 
    non_wear_indices_with_buffer, 
    jump_indices_filtered, 
    plummet_indices_filtered,
    extreme_negative_indices_filtered
  )  
  df['between_low_quality_imputed'] = 0
  df['between_low_quality_imp_cand'] = 0
  df.loc[between_low_quality_indices, 'between_low_quality_imp_cand'] = 1

  all_candidate_indices = already_indexed | set(extreme_negative_indices_filtered) | set(between_low_quality_indices)
  df.loc[all_candidate_indices, 'imp_cand'] = 1
  
  #impute low-quality regions
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
      df = label_imputation_reason(df, low_quality_region_start, low_quality_region_end, gap_indices_with_buffer, non_wear_indices_with_buffer, jump_indices_filtered, plummet_indices_filtered, extreme_negative_indices_filtered)
      
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
