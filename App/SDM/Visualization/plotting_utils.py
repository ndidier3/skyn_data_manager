import pandas as pd
import matplotlib.pyplot as plt
from ..Configuration.configuration import get_closest_index_after_timestamp, get_closest_index_with_timestamp

def plot_event_lines(data, ax, event_timestamp, x_variable, timestamp_column='datetime', font_size=16, text_adjustment=0.07, y_start = 0.95):
  text_start = 0
  
  font_size = font_size if len(list(event_timestamp.keys())) < 3 else round(max(9, int(font_size * (1-(0.1 * (len(list(event_timestamp.keys()))-2))))))
  i = 0
  for event, timestamp in event_timestamp.items():
    if pd.notna(timestamp) and timestamp != None:
      idx = get_closest_index_after_timestamp(data, timestamp, timestamp_column)
      # idx = get_closest_index_with_timestamp(data, timestamp, timestamp_column)
      ax.vlines(data.loc[idx, x_variable], 0, ax.get_ylim()[1] * (y_start), linestyles="dashed")
      plt.text(data.loc[idx, x_variable], ax.get_ylim()[1] * (y_start) * (0.95 - text_start), event, fontsize = font_size, fontstyle = "italic")
      i += 1
      if i > 0:
        text_start += text_adjustment
      elif i > 4:
        text_start -= text_adjustment
      elif i > 8:
        text_start += text_adjustment
      elif i > 12:
        text_start -= text_adjustment
      elif i > 16:
        text_start += text_adjustment
      elif i > 20:
        text_start -= text_adjustment
        

def plot_event_lines_with_fixed_text_height(data, ax, event_timestamp, x_variable, timestamp_column='datetime', font_size=18, y_starts = []):
  start_y_index = 0
  for event, timestamp in event_timestamp.items():
    if pd.notna(timestamp) and timestamp != None:
      idx = get_closest_index_after_timestamp(data, timestamp, timestamp_column)
      # idx = get_closest_index_with_timestamp(data, timestamp, timestamp_column)
      ax.vlines(data.loc[idx, x_variable], 0, ax.get_ylim()[1] * y_starts[start_y_index], linestyles="dashed")
      plt.text(data.loc[idx, x_variable], ax.get_ylim()[1] * y_starts[start_y_index] * (0.95), event, fontsize = font_size, fontstyle = "italic")
      start_y_index += 1

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