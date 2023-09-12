from sklearn.model_selection import cross_validate, cross_val_score, cross_val_predict
from sklearn.model_selection import GroupKFold
from SDM.Machine_Learning.model_optimization import create_optimal_rf
from SDM.Machine_Learning.cv_custom import cv_custom
from sklearn.metrics import roc_auc_score
from sklearn.metrics import accuracy_score

def RF_CV(features, predictors, grouping_column_name, label_column_name, 
          relabeling_dict = {}, #key = existing value, val = value to replace existing value (may not be needed)
          filter_dict = {} #key = column name, val = list of values to exclude (may not be needed)
          ):
  #if needed, use a dictionary to filter out rows
  if len(filter_dict) > 0:
    for column, values_to_exclude in filter_dict.items():
      features = features[~features[column].isin(values_to_exclude)]

  #if needed, use a dictionary to relabel ground truth labels
  if len(relabeling_dict) > 0:
    features.loc[:, label_column_name] = [relabeling_dict[c] for c in features[label_column_name].tolist()]

  split_groupings = features[grouping_column_name].tolist()
  n_splits = len(features[grouping_column_name].unique())
  X = features[predictors]
  y = features[label_column_name]

  #find optimal RF settings
  rf_optimal = create_optimal_rf(cv_method=GroupKFold(n_splits=n_splits))
  #train model using those settings
  rf_optimal.fit(X, y, groups=split_groupings)
  #use model to make predictions and probabilities
  predictions = cross_val_predict(rf_optimal.best_estimator_, X, y, cv=GroupKFold(n_splits=n_splits), groups=split_groupings, method='predict')
  probabilities = cross_val_predict(rf_optimal.best_estimator_, X, y, cv=GroupKFold(n_splits=n_splits), groups=split_groupings, method='predict_proba')

  #acquire more fine grain results (True Positives, True Negatives,)
  cv_results, cv_stats = cv_custom(rf_optimal.best_estimator_, features, X, y)

  columns = [grouping_column_name, label_column_name] + predictors
  incorrect = features[features[label_column_name]!=predictions][columns]
  correct = features[features[label_column_name]==predictions][columns]
  cv_stats['accuracy_sklearn'] = len(correct) / len(predictions)
  cv_stats['auc_roc'] = roc_auc_score(y, probabilities[:, 1])

  return cv_stats, cv_results, incorrect, correct, predictors, n_splits, rf_optimal.best_estimator_

def RF_CV_alc_vs_non(features, predictors = ['curve_auc', 'rise_rate', 'fall_duration', 'peak', 'fall_rate', 'rise_duration', 'TAC_N', 'average_tac_difference', 'tac_alteration_percent']):
  
  if 'major_outlier_N' in features.columns:
    predictors.extend(['major_outlier_N', 'minor_outlier_N'])
  else:
    predictors = [predictor for predictor in predictors if predictor not in ['major_outlier_N', 'minor_outlier_N']]
  
  cv_stats, cv_results, incorrect, correct, predictors, n_splits, lr_optimal_estimator_ = RF_CV(
      features, predictors, grouping_column_name='subid', label_column_name='condition', 
      relabeling_dict = {'Alc': 1, 'Non': 0}, #Converting text into number labels
      filter_dict = {'valid_occasion': [0]} #Removing invalid occasions 
    )
  return cv_stats, cv_results, incorrect, correct, predictors, n_splits, lr_optimal_estimator_

def RF_CV_worn_vs_removed(features, predictors = ['temp', 'temp_pre_neighbors', 'temp_post_neighbors', 'temp_diff',
                                                  'motion', 'motion_pre_neighbors','motion_post_neighbors', 'motion_diff',
                                                  'tac', 'tac_pre_neighbors', 'tac_post_neighbors', 'tac_diff',
                                                  'alc_consumed_in_episode']):

  cv_stats, cv_results, incorrect, correct, predictors, n_splits, lr_optimal_estimator_ = RF_CV(
      features, predictors, grouping_column_name='subid', label_column_name='condition', 
      relabeling_dict = {'Worn': 1, 'Removed': 0}, #Converting text into number labels
    )
  
  return cv_stats, cv_results, incorrect, correct, predictors, n_splits, lr_optimal_estimator_
