from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.metrics import accuracy_score
from sklearn.model_selection import GridSearchCV
import numpy as np

def create_optimal_rf(cv_method = 5):
  rf = RandomForestClassifier()
  max_depth = [int(x) for x in np.linspace(10, 50, num = 11)]
  distributions = {
    'n_estimators': [10, 50, 100, 200, 300],
    'max_features': [3, 5, 7],
    'max_depth': max_depth,
    'min_samples_split': [2],
    'min_samples_leaf': [1],
    'bootstrap': [True]
  }
  rf_optimal = GridSearchCV(estimator = rf, scoring='accuracy', param_grid = distributions, cv = cv_method, n_jobs = -1)
  return rf_optimal

def create_optimal_lr(cv_method=3):
  lr = LogisticRegression(solver='liblinear', random_state=13, max_iter=1000)
  distributions = dict(C=[0.001,0.01,0.1,1,10,100,1000], penalty=['l1', 'l2'])
  lr_optimal = GridSearchCV(estimator = lr, scoring='accuracy', param_grid = distributions, cv=cv_method, n_jobs = -1)
  return lr_optimal

def test_rf_model(X_train, y_train, X_test, y_test, verbose=False):
  rf_optimal = create_optimal_rf()
  rf_optimal.fit(X_train, y_train)
  model = rf_optimal.best_estimator_
  predictions = model.predict(X_test)
  accuracy = accuracy_score(y_test, predictions)
  roc_auc = roc_auc_score(y_test, model.predict_proba(X_test)[:, 1])
  if verbose:
    print('Model Performance')
    print('Accuracy = {:0.2f}%.'.format(accuracy))
    print('roc_auc = {:0.2f}'.format(roc_auc))
  return model, predictions, roc_auc, accuracy

# def holdout_with_resampling(features, test_size, resample_features = True, predictors = ['curve_auc', 'rise_rate', 'fall_duration', 'peak', 'fall_rate', 'rise_duration', 'TAC_N', 'average_tac_difference', 'tac_alteration_percent'], split=True):
#   features = features[features['valid_occasion'] == 1]
#   X = features[predictors]
#   y = features['condition']

#   X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=34)

#   if resample_features:
#     X_train, y_train = resample(X_train, y_train, n_samples=8000)
#     X_test, y_test = resample(X_test, y_test, n_samples=2000)

#   return X_train, X_test, y_train, y_test

# def build_and_test_model(model_type, X_train, X_test, y_train, y_test): 
#   if model_type == 'rf':
#     model = train_random_forest(X_train, X_test, y_train, y_test)
#   if model_type == 'lr':
#     model = LogisticRegression()
#     model.fit(X_train, y_train)
#   predictions = model.predict(X_test)
#   print(y_test)
#   print(predictions)
#   accuracy = accuracy_score(y_test, predictions)
#   roc_auc = roc_auc_score(y_test, model.predict_proba(X_test)[:, 1])

  # return model, roc_auc, accuracy
# def ML_with_rf(all_features, dataset_version, feature_visuals_path, test_size, selected_features = ['curve_auc', 'rise_rate', 'fall_duration', 'peak', 'fall_rate', 'rise_duration', 'TAC_N', 'average_tac_difference', 'tac_alteration_percent']):
#   X_train, X_test, y_train, y_test = holdout_with_resampling(all_features, test_size, resample_features=True)
#   model, roc_auc, accuracy = build_and_test_model('rf', X_train, X_test, y_train, y_test)
#   print(roc_auc, accuracy)
#   plot_rf_feature_importances(model, selected_features, dataset_version, feature_visuals_path)
#   plot_rf_tree(model, selected_features, y_test.unique().tolist(), dataset_version, feature_visuals_path)
#   return model, roc_auc, accuracy

# def ML_with_lr(features, test_size, selected_features):
#   X_train, X_test, y_train, y_test = holdout_with_resampling(features, test_size, resample_features=True, predictors=selected_features)
#   model, roc_auc, accuracy = build_and_test_model('lr', X_train, X_test, y_train, y_test)
#   return model, roc_auc, accuracy

# def cross_validate_with_pairs(features, model, predictors = ['curve_auc', 'rise_rate', 'fall_duration', 'peak', 'fall_rate', 'rise_duration', 'TAC_N', 'average_tac_difference', 'tac_alteration_percent']):
#   print(features)
#   features = features[features['valid_occasion'] == 1]
#   groups = features['subid'].tolist()
#   splits = len(features['subid'].unique())
#   X = features[predictors]
#   y = features['condition']

#   group_k_fold = GroupKFold(n_splits=splits)
  # for train, test in group_k_fold.split(X, y, groups=groups):
  #   X_train, X_test = X[train], X[test]
  #   y_train, y_test = y[train], y[test]

  # result = cross_validate(LogisticRegression(), X, y, cv=group_k_fold, groups=groups)
  # print(result['test_score'])
  # print(sum(result['test_score']) / (len(result['test_score'])))
  # WHAT IS THIS MODEL?
  # result = cross_validate(model, X, y, cv=group_k_fold, groups=groups)
  # scores = result['test_score']
  # accuracy = sum(result['test_score']) / (len(result['test_score']))

  # predictions = cross_val_predict(model, X, y, cv=group_k_fold, groups=groups)

  #get predicted probabilities, use those to generate ROC curve
  #get auc from curve

  # columns = ['subid', 'condition'] + predictors
  # incorrect = features[features['condition']!=predictions][columns]
  # correct = features[features['condition']==predictions][columns]

  # return scores, accuracy, predictions, incorrect, correct, predictors, splits

