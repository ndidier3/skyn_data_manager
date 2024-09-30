from SDM.Skyn_Processors.skyn_dataset import skynDataset
from SDM.User_Interface.Utils.filename_tools import extract_dataset_identifier, extract_subid
from tkinter import *
from tkinter import filedialog
from tkinter.filedialog import askopenfile
from tkinter import messagebox
import traceback

from datetime import date
import pandas as pd
from pathlib import Path
import os

# MAC
project_root = '/Users/nathandidier/Desktop/Repositories/skyn_data_manager'
# Linux
# project_root = '/users/<username>/SDM/skyn_data_manager/Inputs/Skyn_Data/ACE' 
# Windows
# project_root = ''

data_input_folder = f'{project_root}/Inputs/Skyn_Data/LINC'
output_folder_name = 'LINC'

# how to set output folder name? Separate by date?

def run_many(data_input_folder = data_input_folder, output_folder_name = 'LINC', single_file = None):

  # results_dir = f'Users/nathandidier/Desktop/Repositories/skyn_data_manager/Results/{cohort_name}/{date.today().strftime("%m.%d.%Y")}'
  results_dir = f'{project_root}/Results/{output_folder_name}/{date.today().strftime("%m.%d.%Y")}'
  data_out = f'{results_dir}/Processed_Datasets'
  graphs_out = f'{results_dir}/Plots'
  analyses_out = f'{results_dir}/Model_Performance'

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

  #153 left out
  # subids = [101, 102, 106, 112, 113, 114, 115, 117, 118, 120, 121, 122, 123, 127, 130, 
  #           132, 133, 134, 138, 139, 140, 141, 143, 146, 147, 149, 150, 151, 153, 155, 
  #           157, 159, 160, 161, 162, 165, 167, 171, 172, 174, 180, 181, 183, 185, 186, 
  #           189, 190, 194, 198, 199, 202, 204, 206, 207, 208, 209, 210, 211, 212, 213, 
  #           214, 215, 216, 218, 219, 220, 221, 222, 223, 227, 233, 236, 237, 238, 241, 
  #           243, 246, 247, 250, 251, 253, 255, 256, 258, 259, 260, 267, 270, 271, 272, 
  #           273, 274, 276, 277, 280, 281, 282, 286, 291, 292, 295, 296]

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
        messagebox.showerror('Error', 'Dataset ID is not found in filename.')
      else:
        # Determine file path
        
        # Check if the CSV file exists
        if not os.path.isfile(file):
          messagebox.showerror('Error', 'Invalid file.')
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
      messagebox.showerror('SDM Error', f'Failed to load. See error: {traceback.format_exc()}')
      print('SDM Error', f'Failed to load. See error: {traceback.format_exc()}')

    
  if len(processed_datasets):
    combined_day_level_data = pd.concat(processed_datasets, ignore_index=True)
    combined_day_level_data.to_excel(f'{results_dir}/day_level_quality_metrics.xlsx', index=None)

run_many(data_input_folder = data_input_folder, output_folder_name=output_folder_name)