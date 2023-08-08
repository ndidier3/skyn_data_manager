from matplotlib import ticker
from scipy.signal import savgol_filter
import pandas as pd
import numpy as np
from scipy import interpolate
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import DotProduct, WhiteKernel


def smooth_signals(df_prior, window_lengths, polyorder, variables, time_variable):
  df = df_prior.copy()
  smoothed_tac_variables = {}
  for variable in variables:
    for window_length in window_lengths:
      smoothed = savgol_filter(df[variable], window_length = window_length, polyorder = polyorder, mode='nearest')
      TAC_smoothed = pd.Series(smoothed)
      smoothed_tac_variables[f'{variable}_{window_length}'] = TAC_smoothed

  return smoothed_tac_variables

  # except Exception as e:
  #   print(e)
  #   # df_length = len(df)
  #   # nan_list = [np.nan for i in range(0, df_length)]
  #   # print(f'unable to smooth data for {variable} of window length: {window_length}')
  #   # return nan_list
