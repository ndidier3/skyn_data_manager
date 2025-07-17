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
        Set of indices where TAC values are null (device turned off)
    """
    gap_indices = set(df[df['TAC'].isnull()].index.tolist())
    return sorted(gap_indices, key=lambda idx: df.index.get_loc(idx))

def get_non_wear_indices(df):
    """
    Returns:
        Set of indices where device is not worn according to the model
    """
    non_wear_indices = set(df[df['device_worn_model'] == 0].index.tolist())
    return sorted(non_wear_indices, key=lambda idx: df.index.get_loc(idx))

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
            jump_indices.update({df_indices[i], df_indices[i + 1]})
            
            # Project forward
            projected_tac = current_value
            last_processed_idx = i  # Track the last index we process
            for count in range(actual_max_labeling_length):
                idx = i + 2 + count  # Start from the value after next
                if idx >= len(tac_values):
                    break
                    
                if tac_values[idx] < projected_tac:
                    break
                    
                projected_tac += 1.0  # Slightly increase acceptable TAC values
                jump_indices.add(df_indices[idx])
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
            plummet_indices.update({df_indices[i], df_indices[i + 1]})
            
            # Project forward
            projected_tac = current_value
            last_processed_idx = i + 1  # Track the last index we process
            for count in range(actual_max_labeling_length):
                idx = i + 2 + count  # Start from the value after next
                if idx >= len(tac_values):
                    break
                    
                if tac_values[idx] >= projected_tac:
                    break
                    
                projected_tac -= 3.0  # Slightly decrease acceptable TAC values
                plummet_indices.add(df_indices[idx])
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

def get_extreme_negative_indices(df, negative_threshold = -15):
  """
  Get indices where TAC values are below a negative threshold.
  These values are physically impossible since TAC should always be non-negative.
  
  Args:
    df: DataFrame containing TAC values
    negative_threshold: Threshold below which values are considered extreme negative (default: -15)
    
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

