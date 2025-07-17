import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Union
import os

class featureFlagger:
  """
  Takes event features; adds flags (1=flagged) or validation (1=valid)
  """
  def __init__(self, features: pd.DataFrame, flag_selections: Optional[Dict] = None):
    self.ftrs: pd.DataFrame = features
    self.flag_selections: Dict = {
      # Curve flags (matching default_flag_settings.py order)
      'flag_unimputed_low_quality_curve': {},
      'flag_imputed_limit_curve': {},
      'flag_unimputed_jump_curve': {},
      'flag_below_threshold_curve': {},
      # Start / End flags (using only percent)
      'flag_incomplete_curve_start_curve': {},
      'flag_imputed_rise_curve': {},
      'flag_incomplete_curve_end_curve': {},
      'flag_imputed_fall_curve': {},

      # Periphery Before flags (using only percent)
      'flag_gaps_and_non_wear_periphery_before': {},
      'flag_extreme_negative_periphery_before': {},
      'flag_unimputed_low_quality_periphery_before': {},
      # Periphery After flags (using only percent)
      'flag_gaps_and_non_wear_periphery_after': {},
      'flag_extreme_negative_periphery_after': {},
      'flag_unimputed_low_quality_periphery_after': {}
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





  # Dynamic periphery flag methods that auto-detect before/after from flag name
  # These methods eliminate code duplication by dynamically determining periphery type
  def flag_gaps_and_non_wear_periphery_dynamic(self, percent_cutoff: float, flag_name: str) -> None:
    """
    Dynamic method to flag periphery gaps and non-wear that auto-detects before/after from flag name.
    
    Args:
        percent_cutoff: Threshold percentage for flagging
        flag_name: The flag name (e.g., 'flag_gaps_and_non_wear_periphery_before')
    """
    # Extract periphery type from flag name
    if 'before' in flag_name:
      periphery_type = 'before'
    elif 'after' in flag_name:
      periphery_type = 'after'
    else:
      raise ValueError(f"Cannot determine periphery type from flag name: {flag_name}")
    
    suffix = f"PERIPHERY_{periphery_type.upper()}"
    
    # Calculate total percentage of gaps and non-wear
    total_percent = self.ftrs[f'total_gap_percent_{suffix}'] + self.ftrs[f'total_non_wear_percent_{suffix}']
    
    # Store the total in a temporary column
    self.ftrs[f'total_gaps_and_non_wear_percent_{suffix}'] = total_percent
    
    # Flag based on the total percentage
    self.flag_data_above_cutoff(
      f'total_gaps_and_non_wear_percent_{suffix}', percent_cutoff,
      f'FLAG_gaps_and_non_wear_periphery_{periphery_type}'
    )

  def flag_extreme_negative_periphery_dynamic(self, percent_cutoff: float, flag_name: str) -> None:
    """
    Dynamic method to flag periphery extreme negatives that auto-detects before/after from flag name.
    
    Args:
        percent_cutoff: Threshold percentage for flagging
        flag_name: The flag name (e.g., 'flag_extreme_negative_periphery_after')
    """
    # Extract periphery type from flag name
    if 'before' in flag_name:
      periphery_type = 'before'
    elif 'after' in flag_name:
      periphery_type = 'after'
    else:
      raise ValueError(f"Cannot determine periphery type from flag name: {flag_name}")
    
    suffix = f"PERIPHERY_{periphery_type.upper()}"
    
    self.flag_data_above_cutoff(
      f'total_extreme_negative_percent_{suffix}', percent_cutoff,
      f'FLAG_extreme_negative_periphery_{periphery_type}'
    )



  def flag_unimputed_low_quality_periphery_dynamic(self, percent_cutoff: float, flag_name: str) -> None:
    """
    Dynamic method to flag periphery unimputed low quality that auto-detects before/after from flag name.
    
    Args:
        percent_cutoff: Threshold percentage for flagging
        flag_name: The flag name (e.g., 'flag_unimputed_low_quality_periphery_after')
    """
    # Extract periphery type from flag name
    if 'before' in flag_name:
      periphery_type = 'before'
    elif 'after' in flag_name:
      periphery_type = 'after'
    else:
      raise ValueError(f"Cannot determine periphery type from flag name: {flag_name}")
    
    suffix = f"PERIPHERY_{periphery_type.upper()}"
    
    self.flag_data_above_cutoff(
      f'unimputed_low_quality_percent_{suffix}', percent_cutoff,
      f'FLAG_unimputed_low_quality_periphery_{periphery_type}'
    )





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

  def flag_imputed_limit_curve(self, percent_cutoff: float, duration_cutoff: float) -> None:
    """
    Flag a curve if either the imputed low quality percent or duration cutoff is exceeded.
    This is an OR rule - if either condition is met, the flag is set.
    """
    self.flag_data_above_one_of_two_cutoffs(
      'imputed_percent_CURVE', percent_cutoff,
      'imputed_duration_CURVE', duration_cutoff,
      'FLAG_imputed_limit_curve'
    )

  # Additional curve flag methods

  def flag_unimputed_jump_curve(self, percent_cutoff: float) -> None:
    """
    Flag a curve if the percentage of unimputed jump artifacts exceeds the cutoff.
    """
    self.flag_data_above_cutoff(
      'unimputed_jump_percent_CURVE', percent_cutoff,
      'FLAG_unimputed_jump_curve'
    )

  def flag_below_threshold_curve(self, percent_cutoff: float) -> None:
    """
    Flag a curve if the percentage of values below threshold exceeds the cutoff.
    """
    self.flag_data_above_cutoff(
      'below_threshold_percent_CURVE', percent_cutoff,
      'FLAG_below_threshold_curve'
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

  def flag_imputed_rise_curve(self, percent_cutoff: float) -> None:
    """
    Flag a curve if the rise portion has too much low quality data based on percent cutoff.
    """
    self.flag_data_above_cutoff(
      'rise_imputed_percent_CURVE', percent_cutoff,
      'FLAG_imputed_rise_curve'
    )

  def flag_imputed_fall_curve(self, percent_cutoff: float) -> None:
    """
    Flag a curve if the fall portion has too much low quality data based on percent cutoff.
    """
    self.flag_data_above_cutoff(
      'fall_imputed_percent_CURVE', percent_cutoff,
      'FLAG_imputed_fall_curve'
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
    
    # Create mapping from flag names to methods and their parameter requirements
    flag_method_mapping = {
      # Curve flags (matching default_flag_settings.py)
      'flag_unimputed_low_quality_curve': (self.flag_unimputed_low_quality_curve, ['percent_cutoff', 'duration_cutoff']),
      'flag_imputed_limit_curve': (self.flag_imputed_limit_curve, ['percent_cutoff', 'duration_cutoff']),
      'flag_unimputed_jump_curve': (self.flag_unimputed_jump_curve, ['percent_cutoff']),
      'flag_below_threshold_curve': (self.flag_below_threshold_curve, ['percent_cutoff']),
      
      # Start / End flags
      'flag_incomplete_curve_start_curve': (self.flag_incomplete_curve_start_curve, ['percent_cutoff']),
      'flag_imputed_rise_curve': (self.flag_imputed_rise_curve, ['percent_cutoff']),
      'flag_incomplete_curve_end_curve': (self.flag_incomplete_curve_end_curve, ['percent_cutoff']),
      'flag_imputed_fall_curve': (self.flag_imputed_fall_curve, ['percent_cutoff']),
      

      
      # Periphery flags using dynamic methods
      'flag_gaps_and_non_wear_periphery_before': (self.flag_gaps_and_non_wear_periphery_dynamic, ['percent_cutoff']),
      'flag_gaps_and_non_wear_periphery_after': (self.flag_gaps_and_non_wear_periphery_dynamic, ['percent_cutoff']),
      'flag_extreme_negative_periphery_before': (self.flag_extreme_negative_periphery_dynamic, ['percent_cutoff']),
      'flag_extreme_negative_periphery_after': (self.flag_extreme_negative_periphery_dynamic, ['percent_cutoff']),
      'flag_unimputed_low_quality_periphery_before': (self.flag_unimputed_low_quality_periphery_dynamic, ['percent_cutoff']),
      'flag_unimputed_low_quality_periphery_after': (self.flag_unimputed_low_quality_periphery_dynamic, ['percent_cutoff'])
    }
    
    # Define which flags are periphery vs curve for validation
    periphery_flag_names = {
      'flag_gaps_and_non_wear_periphery_before', 'flag_extreme_negative_periphery_before',
      'flag_unimputed_low_quality_periphery_before',
      'flag_gaps_and_non_wear_periphery_after', 'flag_extreme_negative_periphery_after',
      'flag_unimputed_low_quality_periphery_after'
    }
    
    periphery_flags = []
    curve_flags = []
    
    # Loop through flag_selections in order
    for flag_name in self.flag_selections.keys():
      if flag_name in self.flag_selections and self.flag_selections[flag_name]:
        if flag_name in flag_method_mapping:
          method, param_names = flag_method_mapping[flag_name]
          
          # Build parameters from flag_selections
          params = []
          for param_name in param_names:
            if param_name in self.flag_selections[flag_name]:
              params.append(self.flag_selections[flag_name][param_name])
            else:
              # Skip this flag if required parameter is missing
              break
          
          # Only call method if all parameters are available
          if len(params) == len(param_names):
            # Check if this is a dynamic periphery method that needs flag_name
            if method.__name__.endswith('_dynamic'):
              method(*params, flag_name)
            else:
              method(*params)
            
            # Add to appropriate flag list for validation
            flag_column_name = f'FLAG_{flag_name[5:]}'  # Remove 'flag_' prefix
            if flag_name in periphery_flag_names:
              periphery_flags.append(flag_column_name)
            else:
              curve_flags.append(flag_column_name)

    # Validate periphery based on all periphery flags
    if periphery_flags:
      self.validate_periphery('PERIPHERY_VALID', periphery_flags)
    else:
      self.ftrs['PERIPHERY_VALID'] = 1  # If no periphery flags are set, consider periphery valid

    # Validate all curve flags that were actually run
    if curve_flags:
      self.validate_feature('CURVE_VALID', curve_flags)
    else:
      self.ftrs['CURVE_VALID'] = 1  # If no curve flags are set, consider curve valid

    # Return the flags dictionary
    return {
      'periphery_flags': periphery_flags,
      'curve_flags': curve_flags
    }

  def export_flag_analysis_workbooks(self, output_dir: str, plot_columns: Optional[List[str]] = None) -> None:
    """
    Create a series of Excel files, one for each flag, showing curves that meet 
    that specific flag but not previous flags in the processing order.
    
    Each Excel file contains:
    - Data tab: Features for curves meeting this flag
    - Plots tab: Visualizations for flagged curves
    - Near Miss tab: 50 curves closest to hitting this flag but didn't
    - Stats tab: Count breakdown of flag applications
    
    Args:
        output_dir (str): Directory to save the Excel files
        plot_columns (list, optional): List of column names containing plot paths.
                                     Defaults to common plot columns.
    """
    # Default plot columns if none provided
    if plot_columns is None:
      plot_columns = [
        'device_removal_plot', 'signal_processing_plot', 
        'signal_processing_plot_wide'
      ]
    
    # Filter to only plot columns that exist in the data
    available_plot_columns = [col for col in plot_columns if col in self.ftrs.columns]
    
    if not available_plot_columns:
      print("Warning: No plot columns found in data. Excel files will contain data and stats only.")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Create mapping from flag names to their underlying data columns
    flag_to_column_mapping = self._create_flag_to_column_mapping()
    
    # Get all flag columns in order
    flag_columns = []
    for flag_name in self.flag_selections.keys():
      flag_col = f'FLAG_{flag_name[5:]}'  # Remove 'flag_' prefix
      if flag_col in self.ftrs.columns:
        flag_columns.append(flag_col)
    
    if not flag_columns:
      print("No flag columns found in data.")
      return
    
    # Track curves that have been assigned to previous flags
    used_indices = set()
    
    # Create Excel file for each flag
    for i, flag_col in enumerate(flag_columns):
      # Get curves that have this flag
      flagged_curves = self.ftrs[self.ftrs[flag_col] == 1].copy()
      
      # Remove curves that were already assigned to previous flags
      new_flagged_curves = flagged_curves[~flagged_curves.index.isin(used_indices)]
      
      if len(new_flagged_curves) == 0:
        print(f"No new curves found for {flag_col} (all flagged curves already assigned to previous flags)")
        continue
      
      # Update used indices
      used_indices.update(new_flagged_curves.index)
      
      # Create filename
      flag_name = flag_col.replace('FLAG_', '').lower()
      filename = os.path.join(output_dir, f"{i+1:02d}_{flag_name}.xlsx")
      
      # Calculate statistics for this flag
      stats_data = self._calculate_flag_stats(flag_col, used_indices, flag_columns)
      
      # Find closest non-flagged curves
      near_miss_curves = self._find_near_miss_curves(flag_col, flag_to_column_mapping)
      
      # Create Excel file
      with pd.ExcelWriter(filename, engine='xlsxwriter', mode='w') as writer:
        # Data tab
        new_flagged_curves.to_excel(writer, sheet_name='Data', index=False)
        
        # Stats tab
        stats_df = pd.DataFrame(list(stats_data.items()), columns=['Metric', 'Count'])
        stats_df.to_excel(writer, sheet_name='Stats', index=False)
        
        # Plots tab (if plot columns are available)
        if available_plot_columns and len(new_flagged_curves) > 0:
          # Get plot paths for each plot column
          plot_lists = []
          for plot_col in available_plot_columns:
            if plot_col in new_flagged_curves.columns:
              plots = new_flagged_curves[plot_col].dropna().tolist()
              plot_lists.append(plots)
            else:
              plot_lists.append([])
          
          # Only create plots tab if we have some plots
          if any(plot_lists):
            from App.SDM.Documenting.embed_graphs import embed_graphs_into_workbook_tab
            embed_graphs_into_workbook_tab(
              writer.book,
              plot_lists,
              worksheet_name='Plots',
              plot_header_text=f'{flag_col} Flagged Curves',
              missing_plot_path_text='No Plot Available'
            )
        
        # Near Miss tab (curves closest to hitting this flag)
        if near_miss_curves is not None and len(near_miss_curves) > 0:
          near_miss_curves.to_excel(writer, sheet_name='Near Miss Data', index=False)
          
          # Near Miss plots
          if available_plot_columns:
            plot_lists = []
            for plot_col in available_plot_columns:
              if plot_col in near_miss_curves.columns:
                plots = near_miss_curves[plot_col].dropna().tolist()
                plot_lists.append(plots)
              else:
                plot_lists.append([])
            
            if any(plot_lists):
              embed_graphs_into_workbook_tab(
                writer.book,
                plot_lists,
                worksheet_name='Near Miss Plots',
                plot_header_text=f'Curves Nearly Flagged by {flag_col}',
                missing_plot_path_text='No Plot Available'
              )
      
      near_miss_count = len(near_miss_curves) if near_miss_curves is not None else 0
      print(f"Created {filename} with {len(new_flagged_curves)} flagged curves and {near_miss_count} near-miss curves")
    
    # Create summary file with all unflagged curves
    unflagged_curves = self.ftrs[~self.ftrs.index.isin(used_indices)].copy()
    if len(unflagged_curves) > 0:
      summary_filename = os.path.join(output_dir, "00_unflagged_curves.xlsx")
      
      with pd.ExcelWriter(summary_filename, engine='xlsxwriter', mode='w') as writer:
        unflagged_curves.to_excel(writer, sheet_name='Data', index=False)
        
        # Summary stats
        summary_stats = {
          'Total Curves': len(self.ftrs),
          'Unflagged Curves': len(unflagged_curves),
          'Flagged Curves': len(used_indices),
          'Percentage Unflagged': (len(unflagged_curves) / len(self.ftrs)) * 100
        }
        summary_df = pd.DataFrame(list(summary_stats.items()), columns=['Metric', 'Count'])
        summary_df.to_excel(writer, sheet_name='Stats', index=False)
        
        # Plots for unflagged curves
        if available_plot_columns and len(unflagged_curves) > 0:
          plot_lists = []
          for plot_col in available_plot_columns:
            if plot_col in unflagged_curves.columns:
              plots = unflagged_curves[plot_col].dropna().tolist()
              plot_lists.append(plots)
            else:
              plot_lists.append([])
          
          if any(plot_lists):
            from App.SDM.Documenting.embed_graphs import embed_graphs_into_workbook_tab
            embed_graphs_into_workbook_tab(
              writer.book,
              plot_lists,
              worksheet_name='Plots',
              plot_header_text='Unflagged Curves',
              missing_plot_path_text='No Plot Available'
            )
      
      print(f"Created {summary_filename} with {len(unflagged_curves)} unflagged curves")

  def _create_flag_to_column_mapping(self) -> Dict[str, str]:
    """
    Create mapping from flag column names to their underlying data columns.
    
    Returns:
        dict: Mapping from flag column names to data column names
    """
    return {
      # Curve flags (matching default_flag_settings.py)
      'FLAG_unimputed_low_quality_curve': 'unimputed_low_quality_percent_CURVE',
      'FLAG_imputed_limit_curve': 'imputed_percent_CURVE',
      'FLAG_unimputed_jump_curve': 'unimputed_jump_percent_CURVE',
      'FLAG_below_threshold_curve': 'below_threshold_percent_CURVE',
      
      # Start / End flags
      'FLAG_incomplete_curve_start_curve': 'rise_complete_percent_CURVE',
      'FLAG_imputed_rise_curve': 'rise_imputed_percent_CURVE',
      'FLAG_incomplete_curve_end_curve': 'fall_complete_percent_CURVE',
      'FLAG_imputed_fall_curve': 'fall_imputed_percent_CURVE',
      

      
      # Periphery Before flags
      'FLAG_gaps_and_non_wear_periphery_before': 'total_gaps_and_non_wear_percent_PERIPHERY_BEFORE',
      'FLAG_extreme_negative_periphery_before': 'total_extreme_negative_percent_PERIPHERY_BEFORE',
      'FLAG_unimputed_low_quality_periphery_before': 'unimputed_low_quality_percent_PERIPHERY_BEFORE',
      
      # Periphery After flags
      'FLAG_gaps_and_non_wear_periphery_after': 'total_gaps_and_non_wear_percent_PERIPHERY_AFTER',
      'FLAG_extreme_negative_periphery_after': 'total_extreme_negative_percent_PERIPHERY_AFTER',
      'FLAG_unimputed_low_quality_periphery_after': 'unimputed_low_quality_percent_PERIPHERY_AFTER'
    }

  def _find_near_miss_curves(self, flag_col: str, flag_to_column_mapping: Dict[str, str], n_closest: int = 50) -> Optional[pd.DataFrame]:
    """
    Find curves that are closest to hitting the specified flag but didn't.
    
    Args:
        flag_col (str): Name of the flag column
        flag_to_column_mapping (dict): Mapping from flag to data column
        n_closest (int): Number of closest curves to return
        
    Returns:
        pd.DataFrame or None: DataFrame of closest non-flagged curves
    """
    if flag_col not in flag_to_column_mapping:
      print(f"Warning: No data column mapping found for {flag_col}")
      return None
    
    sort_column = flag_to_column_mapping[flag_col]
    
    if sort_column not in self.ftrs.columns:
      print(f"Warning: Data column {sort_column} not found for {flag_col}")
      return None
    
    # Get all flag columns
    all_flag_cols = [col for col in self.ftrs.columns if col.startswith('FLAG_')]
    
    # Get curves that have this flag
    flagged = self.ftrs[self.ftrs[flag_col] == 1]
    
    # Filter to only include rows that have no other flags (uniquely flagged)
    uniquely_flagged = flagged[flagged[all_flag_cols].sum(axis=1) == 1]
    
    # Get non-flagged rows (curves that don't have this flag)
    non_flagged = self.ftrs[self.ftrs[flag_col] != 1]
    
    if len(uniquely_flagged) == 0 or len(non_flagged) == 0:
      return None
    
    # Determine if flag is for high or low values by comparing means
    flagged_mean = uniquely_flagged[sort_column].mean()
    non_flagged_mean = non_flagged[sort_column].mean()
    is_high_flag = flagged_mean > non_flagged_mean
    
    # Get n_closest non-flagged rows
    if is_high_flag:
      # For high flags, take the highest non-flagged values (closest to threshold)
      closest_non_flagged = non_flagged.nlargest(n_closest, sort_column)
    else:
      # For low flags, take the lowest non-flagged values (closest to threshold)
      closest_non_flagged = non_flagged.nsmallest(n_closest, sort_column)
    
    return closest_non_flagged

  def _calculate_flag_stats(self, current_flag: str, used_indices: set, all_flag_columns: List[str]) -> Dict[str, int]:
    """
    Calculate statistics for the current flag analysis.
    
    Args:
        current_flag (str): Name of the current flag column
        used_indices (set): Indices of curves already assigned to previous flags
        all_flag_columns (list): List of all flag column names
    
    Returns:
        dict: Statistics for this flag
    """
    total_curves = len(self.ftrs)
    
    # Curves with flags already applied (previous flags)
    curves_with_previous_flags = len(used_indices)
    
    # Curves that hit the current flag
    current_flag_curves = len(self.ftrs[self.ftrs[current_flag] == 1])
    
    # Curves that hit the current flag but not assigned to previous flags
    new_current_flag_curves = len(self.ftrs[
      (self.ftrs[current_flag] == 1) & 
      (~self.ftrs.index.isin(used_indices))
    ])
    
    # Curves that hit other flags (but not current flag and not already used)
    other_flag_columns = [col for col in all_flag_columns if col != current_flag]
    curves_with_other_flags = 0
    if other_flag_columns:
      other_flags_mask = self.ftrs[other_flag_columns].eq(1).any(axis=1)
      current_flag_mask = self.ftrs[current_flag] == 1
      used_mask = self.ftrs.index.isin(used_indices)
      
      curves_with_other_flags = len(self.ftrs[
        other_flags_mask & ~current_flag_mask & ~used_mask
      ])
    
    # Curves that didn't hit any flag
    any_flag_mask = self.ftrs[all_flag_columns].eq(1).any(axis=1)
    curves_with_no_flags = len(self.ftrs[~any_flag_mask])
    
    return {
      'Total Curves': total_curves,
      'Curves with Previous Flags': curves_with_previous_flags,
      'Curves with Current Flag (Total)': current_flag_curves,
      'Curves with Current Flag (New)': new_current_flag_curves,
      'Curves with Other Flags Only': curves_with_other_flags,
      'Curves with No Flags': curves_with_no_flags
    }
