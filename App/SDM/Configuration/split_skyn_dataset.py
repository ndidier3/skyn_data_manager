import pandas as pd
from datetime import datetime, timedelta
from SDM.Configuration.configuration import configure_timestamp_column

def split_skyn_dataset(data_to_split, split_time):
  data_to_split['datetime'] = configure_timestamp_column(data_to_split)
  data_to_split.sort_values(by='datetime', inplace=True)

  unique_days = data_to_split['datetime'].dt.date.unique().tolist()
  day_before = unique_days[0] - timedelta(days=1)
  unique_days = [day_before] + unique_days

  datasets = {}
  for unique_day in unique_days:
    hour, minute = map(int, split_time.split(':'))
    start = datetime(unique_day.year, unique_day.month, unique_day.day, hour, minute)
    end = start + timedelta(hours=24)
    data = data_to_split[(data_to_split['datetime'] > start) & (data_to_split['datetime'] < end)]
    if len(data) > 0:
      datasets[str(min(data['datetime'])) + ' - ' + str(max(data['datetime']))] = data

  return datasets

def split_skyn_dataset_by_email(data_to_split, split_time):
    data_to_split['datetime'] = configure_timestamp_column(data_to_split)
    data_to_split.sort_values(by='datetime', inplace=True)

    all_datasets = {}

    email_groups = data_to_split.groupby('email')

    for email, group in email_groups:
        datasets = {}

        unique_days = group['datetime'].dt.date.unique().tolist()
        day_before = unique_days[0] - timedelta(days=1)
        unique_days = [day_before] + unique_days

        for unique_day in unique_days:
            hour, minute = map(int, split_time.split(':'))
            start = datetime(unique_day.year, unique_day.month, unique_day.day, hour, minute)
            end = start + timedelta(hours=24)
            data = group[(group['datetime'] > start) & (group['datetime'] < end)]
            if len(data) > 0:
                key = f"{email}: {min(data['datetime'])} - {max(data['datetime'])}"
                datasets[key] = data

        all_datasets[email] = datasets

    return all_datasets




  