def convert_index_sets_to_index_region_pairs(*args):
  """
  Convert sets of indices into pairs of start/end indices for regions, merging regions that are close together.
  Also identifies proximal indices around and between low quality regions.
  
  Process:
  1. Combine all input indices
  2. For each index, calculate extension based on local region length
  3. Group continuous indices into regions
  4. Merge regions using dynamic merge_distance based on region lengths:
     - min_merge_distance = 10
     - max_merge_distance = 20
     - Scales between min and max based on combined length of adjacent regions:
       * At combined length <= 10: uses min_merge_distance
       * At combined length >= 60: uses max_merge_distance
       * Scales linearly between these points
  
  Args:
    *args: Sets of indices to combine
    
  Returns:
    Tuple of:
    - list of [start, end] region pairs with extended boundaries
    - sorted list of proximal indices, which includes:
      a) Extension indices: Values added by extending before/after each region
         (extension length = min(10, max(3, 3 + round(region_length/3))))
      b) Merged gap indices: Values that fall between merged regions
         (when regions are within dynamic merge_distance of each other)
      Note: Proximal indices never include any of the original input indices
  """
  # Combine all indices and get valid index bounds
  combined_indices = sorted(set().union(*args))
  if not combined_indices:
    return [], []
    
  min_valid_idx = min(combined_indices)
  max_valid_idx = max(combined_indices)
  
  # First pass: identify continuous regions to calculate proper extensions
  initial_regions = []
  region_start = combined_indices[0]
  current_end = region_start
  
  for idx in combined_indices[1:]:
    if idx == current_end + 1:
      current_end = idx
    else:
      initial_regions.append([region_start, current_end])
      region_start = idx
      current_end = idx
  initial_regions.append([region_start, current_end])
  
  # Create extended indices set with proper extensions based on region lengths
  extended_indices = set()
  proximal_indices = set()
  
  for region in initial_regions:
    region_length = region[1] - region[0] + 1
    # Calculate extension length: min 3, max 10, otherwise 3 + round(length/3)
    extension = min(10, max(3, 3 + round(region_length / 3)))
    
    # Calculate extended boundaries with bounds checking
    start_extension = max(min_valid_idx, region[0] - extension)
    end_extension = min(max_valid_idx, region[1] + extension)
    
    # Add original indices to extended set
    extended_indices.update(range(region[0], region[1] + 1))
    
    # Add extension indices to proximal set
    if start_extension < region[0]:
      proximal_indices.update(range(start_extension, region[0]))
    if end_extension > region[1]:
      proximal_indices.update(range(region[1] + 1, end_extension + 1))
  
  # Convert extended indices to regions and merge those within dynamic merge_distance
  extended_indices = sorted(extended_indices | proximal_indices)
  if not extended_indices:
    return [], []
    
  # Second pass: create regions and merge based on dynamic merge_distance
  regions = []
  region_start = extended_indices[0]
  current_end = region_start
  
  for idx in extended_indices[1:]:
    if idx == current_end + 1:
      current_end = idx
    else:
      regions.append([region_start, current_end])
      region_start = idx
      current_end = idx
  regions.append([region_start, current_end])
  
  # Final pass: merge regions using dynamic merge_distance
  merged_regions = []
  for i, region in enumerate(regions):
    if not merged_regions:
      merged_regions.append(region)
      continue
      
    # Calculate lengths of adjacent regions
    prev_length = merged_regions[-1][1] - merged_regions[-1][0] + 1
    curr_length = region[1] - region[0] + 1
    combined_length = prev_length + curr_length
    
    # Calculate dynamic merge_distance
    min_merge_distance = 10
    max_merge_distance = 20
    if combined_length <= 10:
      merge_distance = min_merge_distance
    elif combined_length >= 60:
      merge_distance = max_merge_distance
    else:
      # Linear scaling between min and max based on combined length
      scale = (combined_length - 10) / (60 - 10)  # 0->1 as length goes from 10->60
      merge_distance = min_merge_distance + (max_merge_distance - min_merge_distance) * scale
    
    # Check if regions should be merged
    gap = region[0] - merged_regions[-1][1] - 1
    if gap <= merge_distance:
      # Merge with previous region
      merged_regions[-1][1] = region[1]
    else:
      merged_regions.append(region)
  
  # Calculate final proximal indices as any index that wasn't in the original combined_indices
  final_proximal_indices = set(extended_indices) - set(combined_indices)
  
  return merged_regions, sorted(final_proximal_indices)

