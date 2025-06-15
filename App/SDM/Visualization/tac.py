from tokenize import group
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib
matplotlib.use("Agg")
import os
from App.SDM.Configuration.configuration import normalize_column
from App.SDM.Machine_Learning.get_feature_importances import get_feature_importances
from App.SDM.Visualization.plotting_utils import *
import numpy as np
from sklearn.tree import plot_tree

def plot_smoothed_curve(df, plot_path, subid, dataset_identifier, event_number, peak, curve_threshold, title = "TAC Curve", event_timestamps = {}, df_version = 'SEARCH', subtitle_text = '', tac_column = 'TAC'):
  peak_time = df.loc[df[tac_column]==peak, 'datetime']
  # graph_cutoff = curve_ends + ((len(df) - curve_ends)*0.25)
  # df = df.loc[:graph_cutoff]
  
  fig, ax = plt.subplots(figsize = (16, 7))
  ax.plot(df['datetime'], df[tac_column], c='black')

  #annotate with lines for curve threshold, peak, curve_begin, curve_end
  ax.vlines(peak_time, ymin=curve_threshold, ymax=peak, color='black', linestyle='--')
  ax.hlines(curve_threshold, xmin=df['datetime'].min(), xmax=df['datetime'].max(), colors='black', linestyle='--')
  # ax.vlines(
  #   [df.loc[curve_begins, 'datetime'], df.loc[curve_ends, 'datetime']], 
  #   ymin=0, ymax=df['TAC'].max(), color='red', linestyle='--'
  # )

  ax.set_xlabel('Time (hrs)', fontsize = 24)
  ax.set_ylabel('TAC' if 'TAC' in tac_column else 'TAC (Pre-Imputation)', fontsize = 24)
  ax.tick_params(axis='x', labelsize = 18)
  ax.tick_params(axis='y', labelsize = 20)

  ax.set_title(title, fontsize=32, fontweight="semibold", pad=25)
  ax.text(0.5, 1.025, subtitle_text, fontsize=12, style='italic',
    ha='center', va='center', transform=ax.transAxes)
  # if drink_total is not None:
  #   ax.text(0.5, 1.05, f"Drink Total: {drink_total}", fontsize=14, ha='center', va='top', transform=ax.transAxes)

  ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
  ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

  if ax.get_ylim()[1] < 10:
    ax.set_ylim(-10, 20)

  if event_timestamps and all(value is not None for value in event_timestamps.values()):
    plot_event_lines(df, ax, event_timestamps, 'datetime', 'datetime')
  df_version = df_version if tac_column == 'TAC' else f'{df_version}_raw'
  path = f'{plot_path}{subid}_{dataset_identifier}_{event_number}_TAC_curve_{df_version}.png'
  plt.tight_layout()
  plt.savefig(path, bbox_inches='tight')
  plt.close('all')
  return path

