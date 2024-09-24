import pandas as pd
from datetime import timedelta, datetime

def get_day_level_indices(df, day_start_hour = 7):

  # Define the split hour (modifiable), e.g., 7 for a 7:00 AM start of the day
  split_hour = day_start_hour # Use a simple integer to represent the start hour of the day
  minute = 0  # Default minutes set to 0

  # Extract unique days from the datetime column
  unique_days = df['datetime'].dt.date.unique().tolist()

  # Add the day before the first day to capture early hours before the first split time
  day_before = unique_days[0] - timedelta(days=1)
  unique_days = [day_before] + unique_days

  # List to store start and end indices of each "day"
  day_start_end_indices = []

  # Loop through each unique day and determine start and end indices
  for i in range(len(unique_days) - 1):
      # Define the start and end times based on the split hour
      current_day = unique_days[i]
      next_day = unique_days[i + 1]
      
      start = datetime(current_day.year, current_day.month, current_day.day, split_hour, minute)
      end = datetime(next_day.year, next_day.month, next_day.day, split_hour, minute)

      # Get data between the start and end times
      data = df[(df['datetime'] >= start) & (df['datetime'] < end)]
      
      # Capture indices if data exists
      if not data.empty:
          start_idx = data.index.min()
          end_idx = data.index.max()
          day_start_end_indices.append((start_idx, end_idx))

  # If the last day is incomplete or shorter than 24 hours, capture its indices
  last_day_start = datetime(unique_days[-1].year, unique_days[-1].month, unique_days[-1].day, split_hour, minute)
  if not df[df['datetime'] >= last_day_start].empty:
      last_start_idx = df[df['datetime'] >= last_day_start].index.min()
      last_end_idx = df.index.max()
      day_start_end_indices.append((last_start_idx, last_end_idx))
  
  return day_start_end_indices

def create_day_level_dataframe(skyn_days):
  data = [{attr: value for attr, value in day.__dict__.items() if attr != 'day_dataset'} for day in skyn_days]

  return pd.DataFrame(data)