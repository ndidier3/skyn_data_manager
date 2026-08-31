from App.SDM.Skyn_Processors.skyn_dataset import skynDataset
from App.SDM.Run.default_settings.default_curve_settings import DEFAULT_RAW_CURVE_ATTRS
from App.SDM.Configuration.file_management import extract_dataset_identifier, extract_subid
from App.SDM.Configuration.file_management import save_to_computer, create_save_directories, load, create_individual_plot_folder
from App.SDM.Documenting.embed_graphs import embed_graphs_into_workbook_tab
import traceback
from datetime import date, datetime
import pandas as pd
import os

def process_and_analyze_data(
  project_root, 
  data_input_folder, 
  output_folder_name = 'cohort', 
  use_prior_save = True,
  filter_by_study_dates = False, 
  smooth_and_impute = False,
  adjust_for_gaps_and_non_wear = False,
  analyze_days = False,
  compute_curve_threshold = False,
  identify_curves = False,
  include_raw_curves = False,
  refresh_raw_curves_only = False,
  match_events_to_curves = False,
  gaps_and_non_wear_attrs = {},
  smooth_and_impute_attrs = {},
  curve_attrs = {},
  raw_curve_attrs = {},
  day_attrs = {
    'day_start_hour': 0,
    'make_graphs': True
  },
  event_attrs = {},
  day_filter_ranges = {},
  subids_to_process = None
):
  
  """ CREATE SAVE DIRECTORIES"""
  processed_data_out = str(data_input_folder).replace('_RAW', '_PROCESSED')
  results_dir = f'{project_root}/Results/{output_folder_name}/{date.today().strftime("%m.%d.%Y")}'
  data_out = f'{results_dir}/Datasets'
  graphs_out = f'{results_dir}/Plots'
  analyses_out = f'{results_dir}/Model_Performance'
  create_save_directories(project_root, processed_data_out, output_folder_name, data_out, graphs_out, analyses_out)

  """ Load Skyn Files """
  files = [os.path.join(data_input_folder, file) for file in os.listdir(data_input_folder)]

  """ Storage for SDM Processors """
  processors = []
  day_datasets = []
  curve_features = []
  raw_curve_features = []
  curve_features_default_threshold = []
  raw_curve_features_default_threshold = []
  event_datasets = []
  event_curve_matches = []
  no_skyn_data_found = []

  if include_raw_curves and not raw_curve_attrs:
    raw_curve_attrs = DEFAULT_RAW_CURVE_ATTRS.copy()

  for file in files:
    try:
      subid = extract_subid(os.path.basename(file))
      
      # Skip if subid is not in the list of subids to process
      if subids_to_process is not None and int(subid) not in subids_to_process:
        print(f"\nSkipping file for subject {subid} - not in subids_to_process list")
        continue
        
      print(f"\nProcessing file for subject {subid}")
      dataset_identifier = extract_dataset_identifier(os.path.basename(file))
      print(f"Dataset identifier: {dataset_identifier}")
      
      if dataset_identifier == '':
        print(f"Warning: Empty dataset identifier for file: {file}")
        continue
      
      if not os.path.isfile(file):
        print(f"Error: Invalid file path: {file}")
        continue
        
      sdm_processor = None
      prior_processor_loaded = False
      
      if use_prior_save:
        try:
          print(f"Attempting to load prior save for {subid}_{dataset_identifier}")
          sdm_processor = load(f'{subid}_{dataset_identifier}_skyn_data_processed.sdp', processed_data_out)
          sdm_processor.data_out_folder = data_out
          sdm_processor.plot_folder = create_individual_plot_folder(graphs_out, subid)
          sdm_processor.processed_data_out_folder = processed_data_out
          prior_processor_loaded = True
          print(f"Successfully loaded prior save for {subid}_{dataset_identifier}")
        except Exception as e:
          print(f"Failed to load prior save for {subid}_{dataset_identifier}: {str(e)}")
          continue

      if not prior_processor_loaded:
        print(f"Creating new processor for {subid}_{dataset_identifier}")
        sdm_processor = skynDataset(str(file), processed_data_out, data_out, graphs_out, subid, dataset_identifier, 'e' + str(1))
      
      if filter_by_study_dates:
        # Check if subid exists in day_filter_ranges (subids are stored as strings)
        subid_key = str(subid)
        if subid_key in day_filter_ranges and day_filter_ranges[subid_key] is not None:
          first_study_datetime, end_study_datetime = day_filter_ranges[subid_key]
          # Handle cases where one or both datetimes might be None
          first_dt = first_study_datetime if isinstance(first_study_datetime, datetime) else None
          end_dt = end_study_datetime if isinstance(end_study_datetime, datetime) else None
          
          if first_dt is not None or end_dt is not None:
            datetime_range_str = f"{first_dt if first_dt else 'start'} to {end_dt if end_dt else 'end'}"
            print(f"Filtering dataset for {subid}_{dataset_identifier} by study datetime range: {datetime_range_str}")
            sdm_processor.filter_dataset_by_date_range(first_dt, end_dt)
          else:
            print(f"Warning: No valid datetimes found for {subid}_{dataset_identifier} in day_filter_ranges")
        else:
          print(f"Warning: No study datetime range found for {subid}_{dataset_identifier}")

      if adjust_for_gaps_and_non_wear:
        print(f"Adjusting for gaps and non-wear for {subid}_{dataset_identifier}")
        sdm_processor.adjust_for_gaps_and_non_wear(**gaps_and_non_wear_attrs)
        
      if smooth_and_impute:
        print(f"Smoothing and imputing for {subid}_{dataset_identifier}")
        sdm_processor.smooth_and_impute(**smooth_and_impute_attrs)
        
      if compute_curve_threshold:
        print(f"Computing curve threshold for {subid}_{dataset_identifier}")
        sdm_processor.compute_curve_threshold(curve_attrs=curve_attrs)
      elif identify_curves and not sdm_processor.curve_threshold_computed:
        print(f"Warning: identify_curves=True but compute_curve_threshold=False and threshold not computed for {subid}_{dataset_identifier}")
        print(f"Auto-computing threshold for {subid}_{dataset_identifier}")
        sdm_processor.compute_curve_threshold(curve_attrs=curve_attrs)
        
      if refresh_raw_curves_only:
        already_refreshed = (
          getattr(sdm_processor, 'raw_curve_threshold_computed', False)
          and getattr(sdm_processor, 'raw_curve_features', None) is not None
          and len(sdm_processor.raw_curve_features) > 0
          and 'curve_id_imputed_match' in sdm_processor.raw_curve_features.columns
        )
        if already_refreshed:
          print(f"Skipping raw refresh for {subid}_{dataset_identifier} (already refreshed)")
          raw_curve_features.append(sdm_processor.raw_curve_features)
          if getattr(sdm_processor, 'raw_curve_features_default_threshold', None) is not None and len(sdm_processor.raw_curve_features_default_threshold):
            raw_curve_features_default_threshold.append(sdm_processor.raw_curve_features_default_threshold)
        else:
          print(f"Refreshing raw curves only for {subid}_{dataset_identifier}")
          sdm_processor.refresh_raw_curves_only(raw_curve_attrs=raw_curve_attrs)
          if sdm_processor.raw_curve_features is not None and len(sdm_processor.raw_curve_features):
            raw_curve_features.append(sdm_processor.raw_curve_features)
          if getattr(sdm_processor, 'raw_curve_features_default_threshold', None) is not None and len(sdm_processor.raw_curve_features_default_threshold):
            raw_curve_features_default_threshold.append(sdm_processor.raw_curve_features_default_threshold)
      elif identify_curves:
        print(f"Identifying curves for {subid}_{dataset_identifier}")
        sdm_processor.identify_curves(
          curve_attrs=curve_attrs,
          raw_curve_attrs=raw_curve_attrs,
          include_raw_curves=include_raw_curves,
        )
        if not match_events_to_curves:
          print(f"Making curve graphs for {subid}_{dataset_identifier}")
          sdm_processor.make_curve_graphs()
          curve_features.append(sdm_processor.curve_features)
          if include_raw_curves:
            raw_curve_features.append(sdm_processor.raw_curve_features)
          if getattr(sdm_processor, 'curve_features_default_threshold', None) is not None and len(sdm_processor.curve_features_default_threshold):
            curve_features_default_threshold.append(sdm_processor.curve_features_default_threshold)
          if getattr(sdm_processor, 'raw_curve_features_default_threshold', None) is not None and len(sdm_processor.raw_curve_features_default_threshold):
            raw_curve_features_default_threshold.append(sdm_processor.raw_curve_features_default_threshold)
      
      if analyze_days:
        print(f"Running day analysis for {subid}_{dataset_identifier}")
        sdm_processor.run_day_level_analysis(**day_attrs)
        if not sdm_processor.day_level_data.empty:
          print(f"Found day data with shape: {sdm_processor.day_level_data.shape}")
          day_datasets.append(sdm_processor.day_level_data)
        else:
          print(f"WARNING: No day data found for {subid}_{dataset_identifier}")
          
      if match_events_to_curves:
        print(f"Configuring event data for {subid}_{dataset_identifier}")
        sdm_processor.configure_event_data(**event_attrs)
        print(f"Making curve graphs for {subid}_{dataset_identifier}")
        sdm_processor.make_curve_graphs()
        print(f"Setting EMA regions for {subid}_{dataset_identifier}")
        sdm_processor.set_ema_regions()
        curve_features.append(sdm_processor.curve_features)
        event_datasets.append(sdm_processor.events)
        if include_raw_curves:
          raw_curve_features.append(sdm_processor.raw_curve_features)
        if getattr(sdm_processor, 'curve_features_default_threshold', None) is not None and len(sdm_processor.curve_features_default_threshold):
          curve_features_default_threshold.append(sdm_processor.curve_features_default_threshold)
        if getattr(sdm_processor, 'raw_curve_features_default_threshold', None) is not None and len(sdm_processor.raw_curve_features_default_threshold):
          raw_curve_features_default_threshold.append(sdm_processor.raw_curve_features_default_threshold)
          
    except Exception as e:
      print(f"\nError processing file {file}:")
      print(f"Error type: {type(e).__name__}")
      print(f"Error message: {str(e)}")
      print("Full traceback:")
      print(traceback.format_exc())
      print("\n")
          
  if len(day_datasets):
    print(f'Combining {len(day_datasets)} day datasets')
    combined_day_level_data = pd.concat(day_datasets, ignore_index=True)
    print(f'Combined day data shape: {combined_day_level_data.shape}')
    combined_day_level_data.to_excel(f'{results_dir}/day_level_results.xlsx', index=None)
  else:
    print('WARNING: No day datasets to combine')

  if len(curve_features):
    print(f'Combining {len(curve_features)} curve feature datasets')
    with pd.ExcelWriter(f'{results_dir}/curve_level_results.xlsx', engine='xlsxwriter', mode = 'w') as writer:
      combined_curve_features = pd.concat(curve_features, ignore_index=True)
      combined_curve_features.to_excel(writer, index=None, sheet_name="Features")
      print(f'Combined curve features shape: {combined_curve_features.shape}')
  
  if len(raw_curve_features):
    print(f'Combining {len(raw_curve_features)} raw curve feature datasets')
    with pd.ExcelWriter(f'{results_dir}/raw_curve_level_results.xlsx', engine='xlsxwriter', mode = 'w') as writer:
      combined_raw_curve_features = pd.concat(raw_curve_features, ignore_index=True)
      combined_raw_curve_features.to_excel(writer, index=None, sheet_name="Features")
      print(f'Combined raw curve features shape: {combined_raw_curve_features.shape}')

  if len(curve_features_default_threshold):
    print(f'Combining {len(curve_features_default_threshold)} default-threshold curve feature datasets')
    combined_default = pd.concat(curve_features_default_threshold, ignore_index=True)
    combined_default.to_excel(f'{results_dir}/curve_features_default_threshold.xlsx', index=None)
    print(f'Combined default-threshold curve features shape: {combined_default.shape}')

  if len(raw_curve_features_default_threshold):
    print(f'Combining {len(raw_curve_features_default_threshold)} default-threshold raw curve feature datasets')
    combined_raw_default = pd.concat(raw_curve_features_default_threshold, ignore_index=True)
    combined_raw_default.to_excel(f'{results_dir}/raw_curve_features_default_threshold.xlsx', index=None)
    print(f'Combined default-threshold raw curve features shape: {combined_raw_default.shape}')

  if len(event_curve_matches):
    print(f'Combining {len(event_curve_matches)} event curve match datasets')
    with pd.ExcelWriter(f'{results_dir}/curve_level_results.xlsx', engine='xlsxwriter', mode = 'w') as writer:
      combined_curve_features = pd.concat(curve_features, ignore_index=True)
      combined_curve_features.to_excel(writer, index=None, sheet_name="Features")
      print(f'Combined event curve matches shape: {combined_curve_features.shape}')
          
  with pd.ExcelWriter(f'{results_dir}/event_level_results.xlsx', engine='xlsxwriter') as writer:
    if len(event_datasets):
      print(f'Combining {len(event_datasets)} event datasets')
      combined_event_level_datasets = pd.concat(event_datasets, ignore_index=True)
      combined_event_level_datasets.to_excel(writer, index=None, sheet_name = 'event-data')
      print(f'Combined event data shape: {combined_event_level_datasets.shape}')
    if len(no_skyn_data_found):
      print(f'Combining {len(no_skyn_data_found)} no-skyn-data datasets')
      combined_no_skyn_data_events = pd.concat(no_skyn_data_found, ignore_index=True)
      combined_no_skyn_data_events.to_excel(writer, index=None, sheet_name = 'no-skyn-data')
      print(f'Combined no-skyn-data shape: {combined_no_skyn_data_events.shape}')
  