from ..Skyn_Processors.skyn_datapoint import skynDatapoint
import numpy as np

def generate_row_features(skyn_dataset, include_tac = False):
  # Store original DataFrame
  df = skyn_dataset.dataset.copy()
  
  # Initialize lists for labels and features
  labels_off_on = []
  temp = []
  motion = []
  tac = []
  
  # Initialize device_on column
  df['device_on'] = ['unk' for _ in range(len(df))]

  # Populate temp, motion, and TAC features
  for i, row in df.iterrows():
    temp.append(skynDatapoint('Temperature_C', 'datetime', i, df, 10, skyn_dataset.sampling_rate, label=row['device_on'], use_after=True, use_before=True))
    motion.append(skynDatapoint('Motion', 'datetime', i, df, 10, skyn_dataset.sampling_rate, label=row['device_on'], use_after=True, use_before=True))
    tac.append(skynDatapoint('TAC', 'datetime', i, df, 10, skyn_dataset.sampling_rate, label=row['device_on'], use_after=True, use_before=True))
    labels_off_on.append(row['device_on'])

  # Assign labels and features directly to df
  def extract_feature_values(feature_list, prefix):
    df[f'{prefix}'] = [f.value if hasattr(f, 'value') else np.nan for f in feature_list]
    df[f'{prefix}_a_pre'] = [f.a_pre if hasattr(f, 'a_pre') else np.nan for f in feature_list]
    df[f'{prefix}_b_pre'] = [f.b_pre if hasattr(f, 'b_pre') else np.nan for f in feature_list]
    df[f'{prefix}_c_pre'] = [f.c_pre if hasattr(f, 'c_pre') else np.nan for f in feature_list]
    df[f'{prefix}_a_post'] = [f.a_post if hasattr(f, 'a_post') else np.nan for f in feature_list]
    df[f'{prefix}_b_post'] = [f.b_post if hasattr(f, 'b_post') else np.nan for f in feature_list]
    df[f'{prefix}_c_post'] = [f.c_post if hasattr(f, 'c_post') else np.nan for f in feature_list]
    df[f'{prefix}_mean_change_pre'] = [f.mean_change_before if hasattr(f, 'mean_change_before') else np.nan for f in feature_list]
    df[f'{prefix}_mean_change_post'] = [f.mean_change_after if hasattr(f, 'mean_change_after') else np.nan for f in feature_list]
    df[f'{prefix}_change_pre'] = [f.difference_from_prior if hasattr(f, 'difference_from_prior') else np.nan for f in feature_list]
    df[f'{prefix}_change_post'] = [f.difference_from_next if hasattr(f, 'difference_from_next') else np.nan for f in feature_list]

  extract_feature_values(temp, 'temp')
  extract_feature_values(motion, 'motion')
  if include_tac:
    extract_feature_values(tac, 'tac')

  # Set all new columns to NaN where device_turned_on == 0
  if 'device_turned_on' in df.columns:
    columns_to_nan = [
      'temp', 'temp_a_pre', 'temp_b_pre', 'temp_c_pre', 'temp_a_post', 'temp_b_post', 'temp_c_post', 'temp_mean_change_pre', 'temp_mean_change_post', 'temp_change_pre', 'temp_change_post',
      'motion', 'motion_a_pre', 'motion_b_pre', 'motion_c_pre', 'motion_a_post', 'motion_b_post', 'motion_c_post', 'motion_mean_change_pre', 'motion_mean_change_post', 'motion_change_pre', 'motion_change_post',
    ]
    if include_tac:
      columns_to_nan = columns_to_nan + ['tac', 'tac_a_pre', 'tac_b_pre', 'tac_c_pre', 'tac_a_post', 'tac_b_post', 'tac_c_post', 'tac_mean_change_pre', 'tac_mean_change_post', 'tac_change_pre', 'tac_change_post']
    df.loc[df['device_turned_on'] == 0, columns_to_nan] = np.nan

  return df

