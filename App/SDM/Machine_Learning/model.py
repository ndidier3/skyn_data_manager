from SDM.Machine_Learning.model_optimization import *
from sklearn.model_selection import GroupKFold
import pandas as pd

class Model:
  def __init__(self, model, name, predictors, outcome, n_splits, group_kfold=[]):
    self.model = model
    self.model_name = name
    self.predictors = predictors
    self.outcome = outcome
    self.n_splits = n_splits
    self.best = None
    self.use_group_kfold = True if len(group_kfold) else False
    self.group_kfold = group_kfold
    self.optimized = False
    self.feature_importance = pd.DataFrame()
    self.cv_results = {}

  def optimize(self):
      #find optimal model settings
    if "LR" in self.model_name:
      self.model = create_log_reg_search_grid(self.n_splits, group_kfold=self.use_group_kfold)
    if "RF" in self.model_name:
      self.model = create_rf_search_grid(self.n_splits, group_kfold=self.use_group_kfold)
    if 'LinearReg' in self.model_name:
      self.model = create_linear_reg_search_grid(self.n_splits)
    self.optimized = True

  def fit(self, X, y):
    if self.use_group_kfold:
      self.model.fit(X, y, groups=self.group_kfold)
      self.best = self.model.best_estimator_
    else:
      self.model.fit(X, y)
      self.best = self.model.best_estimator_

  def predict(self, X):
    predictions = self.model.predict(X)
    if len(predictions) == 1:
      return predictions[0]
    else:
      return predictions
    
    """
    to add:
      cross val predict
      cross val prob
    """