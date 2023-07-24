from bdb import Breakpoint
import pandas as pd
import numpy as np
from utils.Stats.stats import *
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.linear_model import LinearRegression
import scipy.interpolate
from sklearn.gaussian_process.kernels import DotProduct, WhiteKernel

def impute(df_prior, tac_list, time_variable, index_check_count, knot_proportion = 0.10, variable='TAC', how='both', threshold=False):

  df = df_prior.copy()
  cannot_impute = []

  #get a list of indices where artifacts have been removed
  missing_idx = [i for (i, tac) in enumerate(tac_list) if np.isnan([tac])]

  #artifact gap cannot take more than 20% of dataset
  gap_limit = len(df) * 0.40

  #create a list of each gap
  gaps = [[]]
  gap_count = 0
  for i, index in enumerate(missing_idx):
    if (i > 0):
      if (index != (missing_idx[i-1] + 1)):
        gap_count += 1
        gaps.append([])      
    gaps[gap_count].append(index)

  if len(missing_idx) > 0:
    for gap in gaps:
      if len(gap) < gap_limit:
        if len(index_check_count) > 0:
          gap_index_check_count = {k: index_check_count[k] for k in gap}
          max_impute_attempts = max(gap_index_check_count.values())
        else:
          max_impute_attempts = 0

        #how many data points to use for building spline? X % of the dataset.
        #for front of gap
        first_missing_id = gap[0]
        data_limit = (int(len(df) * knot_proportion)) if (len(df) * knot_proportion) > 30 else 30
        front_ticker = 0
          #while the index is not beyond the length of df or greater than our local data limit
        while (first_missing_id - front_ticker > 0) and (front_ticker <= data_limit):
          front_ticker += 1
        front_index = first_missing_id - front_ticker
        data_before_gap = df.loc[front_index:first_missing_id-1]
        data_before_gap.reset_index(inplace=True)

        #for behind the gap
        last_missing_id = gap[-1]
        data_limit = (int(gap_limit / 2)) if gap_limit > 75 else 30
        back_ticker = 0
          #while the index is not beyond the length of df or greater than our local data limit
        while (last_missing_id + back_ticker < len(df)) and (back_ticker <= data_limit):
          back_ticker += 1
        back_index = last_missing_id + back_ticker
        data_after_gap = df.loc[last_missing_id+1:back_index]
        data_after_gap.reset_index(inplace=True)
        #before and after gap
        

        """
        sometimes the data after gap has values that are artifacts. while we do not want to impute for those now, 
        we do not want those to be used to train the imputation model. 
        this below loop detects those artifacts for removal
        """
        outlier_indices = {'before': [], 'after': []}
        if threshold:
          for position, dataset in {'before': data_before_gap, 'after': data_after_gap}.items():
            local_peak = get_peak(dataset, 'TAC')
            for i, row in dataset.iterrows():
              if i > 0:
                tac_difference = abs(row['TAC'] - dataset.loc[i - 1, 'TAC'])
                if (local_peak > 1) and (tac_difference > 1):
                  if ((np.log(tac_difference) / (np.log(local_peak) + 0.0001)) > threshold) and (local_peak > 3):
                    outlier_indices[position].append(i)
        data_before_gap.loc[outlier_indices['before'], 'TAC'] = np.nan
        data_after_gap.loc[outlier_indices['after'], 'TAC'] = np.nan
        data_around_gap = pd.concat([data_before_gap, data_after_gap])

        key = {
          'left': data_before_gap,
          'right': data_after_gap,
          'both': data_around_gap
        }
        training_data = key[how]
        x = training_data[~pd.isna(training_data[variable])][time_variable]
        y = training_data[~pd.isna(training_data[variable])][variable]
        x_with_gap = df[front_index:back_index][time_variable]      

        # 4 models can be attempted
        # if model fails to bring value below artifact threshold, then next model will be attempted
        if max_impute_attempts == 1:
          model = GaussianProcessRegressor(kernel=DotProduct(), random_state=0).fit(x.to_numpy().reshape(-1, 1), y)
          predictions = model.predict(x_with_gap.to_numpy().reshape(-1, 1))

          data_to_insert = predictions[front_ticker:front_ticker+(last_missing_id-first_missing_id+1)]
          tac_list[first_missing_id:last_missing_id+1] = data_to_insert
        elif max_impute_attempts in [2, 3]:
          model = LinearRegression().fit(x.to_numpy().reshape(-1, 1), y)
          predictions = model.predict(x_with_gap.to_numpy().reshape(-1, 1))
          data_to_insert = predictions[front_ticker:front_ticker+(last_missing_id-first_missing_id+1)]
          tac_list[first_missing_id:last_missing_id+1] = data_to_insert
        elif max_impute_attempts in [3, 4] and (how=='both'):
          y_interp = scipy.interpolate.interp1d(x.tolist(), y.tolist())
          predictions = y_interp(x_with_gap)
          data_to_insert = predictions[front_ticker:front_ticker+(last_missing_id-first_missing_id+1)]
          tac_list[first_missing_id:last_missing_id+1] = data_to_insert
        else:
          model = GaussianProcessRegressor(kernel=DotProduct(), random_state=0).fit(x.to_numpy().reshape(-1, 1), y)
          predictions = model.predict(x_with_gap.to_numpy().reshape(-1, 1))
          data_to_insert = predictions[front_ticker:front_ticker+(last_missing_id-first_missing_id+1)]
          tac_list[first_missing_id:last_missing_id+1] = data_to_insert
          for i in gap:
            cannot_impute.append(i)
      else:
        for i in gap:
          cannot_impute.append(i)

  return tac_list, cannot_impute
  

        # import matplotlib.pyplot as plt
        # plt.figure()
        # plt.plot(x, y)
        # plt.title('interpolation')
        # plt.show()