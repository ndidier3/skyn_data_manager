import pandas as pd
import numpy as np

# Precedence for mutually exclusive low-quality types: gap > non_wear > jump > plummet > extreme_negative
def _has_imp_cand(df):
    """Whether all five *_imp_cand columns are present (from impute_low_quality_data)."""
    required = {'gap_imp_cand', 'non_wear_imp_cand', 'jump_imp_cand',
                'plummet_imp_cand', 'extreme_negative_imp_cand'}
    return required.issubset(df.columns)


def _get_exclusive_masks(df):
    """Return (gap, non_wear, jump, plummet, extreme_negative) masks that are mutually exclusive.
    Uses *_imp_cand when available; otherwise falls back to exclusive masks from raw flags."""
    if _has_imp_cand(df):
        gap_excl = df['gap_imp_cand'] == 1
        non_wear_excl = df['non_wear_imp_cand'] == 1
        jump_excl = df['jump_imp_cand'] == 1
        plummet_excl = df['plummet_imp_cand'] == 1
        extreme_excl = df['extreme_negative_imp_cand'] == 1
        return gap_excl, non_wear_excl, jump_excl, plummet_excl, extreme_excl
    gap_raw = (df['gap'] == 1) if 'gap' in df.columns else pd.Series(False, index=df.index)
    non_wear_raw = (df['non_wear'] == 1) if 'non_wear' in df.columns else pd.Series(False, index=df.index)
    jump_raw = (df['jump'] == 1) if 'jump' in df.columns else pd.Series(False, index=df.index)
    plummet_raw = (df['plummet'] == 1) if 'plummet' in df.columns else pd.Series(False, index=df.index)
    extreme_raw = (df['extreme_negative'] == 1) if 'extreme_negative' in df.columns else pd.Series(False, index=df.index)
    gap_excl = gap_raw
    non_wear_excl = non_wear_raw & ~gap_excl
    jump_excl = jump_raw & ~gap_excl & ~non_wear_excl
    plummet_excl = plummet_raw & ~gap_excl & ~non_wear_excl & ~jump_excl
    extreme_excl = extreme_raw & ~gap_excl & ~non_wear_excl & ~jump_excl & ~plummet_excl
    return gap_excl, non_wear_excl, jump_excl, plummet_excl, extreme_excl

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

def count_longest_consecutive_below(df, variable='TAC', X=-15):
  """Count the longest consecutive period where values are below threshold.
  
  Args:
      df: DataFrame containing the data
      variable: Column name to check (default: 'TAC')
      X: Threshold value (default: -15)
  
  Returns:
      int: Length of longest period below threshold in minutes
  """
  mask = df[variable] <= X 
  df.loc[:, 'sub_negative'] = (mask != mask.shift()).cumsum() * mask
  sub_negative_lengths = df[mask].groupby('sub_negative').size()
  longest_sub_negative_streak = sub_negative_lengths.max() if not sub_negative_lengths.empty else 0
  df = df.loc[:, df.columns != 'sub_negative']
  return longest_sub_negative_streak

def _get_low_quality_mask(df):
  """Union of all five low-quality types; uses *_imp_cand when available."""
  if _has_imp_cand(df):
    return (
      (df['gap_imp_cand'] == 1) | (df['non_wear_imp_cand'] == 1) |
      (df['jump_imp_cand'] == 1) | (df['plummet_imp_cand'] == 1) |
      (df['extreme_negative_imp_cand'] == 1)
    )
  return (
    (df['gap'] == 1) | (df['non_wear'] == 1) | (df['jump'] == 1) |
    (df['plummet'] == 1) | (df['extreme_negative'] == 1)
  )

def get_low_quality_duration(df):
  """Calculate total duration of low quality data in hours.
  
  Low quality includes: jumps, plummets, extreme negatives, non-wear periods, and gaps.
  Uses *_imp_cand when available for consistency with imputation pipeline.
  
  Args:
      df: DataFrame containing the data
  
  Returns:
      float: Duration of low quality data in hours
  """
  return _get_low_quality_mask(df).sum() / 60

