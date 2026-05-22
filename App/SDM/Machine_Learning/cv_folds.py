import pandas as pd
import numpy as np
from sklearn.model_selection import GroupKFold

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


def get_group_kfold_cv_indices(df: pd.DataFrame, grouping_variable: str, n_splits: int):
  """
  Participant-level (group-level) K-fold: each fold's holdout contains rows from disjoint groups
  (e.g. participants). Same group never appears in both train and test within a fold.

  Uses sklearn ``GroupKFold``. Effective number of folds is ``min(n_splits, n_unique_groups)``.

  Returns:
    list[dict]: Each dict has ``training`` and ``holdout`` as lists of row index labels (``df.index``).
  """
  n_groups = df[grouping_variable].nunique()
  n_splits = int(min(n_splits, n_groups))
  if n_splits < 2:
    raise ValueError(
      f"group_kfold requires at least 2 groups with id {grouping_variable!r}; got {n_groups}."
    )

  gkf = GroupKFold(n_splits=n_splits)
  X_dummy = np.zeros((len(df), 1))
  y_dummy = np.zeros(len(df))
  groups = df[grouping_variable].to_numpy()
  index_np = df.index.to_numpy()

  fold_splits = []
  for train_pos, test_pos in gkf.split(X_dummy, y_dummy, groups):
    fold_splits.append({
      'training': index_np[train_pos].tolist(),
      'holdout': index_np[test_pos].tolist(),
    })
  return fold_splits
