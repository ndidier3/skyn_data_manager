import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from SDM.Machine_Learning.binary_model_dev import filter_features
from SDM.Machine_Learning.model import Model
from SDM.Configuration.file_management import save_to_computer

def train_feature_estimator(cohort_processor, predictors, outcome, training_filter={}):
  features = cohort_processor.features

  features, excluded = filter_features(features, training_filter)

  X_train = features[predictors]
  y_train = features[outcome]

  LR = Model(LinearRegression(), outcome + '_LinearReg', predictors, outcome, n_splits=3, group_kfold=[])
  LR.optimize()
  LR.fit(X_train, y_train)

  save_to_computer(LR, LR.model_name, cohort_processor.python_object_folder, extension='sdmtm')


  