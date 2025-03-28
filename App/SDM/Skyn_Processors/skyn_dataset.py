from .skyn_datapoint import skynDatapoint
from ..Configuration.configuration import *
from ..Configuration.day_level import get_day_level_indices, create_day_level_dataframe
from ..Configuration.event_level import get_event_level_indices, create_event_level_dataframe
from ..Configuration.file_management import *
from App.SDM.User_Interface.Utils.filename_tools import extract_additional_filename_text
from ..Crop.crop import *
from ..Signal_Processing.identify_overlapping_curves import identify_overlapping_curves
from ..Signal_Processing.smooth_signal import smooth_savgol
from ..Signal_Processing.remove_outliers import *
from ..Signal_Processing.impute import impute_low_quality_data
from ..Signal_Processing.fill_device_off_gaps import fill_device_off_gaps
from ..Signal_Processing.label_device_non_wear import label_device_non_wear_using_cutoff, label_device_non_wear_using_model, compare_non_wear_methods
from ..Signal_Processing.label_signal_stability import *
from ..Signal_Processing.label_negative_values import label_negative_values
from ..Signal_Processing.curve_demarcation import *
from ..Skyn_Processors.skyn_day import skynDay
from ..Skyn_Processors.alcohol_event import alcoholEvent
from ..Skyn_Processors.curve import Curve
from App.SDM.Skyn_Processors.ema_region import emaRegion
from ..Visualization.tac import *
from ..Visualization.device_non_wear import *
from ..Feature_Engineering.tac_features import *
from ..Feature_Engineering.row_features import generate_row_features
from ..Documenting.variable_keys import *
# from ..Signal_Processing.revise_incomplete_features import revise_fall_features, revise_rise_features

import pandas as pd
import numpy as np
import traceback