def plot_signal_processing(df, plot_path, subid, event_number, dataset_identifier, df_version, 
                           curve_threshold, time_variable='datetime', title='Signal Processing', 
                           event_timestamps={}, subtitle_text='', show_imputations = True):
  passed = df.loc[
    (df['device_worn_model'] == 1) & 
    (df['gap_buffered']==0) & 
    (df['non_wear_buffered']==0) & 
    (df['extreme_negative']==0) &
    (df['jump']==0) & 
    (df['plummet']==0) &
    (df['imputed']==0) &
    (df['between_low_quality']==0)
  ]

  # Non-imputed data
  gap = df.loc[df['gap_buffered'] == 1]
  non_wear = df.loc[(df['non_wear_buffered'] == 1)]
  extreme_negative = df.loc[(df['extreme_negative'] == 1)]
  jumps = df.loc[(df['jump'] == 1) & (df['non_wear_buffered'] == 0)]
  plummet = df.loc[(df['plummet'] == 1) & (df['jump'] == 0) & (df['non_wear_buffered'] == 0)]
  between_low_quality = df.loc[df['between_low_quality'] == 1]

  # Create a figure and axis
  fig, ax = plt.subplots(figsize=(16, 7))
  
  #Smoothed Final TAC
  ax.plot(df[time_variable], df['TAC' if not show_imputations else 'TAC_pre_imputation'], label="TAC (Processed)", alpha=0.5, color="black", linewidth = 2)
  
  #Passed (high quality values)
  ax.scatter(passed[time_variable], passed['TAC_pre_imputation'], label='Passed', 
             color='darkblue', marker='.', alpha=1.0)
  #Non Wear
  if not non_wear.empty:
    ax.scatter(non_wear[time_variable], non_wear['TAC_pre_imputation'], label='Non-Wear', 
             color='lightpink', marker='x', alpha=0.7, s=20)
  #Extreme Negative
  if not extreme_negative.empty:
    ax.scatter(extreme_negative[time_variable], extreme_negative['TAC_pre_imputation'], label='Extreme Negative', 
             color='lightsteelblue', marker='*', alpha=0.7, s=20)
  #Jumps
  if not jumps.empty:
    ax.scatter(jumps[time_variable], jumps['TAC_pre_imputation'], label='Jump', 
              color='lightblue', marker='^', alpha=0.7, s=20)
  #Plummet
  if not plummet.empty:
    ax.scatter(plummet[time_variable], plummet['TAC_pre_imputation'], label='Plummet', 
              color='thistle', marker='v', alpha=0.7, s=20)
  # Between low quality
  if not between_low_quality.empty:
    ax.scatter(between_low_quality[time_variable], between_low_quality['TAC_pre_imputation'],
               label='Between Low Quality', color='gray', marker='s', alpha=0.7, s=20)
    
  # Imputed data
  if show_imputations:
    gap_imputed = df.loc[df['gap_imputed'] == 1]
    non_wear_imputed = df.loc[(df['non_wear_imputed'] == 1)]
    extreme_negative_imputed = df.loc[(df['extreme_negative_imputed'] == 1)]
    jump_imputed = df.loc[df['jump_imputed'] == 1]
    plummet_imputed = df.loc[df['plummet_imputed'] == 1]
    between_low_quality_imputed = df.loc[df['between_low_quality_imputed'] == 1]
    if not gap_imputed.empty:
      ax.scatter(gap_imputed[time_variable], gap_imputed['TAC_pre_savgol'], label='Imputed Gap', 
                marker='o', alpha=1.0, facecolor='gray', edgecolors="black")
    if not non_wear_imputed.empty:
      ax.scatter(non_wear_imputed[time_variable], non_wear_imputed['TAC_pre_savgol'], 
                label='Imputed Non-Wear', facecolor='lightpink', edgecolors= "darkred", marker='o', alpha=1.0)
    if not extreme_negative_imputed.empty:
      ax.scatter(extreme_negative_imputed[time_variable], extreme_negative_imputed['TAC_pre_savgol'], 
                label='Imputed Extreme Negative', facecolor='lightsteelblue', edgecolors= "purple", marker='o', alpha=1.0)
    if not jump_imputed.empty:
      ax.scatter(jump_imputed[time_variable], jump_imputed['TAC_pre_savgol'], 
                label='Imputed Jump', facecolor='lightblue', edgecolors= "darkblue", marker='o', alpha=1.0)
    if not plummet_imputed.empty:
      ax.scatter(plummet_imputed[time_variable], plummet_imputed['TAC_pre_savgol'], 
                label='Imputed Plummet', facecolor='thistle', edgecolors= "purple", marker='o', alpha=1.0)
    if not between_low_quality_imputed.empty:
      ax.scatter(between_low_quality_imputed[time_variable], between_low_quality_imputed['TAC_pre_savgol'],
                label='Imputed Between Low Quality', facecolor='gray', edgecolors="darkgreen", marker='o', alpha=1.0)
  
  # Plot threshold line
  ax.hlines(curve_threshold, xmin=df['datetime'].min(), xmax=df['datetime'].max(), 
            colors='black', linestyle='--', label="Curve Threshold")

  # Plot event timestamps if available
  if event_timestamps and all(value is not None for value in event_timestamps.values()):
    plot_event_lines(df, ax, event_timestamps, 'datetime', 'datetime', font_size=10)

  # Format the x-axis for time
  ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
  ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

  # Add labels, title, and legend
  ax.set_xlabel('Time')
  ax.set_ylabel('TAC')
  ax.set_title(title, fontsize=18, fontweight="semibold", pad=25)
  plt.xticks(rotation=45)
  ax.legend(loc='upper right', bbox_to_anchor=(1.1, 1.1), ncol=2, 
           frameon=True, framealpha=1, edgecolor='black', facecolor='white')

  # Add subtitle
  ax.text(0.5, 1.025, subtitle_text, fontsize=10, style='italic',
          ha='center', va='center', transform=ax.transAxes)
  
  # Save the figure
  df_version = df_version if show_imputations else f'{df_version}_raw'
  path = f'{plot_path}{subid}_{dataset_identifier}_{event_number}_TAC_processing_{df_version}.png'
  plt.tight_layout()
  plt.savefig(path, bbox_inches='tight')
  plt.close('all')
  
  return path

