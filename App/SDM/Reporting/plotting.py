from tokenize import group
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")
import os
from SDM.Configuration.configuration import normalize_column
from SDM.Stats.get_feature_importances import get_feature_importances
import numpy as np
from sklearn.tree import plot_tree


def plot_column(df, plot_folder, subid, condition, dataset_identifier, y_variable, time_variable, xlabel="Time (hours)"):
      ylabel = y_variable    
      title = f'{y_variable} {subid} {condition}'
      plot = df.plot.scatter(y=y_variable, x=time_variable, title=title, ylabel=ylabel, xlabel=xlabel)
      fig = plot.get_figure()
      
      folder = f'{plot_folder}/{subid}/{condition}/{y_variable}'
      if not os.path.exists(folder):
            os.mkdir(folder)
      full_path = f'{folder}/{y_variable} - {subid} - {condition}{dataset_identifier}.png'
      fig.savefig(full_path)
      plt.close('all')
      return full_path

def plot_TAC_curve(df, plot_folder, subid, condition, dataset_identifier, tac_variable, time_variable, ylabel="TAC ug/L", xlabel="Time (hours)"):
      title = f'TAC Curve - {tac_variable}'
       
      plot = df.plot.scatter(y=tac_variable, x=time_variable, title=title, ylabel=ylabel, xlabel=xlabel)
      fig = plot.get_figure()
      if condition == 'Non':
            if df[tac_variable].max() > 15:
                  pass
            else:
                  plt.ylim(df[tac_variable].min() - 1, 15)

      folder = f'{plot_folder}/{subid}/{condition}/'
      if not os.path.exists(folder):
            os.mkdir(folder)

      full_path = f'{folder}/{tac_variable} - {subid} - {condition}{dataset_identifier}.png'
      fig.savefig(full_path)
      plt.close('all')
      return full_path

def plot_overlaid_TAC_curves(df, plot_folder, subid, condition, dataset_identifier, tac_variables, time_variable, plot_name, ylabel="TAC ug/L", xlabel="Time (hours)"):
      title = f'TAC Curve - {plot_name}'
      plot = df.plot(y=tac_variables, x=time_variable, title=title, ylabel=ylabel, xlabel=xlabel)
      fig = plot.get_figure()
      
      folder = f'{plot_folder}/{subid}/{condition}'
      if not os.path.exists(folder):
            os.mkdir(folder)

      full_path = f'{folder}/{plot_name} - {subid} - {condition}{dataset_identifier}.png'
      fig.savefig(full_path)
      plt.close('all')
      return full_path

def plot_overlaid_with_normalization(df_prior, plot_folder, subid, condition, dataset_identifier, variables, time_variable, plot_name):
      df = df_prior.copy()
      title = f'{" ".join(variables)} - {subid} - {condition}'
      fig = plt.figure()
      ax1 = fig.add_subplot(111)
      colors = ['b', 'c', 'g', 'r', 'y']
      markers = ['o', 's', 'v', 'x', '.']
      for i, variable in enumerate(variables):
            df[variable] = normalize_column(df[variable])
            ax1.scatter(y=df[variable], x=df[time_variable], s=10, c=colors[i], marker=markers[i], label=variable)

      # plot = df.plot(y=variables, x=time_variable, title=title, ylabel='Norm Variables', xlabel='Time (hrs)')
      fig.legend(loc='upper right')

      folder = f'{plot_folder}/{subid}/{condition}/overlaid/'
      if not os.path.exists(folder):
            os.mkdir(folder)
            
      full_path = f'{folder}/{plot_name} - {subid} - {condition}{dataset_identifier}.png'
      fig.savefig(full_path, bbox_inches='tight')
      plt.close('all')
      return full_path

def plot_tac_and_temp(df, plot_folder, subid, condition, dataset_identifier, tac_variable, temp_variable, time_variable, plot_title = "TAC and Temperature"):
      fig, ax = plt.subplots(figsize=(16, 7))
      df.plot(x = time_variable, y = tac_variable, ax = ax)
      df.plot(x = time_variable, y = temp_variable, ax = ax, secondary_y = True)
      fig.suptitle(plot_title, fontsize=14)
      path = f'{plot_folder}/{subid}/{condition}/tac_and_temp_plot_{subid}_{condition}{dataset_identifier}.png'
      fig.savefig(path)
      plt.close('all')

      return path

