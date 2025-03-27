def label_predictions_based_on_GT(df, ground_truth_column, prediction_column, prediction_correct_column, result_column):
  """assumes data is already filtered for device_turned_on == 1"""
  df[prediction_correct_column] = (df[ground_truth_column] == df[prediction_column]).astype(int)
  df[result_column] = df.apply(
      lambda row: (
          "True Positive" if row[ground_truth_column] == 0 and row[prediction_column] == 0 else
          "True Negative" if row[ground_truth_column] == 1 and row[prediction_column] == 1 else
          "False Positive" if row[ground_truth_column] == 1 and row[prediction_column] == 0 else
          "False Negative"
      ),
      axis=1
  )
  return df