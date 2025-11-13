from App.SDM.Analysis.statModel import statModel, compare_correlation_strengths
from App.SDM.Analysis.curveFeatures import curveFeatures
from App.SDM.Skyn_Processors.ema_region import emaRegion
from App.SDM.Configuration.file_management import load, save_to_computer
from App.SDM.Documenting.embed_graphs import embed_graphs_into_workbook_tab
from App.SDM.Documenting.report_guide import report_guide
from App.SDM.Visualization.quality import QualityVisualizer

import pandas as pd
import os
import numpy as np

class curveFeaturesWithEvents(curveFeatures):
  def __init__(self, processed_data_folder, smooth_and_impute_attrs=None, curve_attrs=None, event_attrs=None, day_attrs=None, subids=None):
    super().__init__(processed_data_folder, smooth_and_impute_attrs, curve_attrs, subids)
    
    # Filter processors to only include those with both curve features and events
    self.processors = [processor for processor in self.processors 
                      if hasattr(processor, 'event_labels') and 
                      hasattr(processor, 'curve_features') and 
                      len(processor.curve_features) > 0 and
                      hasattr(processor, 'events') and 
                      isinstance(processor.events, pd.DataFrame) and 
                      len(processor.events) > 0]
    
    print(f"Filtered to {len(self.processors)} processors with both curve features and events")
    
    # Collect events from processors
    events_list = []
    for processor in self.processors:
        if hasattr(processor, 'events') and isinstance(processor.events, pd.DataFrame):
            events_list.append(processor.events.reset_index(drop=True))
    
    if events_list:
        # Standardize columns across all DataFrames
        all_columns = set()
        for df in events_list:
            all_columns.update(df.columns)
        all_columns = sorted(list(all_columns))
        
        # Ensure all DataFrames have the same columns
        for df in events_list:
            for col in all_columns:
                if col not in df.columns:
                    df[col] = pd.NA
            df.reindex(columns=all_columns)
        
        # Concatenate with standardized columns
        self.event_data = pd.concat(events_list, ignore_index=True)
    else:
        self.event_data = pd.DataFrame()
    self.event_stat_frames = []
    self.ema_region_columns = [col for col in self.event_data if 'EMA_REGION' in col]
    self.event_type_column = ''
    self.event_type_settings = {}

    # Optional configuration dictionaries
    self.event_attrs = event_attrs
    self.day_attrs = day_attrs

    # Find drink total column
    self.drink_total_column = None
    if not self.event_data.empty:
        for col in self.event_data.columns:
            # More specific search for drink total column
            if ('drink' in col.lower() and 'total' in col.lower()) or 'totsd' in col.lower():
                self.drink_total_column = col
                break

    self.default_tac_features = report_guide.stats_features

    # Convert ID to integer and ema_id to string for consistent data types
    self.event_data['ID'] = self.event_data['ID'].astype(int)
    self.event_data['ema_id'] = self.event_data['ema_id'].astype(str)
    self.event_data.drop(columns=['subid'], inplace=True, errors='ignore')    
                        
    # Split events into matched and unmatched
    self.matched_events = self.event_data[self.event_data['matched']==1]
    self.unmatched_events = self.event_data[self.event_data['matched']!=1]

  def set_datasets_by_valid_and_match(self):
    validity_column = 'REGION_VALID' if 'REGION_VALID' in self.curve_features.columns else 'CURVE_VALID'
    valid = (self.curve_features[validity_column] == 1)
    invalid = (self.curve_features[validity_column] != 1)
    event_found = (self.curve_features['event_matched_1'].notna())
    event_not_found = (self.curve_features['event_matched_1'].isna())

    self.curve_with_event = self.curve_features[event_found]
    self.curve_without_event = self.curve_features[event_not_found]
    self.curve_valid_with_event = self.curve_features[valid & event_found]
    self.curve_invalid_with_event = self.curve_features[invalid & event_found]
    self.curve_valid_without_event = self.curve_features[valid & event_not_found]
    self.curve_invalid_without_event = self.curve_features[invalid & event_not_found]
    
    # Add drinking prediction splits for curves with events
    if 'DRINKING_PRED' in self.curve_features.columns:
      drinking = (self.curve_features['DRINKING_PRED'] == 1)
      non_drinking = (self.curve_features['DRINKING_PRED'] == 0)
      
      self.curve_drinking_with_event = self.curve_features[drinking & event_found]
      self.curve_non_drinking_with_event = self.curve_features[non_drinking & event_found]

  def count_matches(self):
    # Basic counts
    self.counts = {
      'Curves': [len(self.curve_features)],
      'Curves Valid': [len(self.curve_valid)],
      'Curves Invalid': [len(self.curve_invalid)],
      'Curves with Event Match': [len(self.curve_with_event)],
      'Curves (Valid) with Event Match': [len(self.curve_valid_with_event)],
      'Curves (Invalid) with Event Match': [len(self.curve_invalid_with_event)],
      'Events': [self.event_data[['ema_id', 'ID']].drop_duplicates().shape[0]],
      'Events NOT matched to a Curve': [self.unmatched_events[['ema_id', 'ID']].drop_duplicates().shape[0]],
      'Events matched to a Curve': [self.matched_events[['ema_id', 'ID']].drop_duplicates().shape[0]],
      'Events matched to a Valid Curve': [self.matched_events[self.matched_events['valid_curve_match_1'].notna()][['ema_id', 'ID']].drop_duplicates().shape[0]],
      'Events matched to an Invalid Curve': [self.matched_events[self.matched_events['invalid_curve_match_1'].notna()][['ema_id', 'ID']].drop_duplicates().shape[0]],
      'Events matched to Multiple Curves': [
          self.event_data[(self.event_data['num_valid_curves_matched'] + self.event_data['num_invalid_curves_matched']) > 1][['ema_id', 'ID']].drop_duplicates().shape[0]
      ],
      'Events matched to Multiple Curves (Valid Only)': [
          self.event_data[self.event_data['multiple_valid_curves_matched']][['ema_id', 'ID']].drop_duplicates().shape[0]
      ],
      'Events matched to Multiple Curves (Invalid Only)': [
          self.event_data[self.event_data['multiple_invalid_curves_matched']][['ema_id', 'ID']].drop_duplicates().shape[0]
      ],
      'Events matched to Multiple Curves (Mixed Valid/Invalid)': [
          self.event_data[self.event_data['multiple_mixed_curves_matched']][['ema_id', 'ID']].drop_duplicates().shape[0]
      ],
      'Events with a Shared Curve (Valid Only)': [self.event_data[self.event_data['has_shared_match']][['ema_id', 'ID']].drop_duplicates().shape[0]],
      'Events with a Shared Curve (First Match Only, Valid Only)': [self.event_data[self.event_data['has_shared_first_match']][['ema_id', 'ID']].drop_duplicates().shape[0]]
    }
    
    # Add drinking prediction counts if available
    if hasattr(self, 'curve_drinking_with_event'):
      self.counts.update({
        'Curves (Drinking Predicted) with Event Match': [len(self.curve_drinking_with_event)],
        'Curves (Non-Drinking Predicted) with Event Match': [len(self.curve_non_drinking_with_event)]
      })

    # Get counts by event type
    # for event_type in self.event_data['eventuse_merged'].unique():
    #   if pd.isna(event_type):
    #     continue
        
    #   type_events = self.event_data[self.event_data['eventuse_merged'] == event_type]
    #   matched_curves = self.curve_features[
    #     (self.curve_features['event_matched_1'].isin(type_events['ema_id'])) &
    #     (self.curve_features['subid'].isin(type_events['ID']))
    #   ]
      
    #   valid_curves = matched_curves[matched_curves['CURVE_VALID'] == 1]
    #   invalid_curves = matched_curves[matched_curves['CURVE_VALID'] != 1]
      
    #   self.counts.update({
    #     f'{event_type} Events': [len(type_events)],
    #     f'{event_type} Valid Curves': [len(valid_curves)],
    #     f'{event_type} Invalid Curves': [len(invalid_curves)]
    #   })

    self.event_stat_frames.insert(0, pd.DataFrame(self.counts))

    self.participant_info = {
      'N Participants': [len(self.curve_features['subid'].unique())],
      'N Participants (with valid curves)': [len(self.curve_valid['subid'].unique())],
      'Average Curves Per Person': [len(self.curve_features) / len(self.curve_features['subid'].unique())],
      'Average Valid Curves Per Person': [len(self.curve_valid) / len(self.curve_valid['subid'].unique())],
      'Average Invalid Curves Per Person': [len(self.curve_invalid) / len(self.curve_invalid['subid'].unique())],
      'N Participants (with valid curves and event match)': [len(self.curve_valid_with_event['subid'].unique())],
    }
    self.event_stat_frames.insert(1, pd.DataFrame(self.participant_info))

  def count_flags_for_curves_with_events(self):
    stats = statModel(self.curve_with_event)
    flag_cols = [col for col in self.curve_with_event.columns if 'FLAG' in col]
    flag_stats_list = []
    total_curves = len(self.curve_with_event)
    
    # Create a DataFrame with just the flag columns for easier comparison
    flag_df = self.curve_with_event[flag_cols].copy()
    
    # Define the desired order of flags
    desired_flag_order = [
        col for col in self.curve_with_event.columns if 'FLAG' in col
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
      # Only keep relevant columns
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
      
      self.event_stat_frames.append(combined_flag_stats)
  
  def assess_search_quality(self):
    
    for df in [self.matched_events, self.unmatched_events]:
      df_filtered = df.drop_duplicates(subset=['ID']+self.ema_region_columns)  
      stat_model = statModel(df_filtered)
      results = stat_model.continuous_stats_for_columns([col for col in self.ema_region_columns if 'plot' not in col])
      
      # Add multi-index header based on whether these are matched or unmatched events
      header = 'Matched Events' if df is self.matched_events else 'Unmatched Events'
      results.columns = pd.MultiIndex.from_product(
          [[header], results.columns]
      )
      
      self.event_stat_frames.append(results)
  
  def compute_tac_feature_stats_for_matched_curves(self):
    """
    Compute TAC feature statistics for curves that have matched events.
    Only includes curves that have at least one event match.
    """
    print(f"Shape of curve_valid_with_event: {self.curve_valid_with_event.shape}")
    if self.curve_valid_with_event.empty:
        print("No valid curves with events found")
        return
        
    valid = statModel(self.curve_valid_with_event)
    invalid = statModel(self.curve_invalid_with_event)
    valid_feature_stats = valid.continuous_stats_for_columns(self.default_tac_features)
    invalid_feature_stats = invalid.continuous_stats_for_columns(self.default_tac_features)
    
    # Add multi-index header for valid curves with events
    valid_feature_stats.columns = pd.MultiIndex.from_product(
        [['Valid Curves with Events'], valid_feature_stats.columns]
    )
    
    # Add multi-index header for invalid curves with events
    invalid_feature_stats.columns = pd.MultiIndex.from_product(
        [['Invalid Curves with Events'], invalid_feature_stats.columns]
    )
    
    self.event_stat_frames.append(valid_feature_stats)
    self.event_stat_frames.append(invalid_feature_stats)

  def compute_person_level_stats(self):
    """
    Compute person-level statistics for valid curves with event matches.
    Adds the results to event_stat_frames.
    """    
    # Add any flag columns as categorical
    for col in self.curve_valid_with_event.columns:
      if 'FLAG' in col:
        self.person_level_dtypes[col] = 'categorical'
    
    # Compute person-level stats for valid curves with matches
    stats = statModel(self.curve_valid_with_event)
    person_stats = stats.get_subid_level_stats(self.person_level_dtypes)
    
    # Store the person-level stats as an attribute
    self.valid_matched_person_stats = person_stats

  def compute_tac_feature_drink_correlations(self):
    """
    Compute Pearson correlations between TAC features and drink total for valid vs invalid matched curves.
    Creates a DataFrame comparing correlations across the two groups and adds it to event_stat_frames.
    Also includes means and standard deviations of self-reported drinks by valid vs invalid curves.
    """
    # Define the TAC features to analyze
    tac_features = ['auc_total_CURVE', 'peak_CURVE', 'rise_rate_CURVE', 'fall_rate_CURVE']
    
    # Filter to only include features that exist in the data
    available_features = [feat for feat in tac_features if feat in self.curve_features.columns]
    
    if not available_features:
        print("No TAC features found in the data for correlation analysis")
        return
    
    # Use the drink total column found during initialization
    drink_total_col = self.drink_total_column
    
    if drink_total_col is None:
        print("No drink total column found in the event data for correlation analysis")
        return

    # Create a mapping from event to drink total
    drink_map = self.matched_events[['ID', 'ema_id', self.drink_total_column]].copy()
    drink_map.drop_duplicates(subset=['ID', 'ema_id'], inplace=True)
    drink_map[self.drink_total_column] = pd.to_numeric(drink_map[self.drink_total_column], errors='coerce')
    
    # Initialize results dictionary
    correlation_results = {}
    drink_stats = {}
    
    # Compute correlations and drink statistics for valid curves with events
    if not self.curve_valid_with_event.empty:
        valid_data = self.curve_valid_with_event.merge(
            drink_map,
            left_on=['subid', 'event_matched_1'],
            right_on=['ID', 'ema_id'],
            how='left'
        ).dropna(subset=available_features + [drink_total_col])

        if len(valid_data) > 1:
            valid_corr = valid_data[available_features].corrwith(valid_data[drink_total_col], method='pearson')
            correlation_results['Valid Curves with Events'] = valid_corr
            
            # Calculate drink statistics for valid curves
            drink_stats['Valid Curves with Events'] = {
                'mean': valid_data[drink_total_col].mean(),
                'std': valid_data[drink_total_col].std(),
                'n': len(valid_data)
            }
        else:
            print("Insufficient data for valid curves correlation analysis")
            return
    else:
        print("No valid curves with events found for correlation analysis")
        return
    
    # Compute correlations and drink statistics for invalid curves with events
    if not self.curve_invalid_with_event.empty:
        invalid_data = self.curve_invalid_with_event.merge(
            drink_map,
            left_on=['subid', 'event_matched_1'],
            right_on=['ID', 'ema_id'],
            how='left'
        ).dropna(subset=available_features + [drink_total_col])
        
        if len(invalid_data) > 1:
            invalid_corr = invalid_data[available_features].corrwith(invalid_data[drink_total_col], method='pearson')
            correlation_results['Invalid Curves with Events'] = invalid_corr
            
            # Calculate drink statistics for invalid curves
            drink_stats['Invalid Curves with Events'] = {
                'mean': invalid_data[drink_total_col].mean(),
                'std': invalid_data[drink_total_col].std(),
                'n': len(invalid_data)
            }
        else:
            print("Insufficient data for invalid curves correlation analysis")
            return
    else:
        print("No invalid curves with events found for correlation analysis")
        return
    
    # Calculate sample sizes
    valid_n = len(self.curve_valid_with_event.merge(drink_map, left_on=['subid', 'event_matched_1'], right_on=['ID', 'ema_id'], how='left').dropna(subset=available_features + [drink_total_col]))
    invalid_n = len(self.curve_invalid_with_event.merge(drink_map, left_on=['subid', 'event_matched_1'], right_on=['ID', 'ema_id'], how='left').dropna(subset=available_features + [drink_total_col]))
    
    comparison_data = []
    
    for feature in available_features:
        valid_corr_val = correlation_results['Valid Curves with Events'].get(feature, np.nan)
        invalid_corr_val = correlation_results['Invalid Curves with Events'].get(feature, np.nan)
        
        # Calculate difference
        corr_diff = valid_corr_val - invalid_corr_val
        
        # Perform Fisher's z-test
        p_value = compare_correlation_strengths(valid_corr_val, valid_n, invalid_corr_val, invalid_n)

        comparison_data.append({
            'TAC Feature': feature,
            'Valid Curves Correlation': valid_corr_val,
            'Invalid Curves Correlation': invalid_corr_val,
            'Correlation Difference (Valid - Invalid)': corr_diff,
            'p-value (Difference)': p_value
        })
    
    # Create DataFrame and add sample sizes
    correlation_df = pd.DataFrame(comparison_data)

    sample_size_info = pd.DataFrame([{
        'TAC Feature': 'Sample Size',
        'Valid Curves Correlation': valid_n,
        'Invalid Curves Correlation': invalid_n,
        'Correlation Difference (Valid - Invalid)': np.nan,
        'p-value (Difference)': np.nan
    }])
    
    # Add drink statistics
    drink_stats_info = pd.DataFrame([{
        'TAC Feature': 'Drink Total Mean',
        'Valid Curves Correlation': drink_stats['Valid Curves with Events']['mean'],
        'Invalid Curves Correlation': drink_stats['Invalid Curves with Events']['mean'],
        'Correlation Difference (Valid - Invalid)': drink_stats['Valid Curves with Events']['mean'] - drink_stats['Invalid Curves with Events']['mean'],
        'p-value (Difference)': np.nan
    }, {
        'TAC Feature': 'Drink Total Std',
        'Valid Curves Correlation': drink_stats['Valid Curves with Events']['std'],
        'Invalid Curves Correlation': drink_stats['Invalid Curves with Events']['std'],
        'Correlation Difference (Valid - Invalid)': drink_stats['Valid Curves with Events']['std'] - drink_stats['Invalid Curves with Events']['std'],
        'p-value (Difference)': np.nan
    }])
    
    # Combine correlation results with sample size and drink statistics info
    final_results = pd.concat([sample_size_info, drink_stats_info, correlation_df], ignore_index=True)
    
    print("\n--- TAC Feature vs Drink Total Correlations ---")
    print(final_results.to_string())

    # Add to event_stat_frames
    self.event_stat_frames.append(final_results)

  def compare_valid_invalid_tac_features(self):
    """
    Generates a DataFrame comparing TAC feature statistics for valid ('High Quality')
    and invalid ('Low Quality') curves that have matched events.
    """
    if self.curve_valid_with_event.empty and self.curve_invalid_with_event.empty:
        print("No valid or invalid curves with events to compare.")
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
    if not self.curve_valid_with_event.empty:
        valid_df = self.curve_valid_with_event[[col for col in available_features.values() if col in self.curve_valid_with_event.columns]]
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
    if not self.curve_invalid_with_event.empty:
        invalid_df = self.curve_invalid_with_event[[col for col in available_features.values() if col in self.curve_invalid_with_event.columns]]
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
    
    self.event_stat_frames.append(results_df)

  def run_event_stats(self):
    self.count_matches()
    self.count_curve_flags()
    self.count_flags_for_curves_with_events()
    self.compute_tac_feature_stats_for_matched_curves()
    self.assess_search_quality()
    self.compute_person_level_stats()
    self.compute_tac_feature_drink_correlations()
    self.compare_valid_invalid_tac_features()

  def export_workbook_events_and_curves(self, file_name, smooth_and_impute_attrs=None, curve_attrs=None, event_attrs=None, day_attrs=None, export_plots=False, split_plots_by='validity'):
    """
    Export workbook with events, curves, and optional plots.
    
    Args:
      file_name (str): Path to output Excel file
      smooth_and_impute_attrs (dict, optional): Smoothing and imputation attributes
      curve_attrs (dict, optional): Curve attributes
      event_attrs (dict, optional): Event attributes
      day_attrs (dict, optional): Day attributes
      export_plots (bool): Whether to include visualization tabs
      split_plots_by (str): How to split visualization tabs - 'validity' (Valid/Invalid) or 'drinking_pred' (Drinking/Non-Drinking)
    
    Note:
      To use split_plots_by='drinking_pred', you must call set_datasets_by_valid_and_match() first.
      Only curves matched to self-report events will be included in the drinking/non-drinking tabs.
    """
    with pd.ExcelWriter(file_name, engine = 'xlsxwriter', mode = 'w') as writer:
      # Add tab descriptions
      report_guide.get_tab_descriptions_dataframe(include_events=True).to_excel(writer, sheet_name='Tab Descriptions', index=False)
      
      # Add variable key
      row_index = 0
      for name, df in report_guide.get_variable_key_dataframes():
          df.to_excel(writer, sheet_name='Variable Key', startrow=row_index)
          row_index += len(df) + 3  # Add 3 rows of spacing
      
      # Add stats
      row_index = 0
      for i, frame in enumerate(self.curve_stat_frames):
        frame.to_excel(writer, sheet_name='STATS', startrow=row_index)
        row_index += len(frame) + 2
      
      for i, frame in enumerate(self.event_stat_frames):
        frame.to_excel(writer, sheet_name='STATS', startrow=row_index)
        row_index += len(frame) + 2
      
      # Add features
      self.curve_features.to_excel(writer, sheet_name='Features', index=False)
      
      # Add events - reorder columns according to event_feature_descriptions
      # Get ordered columns from event_feature_descriptions that exist in event_data
      ordered_columns = [col for col in report_guide.event_feature_descriptions.keys() if col in self.event_data.columns]
      # Get remaining columns that aren't in event_feature_descriptions
      other_columns = [col for col in self.event_data.columns if col not in report_guide.event_feature_descriptions.keys()]
      # Combine ordered columns with remaining columns
      event_columns = ordered_columns + other_columns
      self.event_data[event_columns].to_excel(writer, sheet_name='Events', index=False)
      
      # Add valid matched by subid
      self.valid_matched_person_stats.to_excel(writer, sheet_name='Valid Matched by SubID', index=True)
      
      if export_plots:
        # Add visualization tabs
        if split_plots_by == 'drinking_pred' and hasattr(self, 'curve_drinking_with_event'):
          # Split by drinking prediction (curves matched to events)
          if not self.curve_non_drinking_with_event.empty:
            embed_graphs_into_workbook_tab(
              writer.book,
              [
                self.curve_non_drinking_with_event['device_removal_plot'].tolist(),
                self.curve_non_drinking_with_event['signal_processing_plot'].tolist(),
                self.curve_non_drinking_with_event['signal_processing_plot_wide'].tolist()
              ],
              worksheet_name = 'Non-Drinking Matched',
              plot_header_text = '',
              missing_plot_path_text = 'No Plot Available'
            )
          
          if not self.curve_drinking_with_event.empty:
            embed_graphs_into_workbook_tab(
              writer.book,
              [
                self.curve_drinking_with_event['device_removal_plot'].tolist(),
                self.curve_drinking_with_event['signal_processing_plot'].tolist(),
                self.curve_drinking_with_event['signal_processing_plot_wide'].tolist()
              ],
              worksheet_name = 'Drinking Matched',
              plot_header_text = '',
              missing_plot_path_text = 'No Plot Available'
            )
        else:
          # Split by validity (default)
          embed_graphs_into_workbook_tab(
            writer.book,
            [
              self.curve_valid_with_event['device_removal_plot'].tolist(),
              self.curve_valid_with_event['signal_processing_plot'].tolist(),
              self.curve_valid_with_event['signal_processing_plot_wide'].tolist()
            ],
            worksheet_name = 'Valid MatchedCurves',
            plot_header_text = '',
            missing_plot_path_text = 'No Plot Available'
          )

          embed_graphs_into_workbook_tab(
            writer.book,
            [
              self.curve_invalid_with_event['device_removal_plot'].tolist(),
              self.curve_invalid_with_event['signal_processing_plot'].tolist(),
              self.curve_invalid_with_event['signal_processing_plot_wide'].tolist()
            ],
            worksheet_name = 'Invalid MatchedCurves',
            plot_header_text = '',
            missing_plot_path_text = 'No Plot Available'
          )
        
        # Always include unmatched events tab
        embed_graphs_into_workbook_tab(
          writer.book,
          [
            self.unmatched_events['device_removal_plot_EMA_REGION'].tolist(),
            self.unmatched_events['signal_processing_plot_EMA_REGION'].tolist(),
          ],
          worksheet_name = 'No Curve - EMA Region',
          plot_header_text = '',
          missing_plot_path_text = 'No Plot Available'
        )
      
      # Add imputations
      if not hasattr(self, 'imputations') or self.imputations is None or self.imputations.empty:
          self.compile_imputation_info()
      self.imputations.to_excel(writer, sheet_name='Imputations', index=False)
      
      # Add run settings
      run_settings_df = report_guide.get_run_settings_dataframe(
          smooth_and_impute_attrs=smooth_and_impute_attrs,
          curve_attrs=curve_attrs,
          event_attrs=event_attrs,
          day_attrs=day_attrs
      )
      if run_settings_df is not None:
          run_settings_df.to_excel(writer, sheet_name='Run Settings', index=False)

  def export_sorted_workbook(self, file_name, sort_column, ascending=True, smooth_and_impute_attrs=None, curve_attrs=None, event_attrs=None, day_attrs=None, flag_prefix=None, split_plots_by='validity'):
    """
    Export a workbook with features and curves sorted by a specified column.
    Includes only rows that are uniquely flagged (have the specified flag but no other flags)
    and 50 non-flagged rows that are closest to the flag threshold.
    Also includes event data and person-level stats for the selected curves.
    
    Args:
        file_name (str): Name of the output Excel file
        sort_column (str): Name of the column to sort by
        ascending (bool): Whether to sort in ascending order (True) or descending order (False)
        smooth_and_impute_attrs (dict, optional): Smoothing and imputation attributes
        curve_attrs (dict, optional): Curve attributes
        event_attrs (dict, optional): Event attributes
        day_attrs (dict, optional): Day attributes
        flag_prefix (str, optional): The exact flag column name to use for filtering
        split_plots_by (str): How to split visualization tabs - 'validity' (Valid/Invalid) or 'drinking_pred' (Drinking/Non-Drinking)
    
    Note:
        To use split_plots_by='drinking_pred', you must call set_datasets_by_valid_and_match() first.
        Only curves matched to self-report events will be included in the drinking/non-drinking tabs.
    """
    
    with pd.ExcelWriter(file_name, engine='xlsxwriter', mode='w') as writer:
      # Add tab descriptions
      report_guide.get_tab_descriptions_dataframe(include_events=True).to_excel(writer, sheet_name='Tab Descriptions', index=False)
      
      # Add variable key
      row_index = 0
      for name, df in report_guide.get_variable_key_dataframes():
          df.to_excel(writer, sheet_name='Variable Key', startrow=row_index)
          row_index += len(df) + 3  # Add 3 rows of spacing
      
      # Add stats
      row_index = 0
      for i, frame in enumerate(self.curve_stat_frames):
        frame.to_excel(writer, sheet_name='STATS', startrow=row_index)
        row_index += len(frame) + 3
      
      for i, frame in enumerate(self.event_stat_frames):
        frame.to_excel(writer, sheet_name='STATS', startrow=row_index)
        row_index += len(frame) + 3
      
      # Sort features
      sorted_features = self.curve_features.sort_values(by=sort_column, ascending=ascending)
      sorted_features.to_excel(writer, sheet_name='Features', index=False)
      
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
          
          # Get non-flagged rows from valid curves with events
          non_flagged = self.curve_valid_with_event[self.curve_valid_with_event[flag_column] != 1]
          
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
              
              # Store the closest non-flagged curves for later use in visualization
              self.closest_non_flagged = closest_non_flagged
              self.is_high_flag = is_high_flag  # Store the flag direction for later use
      
      sorted_features.to_excel(writer, sheet_name='Filtered Features', index=False)
      
      # Add events - reorder columns according to event_feature_descriptions
      # Get ordered columns from event_feature_descriptions that exist in event_data
      ordered_columns = [col for col in report_guide.event_feature_descriptions.keys() if col in self.event_data.columns]
      # Get remaining columns that aren't in event_feature_descriptions
      other_columns = [col for col in self.event_data.columns if col not in report_guide.event_feature_descriptions.keys()]
      # Combine ordered columns with remaining columns
      event_columns = ordered_columns + other_columns
      
      # Filter event data to only include events related to the selected curves
      selected_curve_ids = sorted_features[['subid', 'curve_id']].drop_duplicates()
      filtered_events = self.event_data.merge(
          selected_curve_ids,
          left_on=['ID', 'curve_match_1'],
          right_on=['subid', 'curve_id'],
          how='inner'
      )
      filtered_events[event_columns].to_excel(writer, sheet_name='Events', index=False)
      
      # Add valid matched by subid
      self.valid_matched_person_stats.to_excel(writer, sheet_name='Valid Matched by SubID', index=True)
      
      # Filter sorted_features to only include curves with events
      sorted_features_with_events = sorted_features.merge(
          self.curve_with_event[['subid', 'curve_id']],
          on=['subid', 'curve_id'],
          how='inner'
      )
      
      # Add visualization tabs - split by drinking_pred or validity
      if split_plots_by == 'drinking_pred' and hasattr(self, 'curve_drinking_with_event') and 'DRINKING_PRED' in sorted_features_with_events.columns:
          # Split by drinking prediction (only curves matched to events)
          # sorted_features_with_events is already filtered to curves with events (line 771-775)
          drinking_curves = sorted_features_with_events[sorted_features_with_events['DRINKING_PRED'] == 1]
          non_drinking_curves = sorted_features_with_events[sorted_features_with_events['DRINKING_PRED'] == 0]
          
          if not non_drinking_curves.empty:
              embed_graphs_into_workbook_tab(
                  writer.book,
                  [
                      non_drinking_curves['device_removal_plot'].tolist(),
                      non_drinking_curves['signal_processing_plot'].tolist(),
                      non_drinking_curves['signal_processing_plot_wide'].tolist()
                  ],
                  worksheet_name='Non-Drinking Matched',
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
                  worksheet_name='Drinking Matched',
                  plot_header_text='',
                  missing_plot_path_text='No Plot Available'
              )
      else:
          # Split by validity (default)
          validity_column = 'REGION_VALID' if 'REGION_VALID' in sorted_features_with_events.columns else 'CURVE_VALID'
          valid_curves = sorted_features_with_events[sorted_features_with_events[validity_column] == 1]
          invalid_curves = sorted_features_with_events[sorted_features_with_events[validity_column] != 1]
          
          # Add visualization tabs for valid and invalid curves
          if not invalid_curves.empty and flag_column:
              # Only include curves that are uniquely flagged for the specific flag we're analyzing
              all_flag_cols = [col for col in invalid_curves.columns if col.startswith('FLAG_')]
              uniquely_flagged = invalid_curves[
                  (invalid_curves[flag_column] == 1) & 
                  (invalid_curves[all_flag_cols].sum(axis=1) == 1)
              ]
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
          
          if not valid_curves.empty:
              # For valid curves, use the same 50 non-flagged curves that were selected earlier
              if hasattr(self, 'closest_non_flagged'):
                  # Sort by the sort_column to ensure plots are ordered by proximity to flag threshold
                  closest_non_flagged = self.closest_non_flagged.sort_values(
                      by=sort_column,
                      ascending=self.is_high_flag  # Use same ordering as when we selected the curves
                  )
                  embed_graphs_into_workbook_tab(
                      writer.book,
                      [
                          closest_non_flagged['device_removal_plot'].tolist(),
                          closest_non_flagged['signal_processing_plot'].tolist(),
                          closest_non_flagged['signal_processing_plot_wide'].tolist()
                      ],
                      worksheet_name='Valid Curves',
                      plot_header_text='',
                      missing_plot_path_text='No Plot Available'
                  )
      
      # Add imputations
      if not hasattr(self, 'imputations') or self.imputations is None or self.imputations.empty:
          self.compile_imputation_info()
      self.imputations.to_excel(writer, sheet_name='Imputations', index=False)
      
      # Add run settings
      run_settings_df = report_guide.get_run_settings_dataframe(
          smooth_and_impute_attrs=smooth_and_impute_attrs,
          curve_attrs=curve_attrs,
          event_attrs=event_attrs,
          day_attrs=day_attrs
      )
      if run_settings_df is not None:
          run_settings_df.to_excel(writer, sheet_name='Run Settings', index=False)

  def run_quality_plots_for_matched_curves(self, output_dir=None, use_three_imputation_ratio_groups=False):
    """
    Generate TAC feature quality plots for matched curves using QualityVisualizer.
    Args:
        output_dir (str): Directory to save plots.
        use_three_imputation_ratio_groups (bool): Whether to use three imputation ratio groups.
    """
    print(f"Generating quality plots for matched curves. Output dir: {output_dir}")
    visualizer = QualityVisualizer(use_three_imputation_ratio_groups=use_three_imputation_ratio_groups)
    raw_curve_features = getattr(self, 'raw_curve_features', None)
    visualizer.create_tac_boxplots(self.curve_with_event, output_dir=output_dir)
    
    # Create TAC density plots
    density_plot_filename = os.path.join(output_dir, 'tac_density_distributions.png')
    visualizer.create_tac_density_plots(self.curve_with_event, output_filename=density_plot_filename)
    
    # Optionally, you can add more plot types here, e.g.:
    # visualizer.create_quality_mean_plots(self.curve_with_event, raw_curve_features=raw_curve_features, output_dir=output_dir)

  def clean_out_distant_events(self, distance_threshold=8):
    # This method is designed to remove events that are too far from their matched curves
    # Get all columns for curve matches and their distances
    match_cols = [f'curve_match_{i}' for i in range(1, 6)]
    # ... rest of the method content ...