def plot_temp_cleaning(df, plot_folder, subid, condition, dataset_identifier, temp_variable, time_variable, add_color=False, plot_title = "Temperature Assessment"):
      if add_color:
            marker_colors = ['red', 'dimgray']
      else:
            marker_colors = ['gray', 'black']

      fig, ax = plt.subplots(figsize=(16, 7))
      invalid_temp = df.loc[df[temp_variable]<28, temp_variable].tolist()
      invalid_time = df[df[temp_variable]<28][time_variable]
      valid_temp = df.loc[df[temp_variable]>=28, temp_variable].tolist()
      valid_time = df[df[temp_variable]>=28][time_variable]
      ax.scatter(valid_time, valid_temp, marker='o', c=marker_colors[1])
      ax.scatter(invalid_time, invalid_temp, marker='x', c=marker_colors[0])
      ax.set_xlabel('Time (hrs)', fontsize = 24)
      ax.set_ylabel('Temperature (C)', fontsize = 24)
      ax.set_title(plot_title, fontsize=32, fontweight="semibold", pad=15)
      ax.legend(("Passed", "Flagged"), loc='upper right', fontsize=26)
      if len(invalid_temp) > 0:
            ax.hlines(y=28, xmin = 0, xmax = df[time_variable].max(), color='black', linestyle='--')
            plt.text(df[time_variable].max() * 0.45, 27.0, "Device Not Worn", fontsize = 28, fontstyle = 'italic')
      ax.tick_params(axis='x', labelsize = 22)
      ax.tick_params(axis='y', labelsize = 22)

      path=f'{plot_folder}/{subid}/{condition}/{subid}_{condition}{dataset_identifier}_temp_cleaning.png'
      plt.tight_layout()
      plt.savefig(path, bbox_inches='tight')
      plt.close('all')
      return path

def plot_cropping(data, beginning_timestamp, end_timestamp, subid, condition, dataset_identifier, directory, cutoff, add_color = False, title="Raw Data Cropping"):
      if add_color:
            marker_colors = ['red', 'black']
      else:
            marker_colors = ['lightgray', 'black']

      hours = (data['Time_Adjusted'] - beginning_timestamp) / np.timedelta64(1, 'h')
      cropped = data.loc[(data['Time_Adjusted'] < beginning_timestamp) | (data['Time_Adjusted'] > end_timestamp), 'TAC']
      cropped_time = hours.loc[(data['Time_Adjusted'] < beginning_timestamp) | (data['Time_Adjusted'] > end_timestamp)]

      kept = data.loc[(data['Time_Adjusted'] > beginning_timestamp) & (data['Time_Adjusted'] < end_timestamp), 'TAC']
      kept_time = hours.loc[(data['Time_Adjusted'] > beginning_timestamp) & (data['Time_Adjusted'] < end_timestamp)]

      fig, ax = plt.subplots(figsize=(16, 7))
      ax.scatter(kept_time, kept, marker='.', c = marker_colors[1], s=12)      
      ax.scatter(cropped_time, cropped, marker='x', c = marker_colors[0], s=14)
      #ax.legend(("Kept", "Cropped"), loc='upper right', fontsize=16)
      ax.set_xlabel('Time (hrs)', fontsize = 24)
      ax.set_ylabel('TAC', fontsize = 24, labelpad=3)
      ax.set_title(title, fontsize = 36, fontweight="semibold", pad=15)

      ax.tick_params(axis = 'x', labelsize = 22)
      ax.tick_params(axis = 'y', labelsize = 22)

      if beginning_timestamp > data['Time_Adjusted'].min():
            ax.vlines(x = 0, ymin = -8, ymax = data['TAC'].max(), color = 'black', linestyle = '--')
            plt.text(0.2, data['TAC'].max() * 0.9, "Episode", fontsize = 28, fontstyle = "italic")
            plt.text(0.2, data['TAC'].max() * 0.8, "Beginning", fontsize = 28, fontstyle = "italic")
      if end_timestamp < data['Time_Adjusted'].max():
            ax.vlines(x = 18, ymin = -8, ymax = data['TAC'].max(), color = 'black', linestyle = '--')
            plt.text(15.2, data['TAC'].max() * 0.9, f'{cutoff}-Hour', fontsize = 28, fontstyle = "italic")
            plt.text(15.2, data['TAC'].max() * 0.8, "Cutoff", fontsize = 28, fontstyle = "italic")
      path = f'{directory}/{subid}_{condition}{dataset_identifier}_cropping.png'
      plt.tight_layout()
      plt.savefig(path, bbox_inches='tight')
      plt.close('all')
      return path

