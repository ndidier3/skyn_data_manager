from tokenize import group
import pandas as pd
import matplotlib.pyplot as plt
import os
from utils.Configuration.configuration import normalize_column
import numpy as np

def plot_column(df, plot_folder, subid, condition, y_variable, time_variable, xlabel="Time (hours)"):
      ylabel = y_variable    
      title = f'{y_variable} {subid} {condition}'
      plot = df.plot.scatter(y=y_variable, x=time_variable, title=title, ylabel=ylabel, xlabel=xlabel)
      fig = plot.get_figure()
      
      folder = f'{plot_folder}/{subid}/{condition}/{y_variable}'
      if not os.path.exists(folder):
            os.mkdir(folder)
      full_path = f'{folder}/{y_variable} - {subid} - {condition}.png'
      fig.savefig(full_path)
      return full_path

def plot_TAC_curve(df, plot_folder, subid, condition, tac_variable, time_variable, ylabel="TAC ug/L", xlabel="Time (hours)"):
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

      full_path = f'{folder}/{tac_variable} - {subid} - {condition}.png'
      fig.savefig(full_path)
      return full_path

def plot_overlaid_TAC_curves(df, plot_folder, subid, condition, tac_variables, time_variable, plot_name, ylabel="TAC ug/L", xlabel="Time (hours)"):
      title = f'TAC Curve - {plot_name}'
      plot = df.plot(y=tac_variables, x=time_variable, title=title, ylabel=ylabel, xlabel=xlabel)
      fig = plot.get_figure()
      
      folder = f'{plot_folder}/{subid}/{condition}'
      if not os.path.exists(folder):
            os.mkdir(folder)

      full_path = f'{folder}/{plot_name} - {subid} - {condition}.png'
      fig.savefig(full_path)
      return full_path

def plot_overlaid_with_normalization(df_prior, plot_folder, subid, condition, variables, time_variable, plot_name):
      df = df_prior.copy()
      title = f'{" ".join(variables)} - {subid} - {condition}'
      fig = plt.figure()
      ax1 = fig.add_subplot(111)
      colors = ['b', 'c', 'g', 'r']
      markers = ['o', 's', 'v', 'x']
      for i, variable in enumerate(variables):
            df[variable] = normalize_column(df[variable])
            ax1.scatter(y=df[variable], x=df[time_variable], s=10, c=colors[i], marker=markers[i], label=variable)

      plot = df.plot(y=variables, x=time_variable, title=title, ylabel='Norm Variables', xlabel='Time (hrs)')
      fig.legend(loc='upper right')

      folder = f'{plot_folder}/{subid}/{condition}/overlaid/'
      if not os.path.exists(folder):
            os.mkdir(folder)
            
      full_path = f'{folder}/{plot_name} - {subid} - {condition}.png'
      fig.savefig(full_path)
      return full_path

def plot_cleaning_comparison(occasion, df, df_raw, time_variable):
      imputed_tac = df.loc[df['TAC'] != df['TAC_imputed']]['TAC_imputed'].tolist()
      imputed_x = df[df['TAC'] != df['TAC_imputed']][time_variable].tolist()
      cleaned_tac = df.loc[pd.isna(df['TAC_cleaned']), 'TAC'].tolist()
      cleaned_x = df.loc[pd.isna(df['TAC_cleaned']), time_variable].tolist()
      raw_tac = df_raw.loc[df['TAC'].eq(df['TAC_imputed']), 'TAC'].tolist()
      raw_x = df_raw.loc[df['TAC'].eq(df['TAC_imputed']), time_variable].tolist()
      fig, ax = plt.subplots()
      ax.scatter(raw_x, raw_tac, c='b', marker='o', s=8)
      ax.scatter(cleaned_x, cleaned_tac, c='r', marker='*', s=8)
      ax.scatter(imputed_x, imputed_tac, c='g', marker='o', s=8)
      ax.set_xlabel('Time (hrs)')
      ax.set_ylabel('TAC')
      ax.set_title(f'TAC Signal Processing - {occasion.subid} - {occasion.condition}')
      ax.legend(("Raw", "Removed", "Imputed"), loc='upper right')
      #plt.legend(['Raw', 'Removed', 'Impupted'], loc='upper right')

      folder = f'{occasion.plot_folder}/{occasion.subid}/{occasion.condition}/cleaning/'
      if not os.path.exists(folder):
            os.mkdir(folder)
            
      full_path = f'{folder}/cleaning - {occasion.subid} - {occasion.condition}.png'
      plt.savefig(full_path)
      plt.close()
      return full_path

def plot_box_whisker(stats, variables, group_variable, plot_folder, version):
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

      folder = f'{plot_folder}/feature_visuals/'
      if not os.path.exists(folder):
            os.mkdir(folder)
            
      full_path = f'{folder}/{version}_feature_box_whisker.png'
      figure.savefig(full_path, bbox_inches='tight')
      return f'{folder}/'