def plot_tac_and_temp(df, plot_folder, subid, dataset_identifier, event_number, tac_variable, temp_variable, time_variable, plot_title = "TAC and Temperature", event_timestamps = {}, df_version = 'SEARCH', drink_total = None):
  fig, ax1 = plt.subplots(figsize=(16, 7))
  ax1.plot(df[time_variable], df[tac_variable], color="darkblue", label=tac_variable)
  ax2 = ax1.twinx()
  ax2.plot(df[time_variable], df[temp_variable], color="maroon", label=temp_variable)
  
  ax1.set_title(plot_title, fontsize=26, fontweight="semibold", pad=25 if drink_total is not None else 15)
  if drink_total is not None:
    ax1.text(0.5, 1.05, f"Drink Total: {drink_total}", fontsize=14, ha='center', va='top', transform=ax1.transAxes)
  
  ax1.set_ylabel(tac_variable, color='darkblue')
  ax2.set_ylabel(temp_variable, color='maroon')
  
  ax1.legend(loc='upper left')
  ax2.legend(loc='upper right')
  
  if df[tac_variable].max() < 10:
    ax1.set_ylim(0, 10)
  if df[temp_variable].min() > 15:
    ax2.set_ylim(15, 40) 
    
  if event_timestamps and all(value is not None for value in event_timestamps.values()):
    plot_event_lines(df, ax1, event_timestamps, time_variable, 'datetime')
  
  ax1.xaxis.set_major_locator(mdates.HourLocator(interval=2))
  ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

  path = f'{plot_folder}tac_and_temp_plot_{subid}_{dataset_identifier}_{event_number}_{df_version}.png'
  fig.savefig(path)
  plt.close('all')

  return path

def plot_column(df, plot_folder, subid, condition, dataset_identifier, y_variable, time_variable, xlabel="Time (hours)", event_timestamps = {}):
      ylabel = y_variable    
      title = f'{y_variable} {subid} {condition}'
      fig, ax = plt.subplots(figsize=(16, 7)) 
      ax.scatter(y=df[y_variable], x=df[time_variable])
      ax.set_title(title, fontsize=26, fontweight="semibold", pad=15)
      ax.set_ylabel(ylabel)
      ax.set_xlabel(xlabel)
      plot_event_lines(df, ax, event_timestamps, time_variable, 'datetime')
      full_path = f'{plot_folder}/{y_variable} - {subid} - {condition}{dataset_identifier}.png'
      fig.savefig(full_path)
      plt.close('all')
      return full_path

