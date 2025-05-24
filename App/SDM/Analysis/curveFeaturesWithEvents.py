from App.SDM.Analysis.statModel import statModel
from App.SDM.Analysis.curveFeatures import curveFeatures
from App.SDM.Skyn_Processors.ema_region import emaRegion
from App.SDM.Configuration.file_management import load, save_to_computer
from App.SDM.Documenting.embed_graphs import embed_graphs_into_workbook_tab
from App.SDM.Documenting.report_guide import report_guide

import pandas as pd
import os

class curveFeaturesWithEvents(curveFeatures):
  def __init__(self, processed_data_folder, smooth_and_impute_attrs=None, curve_attrs=None, event_attrs=None, day_attrs=None, subid=None):
    super().__init__(processed_data_folder, smooth_and_impute_attrs, curve_attrs, subid)
    self.processors = [processor for processor in self.processors if hasattr(processor, 'event_labels')]
    self.event_data = pd.concat([processor.events for processor in self.processors if isinstance(processor.events, pd.DataFrame)], ignore_index=True)
    self.event_stat_frames = []
    self.ema_region_columns = [col for col in self.event_data if 'EMA_REGION' in col]
    self.event_type_column = ''
    self.event_type_settings = {}

    # Optional configuration dictionaries
    self.event_attrs = event_attrs
    self.day_attrs = day_attrs

    self.default_tac_features = report_guide.stats_features

  def label_event_curve_matches(self):
    self.event_data['ID'] = self.event_data['ID'].astype(int)
    self.event_data['ema_id'] = self.event_data['ema_id'].astype(str)
    self.event_data.drop(columns=['subid'], inplace=True, errors='ignore')    
    
    # First mark events that matched to any curve
    self.event_data['matched'] = self.event_data.groupby(['ID', 'ema_id'])['curve_match_1'].transform(lambda x: int(x.notna().any()))
    
    self.event_data['has_shared_match'] = False
    self.event_data['shared_curve_id'] = None
    self.event_data['has_shared_first_match'] = False
    self.event_data['shared_first_curve_id'] = None

    curve_cols = [f'curve_match_{i}' for i in range(1, 6) if f'curve_match_{i}' in self.event_data.columns]
    
    # Add curve validity information for each match
    for i in range(1, 6):
        if f'curve_match_{i}' in self.event_data.columns:
            # Create a mapping of (subid, curve_id) to validity
            validity_map = self.curve_features.set_index(['subid', 'curve_id'])[['CURVE_VALID', 'PERIPHERY_VALID']]
            
            # Simple lookup function
            def get_curve_validity(row):
                if pd.isna(row[f'curve_match_{i}']):
                    return None
                try:
                    curve_id = int(row[f'curve_match_{i}'])
                    # Use loc for proper DataFrame indexing
                    validity = validity_map.loc[(row['ID'], curve_id)]
                    # Return 1 if both CURVE_VALID and PERIPHERY_VALID are 1, else 0
                    return 1 if validity['CURVE_VALID'] == 1 and validity['PERIPHERY_VALID'] == 1 else 0
                except (KeyError, ValueError):
                    return None
            
            # Map validity to each curve match
            self.event_data[f'CURVE_and_PERIPHERY_VALID_{i}'] = self.event_data.apply(get_curve_validity, axis=1)
    
    # Assign valid and invalid curve matches per row
    curve_match_cols = [f'curve_match_{i}' for i in range(1, 6) if f'curve_match_{i}' in self.event_data.columns]
    valid_cols = []
    invalid_cols = []
    for idx, row in self.event_data.iterrows():
        valid_matches = []
        invalid_matches = []
        for i, col in enumerate(curve_match_cols, 1):
            val = row[col]
            valid_flag = row.get(f'CURVE_and_PERIPHERY_VALID_{i}', None)
            if pd.notna(val):
                if valid_flag == 1:
                    valid_matches.append(val)
                elif valid_flag == 0:
                    invalid_matches.append(val)
        # Assign valid matches
        for j, v in enumerate(valid_matches, 1):
            colname = f'valid_curve_match_{j}'
            self.event_data.at[idx, colname] = v
            if colname not in valid_cols:
                valid_cols.append(colname)
        # Assign invalid matches
        for j, v in enumerate(invalid_matches, 1):
            colname = f'invalid_curve_match_{j}'
            self.event_data.at[idx, colname] = v
            if colname not in invalid_cols:
                invalid_cols.append(colname)

    for _, group in self.event_data.groupby('ID'):
        # Check first valid curve match only
        first_valid_curve_ids = group['valid_curve_match_1'].dropna()
        shared_first_valid_curves = first_valid_curve_ids[first_valid_curve_ids.duplicated(keep=False)]
        # Mark events that share first valid curve match
        shared_first_mask = group['valid_curve_match_1'].isin(shared_first_valid_curves)
        self.event_data.loc[group.index, 'has_shared_first_match'] = shared_first_mask
        self.event_data.loc[group.index[shared_first_mask], 'shared_first_curve_id'] = group.loc[group.index[shared_first_mask], 'valid_curve_match_1']

        # Get all valid curve match columns for this group
        valid_curve_cols = [col for col in group.columns if col.startswith('valid_curve_match_') and not col.endswith('_overlap')]
        
        for i, row1 in group.iterrows():
            for j, row2 in group.iterrows():
                if i >= j:
                    continue
                curves1 = [row1[col] for col in valid_curve_cols if pd.notna(row1[col])]
                curves2 = [row2[col] for col in valid_curve_cols if pd.notna(row2[col])]
                shared_curves = set(curves1) & set(curves2)
                if shared_curves:
                    self.event_data.loc[[i,j], 'has_shared_match'] = True
                    # Store one of the shared curve IDs
                    shared_curve = list(shared_curves)[0]
                    self.event_data.loc[[i,j], 'shared_curve_id'] = shared_curve
                    
    self.matched_events = self.event_data[self.event_data['matched']==1]
    self.unmatched_events = self.event_data[self.event_data['matched']!=1]

    matched = self.matched_events.copy()
    matched = matched.rename(columns={'ID': 'subid', 'curve_match_1': 'curve_id'}).reset_index(drop=True)
    matched = matched.drop_duplicates(subset=['subid', 'curve_id', 'ema_id'])
    matched['event_rank'] = matched.groupby(['subid', 'curve_id']).cumcount() + 1
    matched_pivot = matched.pivot(index=['subid', 'curve_id'], columns='event_rank', values='ema_id')
    matched_pivot.columns = [f'event_matched_{col}' for col in matched_pivot.columns]
    matched_pivot.reset_index(inplace=True)
    max_events = matched.groupby(['subid', 'curve_id'])['ema_id'].nunique().max()
    valid_columns = [
      col for col in matched_pivot.columns if col.startswith('event_matched_') 
      and int(col.replace('event_matched_', '')) <= max_events
    ]
    matched_pivot = matched_pivot[['subid', 'curve_id'] + valid_columns]
    matched_pivot = matched_pivot.dropna(subset=['subid', 'curve_id'])
    matched_pivot['subid'] = matched_pivot['subid'].astype(int)
    matched_pivot['curve_id'] = matched_pivot['curve_id'].astype(int)
    self.curve_features = self.curve_features.merge(matched_pivot, on=['subid', 'curve_id'], how='left')

    # After assigning all valid/invalid curve match columns, compute counts and binary flags
    valid_curve_cols = [col for col in self.event_data.columns if col.startswith('valid_curve_match_') and not col.endswith('_overlap')]
    invalid_curve_cols = [col for col in self.event_data.columns if col.startswith('invalid_curve_match_') and not col.endswith('_overlap')]

    self.event_data['num_valid_curves_matched'] = self.event_data[valid_curve_cols].notna().sum(axis=1)
    self.event_data['num_invalid_curves_matched'] = self.event_data[invalid_curve_cols].notna().sum(axis=1)

    self.event_data['multiple_valid_curves_matched'] = (self.event_data['num_valid_curves_matched'] > 1) & (self.event_data['num_invalid_curves_matched'] == 0)
    self.event_data['multiple_invalid_curves_matched'] = (self.event_data['num_invalid_curves_matched'] > 1) & (self.event_data['num_valid_curves_matched'] == 0)
    self.event_data['multiple_mixed_curves_matched'] = (self.event_data['num_valid_curves_matched'] > 0) & (self.event_data['num_invalid_curves_matched'] > 0) & ((self.event_data['num_valid_curves_matched'] + self.event_data['num_invalid_curves_matched']) > 1)

  # def set_events_by_type(self):
  #   """Set event types based on event_type_settings configuration"""
  #   self.event_data['eventuse_merged'] = self.event_data[self.event_type_column].copy()
    
  #   # Initialize counters
  #   self.shared_curve_count = 0
  #   self.relabeled_event_count = 0
    
  #   for _, group in self.event_data.groupby(['ID', 'curve_match_1']):
  #     if len(group) > 1:  # Multiple events matched to same curve
  #       self.shared_curve_count += 1
  #       # Get all unique labels for events matching this curve
  #       all_labels = group[self.event_type_column].unique()
        
  #       # If multiple events match same curve, merge their types according to settings
  #       if len(all_labels) > 1:
  #         # Check if both substance types are present
  #         has_substance_one = self.event_type_settings['substance_one'] in all_labels
  #         has_substance_two = self.event_type_settings['substance_two'] in all_labels
  #         has_both = (has_substance_one and has_substance_two) or self.event_type_settings['substance_one_and_two'] in all_labels
  #         if has_both:
  #           self.event_data.loc[group.index, 'eventuse_type_merged'] = self.event_type_settings['substance_one_and_two']
  #           self.relabeled_event_count += len(group)

  def set_datasets_by_valid_and_match(self):
    valid = (self.curve_features['CURVE_VALID'] == 1)
    invalid = (self.curve_features['CURVE_VALID'] != 1)
    event_found = (self.curve_features['event_matched_1'].notna())
    event_not_found = (self.curve_features['event_matched_1'].isna())

    self.curve_with_event = self.curve_features[event_found]
    self.curve_without_event = self.curve_features[event_not_found]
    self.curve_valid_with_event = self.curve_features[valid & event_found]
    self.curve_invalid_with_event = self.curve_features[invalid & event_found]
    self.curve_valid_without_event = self.curve_features[valid & event_not_found]
    self.curve_invalid_without_event = self.curve_features[invalid & event_not_found]

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

  def count_flags_for_curves_with_events(self):
    stats = statModel(self.curve_with_event)
    flag_cols = [col for col in self.curve_with_event.columns if 'FLAG' in col]
    flag_stats_list = []
    total_curves = len(self.curve_with_event)
    for flag_col in flag_cols:
      flag_stats = stats.groupby_counts(flag_col, include_unique_flags=True)
      flag_stats = flag_stats.reset_index()
      flag_stats['Flag_Column'] = flag_col
      flag_stats_list.append(flag_stats)
    if flag_stats_list:
      combined_flag_stats = pd.concat(flag_stats_list, axis=0, ignore_index=True)
      # Only keep relevant columns
      keep_cols = [col for col in combined_flag_stats.columns if col in [
          'Value', 'Count', 'Unique_Flag_Count', 'Unique_Flag_%', 'Flag_Column'
      ]]
      combined_flag_stats = combined_flag_stats[keep_cols]
      # Filter out rows where 'Unique_Flag_Count' is empty (removes counts of non-flagged curves, only keeping flag counts)
      combined_flag_stats = combined_flag_stats[combined_flag_stats['Unique_Flag_Count'].notna() & (combined_flag_stats['Unique_Flag_Count'] != '')]
      # Calculate % of total curves and add column
      combined_flag_stats['% of Total Curves'] = (combined_flag_stats['Count'] / total_curves) * 100
      # Sort by 'Count' descending
      combined_flag_stats = combined_flag_stats.sort_values(by='Count', ascending=False)
      # Set 'Flag_Column' as the index
      combined_flag_stats = combined_flag_stats.set_index('Flag_Column')
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

  def run_event_stats(self):
    self.count_matches()
    self.count_flags_for_curves_with_events()
    self.compute_tac_feature_stats_for_matched_curves()
    self.assess_search_quality()
    self.compute_person_level_stats()

  def export_workbook_events_and_curves(self, file_name, smooth_and_impute_attrs=None, curve_attrs=None, event_attrs=None, day_attrs=None):
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
      
      # Add visualization tabs
      # embed_graphs_into_workbook_tab(
      #   writer.book,
      #   [
      #     self.curve_valid_with_event['device_removal_plot'].tolist(),
      #     self.curve_valid_with_event['signal_processing_plot'].tolist(),
      #     self.curve_valid_with_event['signal_processing_plot_wide'].tolist()
      #   ],
      #    worksheet_name = 'Valid Curves',
      #    plot_header_text = '',
      #    missing_plot_path_text = 'No Plot Available'
      # )

      # embed_graphs_into_workbook_tab(
      #   writer.book,
      #   [
      #     self.curve_invalid_with_event['device_removal_plot'].tolist(),
      #     self.curve_invalid_with_event['signal_processing_plot'].tolist(),
      #     self.curve_invalid_with_event['signal_processing_plot_wide'].tolist()
      #   ],
      #    worksheet_name = 'Invalid Curves',
      #    plot_header_text = '',
      #    missing_plot_path_text = 'No Plot Available'
      # )
      
      # embed_graphs_into_workbook_tab(
      #   writer.book,
      #   [
      #     self.unmatched_events['device_removal_plot_EMA_REGION'].tolist(),
      #     self.unmatched_events['signal_processing_plot_EMA_REGION'].tolist(),
      #   ],
      #   worksheet_name = 'No Curve - EMA Region',
      #   plot_header_text = '',
      #   missing_plot_path_text = 'No Plot Available'
      # )
      
      # Add imputations
      self.compile_imputation_info().to_excel(writer, sheet_name='Imputations', index=False)
      
      # Add run settings
      run_settings_df = report_guide.get_run_settings_dataframe(
          smooth_and_impute_attrs=smooth_and_impute_attrs,
          curve_attrs=curve_attrs,
          event_attrs=event_attrs,
          day_attrs=day_attrs
      )
      if run_settings_df is not None:
          run_settings_df.to_excel(writer, sheet_name='Run Settings', index=False)

  def export_sorted_workbook(self, file_name, sort_column, ascending=True, smooth_and_impute_attrs=None, curve_attrs=None, event_attrs=None, day_attrs=None):
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
        event_attrs (dict, optional): Event attributes
        day_attrs (dict, optional): Day attributes
    """
    # Ensure stats are computed
    if not self.curve_stat_frames or not self.event_stat_frames:
        self.run_event_stats()
    
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
      print(f"[DEBUG] Total rows after sorting: {len(sorted_features)}")
      
      # Find corresponding flag column
      # Remove _CURVE or _PERIPHERY suffix if present
      base_column = sort_column.replace('_CURVE', '').replace('_PERIPHERY', '')
      
      # Flexibly match any flag column containing the base_column
      flag_candidates = [col for col in sorted_features.columns if col.startswith('FLAG_') and base_column in col]
      print(f"[DEBUG] Flag candidates for base_column '{base_column}': {flag_candidates}")
      flag_column = flag_candidates[0] if flag_candidates else None
      print(f"[DEBUG] Selected flag column: {flag_column}")
      
      if flag_column:
          # Get flagged and non-flagged rows
          flagged = sorted_features[sorted_features[flag_column] == 1]
          non_flagged = sorted_features[sorted_features[flag_column] != 1]
          print(f"[DEBUG] Flagged rows: {len(flagged)}; Non-flagged rows: {len(non_flagged)}")
          
          if len(flagged) > 0:
              # Determine if flag is for high or low values by comparing means
              flagged_mean = flagged[sort_column].mean()
              non_flagged_mean = non_flagged[sort_column].mean()
              is_high_flag = flagged_mean > non_flagged_mean
              print(f"[DEBUG] Flagged mean: {flagged_mean}, Non-flagged mean: {non_flagged_mean}, is_high_flag: {is_high_flag}")
              
              # Get 50 closest non-flagged rows
              if is_high_flag:
                  # For high flags, take the highest 50 non-flagged values
                  closest_non_flagged = non_flagged.nlargest(50, sort_column)
              else:
                  # For low flags, take the lowest 50 non-flagged values
                  closest_non_flagged = non_flagged.nsmallest(50, sort_column)
              print(f"[DEBUG] Closest non-flagged rows selected: {len(closest_non_flagged)}")
              
              # Combine flagged and closest non-flagged rows
              selected_indices = sorted(set(flagged.index) | set(closest_non_flagged.index))
              print(f"[DEBUG] Total selected rows (flagged + closest): {len(selected_indices)}")
              sorted_features = sorted_features.loc[selected_indices]
      print(f"[DEBUG] Final rows in Features sheet: {len(sorted_features)}")
      
      sorted_features.to_excel(writer, sheet_name='Features', index=False)
      
      # Add events - reorder columns according to event_feature_descriptions
      ordered_columns = [col for col in report_guide.event_feature_descriptions.keys() if col in self.event_data.columns]
      other_columns = [col for col in self.event_data.columns if col not in report_guide.event_feature_descriptions.keys()]
      event_columns = ordered_columns + other_columns
      self.event_data[event_columns].to_excel(writer, sheet_name='Events', index=False)
      
      # Add valid matched by subid
      self.valid_matched_person_stats.to_excel(writer, sheet_name='Valid Matched by SubID', index=True)
      
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
      
      # Add imputations
      self.compile_imputation_info().to_excel(writer, sheet_name='Imputations', index=False)
      
      # Add run settings
      run_settings_df = report_guide.get_run_settings_dataframe(
          smooth_and_impute_attrs=smooth_and_impute_attrs,
          curve_attrs=curve_attrs,
          event_attrs=event_attrs,
          day_attrs=day_attrs
      )
      if run_settings_df is not None:
          run_settings_df.to_excel(writer, sheet_name='Run Settings', index=False)

  """
  def clean_out_distant_events(self, distance_threshold=8):

    #curve_vs_self_report_time_diff is self report - curve start
    indices_too_far = self.curve_features.index[
      (self.curve_features['curve_vs_self_report_time_diff']-1).abs() > distance_threshold
    ] #-1 is to catch more events that occur later and account for TAC delay

    self.events_too_far_from_curve = self.curve_features.loc[indices_too_far, ['curve_id', 'curve_vs_self_report_time_diff', 'curve_threshold'] + self.ema_columns + self.ema_region_quality_columns]
    self.events_too_far_from_curve.drop_duplicates(subset=['ID', self.event_id_column], inplace=True)
    
    # removing ema data from curves that are too far from self report event start
    self.curve_features.loc[indices_too_far, self.ema_columns + self.ema_region_quality_columns] = np.nan  

    # Filter duplicate events and select the one with the lowest absolute curve_vs_self_report_time_diff - 1
    duplicate_events = self.curve_features[self.curve_features.duplicated(subset=['ID', self.event_id_column], keep=False)].copy()
    indices_closest_curve_to_event = duplicate_events.groupby(['ID', self.event_id_column])['curve_vs_self_report_time_diff']\
      .apply(lambda x: (abs(x - 1)).idxmin()).values   
    indices_closest_curve_to_event = pd.Index(indices_closest_curve_to_event)
    indices_curves_not_closest_to_event = duplicate_events.index.difference(indices_closest_curve_to_event)
    self.curves_with_event_match_but_event_data_removed_because_not_closest = len(indices_curves_not_closest_to_event)
    #remove event data for curves that are farther away from event than a different curve
    self.curve_features.loc[indices_curves_not_closest_to_event, self.ema_columns + self.ema_region_quality_columns] = np.nan     

    # Precompute index sets for faster lookup
    curve_features_idx = set(self.curve_features.set_index(['ID', self.event_id_column]).index)
    events_without_curve_idx = set(self.events_too_far_from_curve.set_index(['ID', self.event_id_column]).index)

    # Remove from self.events_without_curve if it's in curve_features
    # print('TOO FAR: ',  len(self.events_too_far_from_curve))
    self.events_without_curve = self.events_too_far_from_curve[
        ~self.events_too_far_from_curve.set_index(['ID', self.event_id_column]).index.isin(curve_features_idx)
    ]
    print('TOO FAR [cleaned]: ',  len(self.events_without_curve))

    # Find missing events in event_data that are:
    # (1) In event_data, (2) Not in events_without_curve, (3) Not in curve_features
    mask = ~self.event_data.set_index(['ID', self.event_id_column]).index.isin(events_without_curve_idx)
    mask &= ~self.event_data.set_index(['ID', self.event_id_column]).index.isin(curve_features_idx)
    df_missing_events = self.event_data[mask].reset_index(drop=True)
    for col in self.ema_region_quality_columns + ['curve_id', 'curve_vs_self_report_time_diff', 'curve_threshold', 'nearest_curve_id', 'nearest_curve_time_diff']:
      df_missing_events[col] = None
    print('Events from event file not included: ', len(df_missing_events))

    for i, missing_event in df_missing_events.iterrows():
      subid = missing_event['ID']
      ema_id = missing_event[self.event_id_column]
      ema_start_time = missing_event[self.event_start_column]
      self_reported_drinks = missing_event[self.event_drink_total_column]
      processors = [p for p in self.processors if p.subid == str(subid) or p.subid == int(subid)]
      if len(processors) > 0:
        processor = processors[0]
        ema_region = emaRegion(processor.dataset, subid, processor.dataset_identifier, ema_id, ema_start_time)
        if len(ema_region.self_report_region) > 0:
          df_filtered = self.curve_features[(self.curve_features['subid'] == int(subid)) | (self.curve_features['subid'] == str(subid))]
          curve_threshold = df_filtered.iloc[0]['curve_threshold'] if len(df_filtered) else None
          if len(df_filtered):
            closest_row = df_filtered.loc[(df_filtered['begin_CURVE'] - ema_start_time).abs().idxmin()]
            time_diff_hours = (closest_row['begin_CURVE'] - ema_start_time).total_seconds() / 3600
            df_missing_events.at[missing_event.name, 'nearest_curve_id'] = closest_row['curve_id']
            df_missing_events.at[missing_event.name, 'nearest_curve_time_diff'] = time_diff_hours
          df_missing_events.at[missing_event.name, 'curve_threshold'] = curve_threshold
          ema_region.make_device_removal_plot(processor.plot_folder)
          ema_region.make_signal_processing_plot(processor.plot_folder, curve_threshold if curve_threshold else 10, self_reported_drinks)
          for col, new_value in ema_region.self_report_region_quality_features.items():
            if col in self.ema_region_quality_columns:
              df_missing_events.at[missing_event.name, col] = new_value

    # Add missing events and sort
    self.events_without_curve = pd.concat([self.events_without_curve, df_missing_events], ignore_index=True)
    self.events_without_curve.sort_values(by=['ID', self.event_id_column], inplace=True)

  """