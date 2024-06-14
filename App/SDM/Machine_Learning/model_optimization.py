from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.linear_model import LinearRegression
from sklearn.metrics import roc_auc_score
from sklearn.metrics import accuracy_score
from sklearn.model_selection import GroupKFold, KFold, GridSearchCV
import numpy as np
from joblib import parallel_backend
#parallel_backend("threading")

def create_rf_search_grid(n_splits, group_kfold=True):
  rf = RandomForestClassifier()
  max_depth = [int(x) for x in np.linspace(10, 50, num = 11)]
  distributions = {
    'n_estimators': [10, 50, 100, 300],
    'max_features': [3, 5],
    'max_depth': max_depth,
    'min_samples_split': [2],
    'min_samples_leaf': [1],
    'bootstrap': [True]
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
