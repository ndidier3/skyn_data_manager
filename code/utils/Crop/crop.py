import pandas as pd
from datetime import datetime, timedelta

def get_session_start_date_and_time(dataset):
  datetime_start = dataset.loc[0, 'datetime']
  datetime_start = datetime.strptime(str(datetime_start), '%Y-%m-%d %H:%M:%S') 
    
  date = datetime_start.date()
  start_time = datetime_start.time()
  
  return date, start_time

def get_valid_session_info(quality_assessment_df):
  df_good_data = quality_assessment_df[quality_assessment_df['Good?']=='Y']
  subid_condition_list = []
  best_output_dict = {}
  for i, row in df_good_data.iterrows():
      subid_condition = str(row['SubID']) + '_' + row['Condition']
      subid_condition_list.append(subid_condition)
      best_output_dict[subid_condition] = row['Best Output']

  return subid_condition_list, best_output_dict

def get_best_output_column_name(best_output):
    
    output_column_key = {'greedy' : 'TAC_cleaned_greedy',
                        'cleaned': 'TAC_cleaned',
                        'raw': 'TAC'}
    
    return output_column_key[best_output]

def get_session_time_range(session_timestamp):
  time_begin_drinking = str(session_timestamp.loc[0, 'Survey Submitted Time'])
  date_begin_drinking = str(session_timestamp.loc[0, 'Date'])
  datetime_string_begin_drinking =  date_begin_drinking + ' ' + time_begin_drinking
  date_format_str = '%Y-%m-%d %H:%M:%S'
  datetime_begin_drinking = datetime.strptime(datetime_string_begin_drinking, date_format_str)
  eighteen_hours_later = datetime_begin_drinking + timedelta(hours=18)
  return datetime_begin_drinking, eighteen_hours_later

def make_date_column(MW_timestamps):
  #convert Submitted Date/Time column to datetime type
  MW_timestamps.loc[:, 'Survey Submitted Date'] = pd.to_datetime(MW_timestamps.loc[:, 'Survey Submitted Date'])

  #Make a new column Date in dd/mm/yyyy format
  MW_timestamps['Date'] = MW_timestamps['Survey Submitted Date'].dt.strftime('%d/%m/%Y')

  #convert Date column to datetime type
  MW_timestamps.loc[:, 'Date'] = pd.to_datetime(MW_timestamps.loc[:, 'Date'])

  #convert date format to yyyy/mm/dd
  MW_timestamps['Date'] = pd.to_datetime(MW_timestamps['Date'], format='%Y-%m-%d')

  #remove time component of datetime variable to only have date
  MW_timestamps['Date'] = MW_timestamps['Date'].apply(lambda x: x.date())
  
  return MW_timestamps

def crop_using_timestamp(subid, condition, dataset, quality_assessment_df, MW_df):
  date, start_time = get_session_start_date_and_time(dataset)
  valid_session_info, best_output = get_valid_session_info(quality_assessment_df)
  MW_timestamps = make_date_column(MW_df)
  pass_test = {}

  Subid_condition = str(subid) + '_' + condition
  if Subid_condition in valid_session_info:
    session_timestamp = MW_timestamps[(MW_timestamps['SubID']==subid)]
    session_timestamp = session_timestamp[session_timestamp['Date']==date]
    session_timestamp.reset_index(inplace=True, drop=True)

    if len(session_timestamp) == 0:
      pass_test[Subid_condition] = 0
      hour_conversion = 0
    else:
      pass_test[Subid_condition] = 1
      time_zone_code = int(session_timestamp.loc[0, 'Time Zone'][:2])
      hour_conversion = time_zone_code + 5

      dataset['Time_Adjusted'] = dataset['datetime'] + pd.Timedelta(hours=hour_conversion)
      datetime_begin_drinking, eighteen_hours_later = get_session_time_range(session_timestamp)
      cropped_clean_dataset = dataset[(dataset['Time_Adjusted'] > datetime_begin_drinking) & (dataset['Time_Adjusted'] < eighteen_hours_later)]
      cropped_clean_dataset.reset_index(drop=True, inplace=True)

      time_correction = cropped_clean_dataset.loc[0, 'time_elapsed_hours']
      cropped_clean_dataset.loc[:, 'time_elapsed_hours_adjusted'] = cropped_clean_dataset['time_elapsed_hours'] - time_correction

    return cropped_clean_dataset

def crop_device_off_end(df):
  if any([True for temp in df.loc[len(df) - 6: len(df) - 1, 'Temperature_C'].tolist() if temp <= 28]):
    temp_below_28 = True
    counter = 6
    while temp_below_28:
      index = len(df) - counter
      if df.loc[index, 'Temperature_C'] > 28:
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
