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
      print('generating row features')
      self.dataset = generate_row_features(self)
      
      print('labeling non-wear')
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
  
  def smooth_and_impute(self, median_smooth = True, impute_low_quality = True, savgol_smooth = False, export_excel = False):
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
      if impute_low_quality:
        self.dataset, self.imputation_info = impute_low_quality_data(self.dataset)
      
      self.dataset['TAC_pre_savgol'] = self.dataset['TAC'].copy()
      if savgol_smooth:
        self.dataset = smooth_savgol(self.dataset, window_length=11, polyorder=3)
            
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

      self.raw_curves = []
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
        self.raw_curve_features.to_excel(
          f'{self.data_out_folder}/raw_curve_features_{self.subid}_{self.dataset_identifier}.xlsx', 
          index=False
        )
      else:
        self.raw_curve_features = pd.DataFrame(columns=self.curve_columns)

      self.save_as_sdp(valid=True)

    except Exception as e:
      self.error = traceback.format_exc()
      self.log_error()
      self.save_as_sdp(valid=False)
      raise ValueError(f"Failed to identify curves: {str(e)}")
  
  def configure_event_data(self, data: pd.DataFrame, subid_column, ema_id_column, drink_total_column, event_timestamp_columns, buffer_before=2, buffer_after=0, max_event_duration=12, export_excel=False):
    print(f'Configuring event data for {self.subid} - {self.dataset_identifier}')
    try:
      self.events = data[(data[subid_column] == str(self.subid)) | (data[subid_column] == int(self.subid))]
      self.events['max_event_duration'] = max_event_duration
      # Initialize timestamp columns for all rows
      self.events['earliest_timestamp'] = pd.NaT
      self.events['latest_timestamp'] = pd.NaT
      self.events['matching_end_timestamp'] = pd.NaT
      self.events['end_timestamp_modified'] = False
      self.events['modification_note'] = ''
      self.events['ema_id'] = None
      # Convert timestamp columns to datetime
      for col in event_timestamp_columns:
        if col in self.events.columns:
          self.events[col] = pd.to_datetime(self.events[col], errors='coerce')
      
      self.event_labels = pd.DataFrame(columns=['timestamp', 'label'])
      event_ranges = []
      for i, row in self.events.iterrows():
        valid_timestamps = [
          row[col] for col in event_timestamp_columns 
          if pd.notna(row[col]) and isinstance(row[col], pd.Timestamp)
        ]
        
        # Handle cases where end timestamp is null or same as start timestamp
        timestamp_modified = False
        if len(valid_timestamps) == 1 or (len(valid_timestamps) == 2 and valid_timestamps[0] == valid_timestamps[1]):
          # If only start timestamp exists or start/end are the same, set end to start + 6 hours
          start_timestamp = row['drinkStart'] if pd.notna(row['drinkStart']) else row['drinkEnd']
          end_timestamp = start_timestamp + pd.Timedelta(hours=6)
          
          # Update the row data
          row['drinkEnd'] = end_timestamp
          timestamp_modified = True
          
          # Recalculate valid timestamps
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
          self.events.loc[i, 'end_timestamp_modified'] = timestamp_modified
          if timestamp_modified:
            self.events.loc[i, 'modification_note'] = 'drinkEnd set to drinkStart + 6 hours (was null or same as start)'
            # Update the original DataFrame with the modified drinkEnd
            self.events.loc[i, 'drinkEnd'] = row['drinkEnd']
          
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
          
          print(earliest_label)
          print(self.event_labels)

          # Get middle timestamps (excluding earliest and latest, and only including valid timestamps)
          middle_timestamps = [
              row[col] for col in event_timestamp_columns 
              if col not in [earliest_col, latest_col] 
              and pd.notna(row[col]) 
              and isinstance(row[col], pd.Timestamp)
          ]
          middle_abbreviated_labels = [f'EMA' for i in range(len(middle_timestamps))]
          print(middle_abbreviated_labels)
          print(middle_timestamps)

          # Only add middle timestamps if there are any
          if middle_timestamps:
              self.event_labels = pd.concat([self.event_labels, pd.DataFrame({'timestamp': middle_timestamps, 'label': middle_abbreviated_labels})], ignore_index=True)

          latest_label = f'{latest_col}_{row[ema_id_column]}{drink_suffix}'
          self.event_labels = pd.concat([self.event_labels, pd.DataFrame({'timestamp': [latest_timestamp], 'label': [latest_label]})], ignore_index=True)

          event_ranges.append({
            'ema_id': row[ema_id_column],
            'drink_total': row[drink_total_column],
            'earliest_timestamp': earliest_timestamp,
            'latest_timestamp': latest_timestamp,
            'matching_end_timestamp': matching_end_timestamp
          })
      if len(self.curve_features) > 0:
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
                overlap_duration = (overlap_end - overlap_start).total_seconds() if (overlap_end - overlap_start).total_seconds() > 0 else 0
                curve_duration = (curve['CURVE_MATCH_END'] - curve['CURVE_MATCH_START']).total_seconds()
                overlap_proportion = overlap_duration / curve_duration if curve_duration > 0 else None
                
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
        if pd.notna(row['ema_id']) and pd.notna(row['earliest_timestamp']):
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

  def run_day_level_analysis(self, day_start_hour = 0, non_wear_self_report_column = '', morning_report = pd.DataFrame(), make_graphs=False, export_processed_data=False):
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
      
      if export_processed_data:
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

