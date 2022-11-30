from codecs import ignore_errors
import pandas as pd
from datetime import timedelta
from statistics import mode
from sklearn import preprocessing
import numpy as np


def update_column_names(df):
    df.rename(columns = {
            'device timestamp': 'datetime',
            'firmware version': 'Firmware_Version',
            'Firmware Version': 'Firmware_Version',
            'tac (ug/L)': 'TAC ug/L(air)',
            'temperature (C)': 'Temperature_C',
            'Temperature C': 'Temperature_C',
            'motion (g)': 'Motion',
            'device id': 'device_id'
        }, 
            inplace=True,
            errors='ignore'
        )
    return df

def rename_TAC_column(df):
    df.rename(columns = {'TAC ug/L(air)':'TAC'}, inplace=True)
    df.drop('TAC LSB', axis=1, inplace=True, errors='ignore')
    return df

def multiple_device_ids(df):
    return len(df['device_id'].unique()) > 1

def normalize_column(series):
    mean = series.mean()
    stdev = series.std()
    norm = (series - mean) / (stdev)
    return norm

def get_time_elapsed(df):
    try:
        df.loc[:, "datetime"] = pd.to_datetime(df.loc[:, "datetime"], unit='s')
    except:
        df.loc[:, "datetime"] = pd.to_datetime(df.loc[:, "datetime"])
    if 'device time zone' in df.columns.tolist():
        if df['device time zone'].mode().tolist()[0] == 'UTC':
            df['datetime'] = df['datetime'] - timedelta(hours=6)

    df = df.sort_values(by="datetime", ignore_index=True)
    df.reset_index(inplace=True, drop=True)

    timestamp_occurences = {}
    intervals = []
    for timestamp in df['datetime'].unique():
        temp_df = df[df['datetime'] == timestamp]
        timestamp_occurences[timestamp] = len(temp_df)
        interval = len(temp_df)
        intervals.append(interval)
        if interval >= 2:
            n = 0
            for index, row in temp_df.iterrows():
                df.loc[index, 'datetime'] = df.loc[index, 'datetime'] + (timedelta(seconds=(n*(60/interval))))
                n += 1

    df['Time'] = df['datetime'].dt.strftime('%I:%M:%S %p')

    new_day_index_list = df.index[df['Time'] == '12:00:00 AM'].tolist()
    if len(new_day_index_list) > 0:
        first_day_duration = (df.loc[new_day_index_list[0], 'datetime'] - df.loc[0, 'datetime']).total_seconds() / 60 / 60
    else:
        first_day_duration = (df.loc[len(df)-1, 'datetime'] - df.loc[0, 'datetime']).total_seconds() / 60 / 60

    #ADJUST TO BE ABLE TO HANDLE ANY NUMBER OF DAYS
    new_day_index_list.insert(0, 0)
    for i in range(0, len(new_day_index_list)):
        lower_index = new_day_index_list[i]
        if (i + 1) < len(new_day_index_list):
            higher_index = new_day_index_list[i+1]-1
        elif (i + 1) == len(new_day_index_list):
            higher_index = len(df) - 1
        else:
            print('error')
        if i==0:  
            df.loc[lower_index:higher_index,'time_elapsed_hours'] = (df.loc[lower_index:higher_index,'datetime'] - df.loc[0, 'datetime']).dt.seconds / 60 / 60
        else:
            df.loc[lower_index:higher_index:,'time_elapsed_hours'] = ((df.loc[lower_index:higher_index, 'datetime'] - df.loc[lower_index, 'datetime']).dt.seconds / 60 / 60) + (24*(i-1)) + first_day_duration

    df.reset_index(inplace=True)
    df.to_excel('C:/Users/ndidier/Desktop/test_7001.xlsx')
    return df, new_day_index_list, mode(intervals)

def remove_junk_columns(df):
    df.drop('level_0', axis=1, inplace=True, errors='ignore')
    df.drop('index', axis=1, inplace=True, errors='ignore')
    df.drop('Unnamed: 9', axis=1, inplace=True, errors='ignore')
    df.drop('Unnamed: 10', axis=1, inplace=True, errors='ignore')
    df.drop('Unnamed: 11', axis=1, inplace=True, errors='ignore')
    df.drop('Unnamed: 12', axis=1, inplace=True, errors='ignore')
    df.drop('email', axis=1, inplace=True, errors='ignore')
    df.drop('Alcohol episode', axis=1, inplace=True, errors='ignore')
    df.drop('Non alcohol episode', axis=1, inplace=True, errors='ignore')
    df.drop('MARS ID', axis=1, inplace=True, errors='ignore')
    df.drop('SubID', axis=1, inplace=True, errors='ignore')
    #df.drop('bac_level', axis=1, inplace=True, errors='ignore')
    #df.drop('bac_level', axis=1, inplace=True, errors='ignore')
    return df

def get_subid_from_path(path):
    subid_index = path.index('#') + 1
    subid = int(path[subid_index:subid_index+4])
    return subid

def get_condition_from_path(path):
    condition_index = path.index('.') - 3
    condition = path[condition_index:condition_index+3]
    return condition

def get_drink_count(drink_counts_df, subid, condition):
    print(subid)
    if condition == 'Alc':
        return drink_counts_df[drink_counts_df['SubID']==subid]['TotalDrks'].tolist()[0]
    else:
        return 0