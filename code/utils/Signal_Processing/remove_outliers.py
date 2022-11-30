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

def remove_extreme_values(df, limit):
  for index in df.index[df['TAC']>limit].tolist():
    df.loc[index, 'TAC'] = np.nan
  return df

def interpolate(df, variable, method, proportional_limit=0.20):
  limit = int(len(df)*proportional_limit)
  df.loc[:, variable] = df.loc[:, variable].interpolate(method=method, limit=limit, limit_area='inside')
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
          # print('before testing', tac_list_current[index:index+10])
          while threshold_exceeded:
            tac_for_testing = tac_list_current[index + index_ticker]
            threshold_passed = tac_for_testing > (tac_list_current[index-1] * 1.2)
            if threshold_passed:
              tac_list_current[index + index_ticker] = np.nan
              tac_list_cleaned[index + index_ticker] = np.nan
              outlier_counter['major'].append(index + index_ticker)
              index_ticker += 1
            if ~threshold_passed or ((index + index_ticker) == len(tac_list)):
              # print('before impute', tac_list_current[index:index+10])
              tac_list_current, not_imputable = impute(df, tac_list_current, time_variable, index_check_count, how='both', threshold=False)
              # print('after impute', tac_list_current[index:index+10])
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
          # print('before test', tac_list_current[index:index+10])
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
            # test_3 = (current_difference > (2 * tac_list_current[index - 1])) and (current_difference > 2)
            # threshold_tests.append(test_3)

            if any(threshold_tests):
              tac_list_current[index + index_ticker] = np.nan
              tac_list_cleaned[index + index_ticker] = np.nan
              outlier_counter['minor'].append(index + index_ticker)
              index_ticker += 1
              
            if ~any(threshold_tests) or ((index + index_ticker) == len(tac_list)):
              # print('before impute', tac_list_current[index:index+10])
              tac_list_current, not_imputable = impute(df, tac_list_current, time_variable, index_check_count, how='both', threshold=0.35)
              # print('after impute', tac_list_current[index:index+10])
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