def plot_cleaning_comparison(occasion, df, df_raw, time_variable, add_color = False, title = "TAC Signal Cleaning", size = (16, 7), legend = True, snip = None):
      
      if snip:
            df = df.iloc[snip[0]:snip[1]]
            df_raw = df_raw.iloc[snip[0]:snip[1]]

      if add_color:
            marker_colors = ['dimgray', 'b', 'r', 'g']
      else:
            marker_colors = ['dimgray', 'black', 'gray', 'black']

      smoothed_tac = df.loc[:, 'TAC_imputed_smooth_101'].tolist()
      smoothed_tac_x = df.loc[:, time_variable].tolist()
      imputed_tac = df.loc[df['TAC'] != df['TAC_imputed']]['TAC_imputed'].tolist()
      imputed_x = df[df['TAC'] != df['TAC_imputed']][time_variable].tolist()
      cleaned_tac = df.loc[pd.isna(df['TAC_cleaned']), 'TAC'].tolist()
      cleaned_x = df.loc[pd.isna(df['TAC_cleaned']), time_variable].tolist()
      raw_tac = df_raw.loc[df['TAC'].eq(df['TAC_imputed']), 'TAC'].tolist()
      raw_x = df_raw.loc[df['TAC'].eq(df['TAC_imputed']), time_variable].tolist()

      fig, ax = plt.subplots(figsize=size)
      ax.plot(smoothed_tac_x, smoothed_tac, linestyle = 'solid', color = marker_colors[0], linewidth = 4)
      ax.scatter(raw_x, raw_tac, c = marker_colors[1], marker = ',', s = 2)
      ax.scatter(cleaned_x, cleaned_tac, c = marker_colors[2], marker = 'x', s = 40)
      ax.scatter(imputed_x, imputed_tac, c = marker_colors[3], marker = 10, s = 40)
      ax.set_xlabel('Time (hrs)', fontsize = 24)
      ax.set_ylabel('TAC', fontsize = 24)
      ax.set_title(title, fontsize=36, fontweight="semibold", pad=15)
      if legend:
            ax.legend(("Smoothed", "Raw", "Removed", "Imputed"), loc='upper right', fontsize=26)
      ax.tick_params(axis='x', labelsize = 22)
      ax.tick_params(axis='y', labelsize = 22)

      folder = f'{occasion.plot_folder}/{occasion.subid}/{occasion.condition}/cleaning/'
      if not os.path.exists(folder):
            os.mkdir(folder)
      
      filename = f'cleaning - {occasion.subid} - {occasion.condition}{occasion.dataset_identifier}'
      if snip:
            filename = filename + f' - snip{snip[0]}_{snip[1]}'
      full_path = f'{folder}/{filename}.png'
      plt.tight_layout()
      plt.savefig(full_path, bbox_inches='tight')
      plt.close('all')
      return full_path

def plot_smoothed_curve(df, plot_folder, subid, condition, dataset_identifier, time_variable, peak, baseline_cutoff, curve_begins, curve_ends, title = "TAC Curve"):
      peak_time = df.loc[df['TAC_imputed_smooth_101']==peak, time_variable]
      # graph_cutoff = curve_ends + ((len(df) - curve_ends)*0.25)
      # df = df.loc[:graph_cutoff]
         
      fig, ax = plt.subplots(figsize = (16, 7))
      ax.plot(df[time_variable].tolist(), df['TAC_imputed_smooth_101'].tolist(), c='black')
      ax.vlines(peak_time, ymin=baseline_cutoff, ymax=peak, color='black', linestyle='--')
      ax.hlines(baseline_cutoff, xmin=0, xmax=df[time_variable].max(), colors='black', linestyle='--')
      ax.set_xlabel('Time (hrs)', fontsize = 24)
      ax.set_ylabel('TAC', fontsize = 24)
      ax.tick_params(axis='x', labelsize = 22)
      ax.tick_params(axis='y', labelsize = 22)
      ax.set_title(title, fontsize=36, fontweight="semibold", pad=15)

      curve_timepoints = df.loc[[i for i in range(curve_begins, curve_ends)], time_variable].tolist()
      curve_tac_values = df.loc[[i for i in range(curve_begins, curve_ends)], 'TAC_imputed_smooth_101'].tolist()
      plt.fill_between(curve_timepoints, curve_tac_values, [baseline_cutoff for i in range(curve_begins, curve_ends)], color='lightgray')

      path = f'{plot_folder}/{subid}/{condition}/{subid}_{condition}{dataset_identifier}_smoothed_curve.png'
      plt.tight_layout()
      plt.savefig(path, bbox_inches='tight')
      plt.close('all')
      return path

