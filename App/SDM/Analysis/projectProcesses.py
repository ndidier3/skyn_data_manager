from .statModel import statModel
from .featureFlagger import featureFlagger
from ..Configuration.file_management import load, save_to_computer, create_feature_plot_folder
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

""" ACE """
def run_ace_processes():
  event_features = pd.read_excel('Results/ACE/11.20.2024/event_level_quality_metrics.xlsx')
  event_features = event_features[event_features['data_found_CURVE'] == True]
  print(len(event_features))
  event_features = event_features[event_features['flatline_max_CURVE'] <= 50]
  print(len(event_features))
  event_features = event_features[event_features['device_worn_percent_CURVE'] >= 0.8]
  print(len(event_features))
  event_features = event_features[event_features['peak_CURVE'] < 2000]
  print(len(event_features))
  event_features = event_features[event_features['auc_total_CURVE'] < 50000]
  print(len(event_features))
  event_features.drop_duplicates(inplace=True)
  print(len(event_features))
  #remove duplicate rows

  """
  Consider removal based on very negative duration
  Review IDs: 
        subid  event  day_id
  727    197      2       2
  731    197      6       5 
  """

  feature_plot_folder = create_feature_plot_folder('ACE')

  x = 'drink_total'
  y_features = [
    'mean_tac_CURVE','peak_CURVE', 'auc_total_CURVE' ,'rise_duration_CURVE' 
    ,'fall_duration_CURVE', 'rise_rate_CURVE', 'fall_rate_CURVE'
  ]

  # Loop through y_features and create scatter plots
  for y_feature in y_features:
      plt.figure(figsize=(6, 4))
      plt.scatter(event_features[x], event_features[y_feature], alpha=0.7)
      plt.title(f'{x} vs {y_feature}')
      plt.xlabel(x)
      plt.ylabel(y_feature)
      plt.grid(True)
      plt.savefig(f'{feature_plot_folder}/{x}_vs_{y_feature}.png')

run_ace_processes()