"""
def remove_outliers_old(df, test_range, multiplication_factor, constant):
  df_test = df.copy()

  #base_mean, base_stdev = stats.get_baseline_mean_stdev(df_test, 'TAC')

  df_test = remove_extreme_values(df_test, 1000)
  df_test = interpolate(df_test, 'TAC', 'linear')

  df_test['artifact_cleaned'] = [0 for i in range(0, len(df_test))]

  errors_remaining = True

  while errors_remaining == True:
    error_index_list = []

    for index, row in df_test.iterrows():

      if ((index > test_range) and (index < (len(df_test) - test_range))):

        previous_tac_list = []
        post_tac_list = []
        for x in range(1, test_range):
          #record the previous X number of values before and after the current value being assessed
          previous_tac_list.append(df_test.loc[index-x, 'TAC'])
          post_tac_list.append(df_test.loc[index+x, 'TAC'])

        previous_diff_tac_list = []
        post_diff_tac_list = []
        for i in range(0, len(previous_tac_list)):
          if i > 0:
            #get the difference between each adjacent value
            previous_diff_tac_list.append(abs(previous_tac_list[i] - previous_tac_list[i-1]))
            post_diff_tac_list.append(abs(post_tac_list[i] - post_tac_list[i-1]))

        #get the avg of past + post X values
        previous_avg = mean(previous_tac_list)
        post_avg = mean(post_tac_list)

        #get the avg differences
        previous_avg_diff = mean(previous_diff_tac_list)
        post_avg_diff = mean(post_diff_tac_list)
        
        #get difference between current value and avg of previous values
        current_previous_diff = abs(df_test.loc[index, 'TAC'] - previous_avg)
        current_post_diff = abs(df_test.loc[index, 'TAC'] - post_avg)

        #multiply the avg_diff to get a significantly greater comparator - UPDATE TO USE STDEV
        previous_comparator = abs(previous_avg_diff * multiplication_factor) + constant
        post_comparator = abs(post_avg_diff * multiplication_factor) + constant
        
        if (current_previous_diff > previous_comparator) or (current_post_diff > post_comparator):
          df_test.loc[index, 'TAC'] = np.nan
          df_test.loc[index, 'artifact_cleaned'] = 1

    if len(error_index_list) == 0:
        errors_remaining = False

    df_test.reset_index(inplace=True, drop=True)
  
  df_test = interpolate(df_test, 'TAC', 'linear')
  df_test.rename(columns = {'TAC':'TAC_cleaned'}, inplace=True)
  col_list = ['TAC_cleaned', 'datetime', 'artifact_cleaned']
  df_test = df_test[col_list]
  merged_df = df.merge(df_test, how='left', on='datetime')
  tac_cleaned = merged_df['TAC_cleaned'].tolist()
  artifacts = merged_df['artifact_cleaned']

  # #revise the "outlier" values
  # for n, tac_value in enumerate(tac_cleaned):
  #   if n > test_range:
  #     if np.isnan(tac_value):
  #       artifact_index_list.append(n)  
  #       prior_vals = tac_cleaned[n-test_range:n]
  #       avg = mean(prior_vals)
  #       prior_vals_diff = []
  #       for i, tac in enumerate(prior_vals):
  #         if i > 0:
  #           diff = abs(tac - prior_vals[i-1])
  #           prior_vals_diff.append(diff)
  #       avg_diff = mean(prior_vals_diff)
        
  #       #Update: create normal distribution for values, instead of random
  #       flux_val = ((random.randint(-100, 100)/100)*(avg_diff))
  #       tac_cleaned[n] = avg + flux_val

  # tac_cleaned
  
  return tac_cleaned, artifacts

def remove_outliers_greedy(df, test_range, multiplication_factor, constant, baseline_factor):

  df_test = df.copy()

  base_mean, base_stdev = stats.get_baseline_mean_stdev(df_test, 'TAC')
  df_test = remove_extreme_values(df_test, 1000)
  df_test = interpolate(df_test, 'TAC', 'linear')

  tac_list = df_test['TAC'].tolist()
  artifact_binary = [0 for i in range(0, len(df_test['TAC'].tolist()))]

  errors_remaining = True
  while errors_remaining == True:
    artifact_index_list = []
    for n, val in enumerate(tac_list):
      if (n > test_range):
        prior_vals = tac_list[n-test_range:n]
        avg_prior_vals = mean(prior_vals)

        prior_vals_diff = []
        for i, tac in enumerate(prior_vals):
          if i > 0:
            diff = abs(tac - prior_vals[i-1])
            prior_vals_diff.append(diff)
        avg_diff = abs(mean(prior_vals_diff))

        current_diff = val - avg_prior_vals
            
        if current_diff > ((avg_diff * multiplication_factor) + constant):
          artifact_index_list.append(n)
      
      if len(artifact_index_list) != 0:
        split_index_starts = [artifact_index_list[0]]
        for n, artifact_index in enumerate(artifact_index_list):
          if n > 0:
            #if previous artifact index is not consecutive, then it is from a separate 'spike'
            if (artifact_index-1) != artifact_index_list[n-1]:
              split_index_starts.append(artifact_index)
                    
        pre_split_tac_avgs = []
        pre_split_tac_diffs = []
        for index in split_index_starts:
          prior_vals = tac_list[index-test_range:index]
          prior_tac_avg = mean(prior_vals)
          pre_split_tac_avgs.append(prior_tac_avg)
          prior_tac_differences = []
          for n, tac in enumerate(prior_vals):
            if n > 0:
              diff = abs(tac - prior_vals[n-1])
              prior_tac_differences.append(diff)
          avg_tac_diff = mean(prior_vals_diff)
          pre_split_tac_diffs.append(avg_tac_diff)

        for n, artifact_start_index in enumerate(split_index_starts):
          pre_split_avg = pre_split_tac_avgs[n]
          pre_split_avg_diff = pre_split_tac_diffs[n]
          while (tac_list[artifact_start_index]) > (pre_split_avg*baseline_factor):
            # flux_val = ((random.randint(-100, 100)/100)*(pre_split_avg_diff))
            # tac_list[artifact_start_index] = pre_split_avg+flux_val
            tac_list[artifact_start_index] = np.nan
            artifact_binary[artifact_start_index] = np.nan
            artifact_start_index += 1
            if artifact_start_index == len(tac_list):
              break
      else:
          errors_remaining = False
  
  for n, val in enumerate(tac_list):
    if (n > 0) and (n < (len(tac_list)-1)):
      if (abs(val) > abs(tac_list[n-1]*1.7) and (abs(val) > abs(tac_list[n+1]*1.7))):
        tac_list[n] = np.nan
        artifact_binary[n] = 1
  

  df['TAC_cleaned_greedy'] = tac_list
  df = interpolate(df, 'TAC_cleaned_greedy', 'linear')

  return df['TAC_cleaned_greedy'].tolist(), artifact_binary


  REMNANTS FROM CURRENT CLEANING METHOD
  # #get the avg differences
        # previous_avg_diff = mean(previous_diff_tac_list)
        # post_avg_diff = mean(post_diff_tac_list)
        
        # #get difference between current value and avg of previous values
        # current_previous_diff = abs(tac_list_current[index] - previous_avg)
        # current_post_diff = abs(tac_list_current[index] - post_avg)

        #multiply the avg_diff to get a significantly greater comparator - UPDATE TO USE STDEV
        # previous_avg_diff = abs(previous_avg_diff)
        # post_avg_diff = abs(post_avg_diff)

        # multiplication_factor = deviations * 2

        # if ((current_previous_diff / previous_avg_diff) > multiplication_factor) or ((current_post_diff / post_avg_diff) > multiplication_factor):
        #   x = np.array([i for i in range(0, len(previous_tac_list))])
        #   y = np.asarray(previous_tac_list)

          #   model = GaussianProcessRegressor(kernel=DotProduct(), random_state=0).fit(x.reshape(-1, 1), y.reshape(-1, 1))
          #   x_to_predict = x.max() + 1
          #   prediction = model.predict(np.asarray([x_to_predict]).reshape(1, -1))
          # else:
          #deviation = stats_package.pstdev(previous_tac_list)


                    # in_normal_tac_range = False
          # index_ticker = 0
          # while not in_normal_tac_range:
          #   current_tac_difference = abs(tac_list_current[index + index_ticker] - previous_avg)
          #   if ((current_tac_difference < (avg_change + (deviations*stdev_change))) or 
          #       (current_tac_difference < )):
          #     in_normal_tac_range = True
          #   else:
          #     tac_list_current[index + index_ticker] = np.nan
          #     tac_list_cleaned[index + index_ticker] = np.nan
          #     artifacts[index + index_ticker] = 1
          #     index_ticker += 1
          #     if (index + index_ticker) == len(tac_list):
          #       in_normal_tac_range = True


        # making a prediction to use as a threshold
          y = np.array(tac_list_current[index - test_range: index])
          x = np.array([i for i in range(0, len(y))])
          model = GaussianProcessRegressor(kernel=DotProduct(), random_state=0).fit(x.reshape(-1, 1), y)
          prediction, std_pred = model.predict((max(x)+1).reshape(1, -1), return_std=True)
"""
    
        