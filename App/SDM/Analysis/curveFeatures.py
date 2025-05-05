from App.SDM.Analysis.statModel import statModel
from App.SDM.Skyn_Processors.ema_region import emaRegion
from App.SDM.Configuration.file_management import load, save_to_computer
from App.SDM.Documenting.embed_graphs import embed_graphs_into_workbook_tab
from App.SDM.Documenting.report_guide import report_guide
from App.SDM.User_Interface.Utils.filename_tools import extract_subid
import os
import pandas as pd
import numpy as np
from scipy import stats
from scipy.signal import find_peaks

class curveFeatures():
  def __init__(self, processed_data_folder, smooth_and_impute_attrs=None, curve_attrs=None, subid=None):
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
    
    # Add multi-index header for valid curves
    valid_feature_stats.columns = pd.MultiIndex.from_product(
        [['Valid Curves'], valid_feature_stats.columns]
    )
    
    # Add multi-index header for invalid curves
    invalid_feature_stats.columns = pd.MultiIndex.from_product(
        [['Invalid Curves'], invalid_feature_stats.columns]
    )
    
    self.curve_stat_frames.append(valid_feature_stats)
    self.curve_stat_frames.append(invalid_feature_stats)

  def count_curve_flags(self):
    stats = statModel(self.curve_features)
    for flag_col in [col for col in self.curve_features.columns if 'FLAG' in col]:
      setattr(self, 'counts_' + flag_col, stats.groupby_counts(flag_col))
      self.curve_stat_frames.append(getattr(self, 'counts_' + flag_col))

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

  def run_stats(self):
    self.compute_tac_feature_stats()
    self.count_curve_flags()
    self.compute_person_level_stats()

  def export_workbook_curves(self, file_name, smooth_and_impute_attrs=None, curve_attrs=None):
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
        row_index += len(frame) + 2
      
      # Add features
      self.curve_features.to_excel(writer, sheet_name='Features', index=False)
      
      # Add person level stats
      self.person_level_stats.to_excel(writer, sheet_name='Person Level Stats', index=True)
      
      # Add visualization tabs

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
      self.compile_imputation_info().to_excel(writer, sheet_name='Imputations', index=False)
      
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
