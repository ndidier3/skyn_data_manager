import pandas as pd
import numpy as np
from datetime import timedelta
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, ConstantKernel

def identify_and_fill_gaps(df, threshold=30, min_pass_count_before_imputable_gap = 15, min_pass_count_after_imputable_gap = 15):
  """threshold must be >15 and <60"""
  
  # Calculate the time difference (between each row)
  df['time_diff'] = df['datetime'].diff().dt.total_seconds()

  df['gap'] = pd.cut(
    df['time_diff'], 
    bins=[0, 120, threshold*60, float('inf')],
    labels=['pass', 'imputable_gap', 'big_gap'],
    include_lowest=True
  )
  for i, row in df.iterrows():
    if row['gap'] == 'imputable_gap':
      # Check 'pass' values before the imputable_gap
      pre_pass_count = df.iloc[max(0, i - min_pass_count_before_imputable_gap):i]['gap'].eq('pass').sum()

      # Check 'pass' values after the imputable_gap
      post_pass_count = df.iloc[i + 1:min(i + (min_pass_count_after_imputable_gap+1), len(df))]['gap'].eq('pass').sum()

      # If not enough 'pass' values are found on either side, relabel as 'big_gap'
      if pre_pass_count < min_pass_count_before_imputable_gap or post_pass_count < min_pass_count_after_imputable_gap:
        df.at[i, 'gap'] = 'big_gap'

  rows_to_add = []

  # Iterate through the DataFrame to identify and fill "big_gap" sections
  for i, row in df.iterrows():
    if row['gap'] in ['big_gap', 'imputable_gap'] and i > 0:
      # Get the start and end datetimes of the big gap
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
          'gap': row['gap']
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
  df.drop(columns=['time_diff'], inplace=True)

  # Calculate 'Duration_Hrs' as hours passed since the first datetime value
  df['Duration_Hrs'] = (df['datetime'] - df['datetime'].iloc[0]).dt.total_seconds() / 3600

  # Create the 'gap_imputed' column with initial values set to 0
  df['gap_imputed'] = 0

  imputable_mask = df['gap'] == 'imputable_gap'

  # Identify contiguous blocks of imputable gaps
  imputable_blocks = (imputable_mask != imputable_mask.shift()).cumsum()
  gap_blocks = df[imputable_mask].groupby(imputable_blocks)

  # Process each block of imputable gaps
  # Process each block of imputable gaps
  for _, gap_block in gap_blocks:
    start_index = gap_block.index[0]
    end_index = gap_block.index[-1]

    # Define the boundaries for the training data (only 15 before and after the gap)
    front_index = max(0, start_index - 15)
    back_index = min(len(df) - 1, end_index + 15)

    # Define training data excluding missing values
    training_data = df.loc[front_index:back_index][~pd.isna(df['TAC'])]
    if len(training_data) > 0:  # Only proceed if there's data to train on
      x = training_data['Duration_Hrs']
      y = training_data['TAC']
      x_with_gap = df.loc[start_index:end_index, 'Duration_Hrs']

      # Define kernel and fit the model
      kernel = Matern(length_scale=0.4, nu=0.3, length_scale_bounds=(1e-3, 1e3)) * ConstantKernel(constant_value=5)
      model = GaussianProcessRegressor(kernel=kernel, random_state=0).fit(x.to_numpy().reshape(-1, 1), y)

      # Make predictions
      predictions = model.predict(x_with_gap.to_numpy().reshape(-1, 1))

      # Insert predictions back into the DataFrame for the imputed indices
      df.loc[start_index:end_index, 'TAC'] = predictions
      df.loc[start_index:end_index, 'gap_imputed'] = 1

  # Return the modified DataFrame
  return df

