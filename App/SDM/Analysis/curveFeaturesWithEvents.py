from App.SDM.Analysis.statModel import statModel
from App.SDM.Analysis.curveFeatures import curveFeatures
from App.SDM.Skyn_Processors.ema_region import emaRegion
from App.SDM.Configuration.file_management import load, save_to_computer
from App.SDM.Documenting.embed_graphs import embed_graphs_into_workbook_tab
import pandas as pd

class curveFeaturesWithEvents(curveFeatures):
  def __init__(self, processed_data_folder, event_file, event_id_column, event_drink_total_column, event_subid_column, event_subtypes):
    super().__init__(processed_data_folder)
    self.processors = [processor for processor in self.processors if hasattr(processor, 'event_labels')]
    self.event_data = pd.concat([processor.event_labels for processor in self.processors], ignore_index=True)
    self.raw_event_data = pd.read_csv(event_file) if event_file[-3:] == 'csv' else pd.read_excel(event_file)
    self.event_id_column = event_id_column
    self.event_drink_total_column = event_drink_total_column
    self.event_subid_column = event_subid_column
    self.event_stat_frames = []
    self.ema_region_columns = [col for col in self.event_data if 'EMA_REGION' in col]
    self.event_subtypes = event_subtypes

  def label_event_curve_matches(self):
    self.event_data.drop(columns=['subid'], inplace=True)
    self.event_data['ID'] = self.event_data['ID'].astype(int)
    self.event_data['ema_id'] = self.event_data['ema_id'].astype(str)
    self.raw_event_data[self.event_subid_column] = self.raw_event_data[self.event_subid_column].astype(int)
    self.raw_event_data[self.event_id_column] = self.raw_event_data[self.event_id_column].astype(str)
    self.event_data = self.event_data.merge(self.raw_event_data, left_on=['ID', 'ema_id'], right_on=[self.event_subid_column, self.event_id_column], how='left')
    
    self.event_data['matched'] = self.event_data.groupby(['ID', 'ema_id'])['id_WITHIN_CURVE'].transform(lambda x: int(x.notna().any()))
    self.matched_events = self.event_data[self.event_data['matched']==1]
    self.unmatched_events = self.event_data[self.event_data['matched']!=1]

    if 'alc_only' in self.event_subtypes:
      self.event_data['alc_only'] = self.event_data.groupby(['ema_id', 'ID'])['label'].transform(lambda x: int(all('drink' in label for label in x)))
      self.matched_alcohol_events = self.event_data[(self.event_data['alc_only']==1) & (self.event_data['matched']==1)]
      self.unmatched_alcohol_events = self.event_data[(self.event_data['alc_only']==1) & (self.event_data['matched']!=1)]
    if 'co_use' in self.event_subtypes:
      self.event_data['co_use'] = self.event_data.groupby(['ema_id', 'ID'])['label'].transform(
        lambda x: int(any('drink' in label for label in x) and any('drink' not in label for label in x))
      )
      self.matched_co_use_events = self.event_data[(self.event_data['co_use']==1)  & (self.event_data['matched']==1)]
      self.unmatched_co_use_events = self.event_data[(self.event_data['co_use']==1)  & (self.event_data['matched']!=1)]
    if 'no_alc' in self.event_subtypes:
      self.event_data['no_alc'] = self.event_data.groupby(['ema_id', 'ID'])['label'].transform(
        lambda x: int(not any('drink' in label for label in x))
      )
      self.matched_non_alcohol_events = self.event_data[(self.event_data['no_alc']==1)  & (self.event_data['matched']==1)]
      self.unmatched_non_alcohol_events = self.event_data[(self.event_data['no_alc']==1)  & (self.event_data['matched']!=1)]
    
    matched = self.matched_events.copy()
    matched = matched.rename(columns={'ID': 'subid', 'id_WITHIN_CURVE': 'curve_id'}).reset_index(drop=True)
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
    self.counts = {
      'Curves': [len(self.curve_features)],
      'Curves Valid': [len(self.curve_valid)],
      'Curves Invalid': [len(self.curve_invalid)],
      'Curves with Event Match': [len(self.curve_with_event)],
      'Valid Curves with Event Match': [len(self.curve_valid_with_event)],
      'Invalid Curves with Event Match': [len(self.curve_invalid_with_event)],
      'Events': [self.event_data[['ema_id', 'ID']].drop_duplicates().shape[0]],
      'Events with Curve': [self.matched_events[['ema_id', 'ID']].drop_duplicates().shape[0]],
      'Events without Curve': [self.unmatched_events[['ema_id', 'ID']].drop_duplicates().shape[0]]
    }

    if 'alc_only' in self.event_subtypes:
      self.counts.update({
        'Alc Only Events with Curve': [self.matched_alcohol_events[['ema_id', 'ID']].drop_duplicates().shape[0]],
        'Alc Only Events without Curve': [self.unmatched_alcohol_events[['ema_id', 'ID']].drop_duplicates().shape[0]]
      })
    if 'co_use' in self.event_subtypes:
      self.counts.update({
        'Co-Use Events with Curve': [self.matched_co_use_events[['ema_id', 'ID']].drop_duplicates().shape[0]],
        'Co-Use Events without Curve': [self.unmatched_co_use_events[['ema_id', 'ID']].drop_duplicates().shape[0]],
      })
    if 'no_alc' in self.event_subtypes:
      self.counts.update({
        'Non-Alc Events with Curve': [self.matched_non_alcohol_events[['ema_id', 'ID']].drop_duplicates().shape[0]],
        'Non-Alc Events without Curve': [self.unmatched_non_alcohol_events[['ema_id', 'ID']].drop_duplicates().shape[0]],
      })

    self.event_stat_frames.append(pd.DataFrame(self.counts))

  def count_flags_for_curves_with_events(self):
    stats = statModel(self.curve_with_event)
    for flag_col in [col for col in self.curve_with_event.columns if 'FLAG' in col]:
      setattr(self, 'counts_' + flag_col, stats.groupby_counts(flag_col))
      self.event_stat_frames.append(getattr(self, 'counts_' + flag_col))
  
  def assess_search_quality(self):
    if 'alc_only' in self.event_subtypes and 'co_use' in self.event_subtypes:
      dfs = [
        self.matched_alcohol_events, self.unmatched_alcohol_events,
        self.matched_co_use_events, self.unmatched_co_use_events,
      ]
    else:
      dfs = [self.matched_events, self.unmatched_events]
    for df in dfs:
      df_filtered = df.drop_duplicates(subset=['ID']+self.ema_region_columns)  
      stat_model = statModel(df_filtered)
      results = stat_model.continuous_stats_for_columns([col for col in self.ema_region_columns if 'plot' not in col])
      self.event_stat_frames.append(results)
  
  def compute_tac_feature_stats(self):
    valid = statModel(self.curve_valid_with_event)
    invalid = statModel(self.curve_invalid_with_event)
    valid_feature_stats = valid.continuous_stats_for_columns(self.default_tac_features)
    invalid_feature_stats = invalid.continuous_stats_for_columns(self.default_tac_features)
    self.event_stat_frames.append(valid_feature_stats)
    self.event_stat_frames.append(invalid_feature_stats)

  def run_event_stats(self):
    self.count_matches()
    self.count_flags_for_curves_with_events()
    self.compute_tac_feature_stats()
    self.assess_search_quality()

  def export_workbook_events_and_curves(self, file_name):
    with pd.ExcelWriter(file_name, engine = 'xlsxwriter', mode = 'w') as writer:
      self.curve_features.to_excel(writer, sheet_name='Features', index=False)
      self.event_data.to_excel(writer, sheet_name='Events', index=False)
      
      row_index = 0
      for i, frame in enumerate(self.curve_stat_frames):
        frame.to_excel(writer, sheet_name='STATS', startrow=row_index)
        row_index += len(frame) + 2
      
      for i, frame in enumerate(self.event_stat_frames):
        frame.to_excel(writer, sheet_name='STATS', startrow=row_index)
        row_index += len(frame) + 2

      embed_graphs_into_workbook_tab(
        writer.book,
        [
          self.curve_invalid_with_event['device_removal_plot'].tolist(),
          self.curve_invalid_with_event['signal_processing_plot'].tolist(),
          self.curve_invalid_with_event['signal_processing_plot_wide'].tolist()
        ],
         worksheet_name = 'Invalid Curves',
         plot_header_text = '', # this will be revised to work as a list (search valid)
         missing_plot_path_text = 'No Plot Available'
      )

      embed_graphs_into_workbook_tab(
        writer.book,
        [
          self.curve_valid_with_event['device_removal_plot'].tolist(),
          self.curve_valid_with_event['signal_processing_plot'].tolist(),
          self.curve_valid_with_event['signal_processing_plot_wide'].tolist()
        ],
         worksheet_name = 'Valid Curves',
         plot_header_text = '', # this will be revised to work as a list (search valid)
         missing_plot_path_text = 'No Plot Available'
      )

      if 'co_use' in self.event_subtypes and 'alc_only' in self.event_subtypes:
        filtered_unmatched_co_use = (
          self.unmatched_co_use_events
          .drop_duplicates(subset=['device_removal_plot_EMA_REGION'])
          .dropna(subset=['device_removal_plot_EMA_REGION'])
          .drop_duplicates(subset=['signal_processing_plot_EMA_REGION'])
          .dropna(subset=['signal_processing_plot_EMA_REGION'])
        )

        filtered_alcohol_events = (
          self.unmatched_alcohol_events
          .drop_duplicates(subset=['device_removal_plot_EMA_REGION'])
          .dropna(subset=['device_removal_plot_EMA_REGION'])
          .drop_duplicates(subset=['signal_processing_plot_EMA_REGION'])
          .dropna(subset=['signal_processing_plot_EMA_REGION'])
        )

        embed_graphs_into_workbook_tab(
          writer.book,
          [
            filtered_unmatched_co_use['device_removal_plot_EMA_REGION'].tolist() + filtered_alcohol_events['device_removal_plot_EMA_REGION'].tolist(),
            filtered_unmatched_co_use['signal_processing_plot_EMA_REGION'].tolist() + filtered_alcohol_events['signal_processing_plot_EMA_REGION'].tolist(),
          ],
          worksheet_name = 'No Curve with Alc Event',
          plot_header_text = '', # this will be revised to work as a list (search valid)
          missing_plot_path_text = 'No Plot Available'
        )
      else:
        embed_graphs_into_workbook_tab(
          writer.book,
          [
            self.unmatched_events['device_removal_plot_EMA_REGION'].tolist(),
            self.unmatched_events['signal_processing_plot_EMA_REGION'].tolist(),
          ],
          worksheet_name = 'No Curve with Alc Event',
          plot_header_text = '', # this will be revised to work as a list (search valid)
          missing_plot_path_text = 'No Plot Available'
        )

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