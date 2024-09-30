from SDM.Skyn_Processors.skyn_dataset import skynDataset
from SDM.User_Interface.Utils.filename_tools import extract_dataset_identifier
from tkinter import *
from tkinter import filedialog
from tkinter.filedialog import askopenfile
from tkinter import messagebox

from datetime import date
import pandas as pd
from pathlib import Path
import os

# main_dir = '/Users/nathandidier/Desktop/Repositories/skyn_data_manager/Inputs/Skyn_Data/ACE'
main_dir = '/users/ndidier/SDM/skyn_data_manager/Inputs/Skyn_Data/ACE'
cohort_name = 'ACE'

# results_dir = f'Users/nathandidier/Desktop/Repositories/skyn_data_manager/Results/{cohort_name}/{date.today().strftime("%m.%d.%Y")}'
results_dir = f'/users/ndidier/SDM/skyn_data_manager/Results/{cohort_name}/{date.today().strftime("%m.%d.%Y")}'
data_out = f'{results_dir}/Processed_Datasets'
graphs_out = f'{results_dir}/Plots'
analyses_out = f'{results_dir}/Model_Performance'

if not os.path.exists(f'/users/ndidier/SDM/skyn_data_manager/Results/{cohort_name}'):
  os.mkdir(f'/users/ndidier/SDM/skyn_data_manager/Results/{cohort_name}')
  print('results path exists: ', os.path.exists(f'/users/ndidier/SDM/skyn_data_manager/Results/{cohort_name}'))
if not os.path.exists(f'/users/ndidier/SDM/skyn_data_manager/Results/{cohort_name}/{date.today().strftime("%m.%d.%Y")}'):
  os.mkdir(f'/users/ndidier/SDM/skyn_data_manager/Results/{cohort_name}/{date.today().strftime("%m.%d.%Y")}')
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
subids = [5003]

datasets = []
no_file_subids = []

for subid in subids:
  # Determine file path
  csv_file = Path(f'{main_dir}/{subid}_001.csv')
  xlsx_file = Path(f'{main_dir}/{subid}_001.xlsx')
  
  # Check if the CSV file exists
  if csv_file.is_file():
    file_path = csv_file
  # Otherwise, check for an Excel file
  elif xlsx_file.is_file():
    file_path = xlsx_file
  else:
    file_path = None
    no_file_subids.append(subid)
    print(f"File for subid {subid} not found.")

  if not file_path:
    messagebox.showerror('Error', 'Invalid file type.')
  else:
    # <subid>_<datasetID>_<text>.xlsx/csv
    # datasetID is a 3-digit integer
    # First character = burstID
    # Second-Third character = dayNumber
    dataset_identifier = extract_dataset_identifier(file_path)
    if dataset_identifier == '':
      messagebox.showerror('Error', 'Dataset ID is not found in filename.')
    
    sdm_processor = skynDataset(
      str(file_path),
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
    datasets.append(sdm_processor.day_level_data)

combined_day_level_data = pd.concat(datasets, ignore_index=True)
combined_day_level_data.to_excel(f'{results_dir}/day_level_quality_metrics.xlsx')
