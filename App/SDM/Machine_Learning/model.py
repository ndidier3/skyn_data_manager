from App.SDM.Machine_Learning.model_optimization import *
from App.SDM.Machine_Learning.cv_folds import * 
from App.SDM.Machine_Learning.get_feature_importances import get_feature_importances
from App.SDM.Machine_Learning.metrics import *
# from statsmodels.formula.api import mixedlm  # Add this import for mixed-effects model
from sklearn.model_selection import GroupKFold
import pandas as pd
import numpy as np

class Model:
  def __init__(self, model, name, predictors, outcome, grouping_column=None):
    self.model = model
    self.model_name = name
    self.predictors = predictors
    self.outcome = outcome
    self.grouping_column = grouping_column
    self.best = None
    self.current_model = None
    self.optimized = False
    self.metrics = {}
    self.results_df = pd.DataFrame()

  def fit_cv(self, X, y, fold_method = 'within_person', n_folds = 3):
    """
    Perform cross-validation, which can handle both binary and multiclass classifications.
    It ensures that each participant contributes to both training and testing for multi-class problems,
    while using appropriate metrics for binary classification.
    """
    self.results_df = X.copy()
    split_metrics = []

    is_binary = len(y.unique()) == 2 
    is_multi_class = len(y.unique()) > 2 and (y.dtype == 'O' or isinstance(y, pd.Categorical))
    is_continuous = y.dtype in ['float64', 'int64'] and len(y.unique()) > 2  
    
    """ Retrieving CV fold indices """
    if fold_method == 'within_person':
      folds = get_indices_within_group_folding(X, self.grouping_column, folds = n_folds)
      for fold_n in range(n_folds):
        self.results_df[f'y_true_{fold_n}'] = np.nan
        self.results_df[f'y_pred_{fold_n}'] = np.nan
    elif fold_method == 'by_device':
      folds = get_leave_group_out_cv_indices(X, self.grouping_column)
      for fold_n in range(len(folds)):
        self.results_df[f'y_true_{fold_n}'] = np.nan
        self.results_df[f'y_pred_{fold_n}'] = np.nan

    for fold_n, fold in enumerate(folds):
      train_idx = fold['training']
      test_idx = fold['holdout']
      # Split data
      X_train, X_holdout = X.loc[train_idx], X.loc[test_idx]
      y_train, y_holdout = y.loc[train_idx], y.loc[test_idx]

      # Fit model (handling for mixed-effects model)
      if "MixedLM" in self.model_name:
        """ Used when grouping variable is included as predictor to enhance within-person understanding """
        print('Not Available')
        # X_train_with_y = X_train.copy()
        # X_train_with_y[self.outcome] = y_train 
        # formula = f"{self.outcome} ~ {' + '.join(self.predictors)}"
        # self.model = mixedlm(formula, X_train_with_y, groups=X_train_with_y[self.grouping_column])
        # self.current_model = self.model.fit()  # Fit the mixed-effects model

        # X_holdout_with_y = X_holdout.copy()
        # X_holdout_with_y[self.outcome] = y_holdout  # Ensure outcome variable is included for prediction
        # y_pred = self.current_model.predict(X_holdout_with_y)
        # y_prob = []

      else:
        #currently assumes RF -- may need adjustment later
        grid = create_rf_search_grid(n_splits=n_folds, group_kfold=False)
        grid.fit(
          X_train[[col for col in X_train.columns if col != self.grouping_column]],
          y_train
        )
        self.current_model = grid.best_estimator_
        self.current_model.fit(
          X_train[[col for col in X_train.columns if col != self.grouping_column]],
          y_train
        )

        X_holdout_features = X_holdout[[col for col in X_holdout.columns if col != self.grouping_column]]
        y_pred = self.current_model.predict(X_holdout_features)
        y_prob = self.current_model.predict_proba(X_holdout_features)[:, 1] if is_binary else self.current_model.predict_proba(X_holdout_features)

      # Save predictions  
      self.results_df.loc[test_idx, f'y_true_{fold_n}'] = y_holdout.values
      self.results_df.loc[test_idx, f'y_pred_{fold_n}'] = y_pred
      if len(y_prob):
        self.results_df.loc[test_idx, f'y_prob_{fold_n}'] = y_prob

      if is_binary:
        split_metrics.append(compute_binary_metrics(y_holdout, y_pred, y_prob=y_prob))
      elif is_multi_class:
        split_metrics.append(compute_classification_metrics(y_holdout, y_pred, y_prob=y_prob))
      elif is_continuous:
        split_metrics.append(compute_regression_metrics(y_holdout, y_pred))

    #updating results df to have aggregate pred/prob columns
    self.results_df['y_pred_all'] = self.results_df[
        [col for col in self.results_df.columns if 'y_pred_' in col]
      ].bfill(axis=1).iloc[:, 0]

    if any(['y_prob' in col for col in self.results_df.columns]):
      self.results_df['y_prob_all'] = self.results_df[
          [col for col in self.results_df.columns if 'y_prob_' in col]
        ].bfill(axis=1).iloc[:, 0]

    X_all = X[[col for col in X.columns if col != self.grouping_column]]
    if is_binary:
      y_prob = self.current_model.predict_proba(X_all)[:, 1]
      total_metrics = compute_binary_metrics(y, self.results_df['y_pred_all'], self.results_df['y_prob_all'])
    elif is_multi_class:
      y_prob = self.current_model.predict_proba(X_all)
      total_metrics = compute_classification_metrics(y, self.results_df['y_pred_all'], self.results_df['y_prob_all'])
    elif is_continuous:
      valid_idx = self.results_df['y_pred_all'].notnull()
      filtered_y_pred = self.results_df.loc[valid_idx, 'y_pred_all']
      filtered_y = y.loc[valid_idx]
      total_metrics = compute_regression_metrics(filtered_y, filtered_y_pred)

    self.metrics = {
      'split_metrics': split_metrics,
      'total_metrics': total_metrics
    }

  def predict(self, X):
    predictions = self.best.predict(X)
    return predictions[0] if len(predictions) == 1 else predictions

  def get_metrics_group_cv(self):
    split_metrics_df = pd.DataFrame(self.metrics['split_metrics'])
    avg_metrics_df = pd.DataFrame([self.metrics['total_metrics']])
    return split_metrics_df, avg_metrics_df
  
  def get_feature_importance_mdi(self):
    return get_feature_importances(self.best, self.predictors)
  
  def fit_best_model(self, X, y, n_splits):
    """
    Find the optimal model settings using hyperparameter tuning.
    :param n_splits: Number of splits for cross-validation (e.g., number of unique groups).
    """
    if "LR" in self.model_name:
      # Create the search grid for logistic regression
      self.grid = create_log_reg_search_grid(n_splits, group_kfold = self.grouping_column != None)
      # If grouping_column is not None, pass the appropriate group labels
      groups = X[self.grouping_column] if self.grouping_column else None
      X = X[[col for col in X.columns if col != self.grouping_column]]
      self.grid.fit(X, y, groups=groups)
      self.best = self.grid.best_estimator_   
    elif "RF" in self.model_name:
      # Create the search grid for random forest
      self.grid = create_rf_search_grid(n_splits, group_kfold = self.grouping_column != None)
      # Pass the group labels if grouping_column is provided
      groups = X[self.grouping_column] if self.grouping_column else None
      X = X[[col for col in X.columns if col != self.grouping_column]]
      self.grid.fit(X, y, groups=groups)
      self.best = self.grid.best_estimator_   
    elif 'LinearReg' in self.model_name:
      # Create the search grid for linear regression
      self.grid = create_linear_reg_search_grid(n_splits)
      self.grid.fit(X, y)
      self.best = self.grid.best_estimator_   
    elif 'MixedLM' in self.model_name:  # Handle MixedLM model optimization
      self.optimized = True
      print(f"Optimizing MixedLM model...")