import pandas as pd
from datetime import datetime, timedelta
from SDM.Configuration.configuration import configure_timestamp_column

def split_skyn_dataset(data_to_split, split_time, interval, exclude_start = None, exclude_end = None):
  data_to_split['datetime'] = configure_timestamp_column(data_to_split)
  data_to_split.sort_values(by='datetime', inplace=True)

  exclude_timeframe = exclude_start != 'None' and exclude_end != 'None'
  # if exclude_timeframe:
  #   exclude_start_hour, exclude_start_minute = map(int, exclude_start.split(':'))
  #   exclude_end_hour, exclude_end_minute = map(int, exclude_end.split(':'))

  datasets = {}
  for unique_day in data_to_split['datetime'].dt.date.unique().tolist():
    hour, minute = map(int, split_time.split(':'))
    start = datetime(unique_day.year, unique_day.month, unique_day.day, hour, minute)
    end = start + timedelta(hours=24)
    data = data_to_split[(data_to_split['datetime'] > start) & (data_to_split['datetime'] < end)]
    if exclude_timeframe:
      start_time = pd.to_datetime(exclude_start + ':00').time()
      end_time = pd.to_datetime(exclude_end + ':00').time()
      # for day_idx in [0, 1]:
      #   if day_idx == 0:
      #     exclude_start_time = datetime(unique_day.year, unique_day.month, unique_day.day, exclude_start_hour, exclude_start_minute)
      #     exclude_end_time = exclude_start_time + timedelta(hours=exclude_interval_hours)
      #   elif day_idx == 1:
      #     exclude_start_time = exclude_start_time + timedelta(hours=24)
      #     exclude_end_time = exclude_end_time + timedelta(hours=24)
      data = data[~((data['datetime'].dt.time > start_time) & (data['datetime'].dt.time <= end_time))]
    
    if len(data) > 0:
      datasets[str(min(data['datetime'])) + ' - ' + str(max(data['datetime']))] = data

  return datasets






  
