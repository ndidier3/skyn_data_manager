from sklearn.model_selection import cross_val_predict
from sklearn.metrics import roc_auc_score, accuracy_score
from sklearn.model_selection import GroupKFold
import pandas as pd
import numpy as np
from SDM.Configuration.configuration import get_full_identifier
from joblib import parallel_backend
from SDM.Machine_Learning.model import Model
#parallel_backend("threading")

def CV_group_k_fold(model_design, model_name, cohort_processor):

  ground_truth_column, grouping_column_name, ground_truth_labels, filter, additional_columns = get_CV_specs(model_design)
  
  #columns that are required for cross validation or filtering but not used as model predictors
  non_predictor_columns = list(set([grouping_column_name, ground_truth_column] + list(filter.keys()) + additional_columns))
  features = cohort_processor.features[non_predictor_columns + cohort_processor.training_features].reset_index(drop=True)

  features.to_excel('features_c4_lab.xlsx')

  #removing unwanted subjects/datasets
  features, excluded = filter_features(features, filter)

  #relabeling the ground truth labels to integers (for training compatibility)
  if len(ground_truth_labels) > 0:
    features.loc[:, ground_truth_column] = [ground_truth_labels[c] for c in features[ground_truth_column].tolist()]
    
  k_groups = features[grouping_column_name].tolist()
  n_splits = len(features[grouping_column_name].unique())
  X = features[cohort_processor.training_features]
  y = features[ground_truth_column]

  model = Model(model=None, name=model_name, predictors=cohort_processor.training_features, outcome=ground_truth_column, n_splits=n_splits, group_kfold=k_groups)
  model.optimize()
    
  #train model using those settings
  model.fit(X, y)

  # use model to make predictions and probabilities
  predictions = cross_val_predict(model.best, X, y, cv=GroupKFold(n_splits=n_splits), groups=k_groups, method='predict')
  probabilities = cross_val_predict(model.best, X, y, cv=GroupKFold(n_splits=n_splits), groups=k_groups, method='predict_proba')

  features[f'pred_{model_name}'] = predictions
  correct, incorrect, features = split_based_on_correct_predictions(features, ground_truth_column, prediction_column=f'pred_{model_name}', model_name=model_name)

  excluded[f'pred_{model_name}'] = 'excluded'
  all_features = pd.concat([features, excluded])

  incorrect.to_excel(f'test_incorrect_{model_name}.xlsx')
  correct.to_excel(f'test_correct_{model_name}.xlsx')
  excluded.to_excel(f'test_excluded_{model_name}.xlsx')

  cv_results = {
    'Prediction_Features': cohort_processor.training_features,
    'Features': features,
    'Incorrect_Occasions': incorrect,
    'Correct_Occasions': correct,
    'Predictions': predictions,
    'Probabilities': probabilities,
    'Splits': n_splits,
    'Prediction_N': len(correct) + len(incorrect),
    'Correct_N': len(correct),
    'TP': len(correct[correct[ground_truth_column]==1]),
    'TN': len(correct[correct[ground_truth_column]==0]),
    'FP': len(incorrect[incorrect[ground_truth_column]==0]),
    'FN': len(incorrect[incorrect[ground_truth_column]==1]),
    'Accuracy': len(correct) / (len(correct) + len(incorrect)),
    'AUC_ROC': roc_auc_score(y, probabilities[:, 1]),
  }
  cv_results['Sensitivity'] = cv_results['TP'] / (cv_results['TP'] + cv_results['FN'])
  cv_results['Specificity'] = cv_results['TN'] / (cv_results['TN'] + cv_results['FP'])
  cv_results['CV_Results_Dataframe'] = pd.DataFrame(index=['Features', 'Prediction_N', 'Split Method', 'TP', 'TN', 'FP', 'FN', 'Correct', 'Sensitivity', 'Specificity', 'Accuracy', 'AUC_ROC'], data={f'{model_name}_Result': [', '.join(cv_results['Prediction_Features']), cv_results['Prediction_N'] ,cv_results['Splits'], cv_results['TP'], cv_results['TN'], cv_results['FP'], cv_results['FN'], cv_results['Correct_N'],cv_results['Sensitivity'], cv_results['Specificity'], cv_results['Accuracy'], cv_results['AUC_ROC']]})

  model.cv_results = cv_results
  cohort_processor.features[f'{model_name}_prediction'] = ['' for i in range(0, len(cohort_processor.occasions))]

  save_tac_feauture_predictions_to_SDM(cohort_processor, model_name, ground_truth_column, ground_truth_labels, incorrect, correct)

  cohort_processor.models.append(model)

