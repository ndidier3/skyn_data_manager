import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from SDM.Visualization.plotting_utils import *

def create_histogram_self_reported_non_wear(day_id_list, non_wear_duration_list, out_path, version):
  plt.bar(day_id_list, non_wear_duration_list)
  plt.xlabel('Day ID')
  plt.ylabel(f'{version} of Non-Wear')
  plt.title(f'{version} of Non-Wear by EMA Day')
  plt.savefig(out_path)
  plt.close()

def create_histogram_day_level_device_non_wear(day_level_quality_metric_path, out_path): 
  # title = 'Distribution of Device Turned On Duration'
  title = 'Distribution of Device Worn Duration'
  # variable = 'device_turned_on_duration'
  variable = 'device_worn_duration'

  df = pd.read_excel(day_level_quality_metric_path)

  df = df.sort_values(by=['SubID', 'DayNo'])

  # Step 2: Group by 'SubID' and filter first and last 'DayNo' for each group
  first_last_df = df.groupby('SubID').agg(
      first_day=('DayNo', 'first'),
      last_day=('DayNo', 'last')
  ).reset_index()

  # Step 3: Filter the original DataFrame to retain only rows corresponding to the first and last DayNo
  filtered_df = df[df['DayNo'].isin(first_last_df['first_day']) | df['DayNo'].isin(first_last_df['last_day'])]

  filtered_df = filtered_df[filtered_df['SubID']!=1006]

  plt.figure(figsize=(12, 6))
  plt.hist(filtered_df[variable], bins=24, edgecolor='black')
  plt.title(title)
  plt.xlabel(variable)
  plt.ylabel('Frequency')

  plt.savefig(out_path)

def plot_device_removal(df, plot_folder, subid, event_number, dataset_identifier, temp_variable, time_variable, add_color=False, plot_title = "Device Removal Detection", method='Model Predictions', motion_variable=None, prediction_column = 'device_worn_model', event_timestamps = {}, include_temp_cutoff_line = True, df_version = 'SEARCH', subtitle_text = ''):
  if add_color:
    marker_colors = {
    'correct': ['darkblue', 'gray'],
    'incorrect': ['red', 'orange']
    }
  else:
    marker_colors = {
      'correct': ['black', 'black'],
      'incorrect': ['gray', 'gray']
    }

  fig, ax = plt.subplots(figsize=(16, 7))

  device_on_time, device_on_temp, device_off_time, device_off_temp = split_x_y_from_predictions(df, prediction_column, temp_variable, time_variable)

  ax.scatter(device_on_time, device_on_temp, marker='o', c=marker_colors['correct'][0])
  ax.scatter(device_off_time, device_off_temp, marker='x', c=marker_colors['incorrect'][0])
  ax.set_xlabel('Time', fontsize = 20)
  ax.set_ylabel('Temperature (C)', fontsize = 20)
  ax.set_title(plot_title, fontsize=24, fontweight="semibold", pad=25)
  ax.text(0.5, 1.025, subtitle_text, fontsize=12, style='italic',
    ha='center', va='center', transform=ax.transAxes)
  ax.legend(("Temp (Wear)", "Temp (Non-Wear)"), loc='upper left', fontsize=14)
  ax.tick_params(axis='x', labelsize = 16)
  ax.tick_params(axis='y', labelsize = 16)

  x_tick_interval = 2 if (len(df) / 60) > 12 else 1
  ax.xaxis.set_major_locator(mdates.HourLocator(interval=x_tick_interval))
  ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

  if df[temp_variable].min() > 15:
        ax.set_ylim(15, 40)
  if include_temp_cutoff_line:
    ax.hlines(y=28, xmin = df[time_variable].min(), xmax = df[time_variable].max(), color='black', linestyle='--')
  
  if event_timestamps and all(value is not None for value in event_timestamps.values()):
    plot_event_lines(df, ax, event_timestamps, time_variable, 'datetime', font_size=22)

  if motion_variable:
        ax2 = ax.twinx()
        device_on_time, device_on_motion, device_off_time, device_off_motion = split_x_y_from_predictions(df, prediction_column, motion_variable, time_variable)
        ax2.scatter(device_on_time, device_on_motion, marker='.', c=marker_colors['correct'][1])
        ax2.scatter(device_off_time, device_off_motion, marker='^', c=marker_colors['incorrect'][1])
        ax2.set_ylabel('Motion (G)', fontsize=20, rotation=-90, labelpad=25)
        ax2.legend(("Motion (Wear)", 'Motion (Non-Wear)'), loc='upper right', fontsize=14)
        ax2.tick_params(axis='y', labelsize=16)

  path=f'{plot_folder}{subid}_{dataset_identifier}_{event_number}_device_removal_{method}_{df_version}.png'

  plt.tight_layout()
  plt.savefig(path, bbox_inches='tight', dpi=150)
  plt.close('all')
  return path

