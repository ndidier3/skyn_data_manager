import numpy as np
import pandas as pd
import statistics as stats_package
from sklearn.metrics import r2_score

def get_auc(df, variable, time_variable):
  tac = df[variable]
  tac = tac.astype(float)
  total_auc = np.trapz(tac, dx = 0.1)
  auc_per_hour = total_auc / df[time_variable].max()
  return total_auc, auc_per_hour
  
def get_mean_stdev_sem(df, variable):
  tac = df[variable]
  return tac.mean(), tac.std(), tac.sem()

def get_peak(df, variable, window = {}):
  if len(window) > 0:
    window_length = window['window']
    index = window['index']
    previous_window = window_length if (index - window_length) > 0 else (index - 1)
    post_window = window_length if (index + window_length) < len(df) else ((len(df) - window_length) - 1)
    return df.loc[index-previous_window:index+post_window, variable].max()
  else:
    tac = df[variable]
    return tac.max()

def get_peak_index(df, variable):
  tac = df[variable]
  return df.index[df[variable]==tac.max()].tolist()[0]

def get_baseline_mean_stdev(df, variable, baseline_value_count=10):
  tac = df[variable]
  baseline_values = tac.loc[0:baseline_value_count]
  return baseline_values.mean(), baseline_values.std()

def get_rise_duration(df, variable, time_variable, peak_index):
  base_mean, base_stdev = get_baseline_mean_stdev(df, variable)
  baseline_threshold = base_mean + base_stdev
  baseline_threshold_reached = False
  index_count = 1
  while not baseline_threshold_reached:
    if peak_index == 0:
      curve_begins_index = 0
      break
    if (peak_index - index_count) == 0:
      curve_begins_index = 0
      break
    if df[variable].loc[peak_index - index_count] < baseline_threshold:
      curve_begins_index = peak_index - index_count
      baseline_threshold_reached = True
    index_count += 1

  rise_duration =  df.loc[peak_index, time_variable] - df.loc[curve_begins_index, time_variable]
  
  if rise_duration == 0:
    rise_duration = 1

  return rise_duration, curve_begins_index

def get_fall_duration(df, variable, time_variable, peak_index):
  post_peak_data = df.loc[peak_index:]
  base_mean, base_stdev = get_baseline_mean_stdev(df, variable)
  baseline_threshold = base_mean + base_stdev
  baseline_threshold_reached = False
  index_count = 1
  if any(post_peak_data[variable] < baseline_threshold):
    while not baseline_threshold_reached:
      if peak_index == 0:
        curve_ends_index = 0
        break
      if (peak_index + index_count) == (len(df) - 1):
        curve_ends_index = (len(df) - 1)
        break
      if df[variable].loc[peak_index + index_count] < baseline_threshold:
        curve_ends_index = peak_index + index_count
        baseline_threshold_reached = True
      index_count += 1
  else:
    curve_ends_index = (len(df) - 1)

  fall_duration = post_peak_data.loc[curve_ends_index, time_variable] - post_peak_data.loc[peak_index, time_variable]

  if fall_duration == 0:
    fall_duration = 1

  return fall_duration, curve_ends_index

def get_rise_rate(rise_duration, peak):
  return peak / rise_duration

def get_fall_rate(fall_duration, peak):
  return peak / fall_duration

def get_curve_duration(rise_duration, fall_duration):
  return rise_duration + fall_duration

def get_curve_auc(df, variable, curve_begins_index, curve_ends_index):
  df_curve_only = df.loc[curve_begins_index:curve_ends_index]
  tac_cropped = df_curve_only[variable]
  tac_cropped = tac_cropped.astype(float)
  curve_auc = np.trapz(tac_cropped, dx = 0.1)
  return curve_auc

def get_curve_auc_per_hour(curve_auc, curve_duration):
  return curve_auc / curve_duration

def get_average_tac_difference(df, variable):
  """
  takes absolute value of the difference between each consecutive TAC difference, then returns the mean of all differences and a list of each difference
  """
  tac = df[variable]
  differences = []
  for i, value in enumerate(tac):
    if i >= 1:
      absolute_difference = abs(value - tac[i-1])
      differences.append(absolute_difference)
  return stats_package.fmean(differences), differences
  
def get_tac_directional_alteration_percent(df, variable):
  """
  returns % of TAC changes that reverse the direction of previous values
  """
  tac = df[variable]
  alterations = 0
  changes = []
  for i, value in enumerate(tac):
    if i >= 1:
      difference = value - tac[i-1]
      if difference >= 0:
        current_change = 'positive'
      else:
        current_change = 'negative'
      changes.append(current_change)
    if i > 1:
      prior_change = changes[i-2]
      if current_change != prior_change:
        alterations += 1
  
  alteration_percent = (alterations / len(changes)) * 100
  return alteration_percent

def get_value_proportion(df, value, variable):
  """returns proportion (float) of column that equals provided value"""
  return len(df[df[variable] == value][variable]) / len(df)

def get_r2(df, truth, test):
  "Provide dataframe, column name for truth, and column name to test. returns r squared (coeffecient of determination)"
  return r2_score(df[truth].tolist(), df[test].tolist())