def get_CV_specs(model_design):

  if model_design == 'Alc_vs_Non':
    filter = {'valid_occasion': [0]} #Used to remove invalid/irrelevant rows
    ground_truth_column = 'condition'
    grouping_column_name = 'subid'
    ground_truth_labels = {'Alc': 1, 'Non': 0} #Used to convert text values into numbers
    additional_columns = []

  if model_design == 'Light_vs_Heavy':
    filter = {'valid_occasion': [0], 'condition': ['Non'], 'binge': ['Unk', 'None', None]}
    ground_truth_column = 'binge'
    grouping_column_name = 'subid'
    ground_truth_labels = {'Heavy': 1, 'Light': 0, 'None': -9, 'Unk': 999}
    additional_columns = []
  
  if model_design == 'AUD_vs_Not':
    filter = {'valid_occasion': [0], 'condition': ['Non']}
    ground_truth_column = 'AUD'
    grouping_column_name = 'subid'
    ground_truth_labels = {}
    additional_columns = []

  if 'worn_vs_removed' in model_design:
    filter = {'device_on': 'unk'}
    ground_truth_column = 'device_on'
    grouping_column_name = 'Full_Identifier'
    ground_truth_labels = {1: 1, 0: 0}
    additional_columns = ['Row_ID', 'Full_Identifier']

  return ground_truth_column, grouping_column_name, ground_truth_labels, filter, additional_columns

def split_based_on_correct_predictions(features, ground_truth_column, prediction_column, model_name, fill_training_dataset=pd.DataFrame()):
  features[f'{model_name}_result'] = np.where((features[ground_truth_column] == 1) & (features[prediction_column] == 1), 'True Positive',
    np.where((features[ground_truth_column] == 0) & (features[prediction_column] == 1), 'False Positive',
      np.where((features[ground_truth_column] == 0) & (features[prediction_column] == 0), 'True Negative',
        np.where((features[ground_truth_column] == 1) & (features[prediction_column] == 0), 'False Negative', 'Unknown'))))
  
  features[f'{model_name}_correct']= np.where(features[ground_truth_column]==features[prediction_column], 'correct', 'incorrect')
  correct = features[features[f'{model_name}_correct']=='correct']
  incorrect = features[features[f'{model_name}_correct']=='incorrect']
  
  return correct, incorrect, features

def save_tac_feauture_predictions_to_SDM(cohort_processor, model_name, ground_truth_column, group_labels, incorrect, correct):

  for i, occasion in enumerate(cohort_processor.occasions):
    condition = occasion.condition if ground_truth_column != 'condition' else group_labels[getattr(occasion, ground_truth_column.lower())]
    ground_truth = group_labels[getattr(occasion, ground_truth_column.lower())] if len(group_labels) else getattr(occasion, ground_truth_column.lower())

    if len(incorrect[(incorrect['subid']==occasion.subid) & (incorrect[ground_truth_column] == ground_truth) & (incorrect['condition']==condition)]):
      occasion.predictions[model_name] = 'incorrect'
      cohort_processor.features.loc[i, f'{model_name}_prediction'] = 'incorrect'
    elif len(correct[(correct['subid']==occasion.subid) & (correct[ground_truth_column] == ground_truth) & (correct['condition']==condition)]):
      occasion.predictions[model_name] = 'correct'
      cohort_processor.features.loc[i, f'{model_name}_prediction'] = 'correct'
    else:
      occasion.predictions[model_name] = 'excluded'
      cohort_processor.features.loc[i, f'{model_name}_prediction'] = 'excluded'

def filter_features(features, filter):
  excluded = pd.DataFrame(columns=features.columns)
  for column, values_to_exclude in filter.items():
    excluded_rows = features[features[column].isin(values_to_exclude)]
    excluded = pd.concat([excluded, excluded_rows])
  excluded = excluded.drop_duplicates()

  features = features[~features.isin(excluded)].dropna(how='all')
  features = features.drop_duplicates()

  return features, excluded

