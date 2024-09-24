import pandas as pd
import numpy as np
import statistics
from scipy.optimize import curve_fit

class skynDatapoint:
  def __init__(self, column_name, datetime_column, i, df, extension_range, sampling_rate, use_before=True, use_after=True, label=None):
    self.column_name = column_name
    self.datetime_column = datetime_column
    self.index = i
    self.data = df
    self.value = self.data.loc[self.index, self.column_name]
    self.current_time = self.data.loc[self.index, self.datetime_column]
    self.label = label
    self.extension_range = extension_range  # how many values to consider before and after current value
    
    # Initialize attributes
    self.value_before = None
    self.difference_from_prior = None
    self.values_before = []
    self.prior_n = 0
    self.duration_before = 0
    self.mean_before = np.nan
    self.mean_change_before = np.nan
    self.std_before = np.nan
    self.duration_minutes_before = np.nan
    self.x_time_before = []
    self.a_pre = self.b_pre = self.c_pre = np.nan

    self.value_after = None
    self.difference_from_next = None
    self.values_after = []
    self.after_n = 0
    self.duration_after = 0
    self.mean_after = np.nan
    self.mean_change_after = np.nan
    self.std_after = np.nan
    self.duration_minutes_after = np.nan
    self.x_time_after = []
    self.a_post = self.b_post = self.c_post = np.nan

    self.values_before_after = []
    self.n_total = 0
    self.a_all = self.b_all = self.c_all = np.nan

    # Calculate values before
    if self.index - 1 in self.data.index and use_before:
      self._calculate_prior_values(sampling_rate)

    # Calculate values after
    if self.index + 1 in self.data.index and use_after:
      self._calculate_post_values(sampling_rate)

    # Calculate combined parameters
    if self.values_before and self.values_after:
      self.values_before_after = self.values_before + [self.value] + self.values_after
      self.n_total = len(self.values_before_after)
      self.a_all, self.b_all, self.c_all = self.get_quadratic_params(self.x_time_before + [0] + self.x_time_after, self.values_before_after)

  def _calculate_prior_values(self, sampling_rate):
    self.value_before = self.data.loc[self.index - 1, self.column_name]
    self.difference_from_prior = self.value - self.value_before
    self.values_before = self.get_prior_values()
    self.prior_n = len(self.values_before)
    
    if self.prior_n > 0:
      self.duration_before = self.prior_n * sampling_rate
      self.mean_before = sum(self.values_before) / self.prior_n
      self.mean_change_before = self.value - self.mean_before
      self.std_before = statistics.stdev(self.values_before) if self.prior_n > 1 else np.nan
      self.duration_minutes_before = (self.current_time - self.data.loc[self.index - self.prior_n, self.datetime_column]).total_seconds() / 60
      
      self.x_time_before = [self.duration_minutes_before * (i - self.prior_n) / self.prior_n for i in range(self.prior_n)]
      self.a_pre, self.b_pre, self.c_pre = self.get_quadratic_params(self.x_time_before + [0], self.values_before + [self.value])

  def _calculate_post_values(self, sampling_rate):
    self.value_after = self.data.loc[self.index + 1, self.column_name]
    self.difference_from_next = self.value_after - self.value
    self.values_after = self.get_post_values()
    self.after_n = len(self.values_after)
    
    if self.after_n > 0:
      self.duration_after = self.after_n * sampling_rate
      self.mean_after = sum(self.values_after) / self.after_n
      self.mean_change_after = self.value - self.mean_after
      self.std_after = statistics.stdev(self.values_after) if self.after_n > 1 else np.nan
      self.duration_minutes_after = (self.data.loc[self.index + self.after_n, self.datetime_column] - self.current_time).total_seconds() / 60
      
      self.x_time_after = [self.duration_minutes_after * i / self.after_n for i in range(1, self.after_n + 1)]
      self.a_post, self.b_post, self.c_post = self.get_quadratic_params([0] + self.x_time_after, [self.value] + self.values_after)

  def get_prior_values(self):
    before = []
    for i in range(1, self.extension_range + 1):
      index = self.index - i
      if index in self.data.index:
        if 'device_turned_on' in self.data.columns:
          if self.data.loc[index, 'device_turned_on'] == 1:
            before.append(self.data.loc[index, self.column_name])
        else:
          before.append(self.data.loc[index, self.column_name])
    return before

  def get_post_values(self):
    after = []
    for i in range(1, self.extension_range + 1):
      index = self.index + i
      if index in self.data.index:
        if 'device_turned_on' in self.data.columns:
          if self.data.loc[index, 'device_turned_on'] == 1:
            after.append(self.data.loc[index, self.column_name])
        else:
          after.append(self.data.loc[index, self.column_name])
    return after

  @staticmethod
  def quadratic_model(x, a, b, c):
    return a * x**2 + b * x + c
    
  def get_quadratic_params(self, x, y):
    """ Fit a quadratic model to the given x and y data."""
    try:
      if len(y) > 5:
        params, _ = curve_fit(self.quadratic_model, np.array(x), np.array(y))
        return params[0], params[1], params[2]
      else:
        return np.nan, np.nan, np.nan
    except (ValueError, RuntimeError):
      return np.nan, np.nan, np.nan