from ..Configuration.file_management import load_default_model
import numpy as np
import pandas as pd

""" self report non-wear labeling should be added in this file """

def label_device_nonwear_using_cutoff(df, temp_cutoff=28):
  df['device_worn_temp_cutoff'] = np.nan

  # Filter only rows where the device was on (non-gap rows)
  non_gap_rows = df['device_turned_on'] == 1

  df.loc[non_gap_rows, 'device_worn_temp_cutoff'] = np.where(
    df.loc[non_gap_rows, 'temp'] < temp_cutoff, 0, 1
  )
  return df

def label_device_nonwear_using_model(df):

  df['device_worn_model'] = np.nan
  df['pred_method'] = np.nan

  # Filter only rows where the device was on (non-gap rows)
  non_gap_rows = df[df['device_turned_on'] == 1]

  device_worn_model = load_default_model('worn_vs_removed')
  # Identify rows where predictors or the Temp column have NaN values
  nan_indices = non_gap_rows[
    [col for col in df.columns if col in device_worn_model.predictors]
  ].isna().any(axis=1)

  valid_prediction_indices = ~nan_indices

  # Check if there are any valid rows for prediction
  prediction_features = non_gap_rows.loc[valid_prediction_indices, [col for col in df.columns if col in device_worn_model.predictors]]
  
  if not prediction_features.empty:
    # Make predictions using the model where possible
    predictions = device_worn_model.predict(prediction_features)
    df.loc[prediction_features.index, 'device_worn_model'] = predictions
    df.loc[prediction_features.index, 'pred_method'] = 'model'

  # Apply temperature-based prediction fallback where model predictions are not available and temp is available
  temp_cutoff_indices = non_gap_rows.index[(non_gap_rows['temp'].notna()) & (df.loc[non_gap_rows.index, 'pred_method'].isna())]

  if not temp_cutoff_indices.empty:
    df.loc[temp_cutoff_indices, 'device_worn_model'] = np.where(
      df.loc[temp_cutoff_indices, 'temp'] < 28, 0, 1
    )
    df.loc[temp_cutoff_indices, 'pred_method'] = 'temp_cutoff'

  return df

def compare_non_wear_methods(df, compare_col, truth_col, comparison_name = 'cutoff_vs_model'):

  df[f'FP_{comparison_name}'] = ((df[compare_col] == 1) & (df[truth_col] == 0)).astype(int)
  df[f'FN_{comparison_name}'] = ((df[compare_col] == 0) & (df[truth_col] == 1)).astype(int)
  df[f'DISAGREE_{comparison_name}'] = (df[compare_col] != df[truth_col]).astype(int)

  for col in [f'FP_{comparison_name}', f'FN_{comparison_name}', f'DISAGREE_{comparison_name}']:
    df.loc[
      df['device_turned_on'] == 0, col
    ] = np.nan

  return df

