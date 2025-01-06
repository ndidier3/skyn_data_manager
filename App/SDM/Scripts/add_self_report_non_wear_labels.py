from App.SDM.Signal_Processing.label_time_windows import label_time_windows
from App.SDM.Configuration.file_management import load, save_to_computer
import os
import numpy as np
import pandas as pd

non_wear_columns = [
    ['braceoff1', 'braceon1'],
    ['braceoff2_1', 'braceon2_1'],
    ['braceoff2_2', 'braceon2_2'], 
    ['braceoff3_1', 'braceon3_1'],
    ['braceoff3_2', 'braceon3_2'],
    ['braceoff3_3', 'braceon3_3']
  ]
flat_columns = [col for sublist in non_wear_columns for col in sublist]

def compile_non_wear_timestamps(non_wear_data, subid):
  missing_days = []
  non_wear_data = non_wear_data[(non_wear_data['ID'] == int(subid)) | (non_wear_data['ID'] == str(subid))]
  non_wear_intervals = []
  for i, row in non_wear_data.iterrows():
    for column_pair in non_wear_columns:
      start_col = column_pair[0]
      end_col = column_pair[1]
      if row[start_col] and row[end_col]:
        print(row[start_col])
        non_wear_intervals.append([row[start_col], row[end_col]])
  
  return non_wear_intervals

def adjust_non_wear_columns(df, date_col, non_wear_columns):
  """
  Adjusts paired non-wear columns to ensure the "on" timestamp occurs after the "off" timestamp.

  Args:
    df (pd.DataFrame): The DataFrame containing the data.
    date_col (str): The name of the column with the date information.
    non_wear_columns (list[list[str]]): A list of pairs of column names, where each pair contains
                                         an "off" column and an "on" column.

  Returns:
    pd.DataFrame: The modified DataFrame with adjusted "on" columns.
  """
  # Convert the date column to datetime and move it back 1 day
  df[date_col] = pd.to_datetime(df[date_col], errors='coerce') - pd.Timedelta(days=1)
  
  for off_col, on_col in non_wear_columns:
    # Replace "off" and "on" columns with combined datetime values
    print(df[on_col])
    df[off_col] = df.apply(
      lambda row: merge_date_time(row[date_col], row[off_col]),
      axis=1
    )
    df[on_col] = df.apply(
      lambda row: merge_date_time(row[date_col], row[on_col]),
      axis=1
    )

    # Adjust "on" column date if it occurs before "off"
    print(df[on_col])
    df[on_col] = df.apply(
      lambda row: row[on_col] + pd.Timedelta(days=1)
      if pd.notna(row[off_col]) and pd.notna(row[on_col]) and row[on_col] < row[off_col]
      else row[on_col],
      axis=1
    )
  
  return df


def merge_date_time(date, time):
  """
  Combines a date and time into a single datetime value. Handles invalid or missing time values.

  Args:
    date (pd.Timestamp): The date part.
    time (datetime.time or str): The time part.

  Returns:
    pd.Timestamp: Combined datetime or NaT if time is invalid.
  """
  if pd.isna(date) or pd.isna(time):
    return pd.NaT

  try:
    # If time is already in datetime.time format, use it directly
    if isinstance(time, str):
      time_parsed = pd.to_datetime(time, format="%H:%M:%S", errors='coerce').time()
    elif isinstance(time, pd._libs.tslibs.nattype.NaTType) or time is None:
      return pd.NaT
    else:
      time_parsed = time

    if time_parsed:
      return date.replace(hour=time_parsed.hour, minute=time_parsed.minute, second=time_parsed.second)
  except Exception:
    pass
  return pd.NaT  


def compare_self_report(df, self_report_col, cutoff_col, model_col):
  """
  Compares self-report values to temp cutoff and model values, adding columns for false positives,
  false negatives, and disagreements for each comparison.

  Args:
    df (pd.DataFrame): Input DataFrame containing the relevant columns.
    self_report_col (str): Column name for self-report values.
    cutoff_col (str): Column name for temp cutoff values.
    model_col (str): Column name for model values.

  Returns:
    pd.DataFrame: Updated DataFrame with the new comparison columns.
  """

  # False positives, false negatives, and disagreement for cutoff vs model
  df['FP_cutoff_vs_model'] = ((df[cutoff_col] == 1) & (df[model_col] == 0)).astype(int)
  df['FN_cutoff_vs_model'] = ((df[cutoff_col] == 0) & (df[model_col] == 1)).astype(int)
  df['DISAGREE_cutoff_vs_model'] = (df[cutoff_col] != df[model_col]).astype(int)

  # False positives, false negatives, and disagreement for self-report vs model
  df['FP_self_report_vs_model'] = ((df[self_report_col] == 1) & (df[model_col] == 0)).astype(int)
  df['FN_self_report_vs_model'] = ((df[self_report_col] == 0) & (df[model_col] == 1)).astype(int)
  df['DISAGREE_self_report_vs_model'] = (df[self_report_col] != df[model_col]).astype(int)

  # False positives, false negatives, and disagreement for self-report vs cutoff
  df['FP_self_report_vs_cutoff'] = ((df[self_report_col] == 1) & (df[cutoff_col] == 0)).astype(int)
  df['FN_self_report_vs_cutoff'] = ((df[self_report_col] == 0) & (df[cutoff_col] == 1)).astype(int)
  df['DISAGREE_self_report_vs_cutoff'] = (df[self_report_col] != df[cutoff_col]).astype(int)

  for col in [
    'FP_cutoff_vs_model', 'FN_cutoff_vs_model', 'DISAGREE_cutoff_vs_model',
    'FP_self_report_vs_model', 'FN_self_report_vs_model', 'DISAGREE_self_report_vs_model',
    'FP_self_report_vs_cutoff', 'FN_self_report_vs_cutoff', 'DISAGREE_self_report_vs_cutoff'
    ]:
    df.loc[
      df['device_turned_on'] == 0, col
    ] = np.nan

  return df

project_root = '/users/ndidier/SDM/skyn_data_manager' 
non_wear_data = pd.read_excel(f'{project_root}/Results/ACE/EMA/ACE_Morning_Processed.xlsx')
non_wear_data = adjust_non_wear_columns(non_wear_data, 'SURVEYDATE', non_wear_columns)
non_wear_data.to_excel(f'{project_root}/Results/ACE/EMA/ACE_Morning_Processed_new.xlsx', index=False)

processed_data_dir = f'{project_root}/Inputs/Skyn_Data_PROCESSED/ACE/'

day_level_results = []

for file in os.listdir(processed_data_dir):
  if "processed" in file:
    sdm_processor = load(file[:-4], processed_data_dir)
    non_wear_intervals = compile_non_wear_timestamps(non_wear_data, sdm_processor.subid)
    print(non_wear_intervals)
    for start, end in non_wear_intervals:
      sdm_processor.dataset = label_time_windows(sdm_processor.dataset, start, end, 'device_worn_self_report')
    
    sdm_processor.dataset.loc[
      sdm_processor.dataset['device_turned_on'] == 0, 'device_worn_self_report'
    ] = np.nan
    
    sdm_processor.dataset = compare_self_report(sdm_processor.dataset, 'device_worn_self_report', 'device_worn_temp_cutoff', 'device_worn_model')
      
    sdm_processor.run_day_level_analysis(non_wear_self_report_column = 'device_worn_self_report')
    day_level_results.append(sdm_processor.day_level_data)

combined_day_level_data = pd.concat(day_level_results, ignore_index=True)
combined_day_level_data.to_excel(f'{project_root}/Results/ACE/day_level_quality_metrics.xlsx', index=None)