def get_low_quality_percent(df):
  """Calculate percentage of low quality data.
  
  Low quality includes: jumps, plummets, extreme negatives, non-wear periods, and gaps.
  Uses *_imp_cand when available for consistency with imputation pipeline.
  
  Args:
      df: DataFrame containing the data
  
  Returns:
      float: Percentage of low quality data (0-1)
  """
  return _get_low_quality_mask(df).sum() / len(df)

def get_unimputed_low_quality_duration(df):
  """Calculate total duration of unimputed low quality data in hours.
  
  Low quality includes: jumps, plummets, extreme negatives, non-wear periods, and gaps.
  Only counts periods that have not been imputed.
  Uses *_imp_cand when available for consistency with imputation pipeline.
  
  Args:
      df: DataFrame containing the data
  
  Returns:
      float: Duration of unimputed low quality data in hours
  """
  return (_get_low_quality_mask(df) & (df['imputed'] == 0)).sum() / 60

def get_unimputed_low_quality_percent(df):
  """Calculate percentage of unimputed low quality data.
  
  Low quality includes: jumps, plummets, extreme negatives, non-wear periods, and gaps.
  Only counts periods that have not been imputed.
  Uses *_imp_cand when available for consistency with imputation pipeline.
  
  Args:
      df: DataFrame containing the data
  
  Returns:
      float: Percentage of unimputed low quality data (0-1)
  """
  return (_get_low_quality_mask(df) & (df['imputed'] == 0)).sum() / len(df)

def get_imputed_low_quality_duration(df):
  """Calculate total duration of imputed low quality data in hours.
  
  Low quality includes: jumps, plummets, extreme negatives, non-wear periods, and gaps.
  Only counts periods that have been imputed.
  Uses *_imp_cand when available for consistency with imputation pipeline.
  
  Args:
      df: DataFrame containing the data
  
  Returns:
      float: Duration of imputed low quality data in hours
  """
  return (_get_low_quality_mask(df) & (df['imputed'] == 1)).sum() / 60

def get_imputed_low_quality_percent(df):
  """Calculate percentage of imputed low quality data.
  
  Low quality includes: jumps, plummets, extreme negatives, non-wear periods, and gaps.
  Only counts periods that have been imputed.
  Uses *_imp_cand when available for consistency with imputation pipeline.
  
  Args:
      df: DataFrame containing the data
  
  Returns:
      float: Percentage of imputed low quality data (0-1)
  """
  return (_get_low_quality_mask(df) & (df['imputed'] == 1)).sum() / len(df)

def get_imputed_jump_duration(df):
  """Calculate duration of imputed jump data in hours (exclusive mask)."""
  gap_m, non_wear_m, jump_m, plummet_m, extreme_m = _get_exclusive_masks(df)
  return (jump_m & (df['imputed'] == 1)).sum() / 60

def get_imputed_jump_percent(df):
  """Calculate percentage of imputed jump data (exclusive mask)."""
  if len(df) == 0:
    return 0.0
  gap_m, non_wear_m, jump_m, plummet_m, extreme_m = _get_exclusive_masks(df)
  return (jump_m & (df['imputed'] == 1)).sum() / len(df)

def get_unimputed_jump_duration(df):
  """Calculate duration of unimputed jump data in hours (exclusive mask)."""
  gap_m, non_wear_m, jump_m, plummet_m, extreme_m = _get_exclusive_masks(df)
  return (jump_m & (df['imputed'] == 0)).sum() / 60

def get_unimputed_jump_percent(df):
  """Calculate percentage of unimputed jump data (exclusive mask)."""
  if len(df) == 0:
    return 0.0
  gap_m, non_wear_m, jump_m, plummet_m, extreme_m = _get_exclusive_masks(df)
  return (jump_m & (df['imputed'] == 0)).sum() / len(df)

def get_imputed_plummet_duration(df):
  """Calculate duration of imputed plummet data in hours (exclusive mask)."""
  gap_m, non_wear_m, jump_m, plummet_m, extreme_m = _get_exclusive_masks(df)
  return (plummet_m & (df['imputed'] == 1)).sum() / 60

def get_imputed_plummet_percent(df):
  """Calculate percentage of imputed plummet data (exclusive mask)."""
  if len(df) == 0:
    return 0.0
  gap_m, non_wear_m, jump_m, plummet_m, extreme_m = _get_exclusive_masks(df)
  return (plummet_m & (df['imputed'] == 1)).sum() / len(df)

