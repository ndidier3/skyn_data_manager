from App.SDM.Analysis.statModel import statModel
from App.SDM.Skyn_Processors.ema_region import emaRegion
from App.SDM.Configuration.file_management import load, save_to_computer
from App.SDM.Documenting.embed_graphs import embed_graphs_into_workbook_tab
from App.SDM.Documenting.report_guide import report_guide
from App.SDM.Configuration.file_management import extract_subid
from App.SDM.Visualization.quality import QualityVisualizer
import os
import pandas as pd
import numpy as np
from scipy import stats
from scipy.signal import find_peaks
import matplotlib.pyplot as plt

class curveFeatures():
  def __init__(self, processed_data_folder, smooth_and_impute_attrs=None, curve_attrs=None, subid=None, additional_processed_data_folders=[]):
    # Get list of processed files
    processed_files = [file for file in os.listdir(processed_data_folder) if 'processed' in file]
    
    # Filter files by subid if specified
    if subid is not None:
      processed_files = [file for file in processed_files if extract_subid(file) == str(subid)]
      if not processed_files:
        raise ValueError(f"No processed files found for subid {subid}")
    
    print(f"\nFound {len(processed_files)} processed files")
    
    # Load only the filtered processors
    self.processors = [load(file[:-4], processed_data_folder) for file in processed_files]
    self.processors = [processor for processor in self.processors if hasattr(processor, 'curve_features')]
    
    print(f"\nFound {len(self.processors)} processors with curve_features")
    
    # Create a list of DataFrames with consistent columns
    dfs = []
    for i, processor in enumerate(self.processors):

      df = processor.curve_features.copy()
      # Only keep rows that have plot paths
      plot_cols = ['smoothed_curve_plot', 'signal_processing_plot', 'device_removal_plot', 'signal_processing_plot_wide']
      has_plots = df[plot_cols].notna().any(axis=1)
      df = df[has_plots]
      dfs.append(df)
    
    # Concatenate with consistent columns
    self.curve_features = pd.concat(dfs, ignore_index=True)
    
    # Convert subid and curve_id to int
    self.curve_features[['subid', 'curve_id']] = self.curve_features[['subid', 'curve_id']].astype(int)
    
    # Store plot columns before drop_duplicates
    plot_data = self.curve_features[plot_cols].copy()
    
    # Drop duplicates while preserving plot columns
    self.curve_features = self.curve_features.drop_duplicates(subset=['subid', 'curve_id'])
    
    # Restore plot columns
    for col in plot_cols:
      if col in plot_data.columns:
        self.curve_features[col] = plot_data[col]
    
    self.curve_stat_frames = []

    # Store configuration
    self.smooth_and_impute_attrs = smooth_and_impute_attrs
    self.curve_attrs = curve_attrs

    # Create a copy of the feature types dictionary
    self.person_level_dtypes = report_guide.person_level_feature_types.copy()

    self.default_tac_features = report_guide.stats_features

    self.curve_valid = self.curve_features[self.curve_features['CURVE_VALID'] == 1]
    self.curve_invalid = self.curve_features[self.curve_features['CURVE_VALID'] != 1]

    # Initialize quality visualizer
    self.quality_visualizer = QualityVisualizer()

    self.curve_features.to_excel('Results/ARC_auto_threshold/curve_features.xlsx')

  def compile_imputation_info(self):
    """Compile imputation information from all processors"""
    imputation_dfs = []
    for processor in self.processors:
      if hasattr(processor, 'imputation_info'):
        df = processor.imputation_info.copy()
        df['subid'] = processor.subid
        df['dataset_identifier'] = processor.dataset_identifier
        imputation_dfs.append(df)
    return pd.concat(imputation_dfs, ignore_index=True) if imputation_dfs else pd.DataFrame()

  def compute_tac_feature_stats(self):
    valid = statModel(self.curve_valid)
    invalid = statModel(self.curve_invalid)
    valid_feature_stats = valid.continuous_stats_for_columns(self.default_tac_features)
    invalid_feature_stats = invalid.continuous_stats_for_columns(self.default_tac_features)
    
    basic_curve_counts = pd.DataFrame({
      'Total Curves': [len(self.curve_features)],
      'Valid Curves': [len(self.curve_valid)],
      'Invalid Curves': [len(self.curve_invalid)],
      'N Participants': [len(self.curve_features['subid'].unique())],
      'N Participants (with valid curves)': [len(self.curve_valid['subid'].unique())],
      'Average Curves Per Person': [len(self.curve_features) / len(self.curve_features['subid'].unique())],
      'Average Valid Curves Per Person': [len(self.curve_valid) / len(self.curve_valid['subid'].unique())]
    })

    # Add multi-index header for valid curves
    valid_feature_stats.columns = pd.MultiIndex.from_product(
      [['Valid Curves'], valid_feature_stats.columns]
    )
    
    # Add multi-index header for invalid curves
    invalid_feature_stats.columns = pd.MultiIndex.from_product(
      [['Invalid Curves'], invalid_feature_stats.columns]
    )
    self.curve_stat_frames.append(basic_curve_counts)
    self.curve_stat_frames.append(valid_feature_stats)
    self.curve_stat_frames.append(invalid_feature_stats)

  def count_curve_flags(self):
    stats = statModel(self.curve_features)
    flag_cols = [col for col in self.curve_features.columns if 'FLAG' in col]
    flag_stats_list = []
    total_curves = len(self.curve_features)
    
    # Create a DataFrame with just the flag columns for easier comparison
    flag_df = self.curve_features[flag_cols].copy()
    
    # Define the desired order of flags
    desired_flag_order = [
      'FLAG_sub_negative_10_PERIPHERY_>80%_>2hrs',
      'FLAG_sub_negative_20_PERIPHERY_>40%_>1.5hrs',
      'FLAG_sub_negative_40_PERIPHERY_>20%_>0.5hrs',
      'FLAG_non_wear_PERIPHERY_>40%',
      'FLAG_flatlined_peak_CURVE_>20%flatline_peak>350',
      # 'FLAG_sub_negative_10_CURVE_>20%_>1.0',
      'FLAG_rise_completion_CURVE_<50%',
      'FLAG_rise_rate_CURVE_>430',
      'FLAG_fall_completion_CURVE_<50%',
      'FLAG_short_curve_duration_CURVE_<0.25hrs',
      'FLAG_imputed_CURVE_>40%_or_duration>3hrs',
      'FLAG_unimputed_low_quality_CURVE_>20%'
    ]
    
    # Filter flag_cols to only include flags that exist in the data
    flag_cols = [col for col in desired_flag_order if col in flag_cols]
    
    for flag_col in flag_cols:
      flag_stats = stats.groupby_counts(flag_col, include_unique_flags=True)
      flag_stats = flag_stats.reset_index()
      flag_stats['Flag_Column'] = flag_col
      
      # Add columns for shared counts with other flags in the desired order
      for other_flag in flag_cols:
        if other_flag != flag_col:
          # Calculate how many curves have both flags
          shared_count = ((flag_df[flag_col] == 1) & (flag_df[other_flag] == 1)).sum()
          flag_stats[f'shared_count_{other_flag}'] = shared_count
      
      flag_stats_list.append(flag_stats)
    
    if flag_stats_list:
      combined_flag_stats = pd.concat(flag_stats_list, axis=0, ignore_index=True)
      # Only keep relevant columns (adjust as needed)
      keep_cols = [col for col in combined_flag_stats.columns if col in [
        'Value', 'Count', '%', 'Unique_Flag_Count', 'Unique_Flag_%', 'Flag_Column'
      ] or col.startswith('shared_count_')]
      combined_flag_stats = combined_flag_stats[keep_cols]
      # Filter out rows where 'Unique_Flag_Count' is empty (removes counts of non-flagged curves, only keeping flag counts)
      combined_flag_stats = combined_flag_stats[combined_flag_stats['Unique_Flag_Count'].notna() & (combined_flag_stats['Unique_Flag_Count'] != '')]
      # Calculate % of total curves and rename column
      combined_flag_stats['% of Total Curves'] = (combined_flag_stats['Count'] / total_curves) * 100
      # Drop the old '%' column if it exists
      if '%' in combined_flag_stats.columns:
        combined_flag_stats = combined_flag_stats.drop(columns=['%'])
      
      # Set 'Flag_Column' as the index
      combined_flag_stats = combined_flag_stats.set_index('Flag_Column')
      
      # Set diagonal values to null (flag can't share with itself)
      for flag_col in flag_cols:
        col_name = f'shared_count_{flag_col}'
        if col_name in combined_flag_stats.columns:
          combined_flag_stats.loc[flag_col, col_name] = np.nan
      
      # Reorder columns to put '% of Total Curves' after 'Count'
      cols = combined_flag_stats.columns.tolist()
      count_idx = cols.index('Count')
      pct_idx = cols.index('% of Total Curves')
      cols.remove('% of Total Curves')
      cols.insert(count_idx + 1, '% of Total Curves')
      
      # Reorder shared count columns according to desired_flag_order
      shared_count_cols = [col for col in cols if col.startswith('shared_count_')]
      other_cols = [col for col in cols if not col.startswith('shared_count_')]
      ordered_shared_cols = [f'shared_count_{flag}' for flag in desired_flag_order if f'shared_count_{flag}' in shared_count_cols]
      cols = other_cols + ordered_shared_cols
      
      combined_flag_stats = combined_flag_stats[cols]
      
      self.curve_stat_frames.append(combined_flag_stats)

  def compute_person_level_stats(self):
    """
    Compute person-level statistics for both continuous and categorical curve features.
    Adds the results to curve_stat_frames.
    """
    # Add any flag columns as categorical
    for col in self.curve_features.columns:
      if 'FLAG' in col:
        self.person_level_dtypes[col] = 'categorical'
    
    # Compute person-level stats
    stats = statModel(self.curve_features)
    person_stats = stats.get_subid_level_stats(self.person_level_dtypes)
    
    self.person_level_stats = person_stats

  def compute_person_level_stats_valid(self):
    """
    Compute person-level statistics for valid curves only.
    Saves the results to self.person_level_stats_valid.
    """
    # Add any flag columns as categorical
    for col in self.curve_valid.columns:
      if 'FLAG' in col:
        self.person_level_dtypes[col] = 'categorical'
    
    stats = statModel(self.curve_valid)
    person_stats_valid = stats.get_subid_level_stats(self.person_level_dtypes)
    self.person_level_stats_valid = person_stats_valid

  def run_stats(self):
    self.compute_tac_feature_stats()
    self.count_curve_flags()
    self.compute_person_level_stats()
    self.compute_person_level_stats_valid()

  def export_workbook_curves(self, file_name, include_plots=True, export_imputations=False):
    with pd.ExcelWriter(file_name, engine = 'xlsxwriter', mode = 'w') as writer:
      # Add tab descriptions
      report_guide.get_tab_descriptions_dataframe(include_events=False).to_excel(writer, sheet_name='Tab Descriptions', index=False)
      
      # Add variable key
      variable_key = pd.DataFrame({
        'Variable': list(report_guide.curve_features_descriptions.keys()),
        'Description': list(report_guide.curve_features_descriptions.values())
      })
      variable_key.to_excel(writer, sheet_name='Variable Key', index=False)
      
      # Add stats
      row_index = 0
      for i, frame in enumerate(self.curve_stat_frames):
        frame.to_excel(writer, sheet_name='Stats', startrow=row_index)
        row_index += len(frame) + 4
      
      # Add features
      self.curve_features.to_excel(writer, sheet_name='Features', index=False)
      
      # Add person level stats
      self.person_level_stats.to_excel(writer, sheet_name='Person Level Stats', index=True)
      self.person_level_stats_valid.to_excel(writer, sheet_name='Person Level Stats (Valid)', index=True)
      # Add visualization tabs
      if include_plots:
        embed_graphs_into_workbook_tab(
          writer.book,
          [
            self.curve_invalid['device_removal_plot'].tolist(),
            self.curve_invalid['signal_processing_plot'].tolist(),
            self.curve_invalid['signal_processing_plot_wide'].tolist()
          ],
          worksheet_name = 'Invalid Curves',
          plot_header_text = '',
          missing_plot_path_text = 'No Plot Available'
        )

        embed_graphs_into_workbook_tab(
          writer.book,
          [
            self.curve_valid['device_removal_plot'].tolist(),
            self.curve_valid['signal_processing_plot'].tolist(),
            self.curve_valid['signal_processing_plot_wide'].tolist()
          ],
          worksheet_name = 'Valid Curves',
          plot_header_text = '',
          missing_plot_path_text = 'No Plot Available'
        )
      
      # Add imputations
      if export_imputations:
        self.compile_imputation_info().to_excel(writer, sheet_name='Imputations', index=False)
      
      # Add run settings
      run_settings_df = report_guide.get_run_settings_dataframe(
        smooth_and_impute_attrs=self.smooth_and_impute_attrs,
        curve_attrs=self.curve_attrs
      )
      if run_settings_df is not None:
        run_settings_df.to_excel(writer, sheet_name='Run Settings', index=False)

  def export_sorted_workbook(self, file_name, sort_column, ascending=True, smooth_and_impute_attrs=None, curve_attrs=None, flag_prefix=None):
    """
    Export a workbook with features and curves sorted by a specified column.
    Includes only rows that are uniquely flagged (have the specified flag but no other flags)
    and 50 non-flagged rows that are closest to the flag threshold.
    
    Args:
      file_name (str): Name of the output Excel file
      sort_column (str): Name of the column to sort by
      ascending (bool): Whether to sort in ascending order (True) or descending order (False)
      smooth_and_impute_attrs (dict, optional): Smoothing and imputation attributes
      curve_attrs (dict, optional): Curve attributes
      flag_prefix (str, optional): The exact flag column name to use for filtering
    """
    # Ensure stats are computed
    if not self.curve_stat_frames:
      self.run_stats()
    
    with pd.ExcelWriter(file_name, engine='xlsxwriter', mode='w') as writer:
      # Add tab descriptions
      report_guide.get_tab_descriptions_dataframe(include_events=False).to_excel(writer, sheet_name='Tab Descriptions', index=False)
      
      # Add variable key
      variable_key = pd.DataFrame({
        'Variable': list(report_guide.curve_features_descriptions.keys()),
        'Description': list(report_guide.curve_features_descriptions.values())
      })
      variable_key.to_excel(writer, sheet_name='Variable Key', index=False)
      
      # Add stats
      row_index = 0
      for i, frame in enumerate(self.curve_stat_frames):
        frame.to_excel(writer, sheet_name='Stats', startrow=row_index)
        row_index += len(frame) + 3
      
      # Sort features
      sorted_features = self.curve_features.sort_values(by=sort_column, ascending=ascending)
      
      # Use provided flag prefix if available, otherwise try to find it
      if flag_prefix and flag_prefix in sorted_features.columns:
        flag_column = flag_prefix
      else:
        # Find corresponding flag column
        # Remove _CURVE or _PERIPHERY suffix if present
        base_column = sort_column.replace('_CURVE', '').replace('_PERIPHERY', '')
        
        # Flexibly match any flag column containing the base_column
        flag_candidates = [col for col in sorted_features.columns if col.startswith('FLAG_') and base_column in col]
        flag_column = flag_candidates[0] if flag_candidates else None
      
      if flag_column:
        # Get all flag columns
        all_flag_cols = [col for col in sorted_features.columns if col.startswith('FLAG_')]
        
        # Get rows that have the target flag
        flagged = sorted_features[sorted_features[flag_column] == 1]
        
        # Filter to only include rows that have no other flags
        uniquely_flagged = flagged[flagged[all_flag_cols].sum(axis=1) == 1]
        
        # Get non-flagged rows
        non_flagged = sorted_features[sorted_features[flag_column] != 1]
        
        if len(uniquely_flagged) > 0:
          # Determine if flag is for high or low values by comparing means
          flagged_mean = uniquely_flagged[sort_column].mean()
          non_flagged_mean = non_flagged[sort_column].mean()
          is_high_flag = flagged_mean > non_flagged_mean
          
          # Get 50 closest non-flagged rows
          if is_high_flag:
            # For high flags, take the highest 50 non-flagged values
            closest_non_flagged = non_flagged.nlargest(50, sort_column)
          else:
            # For low flags, take the lowest 50 non-flagged values
            closest_non_flagged = non_flagged.nsmallest(50, sort_column)
          
          # Combine uniquely flagged and closest non-flagged rows
          selected_indices = sorted(set(uniquely_flagged.index) | set(closest_non_flagged.index))
          sorted_features = sorted_features.loc[selected_indices]
      
      sorted_features.to_excel(writer, sheet_name='Features', index=False)
      
      # Split curves into valid and invalid based on CURVE_VALID
      valid_curves = sorted_features[sorted_features['CURVE_VALID'] == 1]
      invalid_curves = sorted_features[sorted_features['CURVE_VALID'] != 1]
      
      # Add visualization tabs for valid and invalid curves
      if not invalid_curves.empty:
        if flag_column:
          all_flag_cols = [col for col in invalid_curves.columns if col.startswith('FLAG_')]
          uniquely_flagged = invalid_curves[invalid_curves[all_flag_cols].sum(axis=1) == 1]
          if not uniquely_flagged.empty:
            embed_graphs_into_workbook_tab(
              writer.book,
              [
                uniquely_flagged['device_removal_plot'].tolist(),
                uniquely_flagged['signal_processing_plot'].tolist(),
                uniquely_flagged['signal_processing_plot_wide'].tolist()
              ],
              worksheet_name='Invalid Curves',
              plot_header_text='',
              missing_plot_path_text='No Plot Available'
            )
        else:
          embed_graphs_into_workbook_tab(
            writer.book,
            [
              invalid_curves['device_removal_plot'].tolist(),
              invalid_curves['signal_processing_plot'].tolist(),
              invalid_curves['signal_processing_plot_wide'].tolist()
            ],
            worksheet_name='Invalid Curves',
            plot_header_text='',
            missing_plot_path_text='No Plot Available'
          )
      
      if not valid_curves.empty:
        embed_graphs_into_workbook_tab(
          writer.book,
          [
            valid_curves['device_removal_plot'].tolist(),
            valid_curves['signal_processing_plot'].tolist(),
            valid_curves['signal_processing_plot_wide'].tolist()
          ],
          worksheet_name='Valid Curves',
          plot_header_text='',
          missing_plot_path_text='No Plot Available'
        )
      
      # Add run settings
      run_settings_df = report_guide.get_run_settings_dataframe(
        smooth_and_impute_attrs=smooth_and_impute_attrs,
        curve_attrs=curve_attrs
      )
      if run_settings_df is not None:
        run_settings_df.to_excel(writer, sheet_name='Run Settings', index=False)

  def create_quality_correlation_plots(self, output_dir=None):
    """
    Create correlation scatterplots between quality features and TAC features.
    Creates separate plots for each quality feature, with all TAC features shown in each plot.
    Uses matplotlib for plotting.
    Plots are saved in the output_dir if provided, otherwise in the current directory.
    """
    self.quality_visualizer.create_quality_correlation_plots(self.curve_features, output_dir)

  def create_quality_boxplots(self, output_dir=None):
    """
    Create box and whisker plots for every 5% increase in quality features.
    Uses the same arrangement of quality and TAC features as in create_quality_correlation_plots.
    Plots are saved in the output_dir if provided, otherwise in the current directory.
    
    The plots are split vertically by imputation ratio to show how imputation affects the quality metrics.
    Groups are split into [0], (0,100), [100] for imputation ratios.
    """
    self.quality_visualizer.create_quality_boxplots(self.curve_features, output_dir)

  def create_quality_mean_plots(self, output_dir=None, use_three_imputation_ratio_groups=False):
    """
    Create plots showing mean ± standard error for TAC features across quality feature bins.
    Uses the same arrangement of quality and TAC features as in create_quality_boxplots.
    Plots are saved in the output_dir if provided, otherwise in the current directory.
    
    The plots are split vertically by imputation ratio to show how imputation affects the quality metrics.
    Can use either two groups ([0,100) and [100]) or three groups ([0], (0,100), [100]).
    
    Args:
        output_dir (str, optional): Directory to save plots. If None, saves in current directory.
        use_three_imputation_ratio_groups (bool, optional): If True, uses three imputation ratio groups ([0], (0,100), [100]).
            If False, uses two groups ([0,100), [100]). Default is False.
    """
    # Create a new visualizer with the specified grouping scheme
    visualizer = QualityVisualizer(use_three_imputation_ratio_groups=use_three_imputation_ratio_groups)
    visualizer.create_quality_mean_plots(self.curve_features, output_dir)

  def identify_perfect_curves(self):
    """
    Identify curves that have no low quality data in either periphery or curve regions.
    Sets a 'perfect' column to 1 for curves that meet these criteria:
    - No low quality data in periphery (low_quality_percent_PERIPHERY = 0)
    - No low quality data in curve (low_quality_percent_CURVE = 0)
    """
    # Initialize perfect column to 0
    self.curve_features['perfect'] = 0
    
    # Set perfect to 1 where both periphery and curve have no low quality data
    perfect_mask = (
      (self.curve_features['total_low_quality_duration_REGION'] == 0)
    )
    self.curve_features.loc[perfect_mask, 'perfect'] = 1
    
    # Print summary
    total_curves = len(self.curve_features)
    perfect_curves = perfect_mask.sum()
    print(f"Found {perfect_curves} perfect curves out of {total_curves} total curves ({perfect_curves/total_curves*100:.1f}%)")

def calculate_curve_features(tac_curve, time_points, baseline_value=None):
  """
  Calculate features from a TAC curve.
  
  Args:
    tac_curve (np.ndarray): Array of TAC values
    time_points (np.ndarray): Array of time points in hours
    baseline_value (float, optional): Baseline TAC value. If None, will be calculated.
    
  Returns:
    dict: Dictionary of curve features
  """
  # ... rest of the function ...
