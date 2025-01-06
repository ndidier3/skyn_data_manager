from SDM.Skyn_Processors.skyn_dataset import skynDataset
from SDM.User_Interface.Utils.filename_tools import extract_dataset_identifier, extract_subid
from SDM.Configuration.file_management import save_to_computer, create_save_directories, load, create_individual_plot_folder
from tkinter import messagebox
import traceback
from datetime import date
import pandas as pd
import os

def process_many(project_root, data_input_folder, output_folder_name = 'cohort', single_file = None, use_popups = False, process_raw_data = True, analyze_day_level = False, event_data = pd.DataFrame(columns=['ID']), use_prior_save = True, extra_columns = []):

  processed_data_out = data_input_folder.replace('_RAW', '_PROCESSED')
  results_dir = f'{project_root}/Results/{output_folder_name}/{date.today().strftime("%m.%d.%Y")}'
  data_out = f'{results_dir}/Processed_Datasets'
  graphs_out = f'{results_dir}/Plots'
  analyses_out = f'{results_dir}/Model_Performance'

  create_save_directories(project_root, processed_data_out, output_folder_name, data_out, graphs_out, analyses_out)

  if single_file == None:
    files = [os.path.join(data_input_folder, file) for file in os.listdir(data_input_folder)]
  else:
    files = [os.path.join(data_input_folder, single_file)]
  
  processors = []
  processed_datasets = []
  curve_datasets = []
  no_skyn_data_found = []

  subids_found = event_data['ID'].unique().tolist()
  print(subids_found)
  for file in files:
    try:
      subid = extract_subid(os.path.basename(file))
      print(subid)
      dataset_identifier = extract_dataset_identifier(os.path.basename(file))
      print(dataset_identifier)
      if dataset_identifier == '':
        print(file)
        if use_popups:
          messagebox.showerror('Error', 'Dataset ID is not found in filename.')
        print('Dataset ID is not found in filename.')
      
      else:
        print(file)
        if not os.path.isfile(file):
          if use_popups:
            messagebox.showerror('Error', 'Invalid file.')
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
              pass

          if not prior_processor_loaded:
            sdm_processor = skynDataset(
              str(file),
              processed_data_out,
              data_out,
              graphs_out,
              subid,
              dataset_identifier,
              'e' + str(1),
              False,
              False,
              'CST',
              24
          )
            
          if process_raw_data or not prior_processor_loaded:
            sdm_processor.process_skyn_data()
          if analyze_day_level:
            sdm_processor.run_day_level_analysis(day_start_hour = 0, make_graphs=True)
            processed_datasets.append(sdm_processor.day_level_data)
          if int(subid) in subids_found or str(subid) in subids_found:
            # sdm_processor.dataset.to_excel(f'test_{subid}.xlsx')
            # CHANGE POINT
            """ ARC """
            sdm_processor.run_event_level_analysis(
              event_data = event_data,
              extra_columns = extra_columns,
              curve_threshold = 10,
              save = True
            )
            """ ACE """
            # sdm_processor.run_event_level_analysis(
            #   event_data=event_data,
            #   drink_start_column = "drinkstart_timestamp",
            #   drink_total_column = "totdrinks_fin_mr",
            #   day_id_column = "emaday",
            #   extra_columns = extra_columns,
            #   curve_search_pad_hours_before = 1,
            #   curve_search_pad_hours_after = 23,
            #   search_method = 'first'
            # )
            """ MARS """

            print('SubID Found in Event File')
            curve_datasets.append(sdm_processor.event_level_data)
            processors.append(sdm_processor)
            no_skyn_data_found.append(sdm_processor.events_with_no_skyn_data)
          else:
            print(f'{subid} NOT FOUND - NO DATA')

    except Exception:
      if use_popups:
        messagebox.showerror('SDM Error', f'Failed to load. See error: {traceback.format_exc()}')
      print('SDM Error', f'Failed to load. See error: {traceback.format_exc()}')
  
  save_to_computer(processors, 'processors', f'{project_root}/Results/{output_folder_name}')
    
  if len(processed_datasets):
    combined_day_level_data = pd.concat(processed_datasets, ignore_index=True)
    combined_day_level_data.to_excel(f'{results_dir}/day_level_quality_metrics.xlsx', index=None)

  with pd.ExcelWriter(f'{results_dir}/event_level_quality_metrics.xlsx', engine='xlsxwriter') as writer:
    if len(curve_datasets):
      combined_event_level_datasets = pd.concat(curve_datasets, ignore_index=True)
      combined_event_level_datasets.to_excel(writer, index=None, sheet_name = 'event-data')
    if len(no_skyn_data_found):
      combined_no_skyn_data_events = pd.concat(no_skyn_data_found, ignore_index=True)
      combined_no_skyn_data_events.to_excel(writer, index=None, sheet_name = 'no-skyn-data')
      