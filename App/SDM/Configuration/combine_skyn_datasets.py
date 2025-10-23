import pandas as pd
import os
from .Configuration.configuration import update_column_names, rename_TAC_column, configure_dataset_timestamps

def combine_skyn_datasets(filepaths, out_filepath):
  datasets = []
  for path in filepaths:
    _, ext = os.path.splitext(path)
    if ext == '.csv':
      dataset = pd.read_csv(path)
    elif ext == '.xlsx' or ext == '.xls':
      dataset = pd.read_excel(path)
    
    #standardize column names before combining
    dataset = update_column_names(dataset)
    print(dataset.columns)
    dataset = rename_TAC_column(dataset)
    dataset = configure_dataset_timestamps(dataset)
    datasets.append(dataset)
  
  if all([len(d.columns)==len(datasets[0].columns) for d in datasets]):
    combined = pd.concat(datasets)
    combined_sorted = combined.sort_values(by='datetime')
    combined_sorted.reset_index(inplace=True, drop=True)
    combined_sorted.to_excel(out_filepath)
  else:
    print('error: inconsistent column names across datasets')

file_couples = {
  # 126: [
  #   "Inputs/Skyn_Data_RAW/ACE/126/20210826-20210831/1min_readings-from-2021-08-26-to-2021-08-31.xlsx",
  #   "Inputs/Skyn_Data_RAW/ACE/126/20210908-20210930/20sec_readings-from-2021-09-08-to-2021-09-30.csv"
  # ],
  # 283: [
  #   "Inputs/Skyn_Data_RAW/ACE/283/1st Bracelet (Day 0 - Day 8)/20sec_04192024-04272024.csv",
  #   "Inputs/Skyn_Data_RAW/ACE/283/2nd Bracelet (Day 13 - Day 28)/20sec_20240502-20240517.csv"
  # ],
  # 284: [
  #   "Inputs/Skyn_Data_RAW/ACE/284/1st bracelet (Day 0-Day 9)/20sec_20240425-20240504.csv",
  #   "Inputs/Skyn_Data_RAW/ACE/284/2nd bracelet (Day 11-Day 28)/20sec_20240506-20240524.csv"
  # ],
  # 294: [
  #   "Inputs/Skyn_Data_RAW/ACE/294/1st Bracelet (Day 0 - Day 25)/20sec_20240620-20240715.csv",
  #   "Inputs/Skyn_Data_RAW/ACE/294/2nd Bracelet (Day 26 - Day 28)/20sec_20240716-20240718.csv"
  # ],
  # 297: [
  #   "Inputs/Skyn_Data_RAW/ACE/297/1st Bracelet (Day 0 - Day 21)/20sec_20240730-20240820.csv",
  #   "Inputs/Skyn_Data_RAW/ACE/297/2nd Bracelet (Day 21 - Day 28)/20sec_20240820-20240827.csv"
  # ]
}

for subid, paths in file_couples.items():
  print(subid)
  out_filepath = f'Inputs/Skyn_Data_RAW/ACE/{subid}_001.xlsx'
  combine_skyn_datasets(paths, out_filepath)

