from SDM.Skyn_Processors.skyn_dataset import skynDataset
from SDM.User_Interface.Utils.filename_tools import extract_dataset_identifier, extract_subid
from tkinter import messagebox
import traceback
from datetime import date
import pandas as pd
import os

def process_many(project_root, data_input_folder, output_folder_name = 'cohort', single_file = None, use_popups = False):

  results_dir = f'{project_root}/Results/{output_folder_name}/{date.today().strftime("%m.%d.%Y")}'
  data_out = f'{results_dir}/Processed_Datasets'
  graphs_out = f'{results_dir}/Plots'
  analyses_out = f'{results_dir}/Model_Performance'

  #this should become its own function
  if not os.path.exists(f'{project_root}/Results/{output_folder_name}'):
    os.mkdir(f'{project_root}/Results/{output_folder_name}')
    print('results path exists: ', os.path.exists(f'{project_root}/Results/{output_folder_name}'))
  if not os.path.exists(f'{project_root}/Results/{output_folder_name}/{date.today().strftime("%m.%d.%Y")}'):
    os.mkdir(f'{project_root}/Results/{output_folder_name}/{date.today().strftime("%m.%d.%Y")}')
  if not os.path.exists(data_out):
    os.mkdir(data_out)
  if not os.path.exists(graphs_out):
    os.mkdir(graphs_out)
  if not os.path.exists(analyses_out):
    os.mkdir(analyses_out)

  if single_file == None:
    files = [os.path.join(data_input_folder, file) for file in os.listdir(data_input_folder)]
  else:
    files = [os.path.join(data_input_folder, single_file)]

  processed_datasets = [] #populated in loop below

  

  for file in files:
    print(file)
    try:
      subid = extract_subid(os.path.basename(file))
      dataset_identifier = extract_dataset_identifier(os.path.basename(file))
      print(subid)
      print(dataset_identifier)

      if dataset_identifier == '':
        if use_popups:
          messagebox.showerror('Error', 'Dataset ID is not found in filename.')
        print('Dataset ID is not found in filename.')
      else:
        # Determine file path
        
        if not os.path.isfile(file):
          if use_popups:
            messagebox.showerror('Error', 'Invalid file.')
          print('Invalid File')
        else:
          sdm_processor = skynDataset(
            str(file),
            data_out,
            graphs_out,
            subid,
            1,
            'e' + str(1),
            False,
            False,
            'CST',
            24
          )
          sdm_processor.process_as_multiple_episodes()
          processed_datasets.append(sdm_processor.day_level_data)
    except Exception:
      if use_popups:
        messagebox.showerror('SDM Error', f'Failed to load. See error: {traceback.format_exc()}')
      print('SDM Error', f'Failed to load. See error: {traceback.format_exc()}')
    
  if len(processed_datasets):
    combined_day_level_data = pd.concat(processed_datasets, ignore_index=True)
    combined_day_level_data.to_excel(f'{results_dir}/day_level_quality_metrics.xlsx', index=None)
