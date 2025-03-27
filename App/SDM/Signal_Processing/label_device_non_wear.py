from ..Configuration.file_management import import_model
import numpy as np
import pandas as pd

""" self report non-wear labeling should be added in this file """
def label_device_non_wear_using_cutoff(df, temp_cutoff=28, include_temp_in_col_name = False):
  
  col = f'device_worn_temp_cutoff_{temp_cutoff}' if include_temp_in_col_name else 'device_worn_temp_cutoff'
  df[col] = np.nan

  # Filter only rows where the device was on (non-gap rows)
  non_gap_rows = df['device_turned_on'] == 1

  df.loc[non_gap_rows, col] = np.where(
    df.loc[non_gap_rows, 'temp'] < temp_cutoff, 0, 1
  )
  return df

def label_device_non_wear_using_model(df):
  df['device_worn_model'] = np.nan
  df['pred_method'] = np.nan

  # Filter only rows where the device was on (non-gap rows)
  non_gap_rows = df[df['device_turned_on'] == 1]

  # Import models
  device_worn_model = import_model(name='RF_non_wear_CSDP')
  device_worn_model_pre_gap = import_model(name='RF_non_wear_CSDP_pre_gap')
  device_worn_model_post_gap = import_model(name='RF_non_wear_CSDP_post_gap')
  device_worn_model_between_gaps = import_model(name='RF_non_wear_CSDP_between_gaps')

  # Identify feature sets
  all_features = [col for col in df.columns if col in device_worn_model.predictors]
  pre_features = [col for col in df.columns if col in device_worn_model_pre_gap.predictors]
  post_features = [col for col in df.columns if col in device_worn_model_post_gap.predictors]
  between_features = [col for col in df.columns if col in device_worn_model_between_gaps.predictors]

  # Identify where various models can make predictions
  nan_indices = non_gap_rows[all_features].isna().any(axis=1) #
  pre_nan_indices = non_gap_rows[pre_features].isna().any(axis=1) #pre model can't be used
  post_nan_indices = non_gap_rows[post_features].isna().any(axis=1) #post model can't be used

  # Identify indices for each model
  indices_complete_model = non_gap_rows.loc[~nan_indices].index  # No NaNs, use complete model
  remaining_indices = non_gap_rows.loc[nan_indices].index  # Rows where the complete model cannot be used

  indices_post_gap_list = non_gap_rows.loc[
    (non_gap_rows.index.isin(remaining_indices)) & (pre_nan_indices & ~post_nan_indices)
  ].index.tolist()

  indices_pre_gap_list = non_gap_rows.loc[
      (non_gap_rows.index.isin(remaining_indices)) & (post_nan_indices & ~pre_nan_indices)
  ].index.tolist()

  indices_between_gaps_list = non_gap_rows.loc[
      (non_gap_rows.index.isin(remaining_indices)) & (pre_nan_indices & post_nan_indices)
  ].index.tolist()

  print('INDICES FOR SECONDARY NON WEAR MODELS')
  print(indices_pre_gap_list)
  print(indices_post_gap_list)
  print(indices_between_gaps_list)

  feature_data_for_complete_model = non_gap_rows.loc[indices_complete_model, all_features]
  feature_data_for_pre_gap = non_gap_rows.loc[indices_pre_gap_list, pre_features]
  feature_data_for_post_gap = non_gap_rows.loc[indices_post_gap_list, post_features]
  feature_data_for_between_gaps = non_gap_rows.loc[indices_between_gaps_list, between_features]

  if not feature_data_for_complete_model.empty:
    # Make predictions using the model where possible
    predictions = device_worn_model.predict(feature_data_for_complete_model)
    df.loc[feature_data_for_complete_model.index, 'device_worn_model'] = predictions
    df.loc[feature_data_for_complete_model.index, 'pred_method'] = 'complete_model'

  # Make predictions using the pre_gap model
  if not feature_data_for_pre_gap.empty:
    predictions = device_worn_model_pre_gap.predict(feature_data_for_pre_gap)
    df.loc[feature_data_for_pre_gap.index, 'device_worn_model'] = predictions
    df.loc[feature_data_for_pre_gap.index, 'pred_method'] = 'pre_gap_model'

  # Make predictions using the post_gap model
  if not feature_data_for_post_gap.empty:
    predictions = device_worn_model_post_gap.predict(feature_data_for_post_gap)
    df.loc[feature_data_for_post_gap.index, 'device_worn_model'] = predictions
    df.loc[feature_data_for_post_gap.index, 'pred_method'] = 'post_gap_model'

  # Make predictions using the between_gaps model
  if not feature_data_for_between_gaps.empty:
    predictions = device_worn_model_between_gaps.predict(feature_data_for_between_gaps)
    df.loc[feature_data_for_between_gaps.index, 'device_worn_model'] = predictions
    df.loc[feature_data_for_between_gaps.index, 'pred_method'] = 'between_gaps_model'

  # # Apply temperature-based prediction fallback where model predictions are not available and temp is available
  # temp_cutoff_indices = non_gap_rows.index[(non_gap_rows['temp'].notna()) & (df.loc[non_gap_rows.index, 'pred_method'].isna())]

  # if not temp_cutoff_indices.empty:
  #   df.loc[temp_cutoff_indices, 'device_worn_model'] = np.where(
  #     df.loc[temp_cutoff_indices, 'temp'] < 28, 0, 1
  #   )
  #   df.loc[temp_cutoff_indices, 'pred_method'] = 'temp_cutoff'

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

