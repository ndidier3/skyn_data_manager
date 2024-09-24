from SDM.Skyn_Processors.skyn_datapoint import skynDatapoint
import numpy as np

def generate_row_features(skyn_dataset):
  # Store original DataFrame
  df = skyn_dataset.dataset.copy()
  
  # Initialize lists for labels and features
  labels_off_on = []
  temp = []
  motion = []
  
  # Create a boolean mask for rows where device is turned on
  # if 'device_turned_on' in df.columns:
  #   mask = df['device_turned_on'] == 1
  # else:
  #   mask = [True] * len(df)  # If column doesn't exist, use all rows

  # Initialize device_on column
  df['device_on'] = ['unk' for _ in range(len(df))]

  # Populate temp and motion features
  for i, row in df.iterrows():
    temp.append(skynDatapoint('Temperature_C', 'datetime', i, df, 10, skyn_dataset.sampling_rate, label=row['device_on'], use_after=True, use_before=True))
    motion.append(skynDatapoint('Motion', 'datetime', i, df, 10, skyn_dataset.sampling_rate, label=row['device_on'], use_after=True, use_before=True))
    labels_off_on.append(row['device_on'])

  # Assign labels and features directly to df
  df['temp'] = [t.value if hasattr(t, 'value') else np.nan for t in temp]
  df['temp_a_pre'] = [t.a_pre if hasattr(t, 'a_pre') else np.nan for t in temp]
  df['temp_b_pre'] = [t.b_pre if hasattr(t, 'b_pre') else np.nan for t in temp]
  df['temp_c_pre'] = [t.c_pre if hasattr(t, 'c_pre') else np.nan for t in temp]
  df['temp_a_post'] = [t.a_post if hasattr(t, 'a_post') else np.nan for t in temp]
  df['temp_b_post'] = [t.b_post if hasattr(t, 'b_post') else np.nan for t in temp]
  df['temp_c_post'] = [t.c_post if hasattr(t, 'c_post') else np.nan for t in temp]
  df['temp_mean_change_pre'] = [t.mean_change_before if hasattr(t, 'mean_change_before') else np.nan for t in temp]
  df['temp_mean_change_post'] = [t.mean_change_after if hasattr(t, 'mean_change_after') else np.nan for t in temp]
  df['temp_change_pre'] = [t.difference_from_prior if hasattr(t, 'difference_from_prior') else np.nan for t in temp]
  df['temp_change_post'] = [t.difference_from_next if hasattr(t, 'difference_from_next') else np.nan for t in temp]
  df['motion'] = [m.value if hasattr(m, 'value') else np.nan for m in motion]
  df['motion_a_pre'] = [m.a_pre if hasattr(m, 'a_pre') else np.nan for m in motion]
  df['motion_b_pre'] = [m.b_pre if hasattr(m, 'b_pre') else np.nan for m in motion]
  df['motion_c_pre'] = [m.c_pre if hasattr(m, 'c_pre') else np.nan for m in motion]
  df['motion_a_post'] = [m.a_post if hasattr(m, 'a_post') else np.nan for m in motion]
  df['motion_b_post'] = [m.b_post if hasattr(m, 'b_post') else np.nan for m in motion]
  df['motion_c_post'] = [m.c_post if hasattr(m, 'c_post') else np.nan for m in motion]
  df['motion_mean_change_pre'] = [m.mean_change_before if hasattr(m, 'mean_change_before') else np.nan for m in motion]
  df['motion_mean_change_post'] = [m.mean_change_after if hasattr(m, 'mean_change_after') else np.nan for m in motion]
  df['motion_change_pre'] = [m.difference_from_prior if hasattr(m, 'difference_from_prior') else np.nan for m in motion]
  df['motion_change_post'] = [m.difference_from_next if hasattr(m, 'difference_from_next') else np.nan for m in motion]

  # Set all new columns to NaN where device_turned_on == 0
  if 'device_turned_on' in df.columns:
    columns_to_nan = [
      'temp', 'temp_a_pre', 'temp_b_pre', 'temp_c_pre', 
      'temp_a_post', 'temp_b_post', 'temp_c_post', 
      'temp_mean_change_pre', 'temp_mean_change_post', 
      'temp_change_pre', 'temp_change_post', 
      'motion', 'motion_a_pre', 'motion_b_pre', 'motion_c_pre', 
      'motion_a_post', 'motion_b_post', 'motion_c_post', 
      'motion_mean_change_pre', 'motion_mean_change_post', 
      'motion_change_pre', 'motion_change_post'
    ]
    df.loc[df['device_turned_on'] == 0, columns_to_nan] = np.nan

  return df
