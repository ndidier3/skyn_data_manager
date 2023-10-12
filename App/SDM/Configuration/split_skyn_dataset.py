import pandas as pd
from datetime import datetime

def split_skyn_dataset(data_to_split, split_time, interval, exclude_start = None, exclude_end = None):
  print(data_to_split, split_time, interval, exclude_start, exclude_end)
  data_to_split['datetime'] = pd.to_datetime(data_to_split['datetime'])
  data_to_split.sort_values(by='datetime', inplace=True)

  exclude_timeframe = exclude_start != 'None' and exclude_end != 'None'
  if exclude_timeframe:
    exclude_start_hour, exclude_start_minute = map(int, exclude_start.split(':'))
    exclude_end_hour, exclude_end_minute = map(int, exclude_end.split(':'))
    exclude_interval_crosses_midnight = exclude_start_hour + (exclude_start_minute / 60) > exclude_end_hour + (exclude_end_hour / 60) 
      
  datasets = {}

  for unique_day in data_to_split['datetime'].dt.date.unique().tolist():
    hour, minute = map(int, split_time.split(':'))
    start = datetime(unique_day.year, unique_day.month, unique_day.day, hour, minute)
    end = datetime(unique_day.year, unique_day.month, unique_day.day + 1, hour, minute)
    data = data_to_split[(data_to_split['datetime'] > start) & (data_to_split['datetime'] < end)]
    if exclude_timeframe:
      for day_idx in [0, 1]:
        exclude_start_time = datetime(unique_day.year, unique_day.month, unique_day.day + day_idx, exclude_start_hour, exclude_start_minute)
        exclude_end_time = datetime(unique_day.year, unique_day.month, unique_day.day + day_idx + (1 if exclude_interval_crosses_midnight else 0), exclude_end_hour, exclude_end_minute)
        data = data[~((data['datetime'] >= pd.to_datetime(exclude_start_time)) & (data['datetime'] <= pd.to_datetime(exclude_end_time)))]
    
    if len(data) > 0:
      datasets[str(start) + ' - ' + str(end)] = data

  return datasets






  