def get_unimputed_plummet_duration(df):
  """Calculate duration of unimputed plummet data in hours (exclusive mask)."""
  gap_m, non_wear_m, jump_m, plummet_m, extreme_m = _get_exclusive_masks(df)
  return (plummet_m & (df['imputed'] == 0)).sum() / 60

def get_unimputed_plummet_percent(df):
  """Calculate percentage of unimputed plummet data (exclusive mask)."""
  if len(df) == 0:
    return 0.0
  gap_m, non_wear_m, jump_m, plummet_m, extreme_m = _get_exclusive_masks(df)
  return (plummet_m & (df['imputed'] == 0)).sum() / len(df)

def get_imputed_extreme_negative_duration(df):
  """Calculate duration of imputed extreme negative data in hours (exclusive mask)."""
  gap_m, non_wear_m, jump_m, plummet_m, extreme_m = _get_exclusive_masks(df)
  return (extreme_m & (df['imputed'] == 1)).sum() / 60

def get_imputed_extreme_negative_percent(df):
  """Calculate percentage of imputed extreme negative data (exclusive mask)."""
  if len(df) == 0:
    return 0.0
  gap_m, non_wear_m, jump_m, plummet_m, extreme_m = _get_exclusive_masks(df)
  return (extreme_m & (df['imputed'] == 1)).sum() / len(df)

def get_unimputed_extreme_negative_duration(df):
  """Calculate duration of unimputed extreme negative data in hours (exclusive mask)."""
  gap_m, non_wear_m, jump_m, plummet_m, extreme_m = _get_exclusive_masks(df)
  return (extreme_m & (df['imputed'] == 0)).sum() / 60

def get_unimputed_extreme_negative_percent(df):
  """Calculate percentage of unimputed extreme negative data (exclusive mask)."""
  if len(df) == 0:
    return 0.0
  gap_m, non_wear_m, jump_m, plummet_m, extreme_m = _get_exclusive_masks(df)
  return (extreme_m & (df['imputed'] == 0)).sum() / len(df)

def get_imputed_gap_duration(df):
  """Calculate duration of imputed gap data in hours (exclusive mask)."""
  gap_m, non_wear_m, jump_m, plummet_m, extreme_m = _get_exclusive_masks(df)
  return (gap_m & (df['imputed'] == 1)).sum() / 60

def get_imputed_gap_percent(df):
  """Calculate percentage of imputed gap data (exclusive mask)."""
  if len(df) == 0:
    return 0.0
  gap_m, non_wear_m, jump_m, plummet_m, extreme_m = _get_exclusive_masks(df)
  return (gap_m & (df['imputed'] == 1)).sum() / len(df)

def get_unimputed_gap_duration(df):
  """Calculate duration of unimputed gap data in hours (exclusive mask)."""
  gap_m, non_wear_m, jump_m, plummet_m, extreme_m = _get_exclusive_masks(df)
  return (gap_m & (df['imputed'] == 0)).sum() / 60

def get_unimputed_gap_percent(df):
  """Calculate percentage of unimputed gap data (exclusive mask)."""
  if len(df) == 0:
    return 0.0
  gap_m, non_wear_m, jump_m, plummet_m, extreme_m = _get_exclusive_masks(df)
  return (gap_m & (df['imputed'] == 0)).sum() / len(df)

def get_imputed_non_wear_duration(df):
  """Calculate duration of imputed non-wear data in hours (exclusive mask)."""
  gap_m, non_wear_m, jump_m, plummet_m, extreme_m = _get_exclusive_masks(df)
  return (non_wear_m & (df['imputed'] == 1)).sum() / 60

def get_imputed_non_wear_percent(df):
  """Calculate percentage of imputed non-wear data (exclusive mask)."""
  if len(df) == 0:
    return 0.0
  gap_m, non_wear_m, jump_m, plummet_m, extreme_m = _get_exclusive_masks(df)
  return (non_wear_m & (df['imputed'] == 1)).sum() / len(df)