def plot_TAC_curve(df, plot_folder, subid, condition, dataset_identifier, tac_variable, time_variable, ylabel="TAC ug/L", xlabel="Time (hours)", event_timestamps = {}):
  title = f'TAC Curve - {tac_variable}'
  fig, ax = plt.subplots(figsize=(16, 7)) 
  ax.scatter(df[time_variable], df[tac_variable])
  ax.set_title(title, fontsize=26, fontweight="semibold", pad=15)
  ax.set_ylabel(ylabel)
  ax.set_xlabel(xlabel)
  if df[tac_variable].max() < 15:
        ax.set_ylim(df[tac_variable].min() - 1, 15)
  plot_event_lines(df, ax, event_timestamps, time_variable, 'datetime')

  full_path = f'{plot_folder}/{tac_variable} - {subid} - {condition}{dataset_identifier}.png'
  fig.savefig(full_path)
  plt.close('all')
  return full_path

def plot_overlaid_TAC_curves(df, plot_folder, subid, condition, dataset_identifier, tac_variables, time_variable, plot_name, ylabel="TAC ug/L", xlabel="Time (hours)", event_timestamps = {}):
  title = f'TAC Curve - {plot_name}'
  fig, ax = plt.subplots(figsize=(16, 7))
  for variable in tac_variables:
    ax.plot(df[time_variable], df[variable])
  ax.set_title(title, fontsize=26, fontweight="semibold", pad=15)
  ax.set_ylabel(ylabel)
  ax.set_xlabel(xlabel)
  plot_event_lines(df, ax, event_timestamps, time_variable, 'datetime')
  if ax.get_ylim()[1] < 10:
    ax.set_ylim(0, 10)

  full_path = f'{plot_folder}/{plot_name} - {subid} - {condition}{dataset_identifier}.png'
  fig.savefig(full_path)
  plt.close('all')
  return full_path

def plot_cropping(data, beginning_timestamp, end_timestamp, self, add_color = False, title="Raw Data Cropping"):
      if add_color:
            marker_colors = ['red', 'black']
      else:
            marker_colors = ['lightgray', 'black']

      hours = (data['datetime'] - beginning_timestamp) / np.timedelta64(1, 'h')
      cropped = data.loc[(data['datetime'] < beginning_timestamp) | (data['datetime'] > end_timestamp), 'TAC']
      cropped_time = hours.loc[(data['datetime'] < beginning_timestamp) | (data['datetime'] > end_timestamp)]

      kept = data.loc[(data['datetime'] > beginning_timestamp) & (data['datetime'] < end_timestamp), 'TAC']
      kept_time = hours.loc[(data['datetime'] > beginning_timestamp) & (data['datetime'] < end_timestamp)]
      
      try:
            cropped_at_max_duration = round(kept_time.max()) == round(self.max_duration)
            timestamps_valid = True
      except:
            timestamps_valid = False
            title = "Invalid Timestamps - Cropping Failed"

      fig, ax = plt.subplots(figsize=(16, 7))
      ax.scatter(kept_time, kept, marker='.', c = marker_colors[1], s=12)      
      ax.scatter(cropped_time, cropped, marker='x', c = marker_colors[0], s=14)
      #ax.legend(("Kept", "Cropped"), loc='upper right', fontsize=16)
      ax.set_xlabel('Time (hrs)', fontsize = 24)
      ax.set_ylabel('TAC', fontsize = 24, labelpad=3)
      ax.set_title(title, fontsize = 36, fontweight="semibold", pad=15)
      if ax.get_ylim()[1] < 10:
            ax.set_ylim(0, 10)
      ax.tick_params(axis = 'x', labelsize = 22)
      ax.tick_params(axis = 'y', labelsize = 22)
      if timestamps_valid:
            if beginning_timestamp > data['datetime'].min():
                  ax.vlines(x = 0, ymin = -8, ymax = data['TAC'].max(), color = 'black', linestyle = '--')
                  plt.text(0.2, data['TAC'].max() * 0.9, "Episode", fontsize = 28, fontstyle = "italic")
                  plt.text(0.2, data['TAC'].max() * 0.8, "Beginning", fontsize = 28, fontstyle = "italic")
            if end_timestamp < data['datetime'].max():
                  ax.vlines(x = kept_time.max(), ymin = -8, ymax = data['TAC'].max(), color = 'black', linestyle = '--')
                  cutoff_label = f'{round(self.max_duration)}-Hr' if cropped_at_max_duration else 'Episode End'
                  plt.text(kept_time.max()*0.85, data['TAC'].max() * 0.9, cutoff_label, fontsize = 28, fontstyle = "italic")
                  if cropped_at_max_duration:
                        plt.text(kept_time.max()*0.85, data['TAC'].max() * 0.8, "Cutoff", fontsize = 28, fontstyle = "italic")
      path = f'{self.plot_folder}/{self.subid}_{self.condition}{self.dataset_identifier}_cropping.png'
      plt.tight_layout()
      plt.savefig(path, bbox_inches='tight')
      plt.close('all')
      return path

