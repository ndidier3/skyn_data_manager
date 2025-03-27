import pandas as pd
from App.SDM.Configuration.configuration import get_closest_index_with_timestamp

def label_time_windows(df, start_time, end_time, column_name):
  """ if column does not exist, it will be created with all values as 1,
   then will label values as 0 within the requested timeframe """
  
  if column_name not in df.columns:
    df[column_name] = 1

  datetime_min = df['datetime'].min()
  datetime_max = df['datetime'].max()
  if (datetime_min <= start_time <= datetime_max) and (datetime_min <= end_time <= datetime_max):
    df.loc[(df['datetime'] >= start_time) & (df['datetime'] <= end_time), column_name] = 0

  return df

