from sklearn.model_selection import cross_validate, cross_val_score, cross_val_predict
from sklearn.model_selection import GroupKFold
from utils.Machine_Learning.model_testing import create_optimal_lr
from utils.Machine_Learning.cv_custom import cv_custom

def cv_with_lr(features, predictors = ['curve_auc', 'rise_rate', 'fall_duration', 'peak']):
  
  features = features[features['valid_occasion'] == 1]
  groups = features['subid'].tolist()
  splits = len(features['subid'].unique())
  X = features[predictors]
  features.loc[:, 'condition'] = [{'Alc': 1, 'Non': 0}[c] for c in features['condition'].tolist()]
  y = features['condition']

  group_k_fold = GroupKFold(n_splits=splits)
  lr_optimal = create_optimal_lr(cv_method=group_k_fold)
  lr_optimal.fit(X, y, groups=groups)

  #Using built in method (does not provide probabilities)
  predictions = cross_val_predict(lr_optimal.best_estimator_, X, y, cv=group_k_fold, groups=groups, method='predict')
  probs = cross_val_predict(lr_optimal.best_estimator_, X, y, cv=group_k_fold, groups=groups, method='predict_proba')

  cv_results, cv_stats = cv_custom(lr_optimal.best_estimator_, features, X, y)

  columns = ['subid', 'condition'] + predictors
  incorrect = features[features['condition']!=predictions][columns]
  correct = features[features['condition']==predictions][columns]
  cv_stats['accuracy_sklearn'] = len(correct) / len(predictions)
  cv_stats['auc_roc_sklearn'] = 'NA'

  return cv_stats, cv_results, incorrect, correct, predictors, splits