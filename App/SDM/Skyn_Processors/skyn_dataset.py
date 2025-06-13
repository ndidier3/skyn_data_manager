from .skyn_datapoint import skynDatapoint
from ..Configuration.configuration import *
from ..Configuration.day_level import get_day_level_indices, create_day_level_dataframe
from ..Configuration.event_level import get_event_level_indices, create_event_level_dataframe
from ..Configuration.file_management import *
from ..Crop.crop import *
from ..Signal_Processing.identify_overlapping_curves import identify_overlapping_curves
from ..Signal_Processing.smooth_signal import smooth_savgol
from ..Signal_Processing.impute import impute_low_quality_data
from ..Signal_Processing.fill_device_off_gaps import fill_device_off_gaps
from ..Signal_Processing.label_device_non_wear import label_device_non_wear_using_cutoff, label_device_non_wear_using_model, compare_non_wear_methods
from ..Signal_Processing.label_signal_stability import *
from ..Signal_Processing.curve_demarcation import *
from ..Skyn_Processors.skyn_day import skynDay
from ..Skyn_Processors.alcohol_event import alcoholEvent
from ..Skyn_Processors.curve import Curve
from App.SDM.Skyn_Processors.ema_region import emaRegion
from ..Visualization.tac import *
from ..Visualization.device_non_wear import *
from ..Feature_Engineering.tac_features import *
from ..Feature_Engineering.row_features import generate_row_features
from ..Feature_Engineering.temperature_clusters import get_temperature_clusters
from ..Documenting.variable_keys import *
# from ..Signal_Processing.revise_incomplete_features import revise_fall_features, revise_rise_features