def plot_device_removal_manuscript(
    df, plot_folder, subid, dataset_identifier, session_type,
    add_color=True, 
    method='Algorithm', 
    non_wear_labeling_column = 'device_worn_model', 
    event_timestamps = {}, 
  ):

  if add_color:
    marker_colors = {
    'correct': ['darkblue', 'gray'],
    'incorrect': ['red', 'orange']
    }
  else:
    marker_colors = {
      'correct': ['black', 'black'],
      'incorrect': ['gray', 'gray']
    }

  time_variable = 'datetime'
  temp_variable = 'Temperature_C'
  motion_variable = 'Motion'

  fig, ax = plt.subplots(figsize=(16, 7))

  device_on_time, device_on_temp, device_off_time, device_off_temp = split_x_y_from_predictions(df, non_wear_labeling_column, temp_variable, time_variable)

  ax.scatter(device_on_time, device_on_temp, marker='o', c=marker_colors['correct'][0])
  ax.scatter(device_off_time, device_off_temp, marker='x', c=marker_colors['incorrect'][0])
  ax.set_xlabel('Time (Hour:Minute)', fontsize = 24)
  ax.set_ylabel('Temperature (C)', fontsize = 24)
  
  plot_title = 'Algorithm Non-Wear Detection' if method == 'Algorithm' else 'Ground Truth Non-Wear'
  ax.set_title(plot_title, fontsize=28, fontweight="semibold", pad=25)
  subtitle_text = f'Subject ID: {subid} | Dataset ID: {dataset_identifier} | Session Type: {session_type}'
  ax.text(0.5, 1.02, subtitle_text, fontsize=12, style='italic',
    ha='center', va='center', transform=ax.transAxes)
  ax.legend(("Passed Temp", "Flagged Temp"), loc='upper left', fontsize=14)

  ax.tick_params(axis='x', labelsize = 16)
  ax.tick_params(axis='y', labelsize = 16)
  ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
  ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

  if df[temp_variable].min() > 15:
        ax.set_ylim(15, 40)

  if event_timestamps and all(value is not None for value in event_timestamps.values()):
    if len(event_timestamps.values()) == 5: 
      plot_event_lines_with_fixed_text_height(df, ax, event_timestamps, time_variable, 'datetime', font_size=24, y_starts = [0.9, 0.9, 0.86, 0.86, 0.8])
    else:
      plot_event_lines(df, ax, event_timestamps, time_variable, 'datetime', font_size=24, text_adjustment=0.05, y_start = 0.9)

  ax2 = ax.twinx()
  device_on_time, device_on_motion, device_off_time, device_off_motion = split_x_y_from_predictions(df, non_wear_labeling_column, motion_variable, time_variable)
  ax2.scatter(device_on_time, device_on_motion, marker='.', c=marker_colors['correct'][1])
  ax2.scatter(device_off_time, device_off_motion, marker='^', c=marker_colors['incorrect'][1])
  ax2.set_ylabel('Motion (G)', fontsize=20, rotation=-90, labelpad=25)
  ax2.legend(("Passed Motion", 'Flagged Motion'), loc='upper right', fontsize=14)
  ax2.tick_params(axis='y', labelsize=16)

  path=f'{plot_folder}{subid}_{dataset_identifier}_device_removal_{method}_{session_type}.png'

  plt.tight_layout()
  plt.savefig(path, bbox_inches='tight')
  plt.close('all')
  return path

def plot_temperature_motion(df, plot_folder, subid, event_number, dataset_identifier, temp_variable, time_variable, add_color=False, plot_title = "Temperature & Motion", motion_variable=None, event_timestamps = {}, subtitle_text = ''):
  if add_color:
    marker_colors = {
    'correct': ['darkblue', 'gray'],
    'incorrect': ['red', 'orange']
    }
  else:
    marker_colors = {
      'correct': ['black', 'black'],
      'incorrect': ['gray', 'gray']
    }

  fig, ax = plt.subplots(figsize=(16, 7))

  time = df[time_variable]
  temp = df[temp_variable]

  ax.scatter(time, temp, marker='o', c=marker_colors['correct'][0])
  ax.set_xlabel('Time', fontsize = 20)
  ax.set_ylabel('Temperature (C)', fontsize = 20)
  ax.set_title(plot_title, fontsize=24, fontweight="semibold", pad=25)
  ax.text(0.5, 1.02, subtitle_text, fontsize=12, style='italic',
    ha='center', va='center', transform=ax.transAxes)
  ax.legend(("Passed Temp", "Flagged Temp"), loc='upper left', fontsize=14)
  ax.tick_params(axis='x', labelsize = 16)
  ax.tick_params(axis='y', labelsize = 16)
  ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
  ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

  if df[temp_variable].min() > 15:
        ax.set_ylim(15, 40)

  if event_timestamps and all(value is not None for value in event_timestamps.values()):
    plot_event_lines(df, ax, event_timestamps, time_variable, 'datetime')

  if motion_variable:
    motion = df[motion_variable]
    ax2 = ax.twinx()
    ax2.scatter(time, motion, marker='.', c=marker_colors['correct'][1])
    ax2.set_ylabel('Motion (G)', fontsize=20, rotation=-90, labelpad=25)
    ax2.legend(("Passed Motion", 'Flagged Motion'), loc='upper right', fontsize=14)
    ax2.tick_params(axis='y', labelsize=16)

  path=f'{plot_folder}{subid}_{dataset_identifier}_{event_number}_TEMP_MOTION.png'

  plt.tight_layout()
  plt.savefig(path, bbox_inches='tight')
  plt.close('all')
  return path