def get_unimputed_non_wear_duration(df):
  """Calculate duration of unimputed non-wear data in hours (exclusive mask)."""
  gap_m, non_wear_m, jump_m, plummet_m, extreme_m = _get_exclusive_masks(df)
  return (non_wear_m & (df['imputed'] == 0)).sum() / 60

def get_unimputed_non_wear_percent(df):
  """Calculate percentage of unimputed non-wear data (exclusive mask)."""
  if len(df) == 0:
    return 0.0
  gap_m, non_wear_m, jump_m, plummet_m, extreme_m = _get_exclusive_masks(df)
  return (non_wear_m & (df['imputed'] == 0)).sum() / len(df)

def get_jump_imputation_ratio(df):
  """Calculate ratio of imputed jump data (exclusive mask)."""
  gap_m, non_wear_m, jump_m, plummet_m, extreme_m = _get_exclusive_masks(df)
  total = jump_m.sum()
  if total == 0:
    return None
  return (jump_m & (df['imputed'] == 1)).sum() / total

def get_plummet_imputation_ratio(df):
  """Calculate ratio of imputed plummet data (exclusive mask)."""
  gap_m, non_wear_m, jump_m, plummet_m, extreme_m = _get_exclusive_masks(df)
  total = plummet_m.sum()
  if total == 0:
    return None
  return (plummet_m & (df['imputed'] == 1)).sum() / total

def get_extreme_negative_imputation_ratio(df):
  """Calculate ratio of imputed extreme negative data (exclusive mask)."""
  gap_m, non_wear_m, jump_m, plummet_m, extreme_m = _get_exclusive_masks(df)
  total = extreme_m.sum()
  if total == 0:
    return None
  return (extreme_m & (df['imputed'] == 1)).sum() / total

def get_gap_imputation_ratio(df):
  """Calculate ratio of imputed gap data (exclusive mask)."""
  gap_m, non_wear_m, jump_m, plummet_m, extreme_m = _get_exclusive_masks(df)
  total = gap_m.sum()
  if total == 0:
    return None
  return (gap_m & (df['imputed'] == 1)).sum() / total

def get_non_wear_imputation_ratio(df):
  """Calculate ratio of imputed non-wear data (exclusive mask)."""
  gap_m, non_wear_m, jump_m, plummet_m, extreme_m = _get_exclusive_masks(df)
  total = non_wear_m.sum()
  if total == 0:
    return None
  return (non_wear_m & (df['imputed'] == 1)).sum() / total

def _inclusive_mask(df, col):
  """Raw inclusive mask (flag==1) for the given column."""
  if col not in df.columns:
    return pd.Series(False, index=df.index)
  return df[col] == 1

def get_total_gap_duration_inclusive(df):
  """Total gap duration in hours (inclusive: gap==1, no mutual exclusivity)."""
  return _inclusive_mask(df, 'gap').sum() / 60

def get_total_gap_percent_inclusive(df):
  """Total gap percent (inclusive: gap==1)."""
  if len(df) == 0:
    return 0.0
  return _inclusive_mask(df, 'gap').sum() / len(df)

def get_total_non_wear_duration_inclusive(df):
  """Total non-wear duration in hours (inclusive: non_wear==1)."""
  return _inclusive_mask(df, 'non_wear').sum() / 60

def get_total_non_wear_percent_inclusive(df):
  """Total non-wear percent (inclusive: non_wear==1)."""
  if len(df) == 0:
    return 0.0
  return _inclusive_mask(df, 'non_wear').sum() / len(df)

def get_total_jump_duration_inclusive(df):
  """Total jump duration in hours (inclusive: jump==1)."""
  return _inclusive_mask(df, 'jump').sum() / 60

def get_total_jump_percent_inclusive(df):
  """Total jump percent (inclusive: jump==1)."""
  if len(df) == 0:
    return 0.0
  return _inclusive_mask(df, 'jump').sum() / len(df)

def get_total_plummet_duration_inclusive(df):
  """Total plummet duration in hours (inclusive: plummet==1)."""
  return _inclusive_mask(df, 'plummet').sum() / 60

def get_total_plummet_percent_inclusive(df):
  """Total plummet percent (inclusive: plummet==1)."""
  if len(df) == 0:
    return 0.0
  return _inclusive_mask(df, 'plummet').sum() / len(df)