import pandas as pd
import numpy as np
import traceback
from typing import Union, Dict

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
    self.events = pd.DataFrame()
    self.event_level_data = pd.DataFrame()
    self.events_with_no_skyn_data = pd.DataFrame()
    self.event_labels = pd.DataFrame()

    #Curve Level
    self.curves = []
    self.curve_features = pd.DataFrame()
    self.curve_threshold = 10.0  # Default curve threshold
    self.curve_columns = [
    ]
  
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
      # self.dataset = compare_non_wear_methods(self.dataset, 'device_worn_temp_cutoff', 'device_worn_model', comparison_name = 'cutoff_vs_model')
      # self.dataset = label_signal_stability(self.dataset)
      # self.dataset = label_signal_stability_when_device_equipped(self.dataset)

      self.save_as_sdp(valid=True)

      if export_excel:
        self.dataset.to_excel(f'{self.data_out_folder}/processed_{self.subid}_{self.dataset_identifier}.xlsx')
      
    except Exception:
      self.error = traceback.format_exc()
      self.log_error()
      self.save_as_sdp(valid=False)  
  
  def smooth_and_impute(self, median_smooth = True, impute_gaps = True, impute_non_wear = True, impute_jumps = False, impute_plummets = False, savgol_smooth = False, export_excel = False):
    print(f'Processing Skyn Dataset: {self.subid} - {self.dataset_identifier}')  
    try:
      raw_dataset = configure_raw_data(self)
      raw_dataset_gaps_filled = fill_device_off_gaps(raw_dataset)
      self.dataset['TAC'] = raw_dataset_gaps_filled['TAC'].copy()

      #TAC_pre_smoothing keeps the original raw - TAC will be cleaned/smoothed and remain the highest quality set
      self.dataset['TAC_pre_smoothed'] = self.dataset['TAC'].copy()

      if median_smooth:
        #Smooth signal with moving median
        self.dataset['TAC'] = self.dataset['TAC'].rolling(window=30, min_periods=1, center=True).median()
        self.dataset.loc[self.dataset['device_turned_on'] == 0, 'TAC'] = np.nan

      self.dataset['TAC_pre_imputation'] = self.dataset['TAC'].copy()  # Save original TAC values
      if any([impute_gaps, impute_non_wear, impute_jumps, impute_plummets]):
        self.dataset, self.imputation_info = impute_low_quality_data(self.dataset, impute_gaps=impute_gaps, impute_non_wear=impute_non_wear, impute_jumps=impute_jumps, impute_plummets=impute_plummets)
      
      if savgol_smooth:
        self.dataset = smooth_savgol(self.dataset, window_length=41, polyorder=3)
            
      if export_excel:
        self.dataset.to_excel(f'{self.data_out_folder}/processed_{self.subid}_{self.dataset_identifier}.xlsx', index=False)
        if hasattr(self, 'imputation_info'):
          self.imputation_info.to_excel(f'{self.data_out_folder}/imputation_info_{self.subid}_{self.dataset_identifier}.xlsx', index=False)

      self.save_as_sdp(valid=True)
        
    except Exception:
      self.error = traceback.format_exc()
      self.log_error()
      self.save_as_sdp(valid=False)  
  
  def identify_curves(self, curve_attrs: Dict = {}, include_raw_curves = False):
    """
    Identify curves in the dataset using either an automatic or manual threshold.
    
    Args:
      curve_attrs (dict): Additional curve attributes for processing
        - curve_threshold (float | str): Either a numeric threshold or 'auto' to determine automatically
        - merge_curves_within_duration (int): Duration in hours to merge nearby curves
        - flag_selections (dict): Dictionary containing both curve and periphery flags
        - periphery_buffer_before (int): Buffer before curve in hours
        - periphery_buffer_after (int): Buffer after curve in hours
      include_raw_curves (bool): Whether to process curves using raw (unimputed) TAC values
      
    Returns:
      None
      
    Raises:
      ValueError: If curve_threshold is invalid or automatic threshold determination fails
    """
    self.curve_features = pd.DataFrame()
    self.raw_curve_features = pd.DataFrame()
    self.curve_threshold_method = curve_attrs.get('curve_threshold', 'auto')
    
    try:
      # Get curve threshold using the new function
      result = get_curve_threshold_from_method(self.dataset, self.curve_threshold_method)
      self.curve_threshold, unadjusted_curve_threshold, baseline_mean, baseline_sd = result

      # Get curve start and end indices
      curve_start_and_end_indices = get_start_and_end_of_discrete_curves(self.dataset, self.curve_threshold)

      # Merge nearby curves if specified
      if curve_attrs.get('merge_curves_within_duration', 0) > 0:
        curve_start_and_end_indices_with_curve_count = merge_nearby_curves(
          curve_start_and_end_indices, 
          max_curve_separation_minutes=curve_attrs['merge_curves_within_duration']*60
        )
      
      # Process each curve
      curve_id = 0
      rows = []
      self.curves = []
      
      # Get flag selections from curve_attrs
      flag_selections = curve_attrs.get('flag_selections', {})
      
      for curve_start, curve_end, curve_count in curve_start_and_end_indices_with_curve_count:
        curve = Curve(
          self.dataset, 
          self.subid, 
          self.dataset_identifier, 
          curve_id, 
          curve_start, 
          curve_end,
          curve_count, 
          self.curve_threshold, 
          flag_selections,
          curve_attrs.get('periphery_buffer_before', 0),
          curve_attrs.get('periphery_buffer_after', 0)
        )
        self.curves.append(curve)
        rows.append(curve.row)
        curve_id += 1
      
      # Create curve features DataFrame
      if len(self.curves) > 0:
        self.curve_features = pd.DataFrame(rows, columns=curve.features.columns)
      else:
        self.curve_features = pd.DataFrame(columns=self.curve_columns)

      # Add threshold information
      self.curve_features['unadjusted_threshold'] = unadjusted_curve_threshold
      self.curve_features['baseline_mean'] = baseline_mean
      self.curve_features['baseline_sd'] = baseline_sd
      
      # Save results
      self.curve_features.to_excel(
        f'{self.data_out_folder}/curve_features_{self.subid}_{self.dataset_identifier}.xlsx', 
        index=False
      )

      if include_raw_curves:
        curve_start_and_end_indices_raw = adjust_curve_demarcation_for_raw_tac(
          self.dataset, 
          curve_start_and_end_indices_with_curve_count, 
          self.curve_threshold, 
          curve_attrs['merge_curves_within_duration']*60
        )
        assert len(curve_start_and_end_indices_raw) == len(curve_start_and_end_indices_with_curve_count), \
          f"Length mismatch between raw and processed curve indices: {len(curve_start_and_end_indices_raw)} vs {len(curve_start_and_end_indices_with_curve_count)}"
        
        #process each curve using raw (unimputed) TAC
        curve_id = 0
        raw_rows = []
        self.raw_curves = []
        for curve_start, curve_end, curve_count in curve_start_and_end_indices_raw:
          curve = Curve(
            self.dataset, 
            self.subid, 
            self.dataset_identifier, 
            curve_id, 
            curve_start, 
            curve_end, 
            curve_count, 
            self.curve_threshold, 
            flag_selections,
            curve_attrs.get('periphery_buffer_before', 0),
            curve_attrs.get('periphery_buffer_after', 0),
            TAC_column='TAC_pre_imputation'
          )
          self.raw_curves.append(curve)
          raw_rows.append(curve.row)
          curve_id += 1

        if len(self.raw_curves) > 0:
          self.raw_curve_features = pd.DataFrame(raw_rows, columns=curve.features.columns)
        else:
          self.raw_curve_features = pd.DataFrame(columns=self.curve_columns)

        self.raw_curve_features.to_excel(
          f'{self.data_out_folder}/raw_curve_features_{self.subid}_{self.dataset_identifier}.xlsx', 
          index=False
        )

      self.save_as_sdp(valid=True)

    except Exception as e:
      self.error = traceback.format_exc()
      self.log_error()
      self.save_as_sdp(valid=False)
      raise ValueError(f"Failed to identify curves: {str(e)}")
  
  def configure_event_data(self, data: pd.DataFrame, subid_column, ema_id_column, drink_total_column, event_timestamp_columns, buffer_before=2, buffer_after=0, max_event_duration=12, export_excel=False):
    try:
      self.events = data[(data[subid_column] == str(self.subid)) | (data[subid_column] == int(self.subid))]
      self.events['max_event_duration'] = max_event_duration
      self.event_labels = pd.DataFrame(columns=['timestamp', 'label'])
      event_ranges = []
      for i, row in self.events.iterrows():
        valid_timestamps = [
          row[col] for col in event_timestamp_columns 
          if pd.notna(row[col]) and isinstance(row[col], pd.Timestamp)
        ]
        if valid_timestamps:
          earliest_timestamp = min(valid_timestamps)
          latest_timestamp = max(valid_timestamps)
          
          matching_end_timestamp = min(
            latest_timestamp,
            earliest_timestamp + pd.Timedelta(hours=max_event_duration)
          )
          
          # Add timestamps to self.events
          self.events.loc[i, 'earliest_timestamp'] = earliest_timestamp
          self.events.loc[i, 'latest_timestamp'] = latest_timestamp
          self.events.loc[i, 'matching_end_timestamp'] = matching_end_timestamp
          self.events.loc[i, 'drink_total'] = row[drink_total_column]
          self.events.loc[i, 'ema_id'] = row[ema_id_column]
          
          #Creating labels for curve plots
          # Add earliest timestamp label
          # Get drink total suffix if it exists
          drink_suffix = f'_{row[drink_total_column]}drks' if pd.notna(row[drink_total_column]) else '_NAdrks'
          earliest_col = event_timestamp_columns[
              [valid_timestamps.index(earliest_timestamp) for col in event_timestamp_columns 
               if pd.notna(row[col]) and isinstance(row[col], pd.Timestamp) and row[col] == earliest_timestamp][0]
          ]
          latest_col = event_timestamp_columns[
              [valid_timestamps.index(latest_timestamp) for col in event_timestamp_columns 
               if pd.notna(row[col]) and isinstance(row[col], pd.Timestamp) and row[col] == latest_timestamp][0]
          ]

          earliest_label = f'{earliest_col}_{row[ema_id_column]}{drink_suffix}'
          self.event_labels = pd.concat([self.event_labels, pd.DataFrame({'timestamp': [earliest_timestamp], 'label': [earliest_label]})], ignore_index=True)

          latest_label = f'{latest_col}_{row[ema_id_column]}{drink_suffix}'
          self.event_labels = pd.concat([self.event_labels, pd.DataFrame({'timestamp': [latest_timestamp], 'label': [latest_label]})], ignore_index=True)

          event_ranges.append({
            'ema_id': row[ema_id_column],
            'drink_total': row[drink_total_column],
            'earliest_timestamp': earliest_timestamp,
            'latest_timestamp': latest_timestamp,
            'matching_end_timestamp': matching_end_timestamp
          })

      self.curve_features['CURVE_event_match_before_buffer'] = buffer_before
      self.curve_features['CURVE_event_match_after_buffer'] = buffer_after
      self.curve_features['CURVE_MATCH_START'] = pd.to_datetime(self.curve_features['begin_CURVE']) - pd.Timedelta(hours=buffer_before)
      self.curve_features['CURVE_MATCH_END'] = pd.to_datetime(self.curve_features['end_CURVE']) + pd.Timedelta(hours=buffer_after)
      
      # Filter curve features to only include current subject
      subject_curves = self.curve_features[
          (self.curve_features['subid'] == str(self.subid)) | 
          (self.curve_features['subid'] == int(self.subid))
      ].copy()

      # Process event ranges to match curves
      for event_range in event_ranges:
          # Find curves that overlap with this event's time range using matching_end_timestamp
          overlapping_curves = subject_curves[
            ~(
              (subject_curves['CURVE_MATCH_END'] < event_range['earliest_timestamp']) |  
              (subject_curves['CURVE_MATCH_START'] > event_range['matching_end_timestamp'])
            )
          ].sort_values('CURVE_MATCH_START')  # Sort by start time to get earliest first
          
          matching_curve_ids = overlapping_curves['curve_id'].tolist()
          self.events.loc[self.events['ema_id'] == event_range['ema_id'], 'num_curves_matched'] = len(matching_curve_ids)
          
          # Calculate overlap proportions for each matching curve
          for j in range(1, 6):
            match_key = f'curve_match_{j}'
            overlap_key = f'curve_match_{j}_overlap'
            
            if j <= len(matching_curve_ids):
              curve = overlapping_curves.iloc[j-1]
              curve_id = matching_curve_ids[j-1]
              
              # Calculate overlap
              overlap_start = max(event_range['earliest_timestamp'], curve['CURVE_MATCH_START'])
              overlap_end = min(event_range['matching_end_timestamp'], curve['CURVE_MATCH_END'])
              overlap_duration = (overlap_end - overlap_start).total_seconds()
              curve_duration = (curve['CURVE_MATCH_END'] - curve['CURVE_MATCH_START']).total_seconds()
              overlap_proportion = overlap_duration / curve_duration
              
              self.events.loc[self.events['ema_id'] == event_range['ema_id'], match_key] = curve_id
              self.events.loc[self.events['ema_id'] == event_range['ema_id'], overlap_key] = overlap_proportion
            else:
              self.events.loc[self.events['ema_id'] == event_range['ema_id'], match_key] = None
              self.events.loc[self.events['ema_id'] == event_range['ema_id'], overlap_key] = None

      if export_excel:
        self.event_labels.to_excel(f'{self.data_out_folder}/event_labels_{self.subid}_{self.dataset_identifier}.xlsx', index=False)

      self.save_as_sdp(valid=True)

    except Exception:
      self.error = traceback.format_exc()
      self.log_error()
      self.save_as_sdp(valid=False)

  def make_curve_graphs(self, include_raw_curves = False, export_excel = True):
    try:
      rows = []
      for curve in self.curves:
        if len(self.event_labels):
          curve.update_plot_annotations(self.event_labels)
        curve.create_graphs(self.plot_folder)
        rows.append(curve.row)
      
      if len(self.curves) > 0:
        updated_curve_features = pd.DataFrame(rows, columns=curve.features.columns)
        self.curve_features.update(updated_curve_features[[col for col in updated_curve_features.columns if '_plot' in col]])
      
      if include_raw_curves:
        raw_rows = []
        for curve in self.raw_curves:
          if len(self.event_labels):
            curve.update_plot_annotations(self.event_labels)
          curve.create_graphs(self.plot_folder)
          raw_rows.append(curve.row)

      if len(self.raw_curves) > 0:
        updated_raw_curve_features = pd.DataFrame(rows, columns=curve.features.columns)
        self.raw_curve_features.update(updated_raw_curve_features[[col for col in updated_raw_curve_features.columns if '_plot' in col]])

      if export_excel:
        self.curve_features.to_excel(f'{self.data_out_folder}/curve_features_{self.subid}_{self.dataset_identifier}.xlsx', index=False)
      
      self.save_as_sdp(valid=True)

    except Exception:
      self.error = traceback.format_exc()
      self.log_error()
      self.save_as_sdp(valid=False)

  def set_ema_regions(self, export_excel=True):
    try:
      self.ema_regions = []
      ema_region_feature_dictionaries = []
      for i, row in self.events.iterrows():
        if pd.notna(row['ema_id']):
          drink_start = row['earliest_timestamp']
          drink_total = row['drink_total']
          ema_id = row['ema_id']
          ema_region = emaRegion(self.dataset, self.subid, self.dataset_identifier, ema_id, drink_start, self.event_labels)
          ema_region.make_device_removal_plot(self.plot_folder)
          ema_region.make_signal_processing_plot(self.plot_folder, self.curve_threshold, drink_total)
          ema_region_feature_dictionaries.append(ema_region.self_report_region_quality_features)
          self.ema_regions.append(ema_region)
      self.ema_region_features = pd.DataFrame(ema_region_feature_dictionaries)

      if len(self.ema_region_features) > 0:
        self.events = self.events.merge(self.ema_region_features, on='ema_id', how='left')
      if export_excel:
        self.events.to_excel(f'{self.data_out_folder}/event_labels_{self.subid}_{self.dataset_identifier}.xlsx', index=False)
      self.save_as_sdp(valid=True)

    except Exception:
      self.error = traceback.format_exc()
      self.log_error()
      self.save_as_sdp(valid=False)

  def run_day_level_analysis(self, day_start_hour = 0, non_wear_self_report_column = '', morning_report = pd.DataFrame(), make_graphs=False):
    print(f'Analyzing Days: {self.subid} - {self.dataset_identifier}')  
    self.days = [] #reset to empty
    self.day_level_data = pd.DataFrame() #reset to empty
    try:
      day_start_end_pairs = get_day_level_indices(self.dataset, day_start_hour)
      day_id = 0
      for start, end in day_start_end_pairs:
        print(start, end)
        print(self.dataset.index[0], self.dataset.index[-1])
        day = skynDay(self.dataset, start, end, non_wear_self_report_column = non_wear_self_report_column)
        self.days.append(day)
        if make_graphs:
          # Generate device removal plot
          device_removal_plot = plot_device_removal(
            day.day_dataset, self.plot_folder, self.subid, day_id, self.dataset_identifier, 
            'Temperature_C', 'datetime', motion_variable='Motion', add_color=True, 
            method = 'Model Predictions', prediction_column = 'device_worn_model', df_version = f'DAY{day_id}',
            subtitle_text = f'{self.subid} -- Day: {day_id+1} -- Algorithm Non-Wear Detection'
          )
          self.plot_paths.append(device_removal_plot)
          
          # Generate signal processing plot
          signal_processing_plot = plot_signal_processing(
            day.day_dataset, self.plot_folder, self.subid, day_id, self.dataset_identifier, f'DAY{day_id}',
            self.curve_threshold, time_variable='datetime', title = f'Signal Processing',
            subtitle_text = f'{self.subid} -- Day: {day_id}'
          )
          self.plot_paths.append(signal_processing_plot)
          
          # Add plot paths to day object
          day.device_removal_plot = device_removal_plot
          day.signal_processing_plot = signal_processing_plot
        day_id += 1

      self.day_level_data = create_day_level_dataframe(self.days, self.subid, self.dataset_identifier, morning_report=morning_report)
      
      with pd.ExcelWriter(f'{self.data_out_folder}/processed_{self.subid}_{self.dataset_identifier}.xlsx', engine='xlsxwriter') as writer:
        self.dataset.to_excel(writer, sheet_name='processed_data', index=False)
        signal_quality_feature_key.to_excel(writer, sheet_name='key', index=False)

      with pd.ExcelWriter(f'{self.data_out_folder}/dayLevel_{self.subid}_{self.dataset_identifier}.xlsx', engine='xlsxwriter') as writer:
        self.day_level_data.set_index('day_no').to_excel(writer, sheet_name='day-level-results')
        signal_quality_aggregate_feature_key.to_excel(writer, sheet_name='key', index=False)

      self.save_as_sdp(valid=True)

    except Exception:
      self.error = traceback.format_exc()
      self.log_error()
      self.save_as_sdp(valid=False)

  def run_event_level_analysis(
      self, event_data, 
      drink_start_column = 'drinkstarttime_m', 
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