class skynDataset:
  def __init__(self, path, processed_data_out_folder, data_out_folder, graphs_out_folder, subid, dataset_identifier, episode_identifier='e1'):
    self.path = path

    #Subid, Dataset ID, Episode ID
    self.subid = subid
    self.dataset_identifier = dataset_identifier
    self.episode_identifier = episode_identifier

    #outcomes/variables of interest/self-reported info
    self.condition = extract_additional_filename_text(os.path.basename(self.path))
    if self.condition != 'Non' and self.condition != 'Alc' and self.condition != 'Pla':
      self.condition = 'Unk'

    #Full Identifier, cohort info
    self.full_identifier = get_full_identifier(self.subid, self.dataset_identifier, self.episode_identifier)

    #load data
    self.unprocessed_dataset = load_dataset(self)
    self.sampling_rate = 1 #biosensor readings per minute. this is updated in the command below
    self.dataset = configure_raw_data(self)

    self.time_elapsed_column = 'Duration_Hrs' #updated after cropping/processing

    #EXPORT PATH INFO
    self.processed_data_out_folder = processed_data_out_folder
    self.error_logs_folder = data_out_folder.split('Results/')[0] + 'Results/Error_Logs/'
    self.data_out_folder = data_out_folder
    self.plot_folder = create_individual_plot_folder(graphs_out_folder, self.subid)
    self.plot_paths = []

    self.non_wear_search_plot_paths = {}
    self.tac_processing_search_plot_paths = {}
    self.tac_smooth_search_plot_paths = {}
    self.non_wear_curve_plot_paths = {}
    self.tac_processing_curve_plot_paths = {}
    self.tac_smooth_curve_plot_paths = {}

    self.valid_occasion = 1
    self.invalid_reason = None
    self.error = ''

    #MODEL PREDICTIONS
    self.predictions = {}

    #Day Level
    self.days = []
    self.day_level_data = pd.DataFrame()

    #Event Level
    self.events = []
    self.event_level_data = pd.DataFrame()
    self.events_with_no_skyn_data = pd.DataFrame()
    self.event_labels = pd.DataFrame()

    #Curve Level
    self.curves = []
    self.curve_features = pd.DataFrame()
  
  def save_as_sdp(self, valid=True):
    save_to_computer(self, 
      f'{self.subid}_{self.dataset_identifier}_skyn_data_{"processed" if valid else "invalid"}.sdp',
      self.processed_data_out_folder
    )  
  
  def log_error(self):
    error_file = f'{self.error_logs_folder}{self.subid}_{self.dataset_identifier}_process_error_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.txt'
    with open(error_file, 'w') as file:
      file.write(self.error)

  def adjust_for_gaps_and_non_wear(self, export_excel = False):
    print(f'Processing Skyn Dataset: {self.subid} - {self.dataset_identifier}')  

    try:
      if 'device_turned_on' not in self.dataset.columns:
        self.dataset = fill_device_off_gaps(self.dataset)
      self.dataset['Duration_Hrs'] = (self.dataset['datetime'] - self.dataset['datetime'].iloc[0]).dt.total_seconds() / 3600
      # assert (self.dataset['datetime'].diff().dt.total_seconds() == 60).all(), "Rows are not spaced by one minute"
      self.dataset = generate_row_features(self)
      self.dataset = label_device_non_wear_using_cutoff(self.dataset)
      self.dataset = label_device_non_wear_using_model(self.dataset)
      self.dataset = compare_non_wear_methods(self.dataset, 'device_worn_temp_cutoff', 'device_worn_model', comparison_name = 'cutoff_vs_model')
      # self.dataset = label_signal_stability(self.dataset)
      # self.dataset = label_signal_stability_when_device_equipped(self.dataset)

      self.save_as_sdp(valid=True)

      if export_excel:
        self.dataset.to_excel(f'{self.data_out_folder}/processed_{self.subid}_{self.dataset_identifier}.xlsx')
      
    except Exception:
      self.error = traceback.format_exc()
      self.log_error()
      self.save_as_sdp(valid=False)  
  
  def smooth_and_impute(self, reset_tac = True, median_smooth = True, impute_gaps = True, impute_non_wear = True, impute_jumps = False, impute_plummets = False, savgol_smooth = False, export_excel = False):
    print(f'Processing Skyn Dataset: {self.subid} - {self.dataset_identifier}')  
    try:
      if reset_tac:
        raw_dataset = configure_raw_data(self)
        raw_dataset_gaps_filled = fill_device_off_gaps(raw_dataset)
        self.dataset['TAC'] = raw_dataset_gaps_filled['TAC'].copy()

      #TAC_pre_smoothing keeps the original raw - TAC will be cleaned/smoothed and remain the highest quality set
      self.dataset['TAC_pre_smoothing'] = self.dataset['TAC'].copy()

      if median_smooth:
        #Smooth signal with moving median
        self.dataset['TAC'] = self.dataset['TAC'].rolling(window=30, min_periods=1, center=True).median()
        self.dataset.loc[self.dataset['device_turned_on'] == 0, 'TAC'] = np.nan

      if any([impute_gaps, impute_non_wear, impute_jumps, impute_plummets]):
        self.dataset = impute_low_quality_data(self.dataset, impute_gaps=impute_gaps, impute_non_wear=impute_non_wear, impute_jumps=impute_jumps, impute_plummets=impute_plummets)
      
      self.dataset['TAC_pre_smoothed'] = self.dataset['TAC'].copy()  # Save original TAC values
      if savgol_smooth:
        self.dataset = smooth_savgol(self.dataset, window_length=41, polyorder=3)
      
      self.dataset = label_negative_values(self.dataset)
      
      if export_excel:
        self.dataset.to_excel(f'{self.data_out_folder}/processed_{self.subid}_{self.dataset_identifier}.xlsx', index=False)

      self.save_as_sdp(valid=True)
        
    except Exception:
      self.error = traceback.format_exc()
      self.log_error()
      self.save_as_sdp(valid=False)  
  
  def identify_curves(self, curve_threshold = 'auto', curve_attrs = {}):
    self.curve_features = pd.DataFrame()
    try:
      if curve_threshold == 'auto':
        self.curve_threshold, unadjusted_curve_threshold = determine_curve_threshold(self.dataset)
      else:
        self.curve_threshold = curve_threshold
        unadjusted_curve_threshold = curve_threshold
      curve_start_and_end_indices = get_start_and_end_of_discrete_curves(self.dataset, self.curve_threshold)

      if curve_attrs['merge_curves_within_duration'] > 0:
        curve_start_and_end_indices = merge_nearby_curves(curve_start_and_end_indices, max_curve_separation_minutes=curve_attrs['merge_curves_within_duration']*60)
      
      curve_id = 0
      rows = []
      self.curves = []
      # if all(key in event_attrs for key in ['data', 'subid_column', 'start_column', 'drink_total', 'ema_id']):
      for curve_start, curve_end in curve_start_and_end_indices:
        curve = Curve(self.dataset, self.subid, self.dataset_identifier, curve_id, curve_start, curve_end, self.curve_threshold, curve_attrs['curve_flags'], curve_attrs['periphery_flags'], curve_attrs['periphery_buffer_before'], curve_attrs['periphery_buffer_after'])
          # curve.match_curve_to_event(event_attrs['subid_column'], event_attrs['start_column'], event_attrs['ema_id'])
          # curve.create_graphs(self.plot_folder, drink_total_column=event_attrs['drink_total'], self_report_start_time=event_attrs['start_column'])
        # else:
        #   curve = Curve(self.dataset, self.subid, self.dataset_identifier, curve_id, curve_start, curve_end, self.curve_threshold, curve_attrs['curve_flags'], curve_attrs['periphery_flags'], curve_attrs['periphery_buffer_before'], curve_attrs['periphery_buffer_after'])
        #   curve.create_graphs(self.plot_folder)
        # curve.evaluate_self_report_region(self.plot_folder, event_attrs['drink_total'])
        self.curves.append(curve)
        rows.append(curve.row)
        curve_id += 1

      if len(self.curves) > 0:
        self.curve_features = pd.DataFrame(rows, columns=curve.features.columns)
        self.curve_features['unadjusted_threshold'] = unadjusted_curve_threshold
      # self.curve_features = identify_overlapping_curves(self.curve_features)
      self.curve_features.to_excel(f'{self.data_out_folder}/curve_features_{self.subid}_{self.dataset_identifier}.xlsx', index=False)
      
      self.save_as_sdp(valid=True)

    except Exception:
      self.error = traceback.format_exc()
      self.log_error()
      self.save_as_sdp(valid=False)
  
  def configure_event_data(self, data: pd.DataFrame, subid_column, ema_id_column, drink_total_column, event_timestamp_columns, buffer_before=1, buffer_after=0, export_excel=False):
    self.events = data[(data[subid_column] == str(self.subid)) | (data[subid_column] == int(self.subid))]
    event_timestamps = []
    timestamp_labels = []
    ema_ids = []
    drink_totals = []
    for i, row, in self.events.iterrows():
      event_timestamps.extend([row[col] for col in event_timestamp_columns if pd.notna(row[col]) and isinstance(row[col], pd.Timestamp)])
      if row[drink_total_column]:
        timestamp_labels.extend([f'{col.replace("timestamp", "")}_{row[drink_total_column]}drks_{row[ema_id_column]}' for col in event_timestamp_columns if pd.notna(row[col]) and isinstance(row[col], pd.Timestamp)])
      else:
        timestamp_labels.extend([f'{col.replace("timestamp", "")}_{row[ema_id_column]}' for col in event_timestamp_columns if pd.notna(row[col]) and isinstance(row[col], pd.Timestamp)])
      ema_ids.extend([row[ema_id_column] for col in event_timestamp_columns if pd.notna(row[col]) and isinstance(row[col], pd.Timestamp)])
      drink_totals.extend([row[drink_total_column] for col in event_timestamp_columns if pd.notna(row[col]) and isinstance(row[col], pd.Timestamp)])
    
    subids = [self.subid for i in range(0, len(event_timestamps))]
    self.event_labels = pd.DataFrame({
      'ID': subids,
      'timestamp': event_timestamps,
      'label': timestamp_labels,
      'ema_id': ema_ids,
      'drink_total': drink_totals
    })

    for curve_type in ['WITHIN_CURVE', 'PRIOR_CURVE', 'NEXT_CURVE']:
      for curve_relation_column in ['id', 'event_diff_start', 'event_diff_end']:
        self.event_labels[f'{curve_relation_column}_{curve_type}'] = None
    
    self.curve_features['CURVE_event_match_before_buffer'] = buffer_before
    self.curve_features['CURVE_event_match_after_buffer'] = buffer_after
    self.curve_features['CURVE_MATCH_START'] = self.curve_features['begin_CURVE'] - pd.Timedelta(hours=buffer_before)
    self.curve_features['CURVE_MATCH_END'] = self.curve_features['end_CURVE'] + pd.Timedelta(hours=buffer_after)

    for i, row in self.event_labels.iterrows():
      curve_within = self.curve_features[
        (self.curve_features['CURVE_MATCH_START'] <= row['timestamp']) & 
        (self.curve_features['CURVE_MATCH_END'] >= row['timestamp'])
      ].reset_index(drop=True) #curve that started before event and ended after event
      curves_before = self.curve_features[self.curve_features['CURVE_MATCH_START'] <= row['timestamp']].reset_index(drop=True) #curves that started before event
      curves_after = self.curve_features[self.curve_features['CURVE_MATCH_START'] >= row['timestamp']].reset_index(drop=True) #curve that started after event
      if not curve_within.empty:
        curve_data = curve_within.loc[curve_within['CURVE_MATCH_START'].idxmax()]
        self.event_labels.loc[i,'id_WITHIN_CURVE'] = curve_data['curve_id']
        self.event_labels.loc[i,'event_diff_start_WITHIN_CURVE'] = (curve_data['begin_CURVE'] - row['timestamp']).total_seconds() / 3600
        self.event_labels.loc[i,'event_diff_end_WITHIN_CURVE'] = (curve_data['end_CURVE'] - row['timestamp']).total_seconds() / 3600
      if not curves_before.empty:
        curve_data = curves_before.loc[curves_before['CURVE_MATCH_START'].idxmax()]
        #if curve before matched to curve within, re-assign curve before to one more before
        if curve_data['curve_id'] == self.event_labels.loc[i,'id_WITHIN_CURVE']:
          idx = curves_before['CURVE_MATCH_START'].idxmax()
          if idx in curves_before.index and curves_before.index.get_loc(idx) > 0:
            prev_idx = curves_before.index[curves_before.index.get_loc(idx) - 1]
            curve_data = curves_before.loc[prev_idx]
          else:
            curve_data = pd.DataFrame()
        if not curve_data.empty:
          self.event_labels.loc[i,'id_PRIOR_CURVE'] = curve_data['curve_id']
          self.event_labels.loc[i,'event_diff_start_PRIOR_CURVE'] = (curve_data['begin_CURVE'] - row['timestamp']).total_seconds() / 3600
          self.event_labels.loc[i,'event_diff_end_PRIOR_CURVE'] = (curve_data['end_CURVE'] - row['timestamp']).total_seconds() / 3600
      if not curves_after.empty:
        curve_data = curves_after.loc[curves_after['CURVE_MATCH_START'].idxmin()]
        #if curve after matched to curve within, re-assign curve before to one more in the future
        if curve_data['curve_id'] == self.event_labels.loc[i,'id_WITHIN_CURVE']:
          idx = curves_after['CURVE_MATCH_START'].idxmin()
          if idx in curves_after.index and curves_after.index.get_loc(idx) < len(curves_after) - 1:
            next_idx = curves_after.index[curves_after.index.get_loc(idx) + 1]
            curve_data = curves_after.loc[next_idx]
          else:
            curve_data = pd.DataFrame()
        if not curve_data.empty:
          self.event_labels.loc[i,'id_NEXT_CURVE'] = curve_data['curve_id']
          self.event_labels.loc[i,'event_diff_start_NEXT_CURVE'] = (curve_data['begin_CURVE'] - row['timestamp']).total_seconds() / 3600
          self.event_labels.loc[i,'event_diff_end_NEXT_CURVE'] = (curve_data['end_CURVE'] - row['timestamp']).total_seconds() / 3600
    
    self.event_labels['relative_position_WITHIN_CURVE'] = (self.event_labels['event_diff_start_WITHIN_CURVE'] * -1) / (self.event_labels['event_diff_end_WITHIN_CURVE'] + (self.event_labels['event_diff_start_WITHIN_CURVE'] * -1))

    if export_excel:
      self.event_labels.to_excel(f'{self.data_out_folder}/event_labels_{self.subid}_{self.dataset_identifier}.xlsx', index=False)

    self.save_as_sdp(valid=True)

  def make_curve_graphs(self, export_excel = True):
    rows = []
    for curve in self.curves:
      if len(self.event_labels):
        curve.update_plot_annotations(self.event_labels)
      curve.create_graphs(self.plot_folder)
      rows.append(curve.row)
    
    if len(self.curves) > 0:
      updated_curve_features = pd.DataFrame(rows, columns=curve.features.columns)
      self.curve_features.update(updated_curve_features[[col for col in updated_curve_features.columns if '_plot' in col]])
    
    if export_excel:
      self.curve_features.to_excel(f'{self.data_out_folder}/curve_features_{self.subid}_{self.dataset_identifier}.xlsx', index=False)
    
    self.save_as_sdp(valid=True)

  def set_ema_regions(self, export_excel=True):
    self.ema_regions = []
    ema_region_feature_dictionaries = []
    for ema_id in self.event_labels['ema_id'].unique():
      one_alcohol_event = self.event_labels[
        (self.event_labels['ema_id'] == ema_id) &
        (self.event_labels['label'].str.contains('drink', na=False))
      ]
      if not one_alcohol_event.empty:
        idx = one_alcohol_event['timestamp'].idxmin()

        if pd.notna(idx):  # Ensure idx is valid
          drink_start = one_alcohol_event.loc[idx, 'timestamp']
          ema_region = emaRegion(self.dataset, self.subid, self.dataset_identifier, ema_id, drink_start, self.event_labels)
          self.ema_regions.append(ema_region)
          ema_region.make_device_removal_plot(self.plot_folder)
          ema_region.make_signal_processing_plot(self.plot_folder, self.curve_threshold, one_alcohol_event.loc[idx, 'drink_total'])
          ema_region_feature_dictionaries.append(ema_region.self_report_region_quality_features)
    self.ema_region_features = pd.DataFrame(ema_region_feature_dictionaries)
    self.event_labels = self.event_labels.merge(self.ema_region_features, on='ema_id', how='left')
    if export_excel:
      self.event_labels.to_excel(f'{self.data_out_folder}/event_labels_{self.subid}_{self.dataset_identifier}.xlsx', index=False)
    self.save_as_sdp(valid=True)
    
  # def match_events_to_curves(self, ema_id_column, drink_total_column, drink_start_timestamp_column, event_timestamp_columns):
  #   try:
  #     for curve in self.curves:
  #       curve.identify_proximal_events(self.event_labels, buffer_before = 1, buffer_after = 0)
  #   except Exception:
  #     self.error = traceback.format_exc()
  #     self.log_error()
  #     self.save_as_sdp(valid=False)

  def run_day_level_analysis(self, day_start_hour = 0, non_wear_self_report_column = '', morning_report = pd.DataFrame(), make_graphs=False):
    print(f'Analyzing Days: {self.subid} - {self.dataset_identifier}')  
    self.days = [] #reset to empty
    self.day_level_data = pd.DataFrame() #reset to empty
    try:
      day_start_end_pairs = get_day_level_indices(self.dataset, day_start_hour, )
      day_id = 0
      for start, end in day_start_end_pairs:
        print(start, end)
        print(self.dataset.index[0], self.dataset.index[-1])
        day = skynDay(self.dataset, start, end, non_wear_self_report_column = non_wear_self_report_column)
        self.days.append(day)
        if make_graphs:
          plot_path = plot_device_removal(
            day.day_dataset, self.plot_folder, self.subid, day_id, self.dataset_identifier, 
            'Temperature_C', 'datetime', motion_variable='Motion', add_color=True, 
            method = 'Model Predictions', prediction_column = 'device_worn_model', df_version = f'DAY{day_id}',
            subtitle_text = f'{self.subid} -- Day: {day_id} -- Algorithm Non-Wear Detection'
          )
          self.plot_paths.append(plot_path)
          """ PLAIN PLOT (NO PREDS) """
          plot_path = plot_temperature_motion(
            day.day_dataset, self.plot_folder, self.subid, day_id, self.dataset_identifier, 'Temperature_C', 'datetime',
            add_color=True, subtitle_text = f'Subject ID: {self.subid} | Day: {day_id}', motion_variable='Motion'
          )
          
          self.plot_paths.append(plot_path)
        day_id += 1

      self.day_level_data = create_day_level_dataframe(self.days, self.subid, self.dataset_identifier, morning_report=morning_report)
      
      with pd.ExcelWriter(f'{self.data_out_folder}/processed_{self.subid}_{self.dataset_identifier}.xlsx', engine='xlsxwriter') as writer:
        self.dataset.to_excel(writer, sheet_name='processed_data', index=False)
        signal_quality_feature_key.to_excel(writer, sheet_name='key', index=False)

      with pd.ExcelWriter(f'{self.data_out_folder}/dayLevel_{self.subid}_{self.dataset_identifier}.xlsx', engine='xlsxwriter') as writer:
        self.day_level_data.set_index('DayNo').to_excel(writer, sheet_name='day-level-results')
        signal_quality_aggregate_feature_key.to_excel(writer, sheet_name='key', index=False)

      self.save_as_sdp(valid=True)

    except Exception:
      self.error = traceback.format_exc()
      self.log_error()
      self.save_as_sdp(valid=False)

  def run_event_level_analysis(
      self, event_data, 
      drink_start_column = 'drkstarttime_m', 
      drink_total_column = 'totsd_all_m',
      day_id_column = 'STUDYDAY',
      extra_columns = [],
      search_method = 'peak',
      curve_threshold = 10,
      curve_search_pad_hours_before = 2,
      curve_search_pad_hours_after = 22,
      allow_duplicate_events = False,
      include_prior_curves = False,
      include_subsequent_curves = False,
      make_plots = True,
      save = True
    ):
    #TBD: Common formatting for event_files
    print(f'Analyzing Events: {self.subid} - {self.dataset_identifier}') 
    # self.dataset.to_excel(f'test_{self.subid}.xlsx')
    self.events = []  #reset to empty
    self.event_level_data = pd.DataFrame() #reset to empty
    try:
      event_data[drink_start_column] = pd.to_datetime(event_data[drink_start_column])
      alcohol_event_indices, extra_info = get_event_level_indices(
        self.subid, self.dataset, event_data,
        pad_hours_before = curve_search_pad_hours_before,
        pad_hours_after = curve_search_pad_hours_after, 
        drink_start_column = drink_start_column, 
        drink_total_column = drink_total_column,
        day_id_column = day_id_column,
        extra_columns = extra_columns,
        append_duplicates=allow_duplicate_events
      )
      self.curve_datasets = []
      self.search_datasets = []
      self.no_skyn_data_events = []
      if curve_threshold == 'auto':
        curve_threshold, unadjusted_curve_threshold = determine_curve_threshold(self.dataset)
      for event_number, event_details in enumerate(alcohol_event_indices):
        start, end, drink_total, day_id = event_details[:4]
        if start is not None and end is not None:
          event = alcoholEvent(
            self.dataset, self.subid, self.dataset_identifier, event_number, start, end, 
            drink_total = drink_total, 
            day_id = day_id, 
            extra_info = extra_info[event_number], 
            search_method = search_method, 
            curve_threshold=curve_threshold, 
            include_prior_curves=include_prior_curves,
            include_subsequent_curves=include_subsequent_curves
          )
          event.get_features_of_search_dataset()
          event.get_features_of_curve_dataset()
          event.set_search_plot_dataset()
          event.set_curve_plot_dataset()
          
          if event.quality_features_of_search['data_found_SEARCH'] and make_plots:
            plot_path = event.save_plot_smooth_tac(self.plot_folder, 'SEARCH')
            self.tac_smooth_search_plot_paths[event_number] = plot_path
            plot_path = event.save_plot_of_device_removal(self.plot_folder, 'SEARCH')
            self.non_wear_search_plot_paths[event_number] = plot_path
            plot_path = event.save_plot_of_signal_processing(self.plot_folder, 'SEARCH')
            self.tac_processing_search_plot_paths[event_number] = plot_path
          else:
            self.tac_smooth_search_plot_paths[event_number] = ''
            self.non_wear_search_plot_paths[event_number] = ''
            self.tac_processing_search_plot_paths[event_number] = ''
          
          if event.quality_features_of_curve['data_found_CURVE'] and make_plots:
            plot_path = event.save_plot_smooth_tac(self.plot_folder, 'CURVE')
            self.tac_smooth_curve_plot_paths[event_number] = plot_path
            plot_path = event.save_plot_of_device_removal(self.plot_folder, 'CURVE')
            self.non_wear_curve_plot_paths[event_number] = plot_path
            plot_path = event.save_plot_of_signal_processing(self.plot_folder, 'CURVE')
            self.tac_processing_curve_plot_paths[event_number] = plot_path
          else:
            self.tac_smooth_curve_plot_paths[event_number] = ''
            self.non_wear_curve_plot_paths[event_number] = ''
            self.tac_processing_curve_plot_paths[event_number] = ''
            
          self.events.append(event)
          event.curve_dataset['unadjusted_threshold'] = unadjusted_curve_threshold
          self.curve_datasets.append(event.curve_dataset)
        else:
          self.tac_smooth_search_plot_paths[event_number] = ''
          self.non_wear_search_plot_paths[event_number] = ''
          self.tac_processing_search_plot_paths[event_number] = ''
          self.tac_smooth_curve_plot_paths[event_number] = ''
          self.non_wear_curve_plot_paths[event_number] = ''
          self.tac_processing_curve_plot_paths[event_number] = ''
          info = {
            'subid': self.subid,
            'dataset_identifier': self.dataset_identifier,
            'event': event_number,
            'drink_total': drink_total,
            'day_id': day_id,
          }
          info.update(extra_info[event_number])
          self.no_skyn_data_events.append(
            pd.DataFrame([info])
          )
          #subid dataset_id drink_total day_id extra info as pandas.dataframe
        # event.curve_dataset.to_excel(f'curve_{self.subid}_{event.day_id}.xlsx')
      
      self.event_level_data = create_event_level_dataframe(self.subid, self.dataset_identifier, self.events)
      self.event_level_data = identify_overlapping_curves(self.event_level_data)
      self.event_level_data['unadjusted_threshold'] = unadjusted_curve_threshold
      self.events_with_no_skyn_data = (
          pd.concat(self.no_skyn_data_events)
          if len(self.no_skyn_data_events)
          else pd.DataFrame(
              columns=['subid', 'dataset_identifier', 'drink_total', 'day_id'] + list(extra_info[0].keys())
          )
      )      
      all_event_data = pd.concat(self.curve_datasets, ignore_index=True)
        
      with pd.ExcelWriter(f'{self.data_out_folder}/eventLevel_{self.subid}_{self.dataset_identifier}.xlsx', engine='xlsxwriter') as writer:
        self.event_level_data.to_excel(writer, sheet_name='event-features', index=False)
        all_event_data.to_excel(writer, sheet_name='event-data')
        self.events_with_no_skyn_data.to_excel(writer, sheet_name = 'events-no-skyn', index=False)
      if save:
        self.save_as_sdp(valid=True)

    except Exception:
      self.error = traceback.format_exc()
      self.log_error()
      if save:
        self.save_as_sdp(valid=False)

