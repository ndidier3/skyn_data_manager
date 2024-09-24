from ..Configuration.file_management import load_default_model
import numpy as np
import pandas as pd

def label_device_nonwear(df):
  device_worn_model = load_default_model('worn_vs_removed')

  # Initialize 'device_on_pred' to NaN and add a column to track the prediction strategy
  df['device_worn'] = np.nan  # Initialize as NaN
  df['prediction_strategy'] = np.nan  # Initialize as NaN

  # Filter only rows where the device was on (non-gap rows)
  non_gap_rows = df[df['device_turned_on'] == 1]

  # Identify rows where predictors or the Temp column have NaN values
  nan_indices = non_gap_rows[
      [col for col in df.columns if col in device_worn_model.predictors]
  ].isna().any(axis=1)

  valid_prediction_indices = ~nan_indices

  # Make predictions using the model where possible
  prediction_features = non_gap_rows.loc[valid_prediction_indices, [col for col in df.columns if col in device_worn_model.predictors]]
  predictions = device_worn_model.predict(prediction_features)
  df.loc[prediction_features.index, 'device_worn'] = predictions
  df.loc[prediction_features.index, 'prediction_strategy'] = 'model'

  # Apply temperature-based prediction fallback where model predictions are not available and temp is available
  temp_cutoff_indices = non_gap_rows.index[(non_gap_rows['temp'].notna()) & (df.loc[non_gap_rows.index, 'prediction_strategy'].isna())]
  df.loc[temp_cutoff_indices, 'device_worn'] = np.where(
      df.loc[temp_cutoff_indices, 'temp'] < 28, 0, 1
  )
  df.loc[temp_cutoff_indices, 'prediction_strategy'] = 'temp_cutoff'

  return df