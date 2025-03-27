import pandas as pd
import numpy as np

def count_longest_tac_flatline(df, tac_variable='TAC', threshold=10, tolerance=0.1):
  flatline_mask = (
    df[tac_variable].shift().sub(df[tac_variable]).abs() <= tolerance
  ) & (df[tac_variable] > threshold)
  streak_lengths = (flatline_mask != flatline_mask.shift()).cumsum()
  streak_data = flatline_mask.groupby(streak_lengths).sum()
  return streak_data.max()

def count_longest_consecutive_non_wear(df, variable = 'device_worn_model'):
  df['non_wear_group'] = (df[variable] != 0).cumsum()
  non_wear_lengths = df[df[variable] == 0].groupby('non_wear_group').size()
  longest_non_wear = non_wear_lengths.max() if not non_wear_lengths.empty else 0
  df.drop(columns=['non_wear_group'], inplace=True)
  return longest_non_wear

def count_longest_consecutive_below(df, variable='TAC', X=-10):
    mask = df[variable] <= X 
    df.loc[:, 'sub_negative'] = (mask != mask.shift()).cumsum() * mask
    sub_negative_lengths = df[mask].groupby('sub_negative').size()
    longest_sub_negative_streak = sub_negative_lengths.max() if not sub_negative_lengths.empty else 0
    df = df.loc[:, df.columns != 'sub_negative']
    return longest_sub_negative_streak

def get_low_quality_duration(df):
  return ((df['jump']) | (df['plummet']) | (df['device_worn_model']==0) | (df['device_turned_on'] == 0)).sum() / 60

def get_low_quality_percent(df):
  return ((df['jump']) | (df['plummet']) | (df['device_worn_model']==0) | (df['device_turned_on'] == 0)).sum() / len(df)

def get_unimputed_low_quality_duration(df):
  return (((df['jump']) | (df['plummet']) | (df['device_worn_model']==0) | (df['device_turned_on'] == 0)) & (~df['imputed'])).sum() / 60

def get_unimputed_low_quality_percent(df):
  return (((df['jump']) | (df['plummet']) | (df['device_worn_model']==0) | (df['device_turned_on'] == 0)) & (~df['imputed'])).sum() / len(df)
     