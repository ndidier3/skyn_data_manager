import pandas as pd
import numpy as np

def count_longest_tac_flatline(df, tac_variable='TAC', threshold=10, tolerance=0.1):
  """Count the longest period where TAC values remain flat (within tolerance) above threshold.
  
  Args:
      df: DataFrame containing the data
      tac_variable: Column name for TAC values (default: 'TAC')
      threshold: Minimum TAC value to consider (default: 10)
      tolerance: Maximum allowed difference between consecutive values (default: 0.1)
  
  Returns:
      int: Length of longest flatline period in minutes
  """
  flatline_mask = (
    df[tac_variable].shift().sub(df[tac_variable]).abs() <= tolerance
  ) & (df[tac_variable] > threshold)
  streak_lengths = (flatline_mask != flatline_mask.shift()).cumsum()
  streak_data = flatline_mask.groupby(streak_lengths).sum()
  return streak_data.max()

def count_longest_consecutive_non_wear(df, variable = 'device_worn_model'):
  """Count the longest consecutive period of non-wear time.
  
  Args:
      df: DataFrame containing the data
      variable: Column name for device worn status (default: 'device_worn_model')
  
  Returns:
      int: Length of longest non-wear period in minutes
  """
  df['non_wear_group'] = (df[variable] != 0).cumsum()
  non_wear_lengths = df[df[variable] == 0].groupby('non_wear_group').size()
  longest_non_wear = non_wear_lengths.max() if not non_wear_lengths.empty else 0
  df.drop(columns=['non_wear_group'], inplace=True)
  return longest_non_wear

def count_longest_consecutive_below(df, variable='TAC', X=-10):
  """Count the longest consecutive period where values are below threshold.
  
  Args:
      df: DataFrame containing the data
      variable: Column name to check (default: 'TAC')
      X: Threshold value (default: -10)
  
  Returns:
      int: Length of longest period below threshold in minutes
  """
  mask = df[variable] <= X 
  df.loc[:, 'sub_negative'] = (mask != mask.shift()).cumsum() * mask
  sub_negative_lengths = df[mask].groupby('sub_negative').size()
  longest_sub_negative_streak = sub_negative_lengths.max() if not sub_negative_lengths.empty else 0
  df = df.loc[:, df.columns != 'sub_negative']
  return longest_sub_negative_streak

def get_low_quality_duration(df):
  """Calculate total duration of low quality data in hours.
  
  Low quality includes: jumps, plummets, extreme negatives, non-wear periods, and gaps.
  
  Args:
      df: DataFrame containing the data
  
  Returns:
      float: Duration of low quality data in hours
  """
  return ((df['jump']) | (df['plummet']) | (df['extreme_negative']) | (df['non_wear_buffered']==1) | (df['gap_buffered'] == 1)).sum() / 60

def get_low_quality_percent(df):
  """Calculate percentage of low quality data.
  
  Low quality includes: jumps, plummets, extreme negatives, non-wear periods, and gaps.
  
  Args:
      df: DataFrame containing the data
  
  Returns:
      float: Percentage of low quality data (0-1)
  """
  return ((df['jump']) | (df['plummet']) | (df['extreme_negative']) | (df['non_wear_buffered']==1) | (df['gap_buffered'] == 1)).sum() / len(df)

def get_unimputed_low_quality_duration(df):
  """Calculate total duration of unimputed low quality data in hours.
  
  Low quality includes: jumps, plummets, extreme negatives, non-wear periods, and gaps.
  Only counts periods that have not been imputed.
  
  Args:
      df: DataFrame containing the data
  
  Returns:
      float: Duration of unimputed low quality data in hours
  """
  return (((df['jump']) | (df['plummet']) | (df['extreme_negative']) | (df['non_wear_buffered']==1) | (df['gap_buffered'] == 1)) & (~df['imputed'])).sum() / 60

def get_unimputed_low_quality_percent(df):
  """Calculate percentage of unimputed low quality data.
  
  Low quality includes: jumps, plummets, extreme negatives, non-wear periods, and gaps.
  Only counts periods that have not been imputed.
  
  Args:
      df: DataFrame containing the data
  
  Returns:
      float: Percentage of unimputed low quality data (0-1)
  """
  return (((df['jump']) | (df['plummet']) | (df['extreme_negative']) | (df['non_wear_buffered']==1) | (df['gap_buffered'] == 1)) & (~df['imputed'])).sum() / len(df)

def get_imputed_low_quality_duration(df):
  """Calculate total duration of imputed low quality data in hours.
  
  Low quality includes: jumps, plummets, extreme negatives, non-wear periods, and gaps.
  Only counts periods that have been imputed.
  
  Args:
      df: DataFrame containing the data
  
  Returns:
      float: Duration of imputed low quality data in hours
  """
  return (((df['jump']) | (df['plummet']) | (df['extreme_negative']) | (df['non_wear_buffered']==1) | (df['gap_buffered'] == 1)) & (df['imputed'])).sum() / 60