def plot_cleaning_comparison(occasion, df, time_variable, add_color = False, title = "TAC Signal Cleaning", size = (16, 7), legend = True, snip = None, event_timestamps = {}):

      if snip:
            df = df.iloc[snip[0]:snip[1]]

      tac_columns = ['TAC_Raw', 'TAC_sloped_start_reassigned', 'TAC_negative_reassigned', 'TAC_gaps_filled', 'TAC_extreme_values_imputed', 'TAC_device_off', 'TAC_processed']
      markers = [',', 'o', 'd', 'H', 'v', 's', 'p']
      names = ['Raw (passed)', 'Sloped Beginning Reassigned', 'Subzero Value Reassigned', 'Imputed (Missing Value)', 'Imputed (Extreme Outlier)', 'Imputed (Device Off)', 'Imputed (Artifact)']

      marker_colors = ['dimgray', 'yellow', 'steelblue', 'peru', 'firebrick', 'mediumvioletred', 'maroon'] if add_color else ['black', 'dimgray', 'dimgray', 'dimgray', 'dimgray', 'dimgray', 'dimgray']

      all_imputed_idx = []
      
      tac_plot_specs = {}
      for i, col in enumerate(tac_columns):
            if col in df.columns.tolist():
                  if i > 0 and (i < len(tac_columns) - 1):
                        df_current_col = df[col]
                        df_prior_cols = df[[col for col in tac_columns[:i] if col in df.columns]]
                        df_post_cols = df[[col for col in tac_columns[i+1:] if col in df.columns]]
                        
                        mask_different = df_prior_cols.ne(df_current_col, axis='index').all(axis=1)
                        mask_equal = df_post_cols.eq(df_current_col, axis='index').all(axis=1)

                        combined_mask = mask_different & mask_equal
                        imputed_idx = combined_mask[combined_mask].index
                        all_imputed_idx.extend(imputed_idx)

                  elif i == len(tac_columns) -1:
                        df_current_col = df[col]
                        df_prior_cols = df[[col for col in tac_columns[:i] if col in df.columns]]

                        mask_different = df_prior_cols.ne(df_current_col, axis='index').all(axis=1)
                        imputed_idx = mask_different[mask_different].index
                        all_imputed_idx.extend(imputed_idx)

                  else:
                        imputed_idx = []

                  if len(imputed_idx) > 0:
                        tac_plot_specs[names[i]] = {
                              'x': df.loc[imputed_idx, time_variable].tolist(),
                              'y': df.loc[imputed_idx, col].tolist(),
                              'color': marker_colors[i],
                              'marker': markers[i],
                        }
            
      tac_plot_specs['Raw (passed)'] = {
            'x': df.loc[[i for i in df.index.tolist() if i not in all_imputed_idx], time_variable].tolist(),
            'y': df.loc[[i for i in df.index.tolist() if i not in all_imputed_idx], 'TAC_Raw'].tolist(),
            'color': marker_colors[0],
            'marker': markers[0]
      }

      tac_plot_specs['Raw (removed)'] = {
            'x': df.loc[all_imputed_idx, time_variable].tolist(),
            'y': df.loc[all_imputed_idx, 'TAC_Raw'].tolist(),
            'color': 'crimson' if add_color else 'darkgrey',
            'marker': 'x'
      }

      smoothed_tac = df.loc[:, f'TAC_processed_smooth_{occasion.smoothing_window}'].tolist()
      smoothed_tac_x = df.loc[:, time_variable].tolist()
      fig, ax = plt.subplots(figsize=size)
      ax.plot(smoothed_tac_x, smoothed_tac, linestyle = 'solid', color = 'midnightblue' if add_color else 'dimgray', linewidth = 2)
      for name, specs in tac_plot_specs.items():
            ax.scatter(specs['x'], specs['y'], c = specs['color'], marker = specs['marker'], s = 20)
            if add_color and len(specs['x']) and name not in ['Raw (passed)', 'Raw (removed)']:
                  ranges = find_ranges(specs['x'], threshold=0.05)
                  for start, end in ranges:
                        ax.axvspan(start, end, color=specs['color'], alpha=0.2, label='_nolegend_')

      ax.set_xlabel('Time (hrs)', fontsize = 22)
      ax.set_ylabel('TAC', fontsize = 22)
      if ax.get_ylim()[1] < 10:
            ax.set_ylim(0, 10)
      ax.set_title(title, fontsize=28, fontweight="semibold", pad=15)
      if not occasion.valid_occasion:
            split_text_index = int(round(len(occasion.invalid_reason)/2))
            split_character_is_space = occasion.invalid_reason[split_text_index] == ' '
            while not split_character_is_space:
                  split_text_index += 1
                  split_character_is_space = occasion.invalid_reason[split_text_index] == ' '
                  if split_character_is_space or split_text_index == len(occasion.invalid_reason) - 1:
                        break
            invalid_reason_part_1 = occasion.invalid_reason[:split_text_index]
            invalid_reason_part_2 = occasion.invalid_reason[split_text_index:]
            plt.text(0.03, 0.95, f'Invalid: {invalid_reason_part_1}', ha='left', va='center', transform=plt.gca().transAxes, fontdict={'size':  9})
            plt.text(0.03, 0.92, f'{invalid_reason_part_2}', ha='left', va='center', transform=plt.gca().transAxes, fontdict={'size':  9})
      if legend:
            ax.legend(["Smooth (Final)"] + list(tac_plot_specs.keys()), loc='upper right', fontsize=16)
      ax.tick_params(axis='x', labelsize = 18)
      ax.tick_params(axis='y', labelsize = 18)

      plot_event_lines(df, ax, event_timestamps, time_variable, 'datetime')
      
      filename = f'{occasion.plot_folder}cleaning - {occasion.subid} - {occasion.condition}{occasion.dataset_identifier}'
      if snip:
            filename = filename + f' - snip{snip[0]}_{snip[1]}'
      filename = filename + '.png'
      plt.tight_layout()
      plt.savefig(filename, bbox_inches='tight')
      plt.close('all')
      return filename

