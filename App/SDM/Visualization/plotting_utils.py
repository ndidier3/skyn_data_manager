import pandas as pd
import matplotlib.pyplot as plt
from SDM.Configuration.configuration import get_closest_index_with_timestamp

def plot_event_lines(data, ax, event_timestamp, x_variable, timestamp_column='datetime', font_size=18):
  text_adjustment = 0
  for event, timestamp in event_timestamp.items():
    if pd.notna(timestamp):
      idx = get_closest_index_with_timestamp(data, timestamp, timestamp_column)
      ax.vlines(data.loc[idx, x_variable], 0, ax.get_ylim()[1], linestyles="dashed")
      plt.text(data.loc[idx, x_variable], ax.get_ylim()[1] * (0.95 - text_adjustment), event, fontsize = font_size, fontstyle = "italic")
      text_adjustment += 0.08

def split_x_y_from_temp_cutoff(df, temp_variable, y_variable, time_variable, cutoff=27):
  invalid_x = df[df[temp_variable]<cutoff][time_variable]
  invalid_y = df.loc[df[temp_variable]<cutoff, y_variable].tolist()
  valid_x = df[df[temp_variable]>=cutoff][time_variable]
  valid_y = df.loc[df[temp_variable]>=cutoff, y_variable].tolist()

  return valid_x, valid_y, invalid_x, invalid_y

def split_x_y_from_predictions(df, prediction_column, y_variable, time_variable):
  #must be binary predictions
  positive_idx = df[df[prediction_column]==1].index.tolist()
  negative_idx = df[df[prediction_column]==0].index.tolist()
  invalid_x = df.loc[negative_idx, time_variable].tolist()
  invalid_y = df.loc[negative_idx, y_variable].tolist()
  valid_x = df.loc[positive_idx, time_variable].tolist()
  valid_y = df.loc[positive_idx, y_variable].tolist()

  return  valid_x, valid_y, invalid_x, invalid_y

def find_ranges(values, threshold):
  ranges = []
  start = values[0]
  for i in range(1, len(values)):
      if values[i] - values[i - 1] > threshold:
          ranges.append((start, values[i - 1]))
          start = values[i]
  ranges.append((start, values[-1]))
  return ranges