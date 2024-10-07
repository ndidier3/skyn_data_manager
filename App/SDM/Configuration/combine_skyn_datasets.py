import pandas as pd
import os
from App.SDM.Configuration.configuration import update_column_names, rename_TAC_column, configure_dataset_timestamps

def combine_skyn_datasets(filepaths, export_folder):
  datasets = []
  for path in filepaths:
    _, ext = os.path.splitext(path)
    if ext == '.csv':
      dataset = pd.read_csv(path)
    elif ext == '.xlsx' or ext == '.xls':
      dataset = pd.read_excel(path)
    
    #standardize column names before combining
    dataset = update_column_names(dataset)
    dataset = rename_TAC_column(dataset)
    dataset = configure_dataset_timestamps(dataset)
  
  if all([len(d.columns)==len(datasets[0].columns) for d in datasets]):
    combined = pd.concat(datasets)
    combined_sorted = combined.sort_values(by='datetime')
    combined_sorted.reset_index(inplace=True, drop=True)
    combined_sorted.to_excel(export_folder)
  else:
    print('error: inconsistent column names across datasets')