def create_temp_histogram(self):
  temperatures = []
  for occasion in self.occasions:
    data = occasion.dataset['Temperature_C'].tolist()
    temperatures.extend(data)
  temperatures_below_threshold = [temp for temp in temperatures if temp < 27]

  plt.hist(temperatures, bins = [20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40])
  plt.ylabel("Counts (1000's)")
  plt.xlabel('Temperature (Celsius)')
  plt.title('Temperature Distribution')
  plt.xticks([20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40])
  plt.yticks(ticks = [2000, 4000, 6000, 8000, 10000, 12000, 14000, 16000, 18000], labels=[2, 4, 6, 8, 10, 12, 14, 16, 18])
  plt.savefig(f'{self.analyses_out_folder}/temperature_histogram.png')
  plt.close('all')


def create_simple_histogram_of_feature(feature, save_folder, feature_name):
  # feature_names = [
  #         'ending_non_wear_perc_CURVE', 'flatline_max_SEARCH', 'flatline_max_CURVE',
  #         'device_turned_on_percent_CURVE', 'device_turned_on_duration_CURVE', 'device_turned_on_percent_CURVE', 
  #         'device_worn_duration_CURVE', 'device_worn_percent_CURVE', 'device_worn_percent_of_device_on_CURVE',
  #         'negative_duration_CURVE', 'sub_negative_10_duration_CURVE', 'duration_CURVE', 'first_tac_CURVE', 'last_tac_CURVE',
  #         'mean_tac_CURVE', 'peak_CURVE', 'auc_total_CURVE', 'rise_duration_CURVE', 'fall_duration_CURVE', 'rise_rate_CURVE', 
  #         'fall_rate_CURVE', 'fall_complete_perc_CURVE', ''
  #       ]
  #       for feature in feature_names:
  #         save_feature
  #         if not os.path.exists(processed_data_out):
  #         create_simple_histogram_of_feature(self.event_level_data[feature], f'{self.data_out_folder}/)

  plt.hist(feature, bins = [20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40])
  plt.xlabel(feature_name)
  plt.title(f'{feature_name} Distribution')
  plt.savefig(f'{save_folder}/{feature_name}_histogram.png')
  plt.close('all')