def train_and_test_model_with_holdout(features, predictors, model_name='worn_vs_removed_LR', k=3, holdout=0.3):

  ground_truth_column, grouping_column_name, ground_truth_labels, filter, additional_columns = get_CV_specs(model_name)

  features, excluded = filter_features(features, filter)

  non_predictor_columns = list(set([grouping_column_name, ground_truth_column] + list(filter.keys()) + additional_columns))
  features = features[non_predictor_columns + predictors].reset_index(drop=True)
  features.to_excel('features_device_training.xlsx')
  if len(ground_truth_labels) > 0:
    features.loc[:, ground_truth_column] = [ground_truth_labels[c] for c in features[ground_truth_column].tolist()]

  if holdout > 0:
    holdout_n = round(len(features[grouping_column_name].unique()) * holdout)
    holdout_group = features[grouping_column_name].unique().tolist()[:holdout_n]
    training_group = features[grouping_column_name].unique().tolist()[holdout_n:]
    holdout_features = features[features[grouping_column_name].isin(holdout_group)]
    training_features = features[features[grouping_column_name].isin(training_group)]
  else:
    training_features = features
  
  unique_ids = training_features[grouping_column_name].unique()
  unique_id_count = len(unique_ids)
  group_size = unique_id_count // k
  remainder = unique_id_count % k
  subgroups = [unique_ids[(i * group_size):((i+1) * group_size)+(1 if i==(k-1) and (remainder > 0) else 0)] for i in range(0,k)]

  predictors = [col for col in training_features.columns if col not in additional_columns and col not in [ground_truth_column]]
  X = training_features[predictors]
  y = training_features[ground_truth_column]

  model = Model(model=None, name=model_name, predictors=predictors, outcome=ground_truth_column, n_splits=k)
  model.optimize()
  model.fit(X, y)

  if holdout > 0:
    X_test = holdout_features[predictors]
    pred = model.predict(X_test)
    probabilities = model.model.predict_proba(X_test)
    holdout_features[f'{ground_truth_column}_pred'] = pred
    
    correct, incorrect, holdout_features = split_based_on_correct_predictions(holdout_features, ground_truth_column, prediction_column=f'{ground_truth_column}_pred', model_name=model_name)

    training_features.loc[:, f'{ground_truth_column}_pred'] = 'training'
    training_features.loc[:, f'{model_name}_result'] = 'training'
    training_features.loc[:, f'{model_name}_correct'] = 'training'
    all_features = pd.concat([holdout_features, training_features])
    cv_results = {
      'Prediction_Features': predictors,
      'Training_Features': training_features,
      'Holdout_Features': holdout_features,
      'All_Features': all_features,
      'Incorrect_Rows': incorrect,
      'Correct_Rows': correct,
      'Predictions': pred,
      'Probabilities': probabilities,
      'Splits': 2,
      'Holdout_Proportion': holdout,
      'Prediction_N': len(correct) + len(incorrect),
      'Correct_N': len(correct),
      'TP': len(correct[correct[ground_truth_column]==1]),
      'TN': len(correct[correct[ground_truth_column]==0]),
      'FP': len(incorrect[incorrect[ground_truth_column]==0]),
      'FN': len(incorrect[incorrect[ground_truth_column]==1]),
      'Accuracy': len(correct) / (len(correct) + len(incorrect)),
      'AUC_ROC': roc_auc_score(holdout_features[ground_truth_column], probabilities[:, 1]),
    }
    cv_results['Sensitivity'] = cv_results['TP'] / (cv_results['TP'] + cv_results['FN'])
    cv_results['Specificity'] = cv_results['TN'] / (cv_results['TN'] + cv_results['FP'])
    cv_results['CV_Results_Dataframe'] = pd.DataFrame(index=['Features', 'Prediction_N', 'Split Method', 'TP', 'TN', 'FP', 'FN', 'Correct', 'Sensitivity', 'Specificity', 'Accuracy', 'AUC_ROC'], data={f'{model_name}_Result': [', '.join(cv_results['Prediction_Features']), cv_results['Prediction_N'],cv_results['Splits'], cv_results['TP'], cv_results['TN'], cv_results['FP'], cv_results['FN'], cv_results['Correct_N'], cv_results['Sensitivity'], cv_results['Specificity'], cv_results['Accuracy'], cv_results['AUC_ROC']]})

    model.cv_results = cv_results
    
  return model




