from codecs import ignore_errors
import pandas as pd
from pandas import NaT
from datetime import timedelta
from statistics import mode
from sklearn import preprocessing
import numpy as np
import os
from SDM.User_Interface.Utils.filename_tools import stringify_dataset_id

"""
this file contains utilies for loading the date, standardizing formats, retrieving unique identifiers, etc.
"""

starting_standard_columns = ['datetime', 'device_id', 'Firmware Version', 'TAC ug/L(air)', 'Temperature_C', 'Motion'] 

def update_column_names(df):
    df.rename(columns = {
            'device timestamp': 'datetime',
            'Timestamp': 'datetime',
            'Device Serial Number': 'device_id',
            'firmware version': 'Firmware Version',
            'Firmware version': 'Firmware Version',
            'tac (ug/L)': 'TAC ug/L(air)',
            'temperature (C)': 'Temperature_C',
            'Temperature C': 'Temperature_C',
            'Temperature LSB': 'Temperature_C',
            'motion (g)': 'Motion',
            'Motion LSB': 'Motion',
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

def configure_timestamp_column(df):
    df['datetime_with_timezone'] = pd.to_datetime(df['datetime'], format='%Y-%m-%d %H:%M:%S %z', errors='coerce')
    df['datetime_without_timezone'] = pd.to_datetime(df['datetime'], format='%Y-%m-%d %H:%M:%S', errors='coerce')

    # Check which format was successful
    if not df['datetime_with_timezone'].isna().all():
        df['datetime'] = df['datetime_with_timezone'].dt.tz_localize(None)
    elif not df['datetime_without_timezone'].isna().all():
        df['datetime'] = df['datetime_without_timezone']
    
    # Drop the intermediate columns
    df.drop(['datetime_with_timezone', 'datetime_without_timezone'], axis=1, inplace=True)
    df.reset_index(inplace=True, drop=True)
    return df['datetime']

def get_sampling_rate(df, timestamp_column):

    time_diff = df[timestamp_column].diff()

    # Calculate the average time difference
    average_sampling_rate = time_diff.mean().total_seconds()  # Get the average in seconds
    average_sampling_rate_per_minute = round(60 / average_sampling_rate)  # Calculate samples per minute

    return average_sampling_rate_per_minute

def get_time_elapsed(df, timestamp_column):
    try:
        start_time = df[timestamp_column].iloc[0]
        df['Duration_Hrs'] = (df[timestamp_column] - start_time).dt.total_seconds() / 3600  # Calculate time elapsed in hours
        return df
    except:
        df['Duration_Hrs'] = np.nan
        return df
    
def remove_junk_columns(df):
    for col in df.columns:
        if col not in starting_standard_columns:
            df.drop('level_0', axis=1, inplace=True, errors='ignore')

    return df

def get_metadata_index(self):
    print(self.subid)
    print(self.episode_identifier)
    print(self.dataset_identifier)
    try:
        filtered_metadata = self.metadata[(self.metadata['SubID']==self.subid) & (self.metadata['Episode_Identifier'] == int(self.episode_identifier[1:])) & (self.metadata['Dataset_Identifier'] == int(self.dataset_identifier))]
        return filtered_metadata.index.tolist()[0]
    except:
        return None

def load_metadata(self, column='TotalDrks'):
    try:
        return self.metadata.loc[self.metadata_index, column]
    except:
        return None

def is_binge(self):

    if self.drinks == 0:
        return "None"
    elif (self.sex == None) or (self.drinks == None):
        return "Unk"
    elif (self.sex == 1) and (self.drinks >= 5):
        return "Heavy"
    elif (self.sex == 2) and (self.drinks >= 4):
        return "Heavy"
    elif (self.drinks > 0):
        return "Light"
    else:
        return "Unk"
    

#NOT TESTED
def baseline_correct_tac(tac_column):
    if tac_column.min() < 0:
        return tac_column - tac_column.min()
    else:
        return tac_column
    
def nearest_odd(number):
    return 2 * round(number / 2) + 1
    
def get_full_identifier(subid, dataset_identifier, episode_identifier):
    return str(subid) + '_' + stringify_dataset_id(dataset_identifier) + episode_identifier

def get_full_identifier_from_metadata(metadata_row):
    dataset_identifier = '' if str(metadata_row['Dataset_Identifier']) == 'nan' else stringify_dataset_id(metadata_row['Dataset_Identifier'])
    episode_identifier = 'e1' if str(metadata_row['Episode_Identifier']) == 'nan' else 'e' + str(metadata_row['Episode_Identifier'])
    return str(metadata_row['SubID']) + '_' + dataset_identifier + episode_identifier

def get_cohort_full_identifiers(metadata):
  """provide metadata, function returns a list containing """
  return [get_full_identifier_from_metadata(row) for i, row in metadata.iterrows() if row['Use_Data'] == 'Y']      

def is_DMY_format(dates):

  filtered_dates = dates.dropna()
  any_DMY = pd.to_datetime(filtered_dates, errors='coerce', format='%d/%m/%Y').notnull().any()
  all_MDY = pd.to_datetime(filtered_dates, errors='coerce', format='%m/%d/%Y').notnull().all()
  return any_DMY and not all_MDY

def standardize_date_column_YMD(timestamps, column_name='Crop Begin Date', new_column_name="Crop Begin Date"):
    """provide structured dataframe (see Resource folder for example), 
    ensures standard datetime type for the date column"""

    import warnings
    warnings.filterwarnings("ignore", message="Parsing '.*' in DD/MM/YYYY format.*", category=UserWarning)

    # #convert Submitted Date/Time column to datetime type
    # timestamps.loc[:, column_name] = pd.to_datetime(timestamps.loc[:, column_name])

    #standardize column format
    if is_DMY_format(timestamps[column_name]):
        mask = pd.to_datetime(timestamps[column_name], errors='coerce', format='%d/%m/%Y').notnull()
        timestamps.loc[~mask, column_name] = pd.to_datetime(timestamps.loc[~mask, column_name], errors='coerce').dt.strftime('%m/%d/%Y')
        timestamps[column_name] = pd.to_datetime(timestamps[column_name], errors='coerce', format='%d/%m/%Y')
    else:
        timestamps[column_name] = pd.to_datetime(timestamps[column_name], errors='coerce', format='%m/%d/%Y')
        # timestamps[new_column_name] = timestamps[column_name].dt.strftime('%m/%d/%Y')

    #convert Date string column to datetime type
    # timestamps.loc[:, new_column_name] = pd.to_datetime(timestamps.loc[:, new_column_name])

    #convert date format to yyyy/mm/dd
    # timestamps[new_column_name] = pd.to_datetime(timestamps[new_column_name], format='%Y-%m-%d')

    #remove time component of datetime variable to only have date
    timestamps[new_column_name] = timestamps[new_column_name].apply(lambda x: x.date())
  
    return timestamps

def configure_timestamps(metadata_path):
    metadata = pd.read_excel(metadata_path)
    # metadata = metadata[metadata['Use_Data']=="Y"]
    metadata.reset_index(inplace=True, drop=True)
    # try:
    metadata = standardize_date_column_YMD(metadata, column_name='Crop Begin Date', new_column_name='Crop Begin Date')
    metadata = standardize_date_column_YMD(metadata, column_name='Crop End Date', new_column_name='Crop End Date')
    return metadata
    # except:
    #     return metadata

def create_output_folders(self):
    if not os.path.exists(self.data_out_folder):
      os.mkdir(self.data_out_folder)
    if not os.path.exists(self.plot_folder):
      os.mkdir(self.plot_folder)
    subid_plot_folder = f'{self.plot_folder}/{self.subid}/'
    if not os.path.exists(subid_plot_folder):
      os.mkdir(subid_plot_folder)
    full_plot_folder = f'{self.plot_folder}/{self.subid}/{self.dataset_identifier}{self.condition if self.condition else ""}/'
    if not os.path.exists(full_plot_folder):
      os.mkdir(full_plot_folder)
    self.plot_folder = full_plot_folder

def load_dataset(self):
    if self.path[-3:] == 'csv':
      return pd.read_csv(self.path, index_col=False)
    else:
      return pd.read_excel(self.path, index_col=False)

def configure_raw_data(self):
    print(f'initializing \n{self.subid} \n{self.condition} {self.dataset_identifier}')
    print(self.path)
    self.unprocessed_dataset['SubID'] = self.subid
    self.unprocessed_dataset['Dataset_Identifier'] = self.dataset_identifier
    self.unprocessed_dataset['Episode_Identifier'] = self.episode_identifier
    self.unprocessed_dataset['Full_Identifier'] = get_full_identifier(self.subid, self.dataset_identifier, self.episode_identifier)
    
    df_raw = update_column_names(self.unprocessed_dataset)
    df_raw = rename_TAC_column(df_raw)

    try:
        df_raw["datetime"] = pd.to_datetime(df_raw["datetime"], unit='s')
    except:
        df_raw["datetime"] = pd.to_datetime(df_raw["datetime"])

    df_raw = df_raw.sort_values(by="datetime", ignore_index=True)
    df_raw.reset_index(inplace=True, drop=True)
    df_raw['Row_ID'] = df_raw['Full_Identifier'].astype(str) + '_' + df_raw.index.astype(str)

    df_raw = df_raw[['SubID', 'Dataset_Identifier', 'Episode_Identifier', 'Full_Identifier', 'Row_ID'] + [col for col in df_raw.columns.tolist() if col not in ['SubID', 'Dataset_Identifier', 'Episode_Identifier', 'Full_Identifier', 'Row_ID']]]

    sampling_rate = get_sampling_rate(df_raw, 'datetime')
    if sampling_rate > 1:
        print('reached123')
        df_raw = reduce_sampling_rate(df_raw, 'datetime')

    df_raw = get_time_elapsed(df_raw, 'datetime')

    df_raw = remove_junk_columns(df_raw)

    return df_raw

    # if self.impute_baseline:
    # df_raw['TAC'] = baseline_correct_tac(df_raw['TAC'])
    # self.baseline_corrected = True

def timestamp_available(self, begin_or_end='Begin'):
    filter = (self.metadata['SubID'] == self.subid) & (((self.metadata['Dataset_Identifier'] == str(self.dataset_identifier))) | (self.metadata['Dataset_Identifier'] == int(self.dataset_identifier))) & (self.metadata['Episode_Identifier'] == int(self.episode_identifier[1:]))
    return (self.metadata.loc[filter, f'Crop {begin_or_end} Date'].notnull().any() and
            self.metadata.loc[filter, f'Crop {begin_or_end} Time'].notnull().any())
    
def get_event_timestamps(self, metadata_path):
    try:
        timestamps = pd.read_excel(metadata_path, sheet_name="Additional_Timestamps")
        timestamp_columns = [col for i, col in enumerate(timestamps.columns) if i > 5]
        timestamps[timestamp_columns] = timestamps[timestamp_columns].apply(pd.to_datetime, format='%Y-%m-%d %H:%M', errors='coerce')
        timestamps = timestamps[(timestamps['SubID'] == self.subid) & (timestamps['Dataset_Identifier'] == self.dataset_identifier) & (timestamps['Episode_Identifier'] == int(self.episode_identifier[1:]))]
        event_timestamps = {col: timestamps.loc[timestamps.index.tolist()[0], col] for col in [col for col in timestamps.select_dtypes(include='datetime64').columns]}
        return {key: value for key, value in event_timestamps.items() if value is not NaT}
    except:
        return {}


def get_closest_index_with_timestamp(data, timestamp, datetime_column):
    try:
        return (data[datetime_column] - timestamp).abs().idxmin()
    except:
        return None

def determine_initial_validity(self):

    if self.valid_occasion:
      self.valid_occasion = 1 if self.metadata_index != None else 0
      self.invalid_reason = 'Not in metadata' if self.valid_occasion == 0 else None

    if self.valid_occasion:
        self.valid_occasion = 1 if load_metadata(self, 'Use_Data') == 'Y' else 0
        self.invalid_reason = f'Excluded within Metadata [Use_Data = N]. Note: {self.metadata_note}' if self.valid_occasion == 0 else None
    
    if self.valid_occasion:
      self.valid_occasion = 0 if self.disabled_by_multiple_device_ids else 1
      self.invalid_reason = 'multiple devices detected within dataset' if self.valid_occasion == 0 else None
    
    return self.valid_occasion, self.invalid_reason

def determine_post_cleaning_validity(self):

    device_off_or_removed = (self.dataset['gap_imputed'] == 1) | (self.dataset['TAC_device_off_imputed'] == 1)
    all_imputations = device_off_or_removed | (self.dataset['major_outlier'] == 1) | (self.dataset['minor_outlier'] == 1) | (self.dataset['sloped_start'] == 1) | (self.dataset['extreme_outlier'] == 1)

    self.stats['device_inactive_perc'] = (device_off_or_removed.sum() / len(self.dataset)) * 100
    self.stats['device_inactive_duration'] = (device_off_or_removed.sum() * self.sampling_rate) / 60
    self.stats['device_active_perc'] = 100 - self.stats['device_inactive_perc'] 
    self.stats['device_active_duration'] = (self.dataset['Duration_Hrs'].max() - self.dataset['Duration_Hrs'].min()) - (device_off_or_removed.sum() * self.sampling_rate) / 60

    self.stats[f'imputed_N'] = all_imputations.sum()
    self.stats['tac_imputed_duration'] = (all_imputations.sum() * self.sampling_rate) / 60
    self.stats['tac_imputed_perc'] = (all_imputations.sum() / len(self.dataset)) * 100

    device_active_duration = ((len(self.dataset) - device_off_or_removed.sum()) * self.sampling_rate) / 60
    enough_device_on = (self.stats['device_inactive_perc'] < self.max_percentage_inactive) and device_active_duration > self.min_duration_active
    too_many_imputations = self.stats['tac_imputed_perc'] > self.max_percentage_imputed 

    self.valid_occasion = 1 if enough_device_on else 0
    if not self.valid_occasion:
        self.invalid_reason = f'Duration of device inactivity (device non-wear, device off) is too great either because max allowed percentage of inactivity ({self.max_percentage_inactive}%) was exceeded or minimum required duration of {self.min_duration_active} hour(s) was not met. Device inactive for {round(self.stats["device_inactive_perc"], 1)}% and there is {round(device_active_duration, 1)} hours of valid data.'
        return self.valid_occasion, self.invalid_reason
    
    self.valid_occasion = 0 if too_many_imputations else 1
    if not self.valid_occasion:
        self.invalid_reason = f'Device is too noisy or contains too many artifacts. Specifically, {round(self.stats["tac_imputed_perc"], 1)} of the data was imputed, which exceeds the limit of {self.max_percentage_imputed}.'
        return self.valid_occasion, self.invalid_reason

    return self.valid_occasion, self.invalid_reason

def reduce_sampling_rate(raw_data, timestamp_column, cutoff_sec = 59):
    last_index = 0
    indices_to_keep = [last_index]

    for i, row in raw_data.iterrows():
        if i > 0:
            duration_diff = (raw_data.loc[i, timestamp_column] - raw_data.loc[last_index, timestamp_column]).total_seconds()
            if duration_diff >= cutoff_sec:
                indices_to_keep.append(i)
                last_index = i

    reduced_data = raw_data.loc[indices_to_keep].reset_index(drop=True)

    return reduced_data