def get_imputed_low_quality_percent(df):
  """Calculate percentage of imputed low quality data.
  
  Low quality includes: jumps, plummets, extreme negatives, non-wear periods, and gaps.
  Only counts periods that have been imputed.
  
  Args:
      df: DataFrame containing the data
  
  Returns:
      float: Percentage of imputed low quality data (0-1)
  """
  return (((df['jump']) | (df['plummet']) | (df['extreme_negative']) | (df['non_wear_buffered']==1) | (df['gap_buffered'] == 1)) & (df['imputed'])).sum() / len(df)

def get_imputed_jump_duration(df):
  """Calculate duration of imputed jump data in hours.
  
  Args:
      df: DataFrame containing the data
  
  Returns:
      float: Duration of imputed jump data in hours
  """
  return ((df['jump'] == 1) & (df['imputed'] == 1)).sum() / 60

def get_imputed_jump_percent(df):
  """Calculate percentage of imputed jump data.
  
  Args:
      df: DataFrame containing the data
  
  Returns:
      float: Percentage of imputed jump data (0-1)
  """
  return ((df['jump'] == 1) & (df['imputed'] == 1)).sum() / len(df)

def get_unimputed_jump_duration(df):
  """Calculate duration of unimputed jump data in hours.
  
  Args:
      df: DataFrame containing the data
  
  Returns:
      float: Duration of unimputed jump data in hours
  """
  return ((df['jump'] == 1) & (df['imputed'] == 0)).sum() / 60

def get_unimputed_jump_percent(df):
  """Calculate percentage of unimputed jump data.
  
  Args:
      df: DataFrame containing the data
  
  Returns:
      float: Percentage of unimputed jump data (0-1)
  """
  return ((df['jump'] == 1) & (df['imputed'] == 0)).sum() / len(df)

def get_imputed_plummet_duration(df):
  """Calculate duration of imputed plummet data in hours.
  
  Args:
      df: DataFrame containing the data
  
  Returns:
      float: Duration of imputed plummet data in hours
  """
  return ((df['plummet'] == 1) & (df['imputed'] == 1)).sum() / 60

def get_imputed_plummet_percent(df):
  """Calculate percentage of imputed plummet data.
  
  Args:
      df: DataFrame containing the data
  
  Returns:
      float: Percentage of imputed plummet data (0-1)
  """
  return ((df['plummet'] == 1) & (df['imputed'] == 1)).sum() / len(df)

def get_unimputed_plummet_duration(df):
  """Calculate duration of unimputed plummet data in hours.
  
  Args:
      df: DataFrame containing the data
  
  Returns:
      float: Duration of unimputed plummet data in hours
  """
  return ((df['plummet'] == 1) & (df['imputed'] == 0)).sum() / 60

def get_unimputed_plummet_percent(df):
  """Calculate percentage of unimputed plummet data.
  
  Args:
      df: DataFrame containing the data
  
  Returns:
      float: Percentage of unimputed plummet data (0-1)
  """
  return ((df['plummet'] == 1) & (df['imputed'] == 0)).sum() / len(df)

def get_imputed_extreme_negative_duration(df):
  """Calculate duration of imputed extreme negative data in hours.
  
  Args:
      df: DataFrame containing the data
  
  Returns:
      float: Duration of imputed extreme negative data in hours
  """
  return ((df['extreme_negative'] == 1) & (df['imputed'] == 1)).sum() / 60

def get_imputed_extreme_negative_percent(df):
  """Calculate percentage of imputed extreme negative data.
  
  Args:
      df: DataFrame containing the data
  
  Returns:
      float: Percentage of imputed extreme negative data (0-1)
  """
  return ((df['extreme_negative'] == 1) & (df['imputed'] == 1)).sum() / len(df)

def get_unimputed_extreme_negative_duration(df):
  """Calculate duration of unimputed extreme negative data in hours.
  
  Args:
      df: DataFrame containing the data
  
  Returns:
      float: Duration of unimputed extreme negative data in hours
  """
  return ((df['extreme_negative'] == 1) & (df['imputed'] == 0)).sum() / 60

def get_unimputed_extreme_negative_percent(df):
  """Calculate percentage of unimputed extreme negative data.
  
  Args:
      df: DataFrame containing the data
  
  Returns:
      float: Percentage of unimputed extreme negative data (0-1)
  """
  return ((df['extreme_negative'] == 1) & (df['imputed'] == 0)).sum() / len(df)

def get_imputed_gap_duration(df):
  """Calculate duration of imputed gap data in hours.
  
  Args:
      df: DataFrame containing the data
  
  Returns:
      float: Duration of imputed gap data in hours
  """
  return ((df['gap_buffered'] == 1) & (df['imputed'] == 1)).sum() / 60

def get_imputed_gap_percent(df):
  """Calculate percentage of imputed gap data.
  
  Args:
      df: DataFrame containing the data
  
  Returns:
      float: Percentage of imputed gap data (0-1)
  """
  return ((df['gap_buffered'] == 1) & (df['imputed'] == 1)).sum() / len(df)

