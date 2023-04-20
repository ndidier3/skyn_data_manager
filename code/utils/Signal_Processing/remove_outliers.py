from audioop import avg
from operator import truediv
from socket import if_nameindex
from unicodedata import is_normalized
import pandas as pd
import random
from statistics import mean, pstdev, stdev
import numpy as np
from scipy.stats import sem
from utils.Reporting.stats import *
import statistics as stats_package
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import DotProduct
from utils.Signal_Processing.impute import impute
np.seterr(divide = 'ignore')
from utils.Reporting.plotting import *
from sklearn.linear_model import LinearRegression

def remove_extreme_values(df, limit):
  for index in df.index[df['TAC']>limit].tolist():
    df.loc[index, 'TAC'] = np.nan
  return df

def interpolate(df, variable, method, proportional_limit=0.20):
  limit = int(len(df)*proportional_limit)
  df.loc[:, variable] = df.loc[:, variable].interpolate(method=method, limit=limit, limit_area='inside')
  return df

def remove_baseline_artifact(df, tac_variable):
  peak = df[tac_variable].max()
  baseline_peak = df.loc[0:10, tac_variable].max()
  post_baseline_avg = df.loc[10:20, tac_variable].mean()
  if (peak > 15) and (baseline_peak > (peak * 0.9)) and (post_baseline_avg < (0.4 * peak)):
    df.loc[0:10, tac_variable] = 0
  return df

def replace_extreme_values(df, limit, base_mean):
  for index in df.index[df['TAC']>limit].tolist():
    prior_vals = []
    for i in range(0, 5):
      if (index - i > 0):
        if (df.loc[index - i, 'TAC'] < limit):
          prior_vals.append(df.loc[index - i, 'TAC'])
        else:
          if base_mean > 10:
            prior_vals.append(1)
          else:
            prior_vals.append(base_mean)
      else:
        prior_vals = [1]
    df.loc[index, 'TAC'] = mean(prior_vals)
  return df