def get_total_extreme_negative_duration_inclusive(df):
  """Total extreme negative duration in hours (inclusive: extreme_negative==1)."""
  return _inclusive_mask(df, 'extreme_negative').sum() / 60

def get_total_extreme_negative_percent_inclusive(df):
  """Total extreme negative percent (inclusive: extreme_negative==1)."""
  if len(df) == 0:
    return 0.0
  return _inclusive_mask(df, 'extreme_negative').sum() / len(df)

def get_low_quality_imputation_ratio(df):
  """Calculate ratio of imputed low quality data.
  Uses *_imp_cand when available for consistency with imputation pipeline.
  
  Args:
      df: DataFrame containing the data
  
  Returns:
      float: Ratio of imputed low quality data (0-1)
  """
  low_quality_mask = _get_low_quality_mask(df)
  total_low_quality = low_quality_mask.sum()
  if total_low_quality == 0:
    return None
  return (low_quality_mask & (df['imputed'] == 1)).sum() / total_low_quality

def get_start_to_peak_interval(df, tac_variable='TAC'):
    """
    Returns the number of TAC values between the first TAC and the first occurrence of the peak TAC value.
    Args:
        df: DataFrame containing the data
        tac_variable: Column name for TAC values (default: 'TAC')
    Returns:
        int: Number of values between the first and the first peak (exclusive)
    """
    if len(df) == 0:
        return 0
    # Since curve is reset_index(drop=True), index is positional
    start_to_peak_count = df.index[df[tac_variable] == df[tac_variable].max()].tolist()[0] if df[tac_variable].max() is not None else 0
    return start_to_peak_count
def get_rise_imputed_percent(df, tac_variable='TAC'):
    """Calculate percentage of imputed data in the rise portion of a curve.
    
    Only considers data from start to peak.
    
    Args:
        df: DataFrame containing the data
        tac_variable: Column name for TAC values (default: 'TAC')
    
    Returns:
        float: Percentage of imputed data in rise portion (0-1)
    """
    peak_index = df[tac_variable].idxmax()
    rise_portion = df.loc[:peak_index]
    
    if len(rise_portion) == 0:
        return 0.0
        
    imputed_mask = (
      rise_portion['imputed'] == 1
    )
    
    return imputed_mask.sum() / len(rise_portion)

def get_fall_imputed_percent(df, tac_variable='TAC'):
    """Calculate percentage of imputed data in the fall portion of a curve.
    
    Only considers data from peak to end.
    
    Args:
        df: DataFrame containing the data
        tac_variable: Column name for TAC values (default: 'TAC')
    
    Returns:
        float: Percentage of imputed data in fall portion (0-1)
    """
    peak_index = df[tac_variable].idxmax()
    fall_portion = df.loc[peak_index:]
    
    if len(fall_portion) == 0:
        return 0.0
        
    imputed_mask = (
      fall_portion['imputed'] == 1
    )
    
    return imputed_mask.sum() / len(fall_portion)

def get_total_gaps_and_non_wear_percent(df: pd.DataFrame) -> float:
    """Calculate the total percentage of data that is either a gap or non-wear period.
    Uses *_imp_cand when available for consistency with imputation pipeline.
    
    Args:
        df: DataFrame containing the data
        
    Returns:
        float: Percentage of data that is either a gap or non-wear period (0-1)
    """
    if len(df) == 0:
        return 0.0
    gap_m, non_wear_m, _, _, _ = _get_exclusive_masks(df)
    return (gap_m | non_wear_m).sum() / len(df)


def get_below_threshold_percent(df: pd.DataFrame, tac_variable: str = 'TAC', threshold: float = 0) -> float:
    """Calculate percentage of TAC values that are below a given threshold.
    
    Args:
        df: DataFrame containing the data
        tac_variable: Column name for TAC values (default: 'TAC')
        threshold: Threshold value to compare against (default: 0)
        
    Returns:
        float: Percentage of values below threshold (0-1)
    """
    if len(df) == 0:
        return 0.0
        
    return (df[tac_variable] <= threshold).sum() / len(df)