def plot_box_whisker(features, variables, ground_truth_variable, plot_folder, cohort_name, filter = {}):
      features = features[features['valid_occasion']==1].reset_index(drop=True)
      for variable_name, exclude_values in filter.items():
            features = features[~features[variable_name].isin(exclude_values)]
      data = {}
      for variable in variables:
            data[variable] = [[] for i in range(0, len(features[ground_truth_variable].unique()))]
            for i, truth in enumerate(features[ground_truth_variable].unique()):
                  data[variable][i] = features[features[ground_truth_variable]==truth][variable].tolist()
      
      figure, axis = plt.subplots(1, len(variables))
      figure.set_figheight(12)
      figure.set_figwidth(10 * len(variables))
      colors = ['firebrick', 'silver', 'darkblue']
      ticker = 0
      positions = [i+1 for i in range(0, len(features[ground_truth_variable].unique()))]
      for variable in variables:
            bp = axis[0 + ticker].boxplot(data[variable], positions = positions, widths = 0.5, patch_artist = True)
            axis[0 + ticker].set_title(variable)
            axis[0 + ticker].set_xticks([(i+1) for i in range(0, len(features[ground_truth_variable].unique()))])
            axis[0 + ticker].set_xticklabels(features[ground_truth_variable].unique().tolist())
            axis[0 + ticker].grid(color = 'lightgray', linestyle = '--', linewidth = 0.75, axis='y')
            ticker += 1
            for patch, color in zip(bp['boxes'], colors):
                  patch.set_facecolor(color)
            for median in bp['medians']:
                  median.set(color ='black', linewidth = 2)

            
      full_path = f'{plot_folder}/features_{cohort_name}_{ground_truth_variable}_box_whisker.png'
      figure.savefig(full_path, bbox_inches='tight')
      plt.close('all')


def plot_rf_feature_importances(model, model_name, model_figures_folder):
  forest_importance = get_feature_importances(model.best, model.predictors)
  fig, ax = plt.subplots()
  ax.grid(True, axis = 'x')
  forest_importance.plot.barh(ax=ax, color='dimgray')
  ax.set_title(f'Feature Importance - Random Forest', fontdict={'weight': 'bold', 'size': 15})
  ax.set_xlabel("Mean Decrease in Impurity", fontdict={'size': 13})
  ax.get_legend().remove()
  fig.tight_layout()

  plt.savefig(f'{model_figures_folder}/{model_name} - Feature Importances.png', dpi=55)
  plt.close('all')
  return forest_importance

def plot_rf_tree(rf, feature_names, cohort_name, model_figures_folder):
  fig = plt.figure(figsize=(15, 10))
  plot_tree(rf.best.estimators_[0], 
    feature_names=feature_names, class_names=['Alc', 'Non'], 
    filled=True, impurity=True, rounded=True)
  fig.savefig(f'{model_figures_folder}/Random Forest - {cohort_name} - Decision Tree.png')
  plt.close('all')

