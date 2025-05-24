from App.SDM.Analysis.statModel import statModel
from App.SDM.Skyn_Processors.ema_region import emaRegion
from App.SDM.Configuration.file_management import load, save_to_computer
from App.SDM.Documenting.embed_graphs import embed_graphs_into_workbook_tab
from App.SDM.Documenting.report_guide import report_guide
from App.SDM.Configuration.file_management import extract_subid
import os
import pandas as pd
import numpy as np
from scipy import stats
from scipy.signal import find_peaks

class curveFeatures():
  def __init__(self, processed_data_folder, smooth_and_impute_attrs=None, curve_attrs=None, subid=None, additional_processed_data_folders=[]):
    # Get list of processed files
    processed_files = [file for file in os.listdir(processed_data_folder) if 'processed' in file]
    
    # Filter files by subid if specified
    if subid is not None:
        processed_files = [file for file in processed_files if extract_subid(file) == str(subid)]
        if not processed_files:
            raise ValueError(f"No processed files found for subid {subid}")
    
    # Load only the filtered processors
    self.processors = [load(file[:-4], processed_data_folder) for file in processed_files]
    self.processors = [processor for processor in self.processors if hasattr(processor, 'curve_features')]
    
    # Create a list of DataFrames with consistent columns
    dfs = []
    for processor in self.processors:
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
    for flag_col in flag_cols:
      flag_stats = stats.groupby_counts(flag_col, include_unique_flags=True)
      flag_stats = flag_stats.reset_index()
      flag_stats['Flag_Column'] = flag_col
      flag_stats_list.append(flag_stats)
    if flag_stats_list:
      combined_flag_stats = pd.concat(flag_stats_list, axis=0, ignore_index=True)
      # Only keep relevant columns (adjust as needed)
      keep_cols = [col for col in combined_flag_stats.columns if col in [
          'Value', 'Count', '%', 'Unique_Flag_Count', 'Unique_Flag_%', 'Flag_Column'
      ]]
      combined_flag_stats = combined_flag_stats[keep_cols]
      # Filter out rows where 'Unique_Flag_Count' is empty (removes counts of non-flagged curves, only keeping flag counts)
      combined_flag_stats = combined_flag_stats[combined_flag_stats['Unique_Flag_Count'].notna() & (combined_flag_stats['Unique_Flag_Count'] != '')]
      # Calculate % of total curves and rename column
      combined_flag_stats['% of Total Curves'] = (combined_flag_stats['Count'] / total_curves) * 100
      # Drop the old '%' column if it exists
      if '%' in combined_flag_stats.columns:
          combined_flag_stats = combined_flag_stats.drop(columns=['%'])
      # Sort by 'Count' descending
      combined_flag_stats = combined_flag_stats.sort_values(by='Count', ascending=False)
      # Set 'Flag_Column' as the index
      combined_flag_stats = combined_flag_stats.set_index('Flag_Column')
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

  def export_sorted_workbook(self, file_name, sort_column, ascending=True, smooth_and_impute_attrs=None, curve_attrs=None):
    """
    Export a workbook with features and curves sorted by a specified column.
    Includes all rows that are flagged (flag=1) for the corresponding flag column and 50 non-flagged rows
    that are closest to the flag threshold.
    
    Args:
        file_name (str): Name of the output Excel file
        sort_column (str): Name of the column to sort by
        ascending (bool): Whether to sort in ascending order (True) or descending order (False)
        smooth_and_impute_attrs (dict, optional): Smoothing and imputation attributes
        curve_attrs (dict, optional): Curve attributes
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
      
      # Find corresponding flag column
      # Remove _CURVE or _PERIPHERY suffix if present
      base_column = sort_column.replace('_CURVE', '').replace('_PERIPHERY', '')
      
      # Flexibly match any flag column containing the base_column
      flag_candidates = [col for col in sorted_features.columns if col.startswith('FLAG_') and base_column in col]
      flag_column = flag_candidates[0] if flag_candidates else None
      
      if flag_column:
          # Get flagged and non-flagged rows
          flagged = sorted_features[sorted_features[flag_column] == 1]
          non_flagged = sorted_features[sorted_features[flag_column] != 1]
          
          if len(flagged) > 0:
              # Determine if flag is for high or low values by comparing means
              flagged_mean = flagged[sort_column].mean()
              non_flagged_mean = non_flagged[sort_column].mean()
              is_high_flag = flagged_mean > non_flagged_mean
              
              # Get 50 closest non-flagged rows
              if is_high_flag:
                  # For high flags, take the highest 50 non-flagged values
                  closest_non_flagged = non_flagged.nlargest(50, sort_column)
              else:
                  # For low flags, take the lowest 50 non-flagged values
                  closest_non_flagged = non_flagged.nsmallest(50, sort_column)
              
              # Combine flagged and closest non-flagged rows
              selected_indices = sorted(set(flagged.index) | set(closest_non_flagged.index))
              sorted_features = sorted_features.loc[selected_indices]
      
      sorted_features.to_excel(writer, sheet_name='Features', index=False)
      
      # Split curves into valid and invalid based on CURVE_VALID
      valid_curves = sorted_features[sorted_features['CURVE_VALID'] == 1]
      invalid_curves = sorted_features[sorted_features['CURVE_VALID'] != 1]
      
      # Add visualization tabs for valid and invalid curves
      if not invalid_curves.empty:
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
