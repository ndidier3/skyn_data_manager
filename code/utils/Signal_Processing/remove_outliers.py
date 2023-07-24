import pandas as pd
from statistics import mean
import numpy as np
from utils.Stats.stats import *
from utils.Signal_Processing.impute import impute
np.seterr(divide = 'ignore')
from utils.Reporting.plotting import *
from utils.Stats.get_tac_clusters import get_tac_clusters
from utils.Signal_Processing.returns_to_baseline import returns_to_baseline
from utils.Signal_Processing.tac_slope import tac_slope

def replace_extreme_values(df, time_variable):
  cluster_to_remove = None
  if df['TAC'].max() > 400:
    df = get_tac_clusters(df)
    cluster_minumums = [df[df.cluster == cluster_id]['TAC'].min() for cluster_id in df['cluster'].unique()]
    cluster_maximums = [df[df.cluster == cluster_id]['TAC'].max() for cluster_id in df['cluster'].unique()]
    for i, cluster_id in enumerate(df['cluster'].unique()):
      if i > 0:
        cluster_separation = cluster_minumums[i] - cluster_maximums[i-1]
        if cluster_separation > 200:
          cluster_to_remove = cluster_id
  error_indices = []
  if cluster_to_remove:
    df.loc[df['cluster'] == cluster_to_remove, 'TAC'] = np.nan
    error_indices.extend(df[df['cluster'] == cluster_to_remove].index.tolist())
    tac_cleaned, not_imputable = impute(df, df['TAC'].tolist(), time_variable, {}, how='left', threshold=False)
    df['TAC'] = tac_cleaned
  return df, error_indices

def replace_negative_values(df, time_variable):
  df.loc[df['TAC'] < -3, 'TAC'] = 0
  error_indices = df[df['TAC'] < -3].index.tolist()
  return df, error_indices

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

def find_and_replace_outliers(df, test_range, time_variable, major_threshold=0.75, minor_threshold=0.50):

  df_test = df.copy()

  df_test, extreme_errors = replace_extreme_values(df_test, time_variable)
  
  tac_list = df_test['TAC'].tolist()
  tac_list_cleaned = [tac if i not in extreme_errors else np.nan for i, tac in enumerate(tac_list.copy())]
  tac_list_imputed = tac_list.copy()

  counter = 0
  outlier_counter = {
    'major': extreme_errors,
    'minor': []
  }
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
    if start == 0:
      cycle += 1
      outliers_in_cycle[cycle] = False

    for index, tac in enumerate(tac_list_current):
      #if ((index > test_range) and (index < (len(tac_list) - test_range)) and (index >= start)):
      if ((index > test_range) and (index >= start)):
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
        if tac_difference > 5:
          local_peak = get_peak(df, 'TAC', window={'index': index, 'window': 100})
          log_percent_change_from_peak = (np.log(tac_difference)) / (np.log(local_peak) + 0.0001)
          major_threshold_passed = (log_percent_change_from_peak >= major_threshold) and (local_peak > 20) and (index not in cannot_impute)
          minor_threshold_passed = (log_percent_change_from_peak >= minor_threshold) and (local_peak > 5) and (index not in cannot_impute) and (tac_difference > 2) and (~major_threshold_passed) and (cycle > 1) #this ensures all major errors are detected before minor errors

          if major_threshold_passed:
            index_ticker = 0
            threshold_exceeded = True
            slope = tac_slope(tac_list_current, index, 6)
            slope_direction = 1 if slope >= 0 else -1
            direction_of_tac_change = 1 if (tac_list_current[index] - tac_list_current[index - 1]) > 0 else -1
            threshold_projection_direction = direction_of_tac_change
            tac_returns_to_baseline = returns_to_baseline(previous_avg, tac_list_current, index, direction_of_tac_change)
            # print(slope, direction_of_tac_change, threshold_projection_direction)
            while threshold_exceeded:
              threshold = (((abs(slope)) * threshold_projection_direction) * index_ticker) + tac_list_current[index - 1] + (3 * threshold_projection_direction) 
              tac_for_testing = tac_list_current[index + index_ticker]
              threshold_passed = (tac_for_testing > threshold) if (direction_of_tac_change == 1) else (tac_for_testing < threshold)
              # print(threshold, ' vs  ', tac_for_testing, f' :{threshold_passed}')
              if threshold_passed:
                tac_list_current[index + index_ticker] = np.nan
                tac_list_cleaned[index + index_ticker] = np.nan
                outlier_counter['major'].append(index + index_ticker)
                index_ticker += 1
              if not threshold_passed or ((index + index_ticker) == len(tac_list)):
                imputing_model_method = 'both' if tac_returns_to_baseline else 'left'
                tac_list_current, not_imputable = impute(df, tac_list_current, time_variable, index_check_count, how=imputing_model_method, threshold=False)
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

        tac_review_complete = (index >= (len(tac_list) - 1))
        if tac_review_complete and not outliers_in_cycle[cycle] and (cycle > 1):
          all_data_points_checked = True
          break
        if tac_review_complete and (outliers_in_cycle[cycle]) or (tac_review_complete and (cycle == 1)):
          starting_index[counter] = 0
          

  tac_lists_repo['imputed'][counter] = [tac if tac > 0 else 0 for tac in tac_lists_repo['imputed'][counter]]
  return tac_lists_repo['imputed'][counter], tac_lists_repo['cleaned'][counter], set(outlier_counter['major']), set(outlier_counter['minor'])
