from matplotlib import ticker
from scipy.signal import savgol_filter
import pandas as pd
import numpy as np
from scipy import interpolate
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import DotProduct, WhiteKernel


def smooth_signals(df_prior, window_length, polyorder, variables):
  df = df_prior.copy()
  smoothed_tac_variables = {}
  for variable in variables:
    smoothed = savgol_filter(df[variable], window_length = window_length, polyorder = polyorder, mode='mirror')
    TAC_smoothed = pd.Series(smoothed)
    smoothed_tac_variables[f'{variable}_{window_length}'] = TAC_smoothed

  return smoothed_tac_variables