def create_temp_histogram(self):
    temperatures = []
    for occasion in self.occasions:
      data = occasion.raw_dataset['Temperature_C'].tolist()
      temperatures.extend(data)
    temperatures_below_28 = [temp for temp in temperatures if temp < 28]

    import matplotlib.pyplot as plt
    plt.hist(temperatures, bins = [20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40])
    plt.ylabel("Counts (1000's)")
    plt.xlabel('Temperature (Celsius)')
    plt.title('Temperature Distribution')
    plt.xticks([20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40])
    plt.yticks(ticks = [2000, 4000, 6000, 8000, 10000, 12000, 14000, 16000, 18000], labels=[2, 4, 6, 8, 10, 12, 14, 16, 18])
    plt.savefig(f'{self.analyses_out_folder}/temperature_histogram.png')
    plt.close('all')

def plot_box_whisker(stats, variables, group_variable, plot_folder, dataset_version, cohort_name):
      data = {}
      for variable in variables:
            data[variable] = [[] for i in range(0, len(stats[group_variable].unique()))]
            for i, condition in enumerate(stats[group_variable].unique()):
                  data[variable][i] = stats[stats[group_variable]==condition][variable].tolist()
      
      figure, axis = plt.subplots(1, len(variables))
      figure.set_figheight(12)
      figure.set_figwidth(10 * len(variables))
      colors = ['firebrick', 'silver']
      ticker = 0
      for variable in variables:
            bp = axis[0 + ticker].boxplot(data[variable], positions = [1, 2], widths = 0.5, patch_artist = True)
            axis[0 + ticker].set_title(variable)
            axis[0 + ticker].set_xticks([(i+1) for i in range(0, len(stats[group_variable].unique()))])
            axis[0 + ticker].set_xticklabels(stats[group_variable].unique().tolist())
            axis[0 + ticker].grid(color = 'lightgray', linestyle = '--', linewidth = 0.75, axis='y')
            ticker += 1
            for patch, color in zip(bp['boxes'], colors):
                  patch.set_facecolor(color)
            for median in bp['medians']:
                  median.set(color ='black', linewidth = 2)

            
      full_path = f'{plot_folder}/{dataset_version}_features_{cohort_name}_box_whisker.png'
      figure.savefig(full_path, bbox_inches='tight')
      plt.close('all')


def plot_rf_feature_importances(model, features, dataset_version, cohort_name, model_figures_folder):
  forest_importance = get_feature_importances(model, features)
  fig, ax = plt.subplots()
  ax.grid(True, axis = 'x')
  forest_importance.plot.barh(ax=ax, color='dimgray')
  ax.set_title(f'Feature Importance - Random Forest', fontdict={'weight': 'bold', 'size': 15})
  ax.set_xlabel("Mean Decrease in Impurity", fontdict={'size': 13})
  ax.get_legend().remove()
  fig.tight_layout()

  plt.savefig(f'{model_figures_folder}/Random Forest - {cohort_name} - {dataset_version} - Feature Importances.png', dpi=55)
  plt.close('all')
  return forest_importance

def plot_rf_tree(rf, feature_names, dataset_version, cohort_name, model_figures_folder):
  fig = plt.figure(figsize=(15, 10))
  plot_tree(rf.estimators_[0], 
    feature_names=feature_names, class_names=['Alc', 'Non'], 
    filled=True, impurity=True, rounded=True)
  fig.savefig(f'{model_figures_folder}/Random Forest - {cohort_name} - {dataset_version} - Decision Tree.png')
  plt.close('all')

