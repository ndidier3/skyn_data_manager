from App.SDM.Skyn_Processors.skyn_dataset import skynDataset
from App.SDM.User_Interface.Utils.filename_tools import extract_dataset_identifier, extract_subid
from App.SDM.Configuration.file_management import save_to_computer, create_save_directories, load, create_individual_plot_folder
from App.SDM.Documenting.embed_graphs import embed_graphs_into_workbook_tab
from tkinter import messagebox
import traceback
from datetime import date
import pandas as pd
import os

"""
split into process raw data, analyze_days, analyze_events
"""

def process_and_analyze_data(
  project_root, 
  data_input_folder, 
  output_folder_name = 'cohort', 
  event_data = pd.DataFrame(), 
  event_subid_column = 'ID',
  curve_threshold = 'auto',
  use_prior_save = True, 
  smooth_and_impute = False,
  adjust_for_gaps_and_non_wear = False,
  analyze_days = False,
  analyze_events = False,
  identify_curves = False,
  match_events_to_curves = False,
  gaps_and_non_wear_attrs = {},
  smooth_and_impute_attrs = {},
  curve_attrs = {},
  day_attrs = {'day_start_hour': 0, 'make_graphs': True},
  event_attrs = {}
):
  
  """ CREATE SAVE DIRECTORIES"""
  processed_data_out = data_input_folder.replace('_RAW', '_PROCESSED')
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
  event_datasets = []
  event_curve_matches = []

  no_skyn_data_found = []

  for file in files:
    try:
      subid = extract_subid(os.path.basename(file))
      print(subid)
      dataset_identifier = extract_dataset_identifier(os.path.basename(file))
      print(dataset_identifier)
      if dataset_identifier == '':
        print(file)
      else:
        print(file)
        if not os.path.isfile(file):
          print('Invalid File')
        else:
          sdm_processor = None
          prior_processor_loaded = False
          if use_prior_save:
            try:
              sdm_processor = load(f'{subid}_{dataset_identifier}_skyn_data_processed.sdp', processed_data_out)
              sdm_processor.data_out_folder = data_out
              sdm_processor.plot_folder = create_individual_plot_folder(graphs_out, subid)
              prior_processor_loaded = True
            except:
              continue

          if not prior_processor_loaded:
            sdm_processor = skynDataset(str(file), processed_data_out, data_out, graphs_out, subid, dataset_identifier, 'e' + str(1))
          
          if adjust_for_gaps_and_non_wear:
            sdm_processor.adjust_for_gaps_and_non_wear(**gaps_and_non_wear_attrs)
          if smooth_and_impute:
            sdm_processor.smooth_and_impute(**smooth_and_impute_attrs)
          if analyze_days:
            sdm_processor.run_day_level_analysis(**day_attrs)
            day_datasets.append(sdm_processor.day_level_data)
          if identify_curves:
            sdm_processor.identify_curves(curve_threshold, curve_attrs=curve_attrs)
            if not match_events_to_curves:
              sdm_processor.make_curve_graphs()
            curve_features.append(sdm_processor.curve_features)
          if match_events_to_curves:
            sdm_processor.configure_event_data(**event_attrs)
            sdm_processor.make_curve_graphs()
            sdm_processor.set_ema_regions()
            event_curve_matches.append(sdm_processor.event_labels)
          if analyze_events:
            subids_found = event_data[event_subid_column].unique().tolist()
            if (int(subid) in subids_found or str(subid) in subids_found):
              sdm_processor.run_event_level_analysis(event_data, **event_attrs)
              event_datasets.append(sdm_processor.event_level_data)
              processors.append(sdm_processor)
              no_skyn_data_found.append(sdm_processor.events_with_no_skyn_data)
            else:
              print(f'{subid} {dataset_identifier} -- NO Event DATA')
    except Exception:
      print('SDM Error', f'Failed to load. See error: {traceback.format_exc()}')
          
  if len(day_datasets):
    combined_day_level_data = pd.concat(day_datasets, ignore_index=True)
    combined_day_level_data.to_excel(f'{results_dir}/day_level_results.xlsx', index=None)

  if len(curve_features):
    with pd.ExcelWriter(f'{results_dir}/curve_level_results.xlsx', engine='xlsxwriter', mode = 'w') as writer:
      combined_curve_features = pd.concat(curve_features, ignore_index=True)
      combined_curve_features.to_excel(writer, index=None, sheet_name="Features")
  
  if len(event_curve_matches):
    with pd.ExcelWriter(f'{results_dir}/curve_level_results.xlsx', engine='xlsxwriter', mode = 'w') as writer:
      combined_curve_features = pd.concat(curve_features, ignore_index=True)
      combined_curve_features.to_excel(writer, index=None, sheet_name="Features")
          
  with pd.ExcelWriter(f'{results_dir}/event_level_results.xlsx', engine='xlsxwriter') as writer:
    if len(event_datasets):
      combined_event_level_datasets = pd.concat(event_datasets, ignore_index=True)
      combined_event_level_datasets.to_excel(writer, index=None, sheet_name = 'event-data')
    if len(no_skyn_data_found):
      combined_no_skyn_data_events = pd.concat(no_skyn_data_found, ignore_index=True)
      combined_no_skyn_data_events.to_excel(writer, index=None, sheet_name = 'no-skyn-data')
  