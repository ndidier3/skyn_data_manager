import pandas as pd

def label_signal_stability(df):

  # Identify indices where the device is worn
  device_worn_indices = df[df['device_worn'] == 1].index

  # Setting new column tac_mean_deviance
  df['tac_mean_dev'] = pd.NA
  df['tac_deviation_from_prior_values'] = pd.NA

  # Loop through indices where the device is worn
  for idx in device_worn_indices:

    # Capture recent values when the device is worn
    recent_values = df.loc[max(0, idx - 10):idx - 1]
    recent_values = recent_values[recent_values['device_worn'] == 1]['TAC']

    if len(recent_values) >= 5:
      mean_value = recent_values.mean()
      tac_mean_deviances = (recent_values - mean_value).abs()  # Calculate absolute deviations
      tac_mean_deviance = tac_mean_deviances.mean()  # Mean of the absolute deviations
      df.at[idx, 'tac_mean_dev'] = tac_mean_deviance

      # Calculate the deviation of the current TAC from the mean of prior values
      current_tac = df.at[idx, 'TAC']
      tac_deviation_from_prior_values = current_tac - mean_value  # Deviation from the mean
      df.at[idx, 'tac_deviation_from_prior_values'] = tac_deviation_from_prior_values

  unstable = (df['tac_mean_dev'] > 20) | (df['tac_deviation_from_prior_values'] > 20)
  na_mask = df['tac_mean_dev'].isna()
  
  # Initialize the signal_stable column
  df['signal_stable'] = pd.NA

  # Update signal_stable only for indices where device is worn
  # Set unstable (0) for worn devices that are unstable and have valid metrics
  df.loc[(df['device_worn'] == 1) & (~na_mask) & (unstable), 'signal_stable'] = 0

  # Set stable (1) for worn devices that are stable and have valid metrics
  df.loc[(df['device_worn'] == 1) & (~na_mask) & (~unstable), 'signal_stable'] = 1
  
  return df

def label_signal_stability_when_device_equipped(df):
  df['signal_stable_start'] = pd.NA

  # Identify indices where the device was re-equipped (0 to 1)
  device_reactivated = df[
      ((df['device_worn'].shift(1) == 0) & (df['device_worn'] == 1)) |
      ((df['device_turned_on'].shift(1) == 0) & (df['device_turned_on'] == 1))
  ].index

  # Loop through the indices where the device was re-equipped
  for idx in device_reactivated:
      current_idx = idx
      first_non_null = True

      while current_idx < len(df):
          # Check the signal stability value
          signal_stable = df.at[current_idx, 'signal_stable']
          
          if df.at[current_idx, 'device_worn'] == 0 or df.at[current_idx, 'device_turned_on'] == 0:
            break
          elif pd.isna(signal_stable):
            # If it's null, move to the next index
            current_idx += 1
            continue
          else:
            if signal_stable == 1:
              if first_non_null:
                df.loc[idx:current_idx, 'signal_stable_start'] = 1  # Set prior indices to 1
              else:
                df.at[current_idx, 'signal_stable_start'] = 0
              break  # Stop after the first non-null metric passing criteria

            elif signal_stable == 0:
              df.at[current_idx, 'signal_stable_start'] = 0  # Only set current index to 0
              first_non_null = False
              current_idx += 1

  return df