def label_imputation_reason(df, low_quality_region_start, low_quality_region_end, gap_indices, non_wear_indices, jump_indices, plummet_indices, extreme_negative_indices_candidates):
    imputation_dict = {
      'gap_imputed': [],
      'non_wear_imputed': [],
      'jump_imputed': [],
      'plummet_imputed': [],
      'extreme_negative_imputed': [],
      'proximal_low_quality_imputed': []
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
        imputation_dict['proximal_low_quality_imputed'].append(idx)

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
    'high_quality_minutes_before',
    'high_quality_percent_before',
    'high_quality_minutes_after',
    'high_quality_percent_after',
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
  gap_indices = get_gap_indices(df)
  df.loc[gap_indices, 'gap'] = 1
  df.loc[gap_indices, 'gap_imp_cand'] = 1

  # non wear
  df['non_wear'] = 0
  df['non_wear_imp_cand'] = 0
  df['non_wear_imputed'] = 0
  non_wear_indices = get_non_wear_indices(df)
  df.loc[non_wear_indices, 'non_wear'] = 1
  non_wear_indices_filtered = [idx for idx in non_wear_indices if idx not in gap_indices]
  df.loc[non_wear_indices_filtered, 'non_wear_imp_cand'] = 1

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
  already_indexed = set(gap_indices) | set(non_wear_indices_filtered)
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
  low_quality_regions, proximal_low_quality_indices = convert_index_sets_to_index_region_pairs(
    gap_indices, 
    non_wear_indices_filtered, 
    jump_indices_filtered, 
    plummet_indices_filtered,
    extreme_negative_indices_filtered
  )  
  df['proximal_low_quality_imputed'] = 0
  df['proximal_low_quality_imp_cand'] = 0
  df.loc[proximal_low_quality_indices, 'proximal_low_quality_imp_cand'] = 1

  all_low_quality_indices = set(gap_indices) | set(non_wear_indices_filtered) | set(jump_indices_filtered) | set(plummet_indices_filtered) | set(extreme_negative_indices_filtered)
  all_candidate_indices = already_indexed | set(extreme_negative_indices_filtered) | set(proximal_low_quality_indices)
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

    # Calculate high and low quality values in training regions
    high_quality_before = train_data_before[~train_data_before.index.isin(all_low_quality_indices)]
    low_quality_before = train_data_before[train_data_before.index.isin(all_low_quality_indices)]
    high_quality_after = train_data_after[~train_data_after.index.isin(all_low_quality_indices)]
    low_quality_after = train_data_after[train_data_after.index.isin(all_low_quality_indices)]

    high_quality_minutes_before = len(high_quality_before)
    high_quality_percent_before = (high_quality_minutes_before / len(train_data_before)) if not train_data_before.empty else 0
    training_data_before_valid = (high_quality_minutes_before > min_training_data) and (high_quality_percent_before > 0.5)

    high_quality_minutes_after = len(high_quality_after)
    high_quality_percent_after = (high_quality_minutes_after / len(train_data_after)) if not train_data_after.empty else 0
    training_data_after_valid = (high_quality_minutes_after > min_training_data) and (high_quality_percent_after > 0.5)

    low_quality_region_too_long = low_quality_region_length > 180

    # Record imputation attempt information
    imputation_attempt = {
      'region_start': low_quality_region_start,
      'region_end': low_quality_region_end,
      'region_length': low_quality_region_length,
      'high_quality_minutes_before': high_quality_minutes_before,
      'high_quality_percent_before': high_quality_percent_before,
      'high_quality_minutes_after': high_quality_minutes_after,
      'high_quality_percent_after': high_quality_percent_after,
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

    if (not low_quality_region_too_long) and training_data_before_valid and training_data_after_valid:
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
      df = label_imputation_reason(df, low_quality_region_start, low_quality_region_end, gap_indices, non_wear_indices_filtered, jump_indices_filtered, plummet_indices_filtered, extreme_negative_indices_filtered)
      
      imputation_attempt['was_imputed'] = True

    # Check if region contains only extreme negative and proximal low quality indices
    else:
      region_indices = set(range(low_quality_region_start, low_quality_region_end + 1))
      
      # Check if any indices in this region are gaps, non-wear, jumps, or plummets
      has_gaps = bool(region_indices & set(gap_indices))
      has_non_wear = bool(region_indices & set(non_wear_indices_filtered))
      has_jumps = bool(region_indices & set(jump_indices_filtered))
      has_plummets = bool(region_indices & set(plummet_indices_filtered))
      
      # If region only contains extreme negative and/or proximal low quality
      if not (has_gaps or has_non_wear or has_jumps or has_plummets):
        # Impute with TAC = 0
        df.iloc[low_quality_region_start:low_quality_region_end+1, df.columns.get_loc('TAC')] = 0
        df.iloc[low_quality_region_start:low_quality_region_end+1, df.columns.get_loc('imputed')] = 1
        df = label_imputation_reason(df, low_quality_region_start, low_quality_region_end, gap_indices, non_wear_indices_filtered, jump_indices_filtered, plummet_indices_filtered, extreme_negative_indices_filtered)
        
        imputation_attempt['was_imputed'] = True
        
      # If region contains other types of low quality data, don't impute
      else:
        print('NOT IMPUTED')
        if low_quality_region_too_long:
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
        else:
          imputation_attempt['reason_not_imputed'] = 'contains_other_low_quality_data'
    
    imputation_info = pd.concat([imputation_info, pd.DataFrame([imputation_attempt])], ignore_index=True)
  
  # Store imputation info in the dataframe for later access
  df.attrs['imputation_info'] = imputation_info
  
  return df, imputation_info
