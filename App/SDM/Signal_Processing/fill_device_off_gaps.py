import pandas as pd
from datetime import timedelta

def fill_device_off_gaps(df):
  
  # Calculate the time difference (between each row)
  df['time_diff'] = df['datetime'].diff().dt.total_seconds()

  df['device_turned_on'] = 1

  df['gap'] = pd.cut(
    df['time_diff'], 
    bins=[0, 119, float('inf')],
    labels=[0, 1],
    include_lowest=True
  )

  rows_to_add = []

  # Iterate through the DataFrame to identify and fill "big_gap" sections
  for i, row in df.iterrows():
    if row['gap'] == 1 and i > 0:
      # Get the start and end datetimes of the gap
      start_time = df.loc[i - 1, 'datetime']
      end_time = row['datetime']

      # Generate a range of datetimes, one per minute, between the start and end times
      new_times = pd.date_range(start=start_time + timedelta(minutes=1), end=end_time - timedelta(minutes=1), freq='T')

      # For each generated datetime, create a new row with specified columns
      for new_time in new_times:
        new_row = {
          'SubID': row['SubID'],
          'Dataset_Identifier': row['Dataset_Identifier'],
          'Episode_Identifier': row['Episode_Identifier'],
          'Full_Identifier': row['Full_Identifier'],
          'Row_ID': None,  # Temporary value; will be updated later
          'email': row['email'],
          'datetime': new_time,
          'device_id': row['device_id'],
          'device_turned_on': 0
        }
        # Add the new row to the list of rows to add
        rows_to_add.append(new_row)

  # Convert the list of new rows into a DataFrame
  new_rows_df = pd.DataFrame(rows_to_add)

  # Append the new rows to the original DataFrame
  df = pd.concat([df, new_rows_df]).sort_values(by='datetime').reset_index(drop=True)

  # Update Row_ID for all rows using Full_Identifier and the new index
  df['Row_ID'] = df['Full_Identifier'].astype(str) + '_' + df.index.astype(str)

  # Drop the temporary 'time_diff' column
  df.drop(columns=['time_diff', 'gap'], inplace=True)

  return df
