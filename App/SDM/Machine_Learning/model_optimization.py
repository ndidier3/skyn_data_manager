from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.linear_model import LinearRegression
from sklearn.metrics import roc_auc_score
from sklearn.metrics import accuracy_score
from sklearn.model_selection import GroupKFold, KFold, GridSearchCV
import numpy as np
import pandas as pd
from joblib import parallel_backend
#parallel_backend("threading")


def scale_pos_weight_from_labels(y) -> float:
    """``n_neg / n_pos`` for XGBoost, matching sklearn ``class_weight='balanced'``."""
    y_int = pd.Series(y).astype(int)
    n_pos = int((y_int == 1).sum())
    n_neg = int((y_int == 0).sum())
    if n_pos < 1:
        return 1.0
    return float(n_neg) / float(n_pos)


class XGBClassifierBalanced(BaseEstimator, ClassifierMixin):
    """
  ``XGBClassifier`` wrapper that sets ``scale_pos_weight`` from training labels on each ``fit``.

  Safe inside ``GridSearchCV`` inner folds (weight recomputed per inner-train split).
  """

    def __init__(
        self,
        random_state=44,
        n_jobs=-1,
        tree_method='hist',
        verbosity=0,
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.9,
        colsample_bytree=0.9,
        min_child_weight=1,
        reg_lambda=1.0,
        eval_metric='logloss',
    ):
        self.random_state = random_state
        self.n_jobs = n_jobs
        self.tree_method = tree_method
        self.verbosity = verbosity
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.subsample = subsample
        self.colsample_bytree = colsample_bytree
        self.min_child_weight = min_child_weight
        self.reg_lambda = reg_lambda
        self.eval_metric = eval_metric

    def fit(self, X, y):
        from xgboost import XGBClassifier

        spw = scale_pos_weight_from_labels(y)
        self.clf_ = XGBClassifier(
            random_state=self.random_state,
            n_jobs=self.n_jobs,
            tree_method=self.tree_method,
            verbosity=self.verbosity,
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            subsample=self.subsample,
            colsample_bytree=self.colsample_bytree,
            min_child_weight=self.min_child_weight,
            reg_lambda=self.reg_lambda,
            eval_metric=self.eval_metric,
            scale_pos_weight=spw,
        )
        self.clf_.fit(X, y)
        self.classes_ = self.clf_.classes_
        return self

    def predict(self, X):
        return self.clf_.predict(X)

    def predict_proba(self, X):
        return self.clf_.predict_proba(X)

    @property
    def feature_importances_(self):
        return self.clf_.feature_importances_


def effective_group_kfold_splits(n_groups: int, requested: int) -> int:
    """``GroupKFold`` split count capped by the number of distinct groups (minimum 2)."""
    if n_groups < 2:
        return 0
    return max(2, min(int(requested), int(n_groups)))


def create_xgb_search_grid(n_splits, group_kfold=True, scoring='accuracy', balanced_weights=True):
  """
  GridSearchCV over ``XGBClassifier`` hyperparameters.

  Uses native missing-value handling in XGBoost (NaNs in ``X`` are allowed).

  Raises:
    ImportError: if the ``xgboost`` package is not installed.
  """
  try:
    from xgboost import XGBClassifier
  except ImportError as e:
    raise ImportError(
      "xgboost is required for create_xgb_search_grid. Install with: pip install xgboost"
    ) from e

  if balanced_weights:
    xgb = XGBClassifierBalanced(
      random_state=44,
      n_jobs=-1,
      tree_method="hist",
      verbosity=0,
    )
  else:
    xgb = XGBClassifier(
      random_state=44,
      n_jobs=-1,
      tree_method="hist",
      verbosity=0,
    )
  distributions = {
    "max_depth": [6, 12, 20],
    "learning_rate": [0.05, 0.1],
    "n_estimators": [100, 200],
    "subsample": [0.9, 1.0],
    "colsample_bytree": [0.9, 1.0],
    "min_child_weight": [1, 3],
    "reg_lambda": [1.0],
  }
  cv_method = GroupKFold(n_splits=n_splits) if group_kfold else KFold(n_splits=n_splits, shuffle=True, random_state=42)
  xgb_grid = GridSearchCV(
    estimator=xgb,
    scoring=scoring,
    param_grid=distributions,
    cv=cv_method,
    n_jobs=-1,
  )
  return xgb_grid


def create_rf_search_grid(n_splits, group_kfold=True):
  rf = RandomForestClassifier(random_state=44)
  distributions = {
    'n_estimators': [50, 100],  # More trees for better generalization
    # 'max_features': ['sqrt', 'log2', 5, 7, 10],  # A mix of common values and custom ones
    'max_features': [5, 7, 10],  # A mix of common values and custom ones
    'max_depth': [10, 25, 40],  # Test a range of depths with None as an option
    'min_samples_split': [2, 5],  # Testing slightly higher values to prevent overfitting
    'min_samples_leaf': [2, 5, 10],  # Smoothing effect with higher values
    'bootstrap': [True, False]  # Test both bootstrap and non-bootstrap trees
  }
  cv_method = GroupKFold(n_splits=n_splits) if group_kfold else KFold(n_splits=n_splits, shuffle=True, random_state=42)
  rf_grid = GridSearchCV(estimator = rf, scoring='accuracy', param_grid = distributions, cv=cv_method, n_jobs = -1)
  return rf_grid

def create_log_reg_search_grid(n_splits, group_kfold=True):
  lr = LogisticRegression(solver='liblinear', random_state=13, max_iter=1000)
  distributions = dict(C=[0.001,0.01,0.1,1,10,100,1000], penalty=['l1', 'l2'])
  cv_method = GroupKFold(n_splits=n_splits) if group_kfold else KFold(n_splits=n_splits, shuffle=True, random_state=42)
  lr_grid = GridSearchCV(estimator = lr, scoring='accuracy', param_grid = distributions, cv=cv_method, n_jobs = -1)
  return lr_grid

def create_linear_reg_search_grid(n_splits):
  distributions = {'fit_intercept': [True, False]}
  cv_method = KFold(n_splits=n_splits, shuffle=True, random_state=42)
  linear_regression_grid = GridSearchCV(estimator=LinearRegression(), scoring='neg_mean_squared_error', param_grid=distributions, cv=cv_method, n_jobs=-1)
  return linear_regression_grid

def test_rf_model(X_train, y_train, X_test, y_test, verbose=False):
  rf_grid = create_rf_search_grid()
  rf_grid.fit(X_train, y_train)
  model = rf_grid.best_estimator_
  predictions = model.predict(X_test)
  accuracy = accuracy_score(y_test, predictions)
  roc_auc = roc_auc_score(y_test, model.predict_proba(X_test)[:, 1])
  if verbose:
    print('Model Performance')
    print('Accuracy = {:0.2f}%.'.format(accuracy))
    print('roc_auc = {:0.2f}'.format(roc_auc))
  return model, predictions, roc_auc, accuracy
