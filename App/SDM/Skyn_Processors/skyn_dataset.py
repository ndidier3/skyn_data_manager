from ..Configuration.configuration import *
from ..Configuration.day_level import get_day_level_indices, create_day_level_dataframe
from ..Configuration.file_management import *
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
from ..Event_Matching.get_event_timestamps import process_event_timestamps
from ..Event_Matching.match_curves_to_events import match_curves_to_events
# from ..Signal_Processing.revise_incomplete_features import revise_fall_features, revise_rise_features

import pandas as pd
import numpy as np
import traceback
from datetime import datetime, date, time
from typing import Dict
from App.SDM.Run.default_settings.default_curve_settings import DEFAULT_RAW_CURVE_ATTRS

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
    self.dataset = configure_raw_data(self, error_logger=self.log_error)

    # Unique device_id(s) in this dataset (for filtering by device type, e.g. new vs old_skyn)
    self.device_ids = self.dataset['device_id'].unique().tolist() if 'device_id' in self.dataset.columns else []
    # Device model: T15 (new) vs T10 (old) vs 'mixed'. From ARC raw data: old IDs start with "20-", new with "31-" or "32-".
    # Label as 'T10' if all devices are T10, 'T15' if all are T15, or 'mixed' if there's a mix
    self.device_model = determine_device_model(self.device_ids)

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
    self.curve_threshold_computed = False  # Flag to track if threshold was computed
    self.curve_threshold_results = {}
    self.curve_columns = [
    ]

    #Curves based on default threshold
    #Only populates if computed threshold is different from default threshold
    #And ensure_default_curve_threshold_applied is True
    self.ensure_default_curve_threshold_applied = False
    self.curves_default_threshold = []
    self.curve_features_default_threshold = pd.DataFrame()
    self.raw_curves = []
    self.raw_curve_features = pd.DataFrame()
    self.raw_curves_default_threshold = []
    self.raw_curve_features_default_threshold = pd.DataFrame()
    self.raw_curve_threshold = 10.0
    self.raw_curve_threshold_computed = False
    self.raw_curve_threshold_results = {}
  
  def save_as_sdp(self, valid=True):
    save_to_computer(self, 
      f'{self.subid}_{self.dataset_identifier}_skyn_data_{"processed" if valid else "invalid"}.sdp',
      self.processed_data_out_folder
    )  
  
  def log_error(self):
    error_file = f'{self.error_logs_folder}{self.subid}_{self.dataset_identifier}_process_error_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.txt'
    with open(error_file, 'w') as file:
      file.write(self.error)

  def filter_dataset_by_date_range(self, first_study_datetime: datetime = None, end_study_datetime: datetime = None):
    """
    Filter the dataset to include only data within the specified datetime range.
    
    Args:
        first_study_datetime: First datetime to include (datetime object, optional, inclusive)
        end_study_datetime: Last datetime to include (datetime object, optional, exclusive)
    
    Returns:
        Filtered dataset
    """
    if first_study_datetime is not None and end_study_datetime is not None:
      self.dataset = self.dataset[(self.dataset['datetime'] >= first_study_datetime) & (self.dataset['datetime'] < end_study_datetime)]
      print(f'Filtered dataset to {len(self.dataset)} rows within datetime range ({first_study_datetime} to {end_study_datetime})')
    elif first_study_datetime is not None:
      self.dataset = self.dataset[self.dataset['datetime'] >= first_study_datetime]
      print(f'Filtered dataset to {len(self.dataset)} rows from {first_study_datetime} onwards')
    elif end_study_datetime is not None:
      self.dataset = self.dataset[self.dataset['datetime'] < end_study_datetime]
      print(f'Filtered dataset to {len(self.dataset)} rows up to {end_study_datetime}')
    else:
      print('Warning: No datetime range specified for filtering. Dataset unchanged.')
    
    return self.dataset

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
  
  def smooth_and_impute(self, impute_low_quality = True, savgol_smooth = False, export_excel = False):
    print(f'Processing Skyn Dataset: {self.subid} - {self.dataset_identifier}')  
    try:
      raw_dataset = configure_raw_data(self, error_logger=self.log_error)
      raw_dataset_gaps_filled = fill_device_off_gaps(raw_dataset)
      self.dataset['TAC'] = raw_dataset_gaps_filled['TAC'].copy()

      self.dataset['TAC_pre_imputation'] = self.dataset['TAC'].copy()  # Save original TAC values
      self.dataset['TAC_smoothed_unimputed'] = self.dataset['TAC_pre_imputation'].copy()
      if savgol_smooth:
        self.dataset = smooth_savgol(
          self.dataset, window_length=15, polyorder=2,
          tac_variable='TAC_smoothed_unimputed', skip_imputed=False
        )
      if impute_low_quality:
        self.dataset, self.imputation_info = impute_low_quality_data(self.dataset)
      
      self.dataset['TAC_pre_savgol'] = self.dataset['TAC'].copy()
      if savgol_smooth:
        self.dataset = smooth_savgol(self.dataset, window_length=15, polyorder=2)
            
      if export_excel:
        self.dataset.to_excel(f'{self.data_out_folder}/processed_{self.subid}_{self.dataset_identifier}.xlsx', index=False)
        if hasattr(self, 'imputation_info'):
          self.imputation_info.to_excel(f'{self.data_out_folder}/imputation_info_{self.subid}_{self.dataset_identifier}.xlsx', index=False)

      self.save_as_sdp(valid=True)
        
    except Exception:
      self.error = traceback.format_exc()
      self.log_error()
      self.save_as_sdp(valid=False)  
  
  def compute_curve_threshold(self, curve_attrs: Dict = {}):
    """
    Determine the curve threshold for the dataset.
    This method only handles threshold determination and saves the results.

    After a successful auto run, the following are pickled with the .sdp:
      - self.curve_threshold_results: dataset-level dict (k, selection_method,
        per-k quality, per-cluster TAC stats, threshold rule)
      - self.dataset.attrs['curve_threshold_results']: same dict
      - self.dataset.attrs['curve_threshold_details']: compute-time details
      - self.dataset.attrs['labeled_cluster_data']: minute-level cluster labels
    
    Args:
      curve_attrs (dict): Curve threshold attributes
        - curve_threshold (float | str): Either a numeric threshold or 'auto' to determine automatically
        - default_threshold (float): Default threshold to use if auto-calculation fails (default: 8.0)
        
    Returns:
      None
      
    Raises:
      ValueError: If curve_threshold is invalid or automatic threshold determination fails
    """
    self.curve_threshold_method = curve_attrs.get('curve_threshold', 'auto')
    default_threshold = curve_attrs.get('default_threshold', 8.0)
    
    try:
      # Get curve threshold using the k-means clustering function
      self.curve_threshold, self.curve_threshold_results = get_curve_threshold_from_method(
          self.dataset, self.curve_threshold_method, default_threshold=default_threshold
      )
      # Persist the full record on both the processor and the minute-level frame.
      # labeled_cluster_data / curve_threshold_details are already on dataset.attrs.
      self.dataset.attrs['curve_threshold_results'] = dict(self.curve_threshold_results)

      # # Generate cluster analysis visualization
      # if hasattr(self.dataset, 'attrs') and 'labeled_cluster_data' in self.dataset.attrs:
      #   cluster_plot_path = plot_cluster_analysis(
      #     self.dataset, 
      #     self.plot_folder, 
      #     self.subid, 
      #     self.dataset_identifier, 
      #     self.curve_threshold,
      #     title=f"TAC Cluster Analysis - {self.subid}",
      #     subtitle_text=f"Dataset: {self.dataset_identifier} | Threshold: {self.curve_threshold:.2f}"
      #   )
      #   if cluster_plot_path:
      #     self.plot_paths.append(cluster_plot_path)
      #     print(f"Cluster analysis plot saved: {cluster_plot_path}")

      # # Export curve threshold results to Excel
      # if hasattr(self, 'curve_threshold_results'):
      #     threshold_results_df = pd.DataFrame([self.curve_threshold_results])
      #     threshold_results_df.to_excel(
      #         f'{self.data_out_folder}/curve_threshold_results_{self.subid}_{self.dataset_identifier}.xlsx', 
      #         index=False
      #     )
      
      self.curve_threshold_computed = True
      
      self.save_as_sdp(valid=True)
      print(f"Successfully determined curve threshold {self.curve_threshold:.2f} for {self.subid}_{self.dataset_identifier}")

    except Exception as e:
      self.error = traceback.format_exc()
      self.log_error()
      self.save_as_sdp(valid=False)
      raise ValueError(f"Failed to determine curve threshold: {str(e)}")

  def compute_raw_curve_threshold(self, raw_curve_attrs: Dict = {}):
    """Determine curve threshold from raw TAC (parallel to imputed compute_curve_threshold)."""
    raw_curve_attrs = self._effective_raw_curve_attrs({}, raw_curve_attrs)
    raw_tac_column = raw_curve_attrs.get('raw_tac_column', 'TAC_smoothed_unimputed')
    if raw_tac_column == 'TAC_smoothed_unimputed':
      self.ensure_smoothed_unimputed_tac()

    threshold_method = raw_curve_attrs.get('curve_threshold', 'auto')
    default_threshold = raw_curve_attrs.get('default_threshold', 8.0)

    try:
      self.raw_curve_threshold, self.raw_curve_threshold_results = get_curve_threshold_from_method(
        self.dataset,
        threshold_method,
        default_threshold=default_threshold,
        TAC_column=raw_tac_column,
        details_attrs_key='raw_curve_threshold_details',
        results_attrs_key='raw_curve_threshold_results',
        label_main_dataframe=False,
      )
      self.dataset.attrs['raw_curve_threshold_results'] = dict(self.raw_curve_threshold_results)
      self.raw_curve_threshold_computed = True
      print(
        f"Successfully determined raw curve threshold {self.raw_curve_threshold:.2f} "
        f"({raw_tac_column}) for {self.subid}_{self.dataset_identifier}"
      )
    except Exception as e:
      self.error = traceback.format_exc()
      self.log_error()
      raise ValueError(f"Failed to determine raw curve threshold: {str(e)}")

  def identify_curves(
    self, curve_attrs: Dict = {}, raw_curve_attrs: Dict = {}, include_raw_curves=False
  ):
    """
    Find curve boundaries and process them into Curve objects and extract features.
    If curve threshold has not been determined yet, this method will automatically call
    compute_curve_threshold() first for backward compatibility.

    When ensure_default_curve_threshold_applied is True and the assigned k-means
    threshold differs from default_threshold, a parallel curve set is also built
    at the default threshold (does not replace primary curve_features).
    """
    raw_curve_attrs = self._effective_raw_curve_attrs(curve_attrs, raw_curve_attrs)

    self.curves = []
    self.curve_features = pd.DataFrame()
    self.raw_curves = []
    self.raw_curve_features = pd.DataFrame()
    self.curves_default_threshold = []
    self.curve_features_default_threshold = pd.DataFrame()
    self.raw_curves_default_threshold = []
    self.raw_curve_features_default_threshold = pd.DataFrame()

    self.ensure_default_curve_threshold_applied = curve_attrs.get(
      'ensure_default_curve_threshold_applied',
      getattr(self, 'ensure_default_curve_threshold_applied', False),
    )
    self.raw_ensure_default_curve_threshold_applied = raw_curve_attrs.get(
      'ensure_default_curve_threshold_applied', False
    )
    default_threshold = curve_attrs.get('default_threshold', 8.0)
    raw_default_threshold = raw_curve_attrs.get('default_threshold', 8.0)
    raw_tac_column = raw_curve_attrs.get('raw_tac_column', 'TAC_smoothed_unimputed')
    raw_mode = self._resolve_raw_curve_demarcation_mode(raw_curve_attrs, curve_attrs)

    if not self.curve_threshold_computed:
      print(f"Curve threshold not computed yet for {self.subid}_{self.dataset_identifier}. Auto-computing threshold...")
      self.compute_curve_threshold(curve_attrs=curve_attrs)

    try:
      if include_raw_curves and raw_tac_column == 'TAC_smoothed_unimputed':
        self.ensure_smoothed_unimputed_tac()
      if include_raw_curves and raw_mode == 'independent' and not self.raw_curve_threshold_computed:
        self.compute_raw_curve_threshold(raw_curve_attrs=raw_curve_attrs)

      (
        self.curves,
        self.curve_features,
        self.raw_curves,
        self.raw_curve_features,
      ) = self._build_curves_at_threshold(
        self.curve_threshold,
        curve_attrs,
        include_raw=include_raw_curves,
        raw_curve_attrs=raw_curve_attrs,
        raw_tac_column=raw_tac_column,
      )
      self.curve_features = self._attach_threshold_metadata(
        self.curve_features,
        detection_threshold=self.curve_threshold,
        threshold_results=self.curve_threshold_results,
      )
      if include_raw_curves and len(self.raw_curve_features):
        raw_threshold, raw_results, raw_source = self._raw_threshold_context(
          raw_mode, raw_curve_attrs
        )
        self.raw_curve_features = self._attach_threshold_metadata(
          self.raw_curve_features,
          detection_threshold=raw_threshold,
          threshold_results=raw_results,
        )
        self.raw_curve_features['threshold_source'] = raw_source
      self._export_curve_features(self.curve_features, 'curve_features')
      self._export_curve_features(self.raw_curve_features, 'raw_curve_features')

      run_default_pass = (
        self.ensure_default_curve_threshold_applied
        and not np.isclose(float(self.curve_threshold), float(default_threshold))
      )
      if run_default_pass:
        (
          self.curves_default_threshold,
          self.curve_features_default_threshold,
          self.raw_curves_default_threshold,
          self.raw_curve_features_default_threshold,
        ) = self._build_curves_at_threshold(
          default_threshold,
          curve_attrs,
          include_raw=include_raw_curves,
          raw_curve_attrs=raw_curve_attrs,
          raw_tac_column=raw_tac_column,
          raw_threshold_override=default_threshold if raw_mode == 'independent' else None,
        )
        self.curve_features_default_threshold = self._attach_threshold_metadata(
          self.curve_features_default_threshold,
          detection_threshold=default_threshold,
          threshold_results=self.curve_threshold_results,
          assigned_kmeans_threshold=self.curve_threshold,
        )
        if include_raw_curves and len(self.raw_curve_features_default_threshold):
          raw_def_threshold, raw_def_results, raw_source = self._raw_threshold_context_for_pass(
            raw_mode, raw_curve_attrs, default_threshold
          )
          self.raw_curve_features_default_threshold = self._attach_threshold_metadata(
            self.raw_curve_features_default_threshold,
            detection_threshold=raw_def_threshold,
            threshold_results=raw_def_results,
            assigned_kmeans_threshold=self.raw_curve_threshold if raw_mode == 'independent' else self.curve_threshold,
          )
          self.raw_curve_features_default_threshold['threshold_source'] = raw_source
        self._export_curve_features(
          self.curve_features_default_threshold, 'curve_features_default_threshold'
        )
        self._export_curve_features(
          self.raw_curve_features_default_threshold, 'raw_curve_features_default_threshold'
        )
        print(
          f"Also processed {len(self.curves_default_threshold)} curves at default "
          f"threshold {default_threshold} for {self.subid}_{self.dataset_identifier} "
          f"(k-means={self.curve_threshold:.2f})"
        )

      run_raw_default_pass = (
        include_raw_curves
        and raw_mode == 'independent'
        and self.raw_ensure_default_curve_threshold_applied
        and not np.isclose(float(self.raw_curve_threshold), float(raw_default_threshold))
        and not run_default_pass
      )
      if run_raw_default_pass:
        imputed_indices = get_start_and_end_of_discrete_curves(self.dataset, self.curve_threshold)
        imputed_indices_with_count = self._merge_curve_indices(imputed_indices, curve_attrs)
        (
          _,
          _,
          self.raw_curves_default_threshold,
          self.raw_curve_features_default_threshold,
        ) = self._build_curves_at_threshold(
          self.curve_threshold,
          curve_attrs,
          include_raw=True,
          raw_curve_attrs=raw_curve_attrs,
          raw_tac_column=raw_tac_column,
          imputed_indices_override=imputed_indices_with_count,
          raw_threshold_override=raw_default_threshold,
          skip_imputed=True,
          imputed_features_for_match=self.curve_features,
        )
        self.raw_curve_features_default_threshold = self._attach_threshold_metadata(
          self.raw_curve_features_default_threshold,
          detection_threshold=raw_default_threshold,
          threshold_results=self.raw_curve_threshold_results,
          assigned_kmeans_threshold=self.raw_curve_threshold,
        )
        self.raw_curve_features_default_threshold['threshold_source'] = 'raw'
        self._export_curve_features(
          self.raw_curve_features_default_threshold, 'raw_curve_features_default_threshold'
        )

      self.save_as_sdp(valid=True)
      print(f"Successfully processed {len(self.curves)} curves for {self.subid}_{self.dataset_identifier}")

    except Exception as e:
      self.error = traceback.format_exc()
      self.log_error()
      self.save_as_sdp(valid=False)
      raise ValueError(f"Failed to identify curves: {str(e)}")

  def refresh_raw_curves_only(self, raw_curve_attrs: Dict = {}):
    """Recompute raw curves/threshold only; preserve imputed curve state on the pickle."""
    if self.curve_features is None or self.curve_features.empty:
      raise ValueError(
        f"Cannot refresh raw curves only: imputed curve_features missing for "
        f"{self.subid}_{self.dataset_identifier}"
      )
    if not self.curve_threshold_computed:
      raise ValueError(
        f"Cannot refresh raw curves only: imputed curve_threshold not computed for "
        f"{self.subid}_{self.dataset_identifier}"
      )

    raw_curve_attrs = self._effective_raw_curve_attrs({}, raw_curve_attrs)
    raw_tac_column = raw_curve_attrs.get('raw_tac_column', 'TAC_smoothed_unimputed')
    raw_mode = self._resolve_raw_curve_demarcation_mode(raw_curve_attrs, {})

    if raw_tac_column == 'TAC_smoothed_unimputed':
      self.ensure_smoothed_unimputed_tac()

    self.raw_curves = []
    self.raw_curve_features = pd.DataFrame()
    self.raw_curves_default_threshold = []
    self.raw_curve_features_default_threshold = pd.DataFrame()
    self.raw_ensure_default_curve_threshold_applied = raw_curve_attrs.get(
      'ensure_default_curve_threshold_applied', False
    )
    raw_default_threshold = raw_curve_attrs.get('default_threshold', 8.0)

    try:
      if raw_mode == 'independent':
        self.raw_curve_threshold_computed = False
        self.compute_raw_curve_threshold(raw_curve_attrs=raw_curve_attrs)

      imputed_indices = get_start_and_end_of_discrete_curves(self.dataset, self.curve_threshold)
      imputed_indices_with_count = self._merge_curve_indices(imputed_indices, raw_curve_attrs)
      feature_curve_attrs = {'flag_selections': raw_curve_attrs.get('flag_selections', {})}

      _, _, self.raw_curves, self.raw_curve_features = self._build_curves_at_threshold(
        self.curve_threshold,
        feature_curve_attrs,
        include_raw=True,
        raw_curve_attrs=raw_curve_attrs,
        raw_tac_column=raw_tac_column,
        imputed_indices_override=imputed_indices_with_count,
        skip_imputed=True,
        imputed_features_for_match=self.curve_features,
      )

      if len(self.raw_curve_features):
        raw_threshold, raw_results, raw_source = self._raw_threshold_context(
          raw_mode, raw_curve_attrs
        )
        self.raw_curve_features = self._attach_threshold_metadata(
          self.raw_curve_features,
          detection_threshold=raw_threshold,
          threshold_results=raw_results,
        )
        self.raw_curve_features['threshold_source'] = raw_source

      run_raw_default_pass = (
        raw_mode == 'independent'
        and self.raw_ensure_default_curve_threshold_applied
        and not np.isclose(float(self.raw_curve_threshold), float(raw_default_threshold))
      )
      if run_raw_default_pass:
        _, _, self.raw_curves_default_threshold, self.raw_curve_features_default_threshold = (
          self._build_curves_at_threshold(
            self.curve_threshold,
            feature_curve_attrs,
            include_raw=True,
            raw_curve_attrs=raw_curve_attrs,
            raw_tac_column=raw_tac_column,
            imputed_indices_override=imputed_indices_with_count,
            skip_imputed=True,
            raw_threshold_override=raw_default_threshold,
            imputed_features_for_match=self.curve_features,
          )
        )
        self.raw_curve_features_default_threshold = self._attach_threshold_metadata(
          self.raw_curve_features_default_threshold,
          detection_threshold=raw_default_threshold,
          threshold_results=self.raw_curve_threshold_results,
          assigned_kmeans_threshold=self.raw_curve_threshold,
        )
        self.raw_curve_features_default_threshold['threshold_source'] = 'raw'

      self._export_curve_features(self.raw_curve_features, 'raw_curve_features')
      self.save_as_sdp(valid=True)
      print(
        f"Refreshed {len(self.raw_curves)} raw curves for "
        f"{self.subid}_{self.dataset_identifier} (imputed curves preserved)"
      )
    except Exception as e:
      self.error = traceback.format_exc()
      self.log_error()
      self.save_as_sdp(valid=False)
      raise ValueError(f"Failed to refresh raw curves: {str(e)}")
  
  def configure_event_data(self, data: pd.DataFrame = None, subid_column=None, ema_id_column=None, drink_total_column=None, event_timestamp_columns=None, buffer_before=2, buffer_after=0, max_event_duration=12, export_excel=False):
    print(f'Configuring event data for {self.subid} - {self.dataset_identifier}')
    try:
      # Validate required parameters
      if data is None or subid_column is None or ema_id_column is None or drink_total_column is None or event_timestamp_columns is None:
        raise ValueError("All required parameters must be provided: data, subid_column, ema_id_column, drink_total_column, event_timestamp_columns")
      
      self.events = data[(data[subid_column] == str(self.subid)) | (data[subid_column] == int(self.subid))]
      # Reset index to ensure unique indices
      self.events = self.events.reset_index(drop=True)
      self.events['max_event_duration'] = max_event_duration

      # Convert timestamp columns to datetime
      for col in event_timestamp_columns:
        if col in self.events.columns:
          self.events[col] = pd.to_datetime(self.events[col], errors='coerce')
      
      # Clean and correct timestamps before processing
      print(f"Cleaning and correcting timestamps for {self.subid}...")
      
      # Handle missing end timestamps by adding 8-hour buffer
      if len(event_timestamp_columns) >= 2:
        start_col = event_timestamp_columns[0]  # Assume first is start, second is end
        end_col = event_timestamp_columns[1]
        
        if start_col in self.events.columns and end_col in self.events.columns:
          missing_end_mask = self.events[end_col].isna() & self.events[start_col].notna()
          if missing_end_mask.sum() > 0:
            self.events.loc[missing_end_mask, end_col] = self.events.loc[missing_end_mask, start_col] + pd.Timedelta(hours=8)
            print(f"  Added 8-hour buffer to {missing_end_mask.sum()} events with missing end timestamps")
          
          # Add 24 hours to end times that occur before start times (overnight events)
          overnight_mask = self.events[end_col] < self.events[start_col]
          if overnight_mask.sum() > 0:
            self.events.loc[overnight_mask, end_col] = self.events.loc[overnight_mask, end_col] + pd.Timedelta(hours=24)
            print(f"  Added 24 hours to {overnight_mask.sum()} overnight events")
      
      # Process event timestamps
      self.events, self.event_labels, event_ranges = process_event_timestamps(
        events_df=self.events,
        event_timestamp_columns=event_timestamp_columns,
        drink_total_column=drink_total_column,
        ema_id_column=ema_id_column,
        max_event_duration=max_event_duration
      )
      
      # Filter curve features to only include current subject
      subject_curves = self.curve_features[
          (self.curve_features['subid'] == str(self.subid)) | 
          (self.curve_features['subid'] == int(self.subid))
      ].copy()
      
      # Use the new function to match curves to events
      self.events, updated_curves = match_curves_to_events(
        events_df=self.events,
        curve_features=subject_curves,
        event_ranges=event_ranges,
        buffer_before=buffer_before,
        buffer_after=buffer_after
      )
      
      # Update the original curve_features with the event matching information
      for col in updated_curves.columns:
          if col not in self.curve_features.columns:
              # Add new column
              self.curve_features[col] = updated_curves[col].values

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
        # Reset index to match self.curve_features
        updated_curve_features = updated_curve_features.reset_index(drop=True)
        self.curve_features.update(updated_curve_features[[col for col in updated_curve_features.columns if '_plot' in col]])
      
      raw_rows = []
      if include_raw_curves:
        for curve in self.raw_curves:
          if len(self.event_labels):
            curve.update_plot_annotations(self.event_labels)
          curve.create_graphs(self.plot_folder)
          raw_rows.append(curve.row)

      if len(self.raw_curves) > 0 and len(raw_rows) > 0:
        updated_raw_curve_features = pd.DataFrame(raw_rows, columns=curve.features.columns)
        # Reset index to match self.raw_curve_features
        updated_raw_curve_features = updated_raw_curve_features.reset_index(drop=True)
        self.raw_curve_features.update(updated_raw_curve_features[[col for col in updated_raw_curve_features.columns if '_plot' in col]])

      if export_excel:
        self.curve_features.to_excel(f'{self.data_out_folder}/curve_features_{self.subid}_{self.dataset_identifier}.xlsx', index=False)
      
      self.save_as_sdp(valid=True)

    except Exception:
      self.error = traceback.format_exc()
      self.log_error()
      self.save_as_sdp(valid=False)

  def get_curve_threshold_summary(self):
    """
    Get a summary of the curve threshold determination results.
    
    Returns:
        dict: Dictionary containing curve threshold determination results
    """
    if hasattr(self, 'curve_threshold_results') and self.curve_threshold_results:
        return self.curve_threshold_results.copy()
    return empty_curve_threshold_results(
        curve_threshold=self.curve_threshold,
        unadjusted_threshold=self.curve_threshold,
        threshold_method='manual' if isinstance(self.curve_threshold, (int, float)) else 'not_determined',
        threshold_calculation_method='manual',
        threshold_rule_applied='manual',
    )

  def set_ema_regions(self, export_excel=True, ema_region_extend_before=2, ema_region_extend_after=4):
    """Set EMA regions for each event. Window is (drink_start - extend_before) to (drink_start + extend_after) hours.
    Default 2+4 = 6-hour window (2 hours before, 4 hours after drink start)."""
    try:
      self.ema_regions = []
      ema_region_feature_dictionaries = []
      for i, row in self.events.iterrows():
        if pd.notna(row['ema_id']) and pd.notna(row['earliest_timestamp']):
          drink_start = row['earliest_timestamp']
          drink_total = row['drink_total']
          ema_id = row['ema_id']
          ema_region = emaRegion(self.dataset, self.subid, self.dataset_identifier, ema_id, drink_start, self.event_labels, extend_before_hours=ema_region_extend_before, extend_after_hours=ema_region_extend_after)
          ema_region.make_device_removal_plot(self.plot_folder)
          ema_region.make_signal_processing_plot(self.plot_folder, self.curve_threshold, drink_total)
          ema_region_feature_dictionaries.append(ema_region.self_report_region_quality_features)
          self.ema_regions.append(ema_region)
      self.ema_region_features = pd.DataFrame(ema_region_feature_dictionaries)

      if len(self.ema_region_features) > 0:
        ema_region_cols = [col for col in self.ema_region_features.columns if col != 'ema_id']
        duplicate_cols = [col for col in ema_region_cols if col in self.events.columns]
        if duplicate_cols:
            self.ema_region_features = self.ema_region_features.drop(columns=duplicate_cols)
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
        day = skynDay(
          self.dataset,
          start,
          end,
          self.curve_threshold,
          non_wear_self_report_column = non_wear_self_report_column,
          day_start_hour = day_start_hour
        )
        self.days.append(day)
        if make_graphs:
          # Conditionally include Dataset_ID in subtitle if not '001'
          dataset_id_text = f' -- Dataset: {self.dataset_identifier}' if str(self.dataset_identifier) != '001' else ''
          # 1-based day label (matches day_no / plot subtitle); day_id remains 0-based list index
          day_no = day_id + 1

          # Generate device removal plot
          device_removal_plot = plot_device_removal(
            day.day_dataset, self.plot_folder, self.subid, day_no, self.dataset_identifier,
            'Temperature_C', 'datetime', motion_variable='Motion', add_color=True,
            method='Model Predictions', prediction_column='device_worn_model',
            df_version=f'DAY{day_no}',
            subtitle_text=f'{self.subid}{dataset_id_text} -- Day: {day_no} -- Algorithm Non-Wear Detection',
          )
          self.plot_paths.append(device_removal_plot)

          # Generate signal processing plot
          signal_processing_plot = plot_signal_processing(
            day.day_dataset, self.plot_folder, self.subid, day_no, self.dataset_identifier,
            f'DAY{day_no}',
            self.curve_threshold, time_variable='datetime', title='Signal Processing',
            subtitle_text=f'{self.subid}{dataset_id_text} -- Day: {day_no}',
          )
          self.plot_paths.append(signal_processing_plot)

          # Add plot paths to day object
          day.device_removal_plot = device_removal_plot
          day.signal_processing_plot = signal_processing_plot
        day_id += 1

      self.day_level_data = create_day_level_dataframe(self.days, self.subid, self.dataset_identifier, morning_report=morning_report)
      
      # If graphs were made, ensure plot paths in day_level_data point to the current plot_folder
      # This is important when loading saved processors that may have old plot paths
      if make_graphs and not self.day_level_data.empty:
        # Update plot paths to use current plot_folder if they exist
        if 'device_removal_plot' in self.day_level_data.columns:
          # Update paths to point to current plot_folder
          for idx, row in self.day_level_data.iterrows():
            day_id = int(row['day_no']) - 1  # day_no is 1-indexed, day_id is 0-indexed
            if day_id < len(self.days) and hasattr(self.days[day_id], 'device_removal_plot'):
              self.day_level_data.at[idx, 'device_removal_plot'] = self.days[day_id].device_removal_plot
        if 'signal_processing_plot' in self.day_level_data.columns:
          for idx, row in self.day_level_data.iterrows():
            day_id = int(row['day_no']) - 1
            if day_id < len(self.days) and hasattr(self.days[day_id], 'signal_processing_plot'):
              self.day_level_data.at[idx, 'signal_processing_plot'] = self.days[day_id].signal_processing_plot
      
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

  # ---------------------------------------------------------------------------
  # Curve-identification helpers used by identify_curves
  # ---------------------------------------------------------------------------

  def ensure_smoothed_unimputed_tac(self, window_length=15, polyorder=2):
    """Add TAC_smoothed_unimputed for existing .sdp files that predate the column.

    Copies TAC_pre_imputation and applies Savitzky–Golay to all non-null minutes
    (skip_imputed=False), including minutes later marked imputed==1.
    Does not re-run imputation.
    """
    if 'TAC_smoothed_unimputed' in self.dataset.columns:
      return
    if 'TAC_pre_imputation' not in self.dataset.columns:
      raise ValueError(
        f"TAC_pre_imputation missing; cannot build TAC_smoothed_unimputed "
        f"for {self.subid}_{self.dataset_identifier}"
      )
    self.dataset['TAC_smoothed_unimputed'] = self.dataset['TAC_pre_imputation'].copy()
    self.dataset = smooth_savgol(
      self.dataset,
      window_length=window_length,
      polyorder=polyorder,
      tac_variable='TAC_smoothed_unimputed',
      skip_imputed=False,
    )

  def _merge_curve_indices(self, curve_start_and_end_indices, curve_attrs):
    """Merge nearby islands, or tag each remaining island with curve_count=1.

    Drops islands shorter than 15 minutes when merge_curves_within_duration is 0.
    """
    if curve_attrs.get('merge_curves_within_duration', 0) > 0:
      return merge_nearby_curves(
        curve_start_and_end_indices,
        max_curve_separation_minutes=curve_attrs['merge_curves_within_duration'] * 60,
      )
    return [
      [start, end, 1] for start, end in curve_start_and_end_indices
      if (end - start) >= 15
    ]

  def _curves_from_indices(self, indices_with_count, threshold, curve_attrs, TAC_column='TAC'):
    """Build Curve objects and a features table from (start, end, curve_count) rows.

    TAC_column selects the series used for peak/AUC/quality ('TAC' or a raw column).
    curve_id is 0-based within this call, so a default-threshold pass is not 1:1
    with the k-means pass.
    """
    flag_selections = curve_attrs.get('flag_selections', {})
    curves = []
    rows = []
    curve_id = 0
    for curve_start, curve_end, curve_count in indices_with_count:
      curve = Curve(
        self.dataset,
        self.subid,
        self.dataset_identifier,
        curve_id,
        curve_start,
        curve_end,
        curve_count,
        threshold,
        flag_selections,
        curve_attrs.get('periphery_buffer_before', 0),
        curve_attrs.get('periphery_buffer_after', 0),
        TAC_column=TAC_column,
      )
      curves.append(curve)
      rows.append(curve.row)
      curve_id += 1
    if curves:
      features = pd.DataFrame(rows, columns=curves[0].features.columns)
    else:
      features = pd.DataFrame(columns=self.curve_columns)
    return curves, features.reset_index(drop=True)

  def _attach_threshold_metadata(
    self, features_df, detection_threshold, threshold_results=None, assigned_kmeans_threshold=None
  ):
    """Copy k-means clustering fields onto a curve-features table.

    detection_threshold is the value actually used to find islands for this table
    (k-means or default 8.0). assigned_kmeans_threshold is set only on the
    default-threshold pass so those rows still record the dataset's k-means value.
    """
    if features_df is None:
      return pd.DataFrame(columns=self.curve_columns)
    if threshold_results is None:
      threshold_results = getattr(self, 'curve_threshold_results', {}) or {}
    results = threshold_results or {}
    features_df = features_df.copy()
    features_df['unadjusted_threshold'] = results.get('unadjusted_threshold')
    features_df['baseline_mean'] = results.get('baseline_mean')
    features_df['baseline_sd'] = results.get('baseline_sd')
    features_df['next_cluster_mean'] = results.get('next_cluster_mean')
    features_df['threshold_calculation_method'] = results.get('threshold_calculation_method')
    features_df['beta_value'] = results.get('beta_value')
    features_df['threshold_capped'] = results.get('threshold_capped')
    features_df['capped_reason'] = results.get('capped_reason')
    features_df['optimal_k'] = results.get('optimal_k')
    k_tested = results.get('k_values_tested')
    features_df['k_values_tested'] = str(k_tested) if k_tested else None
    features_df['selection_method'] = results.get('selection_method')
    features_df['baseline_cluster_id'] = results.get('baseline_cluster_id')
    features_df['use_safety_rule'] = results.get('use_safety_rule')
    features_df['n_clusters_mean_tac_gt_10'] = results.get('n_clusters_mean_tac_gt_10')
    features_df['threshold_rule_applied'] = results.get('threshold_rule_applied')
    features_df['n_minutes_clustered'] = results.get('n_minutes_clustered')
    features_df['n_minutes_baseline'] = results.get('n_minutes_baseline')
    features_df['clustering_quality_silhouette'] = results.get('clustering_quality_silhouette')
    features_df['clustering_quality_calinski_harabasz'] = results.get('clustering_quality_calinski_harabasz')
    features_df['clustering_quality_davies_bouldin'] = results.get('clustering_quality_davies_bouldin')
    features_df['clustering_quality_inertia'] = results.get('clustering_quality_inertia')
    features_df['detection_threshold'] = detection_threshold
    if assigned_kmeans_threshold is not None:
      features_df['assigned_kmeans_threshold'] = assigned_kmeans_threshold
    return features_df

  def _export_curve_features(self, features_df, filename_stem):
    """Write a per-dataset Excel file; no-op when the table is empty."""
    if features_df is None or features_df.empty:
      return
    features_df.to_excel(
      f'{self.data_out_folder}/{filename_stem}_{self.subid}_{self.dataset_identifier}.xlsx',
      index=False,
    )

  @staticmethod
  def _resolve_raw_curve_demarcation_mode(raw_curve_attrs, curve_attrs=None):
    if raw_curve_attrs.get('raw_curve_demarcation_mode'):
      return raw_curve_attrs['raw_curve_demarcation_mode']
    legacy = (curve_attrs or {}).get('raw_curve_use_imputed_windows')
    if legacy is True:
      return 'imputed_windows'
    if legacy is False:
      return 'adjust'
    return 'independent'

  def _effective_raw_curve_attrs(self, curve_attrs, raw_curve_attrs):
    from App.SDM.Run.default_settings.default_curve_settings import DEFAULT_CURVE_ATTRS

    merged = DEFAULT_RAW_CURVE_ATTRS.copy()
    merged.update(raw_curve_attrs or {})
    source = curve_attrs or {}
    if 'flag_selections' not in merged:
      merged['flag_selections'] = source.get(
        'flag_selections', DEFAULT_CURVE_ATTRS.get('flag_selections', {})
      )
    for key in ('periphery_buffer_before', 'periphery_buffer_after', 'merge_curves_within_duration'):
      if key not in (raw_curve_attrs or {}) and key in source:
        merged[key] = source[key]
    return merged

  def _raw_threshold_context(self, raw_mode, raw_curve_attrs):
    if raw_mode == 'independent':
      return self.raw_curve_threshold, self.raw_curve_threshold_results, 'raw'
    return self.curve_threshold, self.curve_threshold_results, 'imputed'

  def _raw_threshold_context_for_pass(self, raw_mode, raw_curve_attrs, pass_threshold):
    if raw_mode == 'independent':
      return pass_threshold, self.raw_curve_threshold_results, 'raw'
    return pass_threshold, self.curve_threshold_results, 'imputed'

  def _curve_attrs_for_features(self, curve_attrs, raw_curve_attrs):
    """Merge imputed curve attrs with raw demarcation attrs for Curve construction."""
    attrs = dict(curve_attrs or {})
    attrs.update(raw_curve_attrs or {})
    return attrs

  def _build_raw_curves(
    self,
    imputed_indices_with_count,
    imputed_threshold,
    curve_attrs,
    raw_curve_attrs,
    imputed_features,
    raw_threshold_override=None,
  ):
    mode = self._resolve_raw_curve_demarcation_mode(raw_curve_attrs, curve_attrs)
    raw_tac_column = raw_curve_attrs.get('raw_tac_column', 'TAC_smoothed_unimputed')
    feature_attrs = self._curve_attrs_for_features(curve_attrs, raw_curve_attrs)

    if mode == 'independent':
      raw_threshold = (
        raw_threshold_override if raw_threshold_override is not None else self.raw_curve_threshold
      )
      raw_indices = get_start_and_end_of_discrete_curves(
        self.dataset, raw_threshold, TAC_column=raw_tac_column
      )
      raw_indices_with_count = self._merge_curve_indices(raw_indices, raw_curve_attrs)
    elif mode == 'imputed_windows':
      raw_threshold = imputed_threshold
      raw_indices_with_count = [list(row) for row in imputed_indices_with_count]
    else:
      raw_threshold = imputed_threshold
      raw_indices_with_count = adjust_curve_demarcation_for_raw_tac(
        self.dataset,
        imputed_indices_with_count,
        raw_threshold,
        raw_curve_attrs.get('merge_curves_within_duration', 0) * 60,
        TAC_column=raw_tac_column,
      )
      if len(raw_indices_with_count) != len(imputed_indices_with_count):
        raise ValueError(
          f"Length mismatch between raw and processed curve indices: "
          f"{len(raw_indices_with_count)} vs {len(imputed_indices_with_count)}"
        )

    raw_curves, raw_features = self._curves_from_indices(
      raw_indices_with_count, raw_threshold, feature_attrs, TAC_column=raw_tac_column
    )

    if mode == 'independent':
      raw_features = attach_imputed_curve_matches(raw_features, imputed_features)
    else:
      raw_features = raw_features.copy()
      raw_features['curve_id_imputed_match'] = raw_features['curve_id']
      raw_features['imputed_match_overlap_percent'] = 1.0

    return raw_curves, raw_features

  def _build_curves_at_threshold(
    self,
    threshold,
    curve_attrs,
    include_raw=False,
    raw_curve_attrs=None,
    raw_tac_column='TAC_smoothed_unimputed',
    imputed_indices_override=None,
    skip_imputed=False,
    raw_threshold_override=None,
    imputed_features_for_match=None,
  ):
    """Detect islands on imputed TAC at `threshold`; optionally build raw curves."""
    raw_curve_attrs = raw_curve_attrs or {}
    curves = []
    features = pd.DataFrame(columns=self.curve_columns)

    if not skip_imputed:
      if imputed_indices_override is not None:
        indices_with_count = imputed_indices_override
      else:
        indices = get_start_and_end_of_discrete_curves(self.dataset, threshold)
        indices_with_count = self._merge_curve_indices(indices, curve_attrs)
      curves, features = self._curves_from_indices(
        indices_with_count, threshold, curve_attrs, TAC_column='TAC'
      )
    else:
      indices_with_count = imputed_indices_override or []

    raw_curves = []
    raw_features = pd.DataFrame(columns=self.curve_columns)
    if include_raw:
      if raw_tac_column not in self.dataset.columns:
        raise ValueError(
          f"{raw_tac_column} missing from dataset {self.subid}_{self.dataset_identifier}"
        )
      imputed_features = imputed_features_for_match if imputed_features_for_match is not None else features
      raw_curves, raw_features = self._build_raw_curves(
        indices_with_count,
        threshold,
        curve_attrs,
        raw_curve_attrs,
        imputed_features,
        raw_threshold_override=raw_threshold_override,
      )
    return curves, features, raw_curves, raw_features

