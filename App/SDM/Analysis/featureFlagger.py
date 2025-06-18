import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Union

class featureFlagger:
  """
  Takes event features; adds flags (1=flagged) or validation (1=valid)
  """
  def __init__(self, features: pd.DataFrame, flag_selections: Optional[Dict] = None):
    self.ftrs: pd.DataFrame = features
    self.flag_selections: Dict = {
      # Curve flags (using both percent and duration)
      'flag_unimputed_low_quality_curve': {},
      'flag_imputed_low_quality_curve': {},
      
      # Periphery flags (using only percent)
      'flag_extreme_negative_periphery': {},
      'flag_low_quality_periphery': {},
      'flag_unimputed_low_quality_periphery': {},
      
      # Curve completion flags (using only percent)
      'flag_incomplete_curve_start_curve': {},
      'flag_incomplete_curve_end_curve': {},
      'flag_rise_low_quality_curve': {},
      'flag_fall_low_quality_curve': {}
    }
    if flag_selections:
      self.flag_selections.update(flag_selections)

  # Utility flag methods
  def flag_data_above_cutoff(self, column: str, cutoff: float, flag_name: str) -> None:
    """Flag data points where column value is above cutoff"""
    flag_col = flag_name if flag_name.startswith('FLAG_') else f'FLAG_{flag_name}'
    self.ftrs[flag_col] = np.where(self.ftrs[column].isna(), np.nan, (self.ftrs[column] > cutoff).astype(int))

  def flag_data_below_cutoff(self, column: str, cutoff: float, flag_name: str) -> None:
    """Flag data points where column value is below cutoff"""
    flag_col = flag_name if flag_name.startswith('FLAG_') else f'FLAG_{flag_name}'
    self.ftrs[flag_col] = np.where(self.ftrs[column].isna(), np.nan, (self.ftrs[column] < cutoff).astype(int))

  def flag_data_above_cutoffs(self, column1: str, cutoff1: float, column2: str, cutoff2: float, flag_name: str) -> None:
    """Flag data points where BOTH columns are above their cutoffs (AND logic)"""
    flag_col = flag_name if flag_name.startswith('FLAG_') else f'FLAG_{flag_name}'
    self.ftrs[flag_col] = np.where(
      self.ftrs[[column1, column2]].isna().any(axis=1), 
      np.nan, 
      ((self.ftrs[column1] > cutoff1) & (self.ftrs[column2] > cutoff2)).astype(int)
    )

  def flag_data_above_one_of_two_cutoffs(self, column1: str, cutoff1: float, column2: str, cutoff2: float, flag_name: str) -> None:
    """Flag data points where EITHER column is above its cutoff (OR logic)"""
    flag_col = flag_name if flag_name.startswith('FLAG_') else f'FLAG_{flag_name}'
    self.ftrs[flag_col] = np.where(
      self.ftrs[[column1, column2]].isna().any(axis=1), 
      np.nan, 
      ((self.ftrs[column1] > cutoff1) | (self.ftrs[column2] > cutoff2)).astype(int)
    )

  def flag_data_below_cutoffs(self, column1: str, cutoff1: float, column2: str, cutoff2: float, flag_name: str) -> None:
    """Flag data points where BOTH columns are below their cutoffs (AND logic)"""
    flag_col = flag_name if flag_name.startswith('FLAG_') else f'FLAG_{flag_name}'
    self.ftrs[flag_col] = np.where(
      self.ftrs[[column1, column2]].isna().any(axis=1), 
      np.nan, 
      ((self.ftrs[column1] < cutoff1) & (self.ftrs[column2] < cutoff2)).astype(int)
    )

  def flag_data_below_one_of_two_cutoffs(self, column1: str, cutoff1: float, column2: str, cutoff2: float, flag_name: str) -> None:
    """Flag data points where EITHER column is below its cutoff (OR logic)"""
    flag_col = flag_name if flag_name.startswith('FLAG_') else f'FLAG_{flag_name}'
    self.ftrs[flag_col] = np.where(
      self.ftrs[[column1, column2]].isna().any(axis=1), 
      np.nan, 
      ((self.ftrs[column1] < cutoff1) | (self.ftrs[column2] < cutoff2)).astype(int)
    )

  def flag_data_below_or_above_cutoffs(self, column1: str, below_cutoff: float, column2: str, above_cutoff: float, flag_name: str) -> None:
    """Flag data points where first column is below cutoff OR second column is above cutoff (OR logic)"""
    flag_col = flag_name if flag_name.startswith('FLAG_') else f'FLAG_{flag_name}'
    self.ftrs[flag_col] = np.where(
      self.ftrs[[column1, column2]].isna().any(axis=1), 
      np.nan, 
      ((self.ftrs[column1] < below_cutoff) | (self.ftrs[column2] > above_cutoff)).astype(int)
    )

  def flag_data_below_and_above_cutoffs(self, column1: str, below_cutoff: float, column2: str, above_cutoff: float, flag_name: str) -> None:
    """Flag data points where first column is below cutoff AND second column is above cutoff (AND logic)"""
    flag_col = flag_name if flag_name.startswith('FLAG_') else f'FLAG_{flag_name}'
    self.ftrs[flag_col] = np.where(
      self.ftrs[[column1, column2]].isna().any(axis=1), 
      np.nan, 
      ((self.ftrs[column1] < below_cutoff) & (self.ftrs[column2] > above_cutoff)).astype(int)
    )

  # Periphery flag methods
  def flag_gaps_and_non_wear_periphery(self, percent_cutoff: float) -> None:
    """
    Flag periphery if the total percentage of gaps and non-wear exceeds the cutoff.
    Combines both gap and non-wear percentages.
    """
    # Calculate total percentage of gaps and non-wear
    total_percent = self.ftrs['total_gap_percent_PERIPHERY'] + self.ftrs['total_non_wear_percent_PERIPHERY']
    
    # Store the total in a temporary column
    self.ftrs['total_gaps_and_non_wear_percent_PERIPHERY'] = total_percent
    
    # Flag based on the total percentage
    self.flag_data_above_cutoff(
      'total_gaps_and_non_wear_percent_PERIPHERY', percent_cutoff,
      'FLAG_gaps_and_non_wear_periphery'
    )

  def flag_extreme_negative_periphery(self, percent_cutoff: float) -> None:
    """
    Flag periphery if the percent cutoff is exceeded.
    """
    self.flag_data_above_cutoff(
      'total_extreme_negative_percent_PERIPHERY', percent_cutoff,
      'FLAG_extreme_negative_periphery'
    )

  def flag_low_quality_periphery(self, percent_cutoff: float) -> None:
    """
    Flag periphery if the percent cutoff is exceeded.
    Uses total low quality metrics (imputed + unimputed).
    """
    self.ftrs['total_low_quality_percent_PERIPHERY'] = (
      self.ftrs['imputed_low_quality_percent_PERIPHERY'] + 
      self.ftrs['unimputed_low_quality_percent_PERIPHERY']
    )
    self.flag_data_above_cutoff(
      'total_low_quality_percent_PERIPHERY', percent_cutoff,
      'FLAG_low_quality_periphery'
    )

  def flag_unimputed_low_quality_periphery(self, percent_cutoff: float) -> None:
    """
    Flag periphery if the unimputed low quality percent cutoff is exceeded.
    """
    self.flag_data_above_cutoff(
      'unimputed_low_quality_percent_PERIPHERY', percent_cutoff,
      'FLAG_unimputed_low_quality_periphery'
    )

  # Non-wear and gap flag methods
  # Remove the flag_unimputed_gaps_and_non_wear_region method entirely

  # Low quality flag methods
  def flag_unimputed_low_quality_curve(self, percent_cutoff: float, duration_cutoff: float) -> None:
    """
    Flag a curve if either the unimputed low quality percent or duration cutoff is exceeded.
    This is an OR rule - if either condition is met, the flag is set.
    """
    self.flag_data_above_one_of_two_cutoffs(
      'unimputed_low_quality_percent_CURVE', percent_cutoff,
      'unimputed_low_quality_duration_CURVE', duration_cutoff,
      'FLAG_unimputed_low_quality_curve'
    )

  def flag_imputed_low_quality_curve(self, percent_cutoff: float, duration_cutoff: float) -> None:
    """
    Flag a curve if either the imputed low quality percent or duration cutoff is exceeded.
    This is an OR rule - if either condition is met, the flag is set.
    """
    self.flag_data_above_one_of_two_cutoffs(
      'imputed_low_quality_percent_CURVE', percent_cutoff,
      'imputed_low_quality_duration_CURVE', duration_cutoff,
      'FLAG_imputed_low_quality_curve'
    )

  # Rise/fall completion flag methods
  def flag_incomplete_curve_start_curve(self, percent_cutoff: float) -> None:
    """
    Flag a curve if the start is incomplete based on percent cutoff.
    """
    self.flag_data_below_cutoff(
      'rise_complete_percent_CURVE', percent_cutoff,
      'FLAG_incomplete_curve_start_curve'
    )

  def flag_incomplete_curve_end_curve(self, percent_cutoff: float) -> None:
    """
    Flag a curve if the end is incomplete based on percent cutoff.
    """
    self.flag_data_below_cutoff(
      'fall_complete_percent_CURVE', percent_cutoff,
      'FLAG_incomplete_curve_end_curve'
    )

  def flag_low_quality_rise_curve(self, percent_cutoff: float) -> None:
    """
    Flag a curve if the rise portion has too much low quality data based on percent cutoff.
    """
    self.flag_data_above_cutoff(
      'rise_low_quality_percent_CURVE', percent_cutoff,
      'FLAG_low_quality_rise_curve'
    )

  def flag_low_quality_fall_curve(self, percent_cutoff: float) -> None:
    """
    Flag a curve if the fall portion has too much low quality data based on percent cutoff.
    """
    self.flag_data_above_cutoff(
      'fall_low_quality_percent_CURVE', percent_cutoff,
      'FLAG_low_quality_fall_curve'
    )

  def flag_below_threshold_curve(self, percent_cutoff: float) -> None:
    """
    Flag a curve if the percentage of values below threshold exceeds the cutoff.
    """
    self.flag_data_above_cutoff(
      'below_threshold_percent_CURVE', percent_cutoff,
      'FLAG_below_threshold_curve'
    )

  # Validation methods
  def validate_periphery(self, new_column: str, flag_columns: List[str]) -> None:
    """Validate periphery based on flag columns"""
    # Only use columns that actually exist
    flag_columns = [col for col in flag_columns if col in self.ftrs.columns]
    if not flag_columns:
        self.ftrs[new_column] = 1  # If no flags, consider periphery valid
        return
    any_nan = self.ftrs[flag_columns].isna().any(axis=1)
    any_one = self.ftrs[flag_columns].eq(1).any(axis=1)
    all_zero = self.ftrs[flag_columns].fillna(0).eq(0).all(axis=1)
    self.ftrs[new_column] = np.where(
      any_nan, 0, np.where(
        any_one, 0, np.where(
          all_zero, 1, np.nan
    )))

  def validate_feature(self, new_column: str, flag_columns: List[str]) -> None:
    """Validate feature based on flag columns and periphery validity"""
    search_valid = self.ftrs['PERIPHERY_VALID'] 
    any_nan = self.ftrs[flag_columns].isna().any(axis=1)
    any_one = self.ftrs[flag_columns].eq(1).any(axis=1)
    all_zero = self.ftrs[flag_columns].fillna(0).eq(0).all(axis=1)

    self.ftrs[new_column] = np.where(
      search_valid,
        np.where(any_nan, np.nan, 
          np.where(any_one, 0, 
            np.where(all_zero, 1, 
              np.nan
        ))),
      np.nan #if search invalid
    )

  def run_flags_and_validation(self) -> Dict[str, List[str]]:
    """Run all flags and validation in the correct order"""
    # First run periphery flags
    periphery_flags = []
    if 'flag_gaps_and_non_wear_periphery' in self.flag_selections and self.flag_selections['flag_gaps_and_non_wear_periphery']:
      self.flag_gaps_and_non_wear_periphery(
        self.flag_selections['flag_gaps_and_non_wear_periphery']['percent_cutoff']
      )
      periphery_flags.append('FLAG_gaps_and_non_wear_periphery')
    if 'flag_extreme_negative_periphery' in self.flag_selections and self.flag_selections['flag_extreme_negative_periphery']:
      self.flag_extreme_negative_periphery(
        self.flag_selections['flag_extreme_negative_periphery']['percent_cutoff']
      )
      periphery_flags.append('FLAG_extreme_negative_periphery')
    if 'flag_low_quality_periphery' in self.flag_selections and self.flag_selections['flag_low_quality_periphery']:
      self.flag_low_quality_periphery(
        self.flag_selections['flag_low_quality_periphery']['percent_cutoff']
      )
      periphery_flags.append('FLAG_low_quality_periphery')
    if 'flag_unimputed_low_quality_periphery' in self.flag_selections and self.flag_selections['flag_unimputed_low_quality_periphery']:
      self.flag_unimputed_low_quality_periphery(
        self.flag_selections['flag_unimputed_low_quality_periphery']['percent_cutoff']
      )
      periphery_flags.append('FLAG_unimputed_low_quality_periphery')

    # Validate periphery based on all periphery flags
    if periphery_flags:
      self.validate_periphery('PERIPHERY_VALID', periphery_flags)
    else:
      self.ftrs['PERIPHERY_VALID'] = 1  # If no periphery flags are set, consider periphery valid

    # Run curve flags
    curve_flags = []
    # Remove the block that checks and runs flag_unimputed_gaps_and_non_wear_region
    if 'flag_unimputed_low_quality_curve' in self.flag_selections and self.flag_selections['flag_unimputed_low_quality_curve']:
      self.flag_unimputed_low_quality_curve(
        self.flag_selections['flag_unimputed_low_quality_curve']['percent_cutoff'],
        self.flag_selections['flag_unimputed_low_quality_curve']['duration_cutoff']
      )
      curve_flags.append('FLAG_unimputed_low_quality_curve')

    if 'flag_imputed_low_quality_curve' in self.flag_selections and self.flag_selections['flag_imputed_low_quality_curve']:
      self.flag_imputed_low_quality_curve(
        self.flag_selections['flag_imputed_low_quality_curve']['percent_cutoff'],
        self.flag_selections['flag_imputed_low_quality_curve']['duration_cutoff']
      )
      curve_flags.append('FLAG_imputed_low_quality_curve')

    # Run incomplete curve flags
    if 'flag_incomplete_curve_start_curve' in self.flag_selections and self.flag_selections['flag_incomplete_curve_start_curve']:
      self.flag_incomplete_curve_start_curve(
        self.flag_selections['flag_incomplete_curve_start_curve']['percent_cutoff']
      )
      curve_flags.append('FLAG_incomplete_curve_start_curve')
    if 'flag_incomplete_curve_end_curve' in self.flag_selections and self.flag_selections['flag_incomplete_curve_end_curve']:
      self.flag_incomplete_curve_end_curve(
        self.flag_selections['flag_incomplete_curve_end_curve']['percent_cutoff']
      )
      curve_flags.append('FLAG_incomplete_curve_end_curve')

    # Run rise/fall low quality flags
    if 'flag_low_quality_rise_curve' in self.flag_selections and self.flag_selections['flag_low_quality_rise_curve']:
      self.flag_low_quality_rise_curve(
        self.flag_selections['flag_low_quality_rise_curve']['percent_cutoff']
      )
      curve_flags.append('FLAG_low_quality_rise_curve')
    if 'flag_low_quality_fall_curve' in self.flag_selections and self.flag_selections['flag_low_quality_fall_curve']:
      self.flag_low_quality_fall_curve(
        self.flag_selections['flag_low_quality_fall_curve']['percent_cutoff']
      )
      curve_flags.append('FLAG_low_quality_fall_curve')

    # Run below threshold flag
    if 'flag_below_threshold_curve' in self.flag_selections and self.flag_selections['flag_below_threshold_curve']:
      self.flag_below_threshold_curve(
        self.flag_selections['flag_below_threshold_curve']['percent_cutoff']
      )
      curve_flags.append('FLAG_below_threshold_curve')

    # Validate all flags that were actually run
    if curve_flags:
      self.validate_feature('CURVE_VALID', curve_flags)
    else:
      self.ftrs['CURVE_VALID'] = 1  # If no curve flags are set, consider curve valid

    # Return the flags dictionary
    return {
      'periphery_flags': periphery_flags,
      'curve_flags': curve_flags
    }