def find_and_replace_outliers(df, test_range, time_variable, major_threshold=0.65, minor_threshold=0.40):
  df_test = df.copy()
  df_test = remove_extreme_values(df_test, 1100)
  df_test = interpolate(df_test, 'TAC', 'linear')

  artifacts = [0 for i in range(0, len(df_test))]
  tac_list = df_test['TAC'].tolist()
  tac_list_cleaned = tac_list.copy()
  tac_list_imputed = tac_list.copy()
  avg_change, changes = get_average_tac_difference(df_test, 'TAC')
  outlier_counter = {
    'major': [],
    'minor': []
  }
  counter = 0
  tac_lists_repo = {
    'imputed': { counter: tac_list_imputed.copy() },
    'cleaned': { counter: tac_list_cleaned.copy() }
  }
  cannot_impute = []
  starting_index = {0: 0}
  index_check_count = {}
  for i, tac in enumerate(tac_list_imputed):
    index_check_count[i] = 0
  
  cycle = 0
  outliers_in_cycle = {}

  all_data_points_checked = False
  while not all_data_points_checked:
    tac_list_current = tac_lists_repo['imputed'][counter]
    start = starting_index[counter]
    print('count:', counter, 'start:', start)
    if start == 0:
      cycle += 1
      outliers_in_cycle[cycle] = False
      print('CYCLE', cycle)

    for index, tac in enumerate(tac_list_current):
      if ((index > test_range) and (index < (len(tac_list) - test_range)) and (index >= start)):
        previous_tac_list = []
        for x in range(1, test_range):
          previous_tac_list.append(tac_list_current[index-x])
        
        previous_diff_tac_list = []
        for i in range(0, len(previous_tac_list)):
          if i > 0:
            previous_diff_tac_list.append(abs(previous_tac_list[i] - previous_tac_list[i-1]))

        previous_avg_diff = mean(previous_diff_tac_list)
        previous_avg = mean(previous_tac_list)

        tac_difference = abs(tac_list_current[index] - tac_list_current[index - 1])
        local_peak = get_peak(df, 'TAC', window={'index': index, 'window': 100})
        log_percent_change_from_peak = (np.log(tac_difference)) / (np.log(local_peak) + 0.0001)
        major_threshold_passed = (log_percent_change_from_peak >= major_threshold) and (local_peak > 20) and (index not in cannot_impute)
        minor_threshold_passed = (log_percent_change_from_peak >= minor_threshold) and (local_peak > 5) and (index not in cannot_impute) and (tac_difference > 2) and (~major_threshold_passed) and (cycle > 1) #this ensures all major errors are detected before minor errors

        if major_threshold_passed:
          print('REACHED MAJOR')
          index_ticker = 0
          threshold_exceeded = True

          while threshold_exceeded:
            tac_for_testing = tac_list_current[index + index_ticker]
            threshold_passed = (tac_for_testing > (tac_list_current[index-1] * (1.2 + (0.05 * index_ticker)))) 
            if threshold_passed:
              tac_list_current[index + index_ticker] = np.nan
              tac_list_cleaned[index + index_ticker] = np.nan
              outlier_counter['major'].append(index + index_ticker)
              index_ticker += 1
            if ~threshold_passed or ((index + index_ticker) == len(tac_list)):
              tac_list_current, not_imputable = impute(df, tac_list_current, time_variable, index_check_count, how='both', threshold=False)
              if len(not_imputable) > 0:
                for i in not_imputable:
                  cannot_impute.append(i)
              tac_lists_repo['imputed'][counter + 1] = tac_list_current
              tac_lists_repo['cleaned'][counter + 1] = tac_list_cleaned
              counter += 1
              if index_ticker > 0:
                outliers_in_cycle[cycle] = True
              else:
                outliers_in_cycle[cycle] = False
              threshold_exceeded = False

        if minor_threshold_passed:
          print('MINOR REACHED')
          index_ticker = 0
          threshold_exceeded = True
          while threshold_exceeded:
            threshold_tests = []
            temp_df = df.copy()
            temp_df.loc[:, 'TAC'] = tac_list_cleaned
            current_difference = abs(tac_list_current[index + index_ticker] - tac_list_current[index - 1])
            current_local_peak = get_peak(temp_df, 'TAC', window = {'window': 100, 'index': index + index_ticker})
            log_percent_change_from_peak = (np.log(current_difference)) / (np.log(current_local_peak) + 1)
            test_1 = (log_percent_change_from_peak > 0.35) and (current_difference > 2)
            threshold_tests.append(test_1)
            neighbor_difference = abs(tac_list_current[index + index_ticker] - tac_list_current[index + index_ticker - 1])
            log_percent_change_from_peak = (np.log(neighbor_difference)) / (np.log(current_local_peak) + 1)
            test_2 = (log_percent_change_from_peak > 0.35) and (neighbor_difference > 2)
            threshold_tests.append(test_2)

            if any(threshold_tests):
              tac_list_current[index + index_ticker] = np.nan
              tac_list_cleaned[index + index_ticker] = np.nan
              outlier_counter['minor'].append(index + index_ticker)
              index_ticker += 1
              
            if ~any(threshold_tests) or ((index + index_ticker) == len(tac_list)):
              tac_list_current, not_imputable = impute(df, tac_list_current, time_variable, index_check_count, how='both', threshold=0.35)
              if len(not_imputable) > 0:
                for i in not_imputable:
                  cannot_impute.append(i)
              tac_lists_repo['imputed'][counter + 1] = tac_list_current
              tac_lists_repo['cleaned'][counter + 1] = tac_list_cleaned
              counter += 1
              if index_ticker > 0:
                outliers_in_cycle[cycle] = True
              else:
                outliers_in_cycle[cycle] = False
              threshold_exceeded = False

        tac_review_complete = (index >= (len(tac_list) - test_range - 1))
        if tac_review_complete and not outliers_in_cycle[cycle] and (cycle > 1):
          print('END!!!!')
          all_data_points_checked = True
          break
        if tac_review_complete and (outliers_in_cycle[cycle]) or (tac_review_complete and (cycle == 1)):
          print('RESTART')
          starting_index[counter] = 0
          


  return tac_lists_repo['imputed'][counter], tac_lists_repo['cleaned'][counter], set(outlier_counter['major']), set(outlier_counter['minor'])
