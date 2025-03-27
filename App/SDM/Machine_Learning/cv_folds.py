import pandas as pd
import numpy as np
from sklearn.model_selection import BaseCrossValidator

def get_indices_within_group_folding(df: pd.DataFrame, grouping_variable, folds=3):
  """
  Performs group-based K-fold splitting, ensuring that all instances of a group 
  appear together in either the training or holdout set for each fold.

  Args:
    df (pd.DataFrame): The input dataframe containing data to be split.
    grouping_variable (str): The column name used for grouping data.
    folds (int): The number of folds for splitting (default is 3).

  Returns:
    list[dict]: A list of dictionaries, each representing a fold with:
      - 'training': List of row indices used for training.
      - 'holdout': List of row indices used for holdout (validation/testing).
  """

  unique_groups = df[grouping_variable].unique()
  fold_splits = [{'training': [], 'holdout': []} for _ in range(folds)]
  
  for group in unique_groups:
    subset = df[df[grouping_variable] == group]
    subset_indices = subset.index.to_list()
    
    if len(subset) >= folds:
      for i, idx in enumerate(subset_indices):
        fold_idx = i % folds
        fold_splits[fold_idx]['holdout'].append(idx)
        for j, split in enumerate(fold_splits):
          if j != fold_idx:
            split['training'].append(idx)
    else:
      for split in fold_splits:
        split['training'].extend(subset_indices)  # groups smaller than number of folds only go to training
  
  return fold_splits

def get_leave_group_out_cv_indices(df: pd.DataFrame, grouping_column='device_id'):
  unique_groups = df[grouping_column].unique()
  fold_splits = []
  for group in unique_groups:
    holdout_group_indices = df[df[grouping_column] == group].index.tolist()
    training_group_indices = df[df[grouping_column] != group].index.tolist()  # Fixed ordering
    fold_splits.append({'training': training_group_indices, 'holdout': holdout_group_indices})
  return fold_splits