def get_unimputed_gap_duration(df):
  """Calculate duration of unimputed gap data in hours.
  
  Args:
      df: DataFrame containing the data
  
  Returns:
      float: Duration of unimputed gap data in hours
  """
  return ((df['gap_buffered'] == 1) & (df['imputed'] == 0)).sum() / 60

def get_unimputed_gap_percent(df):
  """Calculate percentage of unimputed gap data.
  
  Args:
      df: DataFrame containing the data
  
  Returns:
      float: Percentage of unimputed gap data (0-1)
  """
  return ((df['gap_buffered'] == 1) & (df['imputed'] == 0)).sum() / len(df)

def get_imputed_non_wear_duration(df):
  """Calculate duration of imputed non-wear data in hours.
  
  Args:
      df: DataFrame containing the data
  
  Returns:
      float: Duration of imputed non-wear data in hours
  """
  return ((df['non_wear_buffered'] == 1) & (df['imputed'] == 1)).sum() / 60

def get_imputed_non_wear_percent(df):
  """Calculate percentage of imputed non-wear data.
  
  Args:
      df: DataFrame containing the data
  
  Returns:
      float: Percentage of imputed non-wear data (0-1)
  """
  return ((df['non_wear_buffered'] == 1) & (df['imputed'] == 1)).sum() / len(df)

def get_unimputed_non_wear_duration(df):
  """Calculate duration of unimputed non-wear data in hours.
  
  Args:
      df: DataFrame containing the data
  
  Returns:
      float: Duration of unimputed non-wear data in hours
  """
  return ((df['non_wear_buffered'] == 1) & (df['imputed'] == 0)).sum() / 60

def get_unimputed_non_wear_percent(df):
  """Calculate percentage of unimputed non-wear data.
  
  Args:
      df: DataFrame containing the data
  
  Returns:
      float: Percentage of unimputed non-wear data (0-1)
  """
  return ((df['non_wear_buffered'] == 1) & (df['imputed'] == 0)).sum() / len(df)

def get_jump_imputation_ratio(df):
  """Calculate ratio of imputed jump data.
  
  Args:
      df: DataFrame containing the data
  
  Returns:
      float: Ratio of imputed jump data (0-1)
  """
  total_jumps = (df['jump'] == 1).sum()
  if total_jumps == 0:
    return 0
  return ((df['jump'] == 1) & (df['imputed'] == 1)).sum() / total_jumps

def get_plummet_imputation_ratio(df):
  """Calculate ratio of imputed plummet data.
  
  Args:
      df: DataFrame containing the data
  
  Returns:
      float: Ratio of imputed plummet data (0-1)
  """
  total_plummets = (df['plummet'] == 1).sum()
  if total_plummets == 0:
    return 0
  return ((df['plummet'] == 1) & (df['imputed'] == 1)).sum() / total_plummets

def get_extreme_negative_imputation_ratio(df):
  """Calculate ratio of imputed extreme negative data.
  
  Args:
      df: DataFrame containing the data
  
  Returns:
      float: Ratio of imputed extreme negative data (0-1)
  """
  total_extreme_negatives = (df['extreme_negative'] == 1).sum()
  if total_extreme_negatives == 0:
    return 0
  return ((df['extreme_negative'] == 1) & (df['imputed'] == 1)).sum() / total_extreme_negatives

def get_gap_imputation_ratio(df):
  """Calculate ratio of imputed gap data.
  
  Args:
      df: DataFrame containing the data
  
  Returns:
      float: Ratio of imputed gap data (0-1)
  """
  total_gaps = (df['gap_buffered'] == 1).sum()
  if total_gaps == 0:
    return 0
  return ((df['gap_buffered'] == 1) & (df['imputed'] == 1)).sum() / total_gaps

def get_non_wear_imputation_ratio(df):
  """Calculate ratio of imputed non-wear data.
  
  Args:
      df: DataFrame containing the data
  
  Returns:
      float: Ratio of imputed non-wear data (0-1)
  """
  total_non_wear = (df['non_wear_buffered'] == 1).sum()
  if total_non_wear == 0:
    return 0
  return ((df['non_wear_buffered'] == 1) & (df['imputed'] == 1)).sum() / total_non_wear

def get_low_quality_imputation_ratio(df):
  """Calculate ratio of imputed low quality data.
  
  Args:
      df: DataFrame containing the data
  
  Returns:
      float: Ratio of imputed low quality data (0-1)
  """
  low_quality_mask = ((df['jump']) | (df['plummet']) | (df['extreme_negative']) | 
                     (df['non_wear_buffered']==1) | (df['gap_buffered'] == 1))
  total_low_quality = low_quality_mask.sum()
  if total_low_quality == 0:
    return 0
  return (low_quality_mask & (df['imputed'] == 1)).sum() / total_low_quality