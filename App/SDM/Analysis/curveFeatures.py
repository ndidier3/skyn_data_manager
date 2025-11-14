from App.SDM.Analysis.statModel import statModel
from App.SDM.Skyn_Processors.ema_region import emaRegion
from App.SDM.Configuration.file_management import load, save_to_computer
from App.SDM.Documenting.embed_graphs import embed_graphs_into_workbook_tab
from App.SDM.Documenting.report_guide import report_guide
from App.SDM.Configuration.file_management import extract_subid
from App.SDM.Visualization.quality import QualityVisualizer
from App.SDM.Analysis.featureFlagger import featureFlagger
from App.SDM.Run.default_settings.default_flag_settings import DEFAULT_FLAG_SELECTIONS
import os
import pandas as pd
import numpy as np

class curveFeatures():
  def __init__(self, processed_data_folder, smooth_and_impute_attrs=None, curve_attrs=None, subids=None, additional_processed_data_folders=[]):
    """
    Args:
      processed_data_folder (str): Path to the folder containing processed files.
      smooth_and_impute_attrs (dict, optional): Smoothing and imputation attributes.
      curve_attrs (dict, optional): Curve attributes.
      subids (list of str or int, optional): If provided, only load files for these subids.
      additional_processed_data_folders (list, optional): Additional folders to search for processed files.
    """
    # Get list of processed files (exclude hidden files)
    processed_files = [file for file in os.listdir(processed_data_folder) 
                      if 'processed' in file and not file.startswith('.')]
    
    # Filter files by subids if specified
    if subids is not None:
      subids_str = set(str(s) for s in subids)
      processed_files = [file for file in processed_files if extract_subid(file) in subids_str]
      if not processed_files:
        raise ValueError(f"No processed files found for subids {subids}")
    
    print(f"\nFound {len(processed_files)} processed files")
    
    # Load only the filtered processors
    self.processors = [load(file[:-4], processed_data_folder) for file in processed_files]
    self.processors = [processor for processor in self.processors if hasattr(processor, 'curve_features')]
    self.processors = [processor for processor in self.processors if len(processor.curve_features) > 0]
    self.no_curve_subids = [processor.subid for processor in self.processors if len(processor.curve_features) == 0]
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

    # Collect raw curve features if available
    raw_dfs = []
    for i, processor in enumerate(self.processors):
      if hasattr(processor, 'raw_curve_features'):
        raw_df = processor.raw_curve_features.copy()
        raw_dfs.append(raw_df)
    
    # Concatenate with consistent columns (or create empty DataFrame if none exist)
    if raw_dfs:
      self.raw_curve_features = pd.concat(raw_dfs, ignore_index=True)
    else:
      self.raw_curve_features = pd.DataFrame()
    
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

    validity_column = 'REGION_VALID' if 'REGION_VALID' in self.curve_features.columns else 'CURVE_VALID'
    self.curve_valid = self.curve_features[self.curve_features[validity_column] == 1]
    self.curve_invalid = self.curve_features[self.curve_features[validity_column] != 1]

    # Initialize quality visualizer
    self.quality_visualizer = QualityVisualizer()
  
  def apply_flag_analysis(self, export = False, output_dir = None, flag_settings = DEFAULT_FLAG_SELECTIONS):
    """
    Apply flag analysis to the curve features.
    """
    self.curve_features.drop(columns=[col for col in self.curve_features.columns if 'FLAG' in col], inplace=True)
    flag_analysis = featureFlagger(self.curve_features, flag_settings)
    flags_result = flag_analysis.run_flags_and_validation()
    self.curve_features = flag_analysis.ftrs
    validity_column = 'REGION_VALID' if 'REGION_VALID' in self.curve_features.columns else 'CURVE_VALID'
    self.curve_valid = self.curve_features[self.curve_features[validity_column] == 1]
    self.curve_invalid = self.curve_features[self.curve_features[validity_column] != 1]
    if export:
      flag_analysis.export_flag_analysis_workbooks(output_dir=output_dir, plot_columns=['smoothed_curve_plot', 'signal_processing_plot', 'device_removal_plot', 'signal_processing_plot_wide'])

  def compile_imputation_info(self):
    """Compile imputation information from all processors"""
    imputation_dfs = []
    for processor in self.processors:
      if hasattr(processor, 'imputation_info'):
        df = processor.imputation_info.copy()
        df['subid'] = processor.subid
        df['dataset_identifier'] = processor.dataset_identifier
        imputation_dfs.append(df)
    self.imputations = pd.concat(imputation_dfs, ignore_index=True) if imputation_dfs else pd.DataFrame()

  def compute_imputation_stats(self):
    """
    Compute statistics on low-quality intervals from the imputation info DataFrame and store as a single dict:
    - Number of intervals (rows)
    - Average length of intervals (region_length)
    - Percentage of intervals that were imputed (was_imputed)
    - For each reason_not_imputed (for was_imputed == False), add a key 'Not Imputed: <reason>' with its count
    Appends this dict to self.curve_stat_frames.
    """
    if not hasattr(self, 'imputations') or self.imputations is None or self.imputations.empty:
      self.compile_imputation_info()
    imputation_df = self.imputations
    stats = {
      'Number of Low-Quality Intervals': 0,
      'Average Interval Length (min)': float('nan'),
      'Median Interval Length (min)': float('nan'),
      'Percent Intervals Imputed': float('nan')
    }
    if not imputation_df.empty:
      stats['Number of Low-Quality Intervals'] = len(imputation_df)
      stats['Average Interval Length (min)'] = imputation_df['region_length'].mean()
      stats['Median Interval Length (min)'] = imputation_df['region_length'].median()
      stats['Percent Intervals Imputed'] = imputation_df['was_imputed'].mean() * 100
      not_imputed = imputation_df[imputation_df['was_imputed'] == False]
      reason_counts = not_imputed['reason_not_imputed'].value_counts(dropna=False).to_dict()
      for reason, count in reason_counts.items():
        stats[f'Not Imputed: {reason}'] = count
    # Create DataFrame with index
    self.curve_stat_frames.append(pd.DataFrame.from_dict(stats, orient='index', columns=['Value']))

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
      col for col in self.curve_features.columns if 'FLAG' in col
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
      # Only perform this filtering if the Unique_Flag_Count column exists
      if 'Unique_Flag_Count' in combined_flag_stats.columns:
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

  def compare_valid_invalid_tac_features(self):
    """
    Generates a DataFrame comparing TAC feature statistics for valid ('High Quality')
    and invalid ('Low Quality') curves.
    """
    if self.curve_valid.empty and self.curve_invalid.empty:
        print("No valid or invalid curves to compare.")
        return

    features_map = {
        'Area Under': 'auc_total_CURVE',
        'Peak Value': 'peak_CURVE',
        'Rise Rate': 'rise_rate_CURVE',
        'Fall Rate': 'fall_rate_CURVE'
    }

    results = []
    
    available_features = {name: col for name, col in features_map.items() if col in self.curve_features.columns}

    if not available_features:
        print("None of the specified TAC features for comparison are available in curve_features.")
        return

    # Process "High Quality" (valid) curves
    if not self.curve_valid.empty:
        valid_df = self.curve_valid[[col for col in available_features.values() if col in self.curve_valid.columns]]
        if not valid_df.empty:
            valid_stats = valid_df.agg(['count', 'mean', 'std', 'median', 'min', 'max'])
            for feature_name, feature_col in available_features.items():
                if feature_col in valid_stats.columns:
                    stats = valid_stats[feature_col]
                    n = stats['count']
                    se = stats['std'] / np.sqrt(n) if n > 0 else 0
                    results.append({
                        'Feature': feature_name,
                        'Curve_Quality': 'High Quality',
                        'N': int(n),
                        'Mean': stats['mean'],
                        'Std': stats['std'],
                        'SE': se,
                        'Median': stats['median'],
                        'Min': stats['min'],
                        'Max': stats['max']
                    })

    # Process "Low Quality" (invalid) curves
    if not self.curve_invalid.empty:
        invalid_df = self.curve_invalid[[col for col in available_features.values() if col in self.curve_invalid.columns]]
        if not invalid_df.empty:
            invalid_stats = invalid_df.agg(['count', 'mean', 'std', 'median', 'min', 'max'])
            for feature_name, feature_col in available_features.items():
                if feature_col in invalid_stats.columns:
                    stats = invalid_stats[feature_col]
                    n = stats['count']
                    se = stats['std'] / np.sqrt(n) if n > 0 else 0
                    results.append({
                        'Feature': feature_name,
                        'Curve_Quality': 'Low Quality',
                        'N': int(n),
                        'Mean': stats['mean'],
                        'Std': stats['std'],
                        'SE': se,
                        'Median': stats['median'],
                        'Min': stats['min'],
                        'Max': stats['max']
                    })

    if not results:
        return

    results_df = pd.DataFrame(results)
    
    results_df['Feature'] = pd.Categorical(results_df['Feature'], categories=available_features.keys(), ordered=True)
    results_df = results_df.sort_values(['Feature', 'Curve_Quality'])

    results_df = results_df.set_index(['Feature', 'Curve_Quality'])
    
    self.curve_stat_frames.append(results_df)

  def run_stats(self):
    self.compute_tac_feature_stats()
    self.count_curve_flags()
    self.compare_valid_invalid_tac_features()
    self.compute_person_level_stats()
    self.compute_person_level_stats_valid()
    self.compute_imputation_stats()

  def export_workbook_curves(self, file_name, include_plots=True, export_imputations=False, first_subid=None, last_subid=None, split_plots_by='validity'):
    """
    Export workbook with curve features and optional plots.
    
    Args:
      file_name (str): Path to output Excel file
      include_plots (bool): Whether to include visualization tabs
      export_imputations (bool): Whether to export imputation data
      first_subid (int, optional): First subid in range filter
      last_subid (int, optional): Last subid in range filter
      split_plots_by (str): How to split visualization tabs - 'validity' (Valid/Invalid) or 'drinking_pred' (Drinking/Non-Drinking)
    """
    # Filter data by subid range if specified
    filtered_features = self.curve_features
    if first_subid is not None and last_subid is not None:
      filtered_features = self.curve_features[
        (self.curve_features['subid'] >= first_subid) & 
        (self.curve_features['subid'] <= last_subid)
      ]
    
    # Sort by subid, dataset_id, curve_id for consistent ordering
    sort_columns = ['subid', 'dataset_id', 'curve_id']
    available_sort_columns = [col for col in sort_columns if col in filtered_features.columns]
    if available_sort_columns:
      filtered_features = filtered_features.sort_values(available_sort_columns)
    
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
      
      # Add features (filtered if subid range specified)
      filtered_features.to_excel(writer, sheet_name='Features', index=False)
      
      # Add person level stats
      if hasattr(self, 'person_level_stats'):
        self.person_level_stats.to_excel(writer, sheet_name='Person Level Stats', index=True)
      if hasattr(self, 'person_level_stats_valid'):
        self.person_level_stats_valid.to_excel(writer, sheet_name='Person Level Stats (Valid)', index=True)
      
      # Add visualization tabs
      if include_plots:
        if split_plots_by == 'drinking_pred' and 'DRINKING_PRED' in filtered_features.columns:
          # Split by drinking prediction
          drinking_curves = filtered_features[filtered_features['DRINKING_PRED'] == 1]
          non_drinking_curves = filtered_features[filtered_features['DRINKING_PRED'] == 0]
          
          if not non_drinking_curves.empty:
            embed_graphs_into_workbook_tab(
              writer.book,
              [
                non_drinking_curves['device_removal_plot'].tolist(),
                non_drinking_curves['signal_processing_plot'].tolist(),
                non_drinking_curves['signal_processing_plot_wide'].tolist()
              ],
              worksheet_name = 'Non-Drinking Curves',
              plot_header_text = '',
              missing_plot_path_text = 'No Plot Available'
            )
          
          if not drinking_curves.empty:
            embed_graphs_into_workbook_tab(
              writer.book,
              [
                drinking_curves['device_removal_plot'].tolist(),
                drinking_curves['signal_processing_plot'].tolist(),
                drinking_curves['signal_processing_plot_wide'].tolist()
              ],
              worksheet_name = 'Drinking Curves',
              plot_header_text = '',
              missing_plot_path_text = 'No Plot Available'
            )
        else:
          # Split by validity (default)
          # Filter invalid curves by subid range if specified
          filtered_invalid = self.curve_invalid
          if first_subid is not None and last_subid is not None:
            filtered_invalid = self.curve_invalid[
              (self.curve_invalid['subid'] >= first_subid) & 
              (self.curve_invalid['subid'] <= last_subid)
            ]
          
          if not filtered_invalid.empty:
            embed_graphs_into_workbook_tab(
              writer.book,
              [
                filtered_invalid['device_removal_plot'].tolist(),
                filtered_invalid['signal_processing_plot'].tolist(),
                filtered_invalid['signal_processing_plot_wide'].tolist()
              ],
              worksheet_name = 'Invalid Curves',
              plot_header_text = '',
              missing_plot_path_text = 'No Plot Available'
            )

          # Filter valid curves by subid range if specified
          filtered_valid = self.curve_valid
          if first_subid is not None and last_subid is not None:
            filtered_valid = self.curve_valid[
              (self.curve_valid['subid'] >= first_subid) & 
              (self.curve_valid['subid'] <= last_subid)
            ]
          
          if not filtered_valid.empty:
            embed_graphs_into_workbook_tab(
              writer.book,
              [
                filtered_valid['device_removal_plot'].tolist(),
                filtered_valid['signal_processing_plot'].tolist(),
                filtered_valid['signal_processing_plot_wide'].tolist()
              ],
              worksheet_name = 'Valid Curves',
              plot_header_text = '',
              missing_plot_path_text = 'No Plot Available'
            )
      
      # Add imputations
      if export_imputations:
        if not hasattr(self, 'imputations'):
          self.compile_imputation_info()
        self.imputations.to_excel(writer, sheet_name='Imputations', index=False)
      
      # Add run settings
      run_settings_df = report_guide.get_run_settings_dataframe(
        smooth_and_impute_attrs=self.smooth_and_impute_attrs,
        curve_attrs=self.curve_attrs
      )
      if run_settings_df is not None:
        run_settings_df.to_excel(writer, sheet_name='Run Settings', index=False)

  def export_sorted_workbook(self, file_name, sort_column, ascending=True, smooth_and_impute_attrs=None, curve_attrs=None, flag_prefix=None, split_plots_by='validity'):
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
      split_plots_by (str): How to split visualization tabs - 'validity' (Valid/Invalid) or 'drinking_pred' (Drinking/Non-Drinking)
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
      
      # Sort features by specified column, then by subid, dataset_id, curve_id for consistent ordering
      sort_columns = [sort_column, 'subid', 'dataset_id', 'curve_id']
      available_sort_columns = [col for col in sort_columns if col in self.curve_features.columns]
      sorted_features = self.curve_features.sort_values(available_sort_columns, ascending=[ascending] + [True] * (len(available_sort_columns) - 1))
      
      # Use provided flag prefix if available, otherwise try to find it
      if flag_prefix and flag_prefix in sorted_features.columns:
        flag_column = flag_prefix
      else:
        # Find corresponding flag column
        # Remove _CURVE, _PERIPHERY_BEFORE, _PERIPHERY_AFTER, or _PERIPHERY suffix if present
        base_column = sort_column.replace('_CURVE', '').replace('_PERIPHERY_BEFORE', '').replace('_PERIPHERY_AFTER', '').replace('_PERIPHERY', '')
        
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
      
      # Add visualization tabs - split by drinking_pred or validity
      if split_plots_by == 'drinking_pred' and 'DRINKING_PRED' in sorted_features.columns:
        # Split by drinking prediction
        drinking_curves = sorted_features[sorted_features['DRINKING_PRED'] == 1]
        non_drinking_curves = sorted_features[sorted_features['DRINKING_PRED'] == 0]
        
        if not non_drinking_curves.empty:
          embed_graphs_into_workbook_tab(
            writer.book,
            [
              non_drinking_curves['device_removal_plot'].tolist(),
              non_drinking_curves['signal_processing_plot'].tolist(),
              non_drinking_curves['signal_processing_plot_wide'].tolist()
            ],
            worksheet_name='Non-Drinking Curves',
            plot_header_text='',
            missing_plot_path_text='No Plot Available'
          )
        
        if not drinking_curves.empty:
          embed_graphs_into_workbook_tab(
            writer.book,
            [
              drinking_curves['device_removal_plot'].tolist(),
              drinking_curves['signal_processing_plot'].tolist(),
              drinking_curves['signal_processing_plot_wide'].tolist()
            ],
            worksheet_name='Drinking Curves',
            plot_header_text='',
            missing_plot_path_text='No Plot Available'
          )
      else:
        # Split by validity (default)
        validity_column = 'REGION_VALID' if 'REGION_VALID' in sorted_features.columns else 'CURVE_VALID'
        valid_curves = sorted_features[sorted_features[validity_column] == 1]
        invalid_curves = sorted_features[sorted_features[validity_column] != 1]
        
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

  def identify_drinking_curves(self):
    """
    Identify curves likely to represent actual drinking events based on data quality and shape.
    Sets a 'DRINKING_PRED' column to 1 for curves that meet all criteria:
    - high_quality_duration_CURVE > required_HQ_duration (dynamic requirement based on curve length)
    - FLAG_flat_curve == 0 (not flagged as flat)
    - FLAG_incomplete_curve_start_curve == 0 (has complete rise phase) - ONLY for curves < 1 hour
    
    The incomplete rise flag is only applied to short curves (< 1 hour) because longer curves
    may have legitimate reasons for short rise phases that don't indicate poor quality.
    
    Required HQ duration uses a two-phase algorithm:
    - Phase 1 (30-60 min): 9 non-HQ minutes allowed per 15-minute block (strict for short curves)
    - Phase 2 (60+ min): Only 5 additional HQ minutes required per 15-minute block (more lenient for long curves)
    
    Creates helper column:
    - required_HQ_duration: Absolute hours of HQ data required based on two-phase algorithm
    
    Returns:
        None (modifies self.curve_features in place)
    """
    # Initialize DRINKING_PRED column to 0
    self.curve_features['DRINKING_PRED'] = 0
    
    # Compute required high quality duration using two-phase algorithm
    def compute_required_hq(duration_hours):
      duration_min = duration_hours * 60
      
      # Phase 1: <= 30 minutes requires 100% HQ
      if duration_min <= 30:
        return duration_hours
      
      # Phase 2: 30-60 minutes (9 non-HQ allowed per 15-min block)
      elif duration_min <= 60:
        n_blocks = int((duration_min - 30) / 15)
        non_hq_allowed_min = 9 * n_blocks
        hq_required_min = duration_min - non_hq_allowed_min
        return hq_required_min / 60  # Convert to hours
      
      # Phase 3: > 60 minutes (5 additional HQ minutes per 15-min block)
      else:
        base_hq_min = 42  # HQ required at 60 minutes
        n_blocks_beyond_60 = int((duration_min - 60) / 15)
        hq_required_min = base_hq_min + (5 * n_blocks_beyond_60)
        return hq_required_min / 60  # Convert to hours
    
    self.curve_features['required_HQ_duration'] = (
      self.curve_features['duration_CURVE'].apply(compute_required_hq)
    )
    
    # Identify curves meeting drinking prediction criteria
    # Base: high-quality duration threshold + not flat
    # Rise phase: only required for curves < 1 hour
    drinking_mask = (
      (self.curve_features['high_quality_duration_CURVE'] > self.curve_features['required_HQ_duration']) &
      (self.curve_features['FLAG_below_threshold_curve'] == 0) &
      (
        (self.curve_features['duration_CURVE'] >= 1.0) | 
        (self.curve_features['FLAG_incomplete_curve_start_curve'] == 0)
      )
    )
    
    self.curve_features.loc[drinking_mask, 'DRINKING_PRED'] = 1

  def identify_perfect_curves(self, output_dir):
    """
    Identify curves that have no low quality data in either periphery or curve regions.
    Sets a 'perfect' column to 1 for curves that meet these criteria:
    - No low quality data in periphery before and after (low_quality_percent_PERIPHERY_BEFORE = 0 and low_quality_percent_PERIPHERY_AFTER = 0)
    - No low quality data in curve (low_quality_percent_CURVE = 0)
    """
    # Initialize perfect column to 0
    self.curve_features['perfect'] = 0
    
    # Calculate combined non-wear and gap features for each region type
    region_types = ['CURVE', 'PERIPHERY_BEFORE', 'PERIPHERY_AFTER', 'REGION']
    for region in region_types:
        # Calculate combined percent features
        self.curve_features[f'total_non_wear_gap_percent_{region}'] = (
            self.curve_features[f'total_gap_percent_{region}'] + 
            self.curve_features[f'total_non_wear_percent_{region}']
        )
        
        # Calculate combined duration features
        self.curve_features[f'total_non_wear_gap_duration_{region}'] = (
            self.curve_features[f'total_gap_duration_{region}'] + 
            self.curve_features[f'total_non_wear_duration_{region}']
        )
        
        if self.raw_curve_features is not None:
          # Calculate same features for raw data
          self.raw_curve_features[f'total_non_wear_gap_percent_{region}'] = (
              self.raw_curve_features[f'total_gap_percent_{region}'] + 
              self.raw_curve_features[f'total_non_wear_percent_{region}']
          )
          
          self.raw_curve_features[f'total_non_wear_gap_duration_{region}'] = (
              self.raw_curve_features[f'total_gap_duration_{region}'] + 
              self.raw_curve_features[f'total_non_wear_duration_{region}']
          )
    
    # Set perfect to 1 where both periphery and curve have no low quality data
    perfect_mask = (
      (self.curve_features['total_low_quality_duration_REGION'] == 0)
    )
    self.curve_features.loc[perfect_mask, 'perfect'] = 1

    self.curve_features.to_excel(f'{output_dir}/curve_features.xlsx', index=False)
    if self.raw_curve_features is not None:
        self.raw_curve_features.to_excel(f'{output_dir}/raw_curve_features.xlsx', index=False)
    # Print summary
    total_curves = len(self.curve_features)
    perfect_curves = perfect_mask.sum()
    print(f"Found {perfect_curves} perfect curves out of {total_curves} total curves ({perfect_curves/total_curves*100:.1f}%)")

    # Get the list of plot paths for these curves
    plot_paths = self.curve_features[self.curve_features['perfect'] == 1]['signal_processing_plot_wide'].dropna().tolist()

  def run_density_plots(self, output_filename='tac_density_distributions.png', show_legend=False):
    """
    Generate TAC feature density plots using QualityVisualizer.
    Args:
        output_filename (str): Filename for the output plot.
        show_legend (bool): Whether to display legends on the plots.
    """
    print(f"Generating TAC density plots. Output file: {output_filename}")
    self.quality_visualizer.create_tac_density_plots(
        self.curve_features,
        output_filename=output_filename,
        show_legend=show_legend
    )
  
  def run_violin_plots(self, output_filename='tac_violin_plots.png', show_legend=False):
    """
    Generate TAC feature violin plots using QualityVisualizer.
    Args:
        output_filename (str): Filename for the output plot.
        show_legend (bool): Whether to display legends on the plots.
    """ 
    self.quality_visualizer.create_tac_violin_plots(
        self.curve_features,
        output_filename=output_filename,
        show_legend=show_legend
    )
