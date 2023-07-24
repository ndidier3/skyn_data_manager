import pandas as pd
from datetime import datetime, timedelta
import numpy as np
from utils.Reporting.plotting import plot_cropping
"""
FOR REVISIONS

if baseline mean is very high and drinking began prior to captured baseline, 
then impute values prior to go back in time

"""

def get_session_start_date_and_time(dataset):
  datetime_start = dataset.loc[0, 'datetime']
  datetime_start = datetime.strptime(str(datetime_start), '%Y-%m-%d %H:%M:%S') 
    
  date = datetime_start.date()
  start_time = datetime_start.time()
  
  return date, start_time

def get_valid_session_info(metadata):
  df_good_data = metadata[metadata['Use_Data']=='Y']
  subid_condition_list = []
  for i, row in df_good_data.iterrows():
      sub_condition = '' if str(row['Sub_Condition']) == 'nan' else row['Sub_Condition']
      subid_condition = str(row['SubID']) + '_' + str(row['Condition']) + sub_condition
      subid_condition_list.append(subid_condition)

  return subid_condition_list

# def is_date_column_DMY_format(date_column):
#   for row in date_column.tolist():
#     if int(str(row).split('/')[0]) > 12:
#       return True
#   return False

def get_session_time_range(session_timestamp, max_duration):
  time_begin_drinking = str(session_timestamp.loc[0, 'Start Time'])
  date_begin_drinking = str(session_timestamp.loc[0, 'Date'])
  datetime_string_begin_drinking =  date_begin_drinking + ' ' + time_begin_drinking
  date_format_str = '%Y-%m-%d %H:%M:%S'
  datetime_begin_drinking = datetime.strptime(datetime_string_begin_drinking, date_format_str)
  datetime_end_episode = datetime_begin_drinking + timedelta(hours=max_duration)
  return datetime_begin_drinking, datetime_end_episode

def make_date_column(timestamps):
  #convert Submitted Date/Time column to datetime type
  timestamps.loc[:, 'Start Date'] = pd.to_datetime(timestamps.loc[:, 'Start Date'])

  #standardize column format
  #if is_date_column_DMY_format(timestamps['Start Date']):
  timestamps['Date'] = timestamps['Start Date'].dt.strftime('%d/%m/%Y')
  #else:
   # timestamps['Date'] = timestamps['Start Date'].dt.strftime('%m/%d/%Y')

  #convert Date string column to datetime type
  timestamps.loc[:, 'Date'] = pd.to_datetime(timestamps.loc[:, 'Date'])

  #convert date format to yyyy/mm/dd
  timestamps['Date'] = pd.to_datetime(timestamps['Date'], format='%Y-%m-%d')

  #remove time component of datetime variable to only have date
  timestamps['Date'] = timestamps['Date'].apply(lambda x: x.date())
  
  return timestamps

def crop_using_timestamp(subid, condition, sub_condition, dataset, metadata, timestamp_data, plot_directory, max_duration, skyn_download_timezone):
  start_date, start_time = get_session_start_date_and_time(dataset)
  valid_session_info = get_valid_session_info(metadata)
  timestamps = make_date_column(timestamp_data)
  pass_test = {}

  Subid_condition = str(subid) + '_' + condition + sub_condition
  if Subid_condition in valid_session_info:
    session_timestamp = timestamps[(timestamps['SubID']==subid)]
    session_timestamp = session_timestamp[session_timestamp['Date']==start_date]
    session_timestamp.reset_index(inplace=True, drop=True)
    if len(session_timestamp) == 0:
      pass_test[Subid_condition] = 0
      hour_adjustment = 0
    else:
      pass_test[Subid_condition] = 1
      time_zone_code = int(session_timestamp.loc[0, 'Time Zone'].split(':')[0]) if session_timestamp.loc[0, 'Time Zone'] else skyn_download_timezone
      hour_adjustment = time_zone_code - (skyn_download_timezone)
      dataset.loc[:, 'Time_Adjusted'] = dataset.loc[:, 'datetime'] + pd.Timedelta(hours=hour_adjustment)
      datetime_begin_drinking, datetime_end_episode = get_session_time_range(session_timestamp, max_duration)
      cropped_plot_path = plot_cropping(dataset, datetime_begin_drinking, datetime_end_episode, subid, condition, sub_condition, plot_directory, max_duration)
      cropped_clean_dataset = dataset[(dataset['Time_Adjusted'] > datetime_begin_drinking) & (dataset['Time_Adjusted'] < datetime_end_episode)]
      cropped_clean_dataset.reset_index(drop=True, inplace=True)

      time_correction = cropped_clean_dataset.loc[0, 'time_elapsed_hours']
      cropped_clean_dataset.loc[:, 'time_elapsed_hours_adjusted'] = cropped_clean_dataset['time_elapsed_hours'] - time_correction
      return cropped_clean_dataset, cropped_plot_path


def crop_device_off_end(df):
  if any([True for temp in df.loc[len(df) - 6: len(df) - 1, 'Temperature_C'].tolist() if temp <= 28]):
    temp_below_28 = True
    counter = 6
    while temp_below_28:
      index = len(df) - counter
      if df.loc[index, 'Temperature_C'] > 28:
        temp_below_28 = False
      if counter == len(df) - 6:
        temp_below_28 = False
      counter += 1
    return df.loc[:index], counter
  else:
    return df, 0

def crop_device_off_start(df):
  if any([True for temp in df.loc[:6, 'Temperature_C'].tolist() if temp <= 28]):
    temp_below_28 = True
    counter = 6
    while temp_below_28:
      index = counter
      if df.loc[index, 'Temperature_C'] > 28:
        temp_below_28 = False
      counter += 1
    df = df.loc[index:]
    df.reset_index(inplace=True)
    return df, counter
  else:
    return df, 0
