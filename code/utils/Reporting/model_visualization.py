import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import plot_roc_curve
from sklearn.tree import plot_tree

def plot_rf_feature_importances(model, features, version, feature_visuals_path):
  std = np.std([model.feature_importances_ for tree in model.estimators_], axis=0)
  forest_importances = pd.Series(model.feature_importances_, index=features)
  fig, ax = plt.subplots()
  forest_importances.plot.bar(yerr=std, ax=ax)
  print(std)
  ax.set_title(f'Comparison of Feature Importance - {version} data')
  ax.set_ylabel("Mean Decrease in Impurity")
  fig.tight_layout()
  plt.savefig(f'{feature_visuals_path}Random Forest - {version} - Feature Importances.png')
  return forest_importances

def plot_rf_tree(rf, feature_names, outcome_classes, version, feature_visuals_path):
  fig = plt.figure(figsize=(15, 10))
  plot_tree(rf.estimators_[0], 
    feature_names=feature_names, class_names=outcome_classes, 
    filled=True, impurity=True, rounded=True)
  fig.savefig(f'{feature_visuals_path}Random Forest - {version} - Decision Tree.png')