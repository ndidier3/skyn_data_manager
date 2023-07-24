import pandas as pd
from pathlib import Path
from configuration import multiple_device_ids

def check_for_multiple_devices(path):
    for ext in ['csv', 'xlsx']:
      files = Path(path).glob(f'*.{ext}')
      for file in files:
        if ext == 'xlsx': 
          data = pd.read_excel(file)
        else:
          data = pd.read_csv(file)
        data.rename(columns={'device id': 'device_id'}, inplace=True)
        if multiple_device_ids(data):
            print(file)

def check_for_invalid_dataset(path):
    for ext in ['csv', 'xlsx']:
      files = Path(path).glob(f'*.{ext}')
      for file in files:
        if ext == 'xlsx': 
          data = pd.read_excel(file)
        else:
          data = pd.read_csv(file)
        if (data.iloc[:, 7] < 0).any():
           print(file)

# check_for_multiple_devices('raw/C4_lab/')
# check_for_invalid_dataset('raw/C4_lab/')