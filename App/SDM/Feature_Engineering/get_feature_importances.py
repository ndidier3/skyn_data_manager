import pandas as pd
import pickle

def get_feature_importances(model, features):
  #std = np.std([model.feature_importances_ for tree in model.estimators_], axis=0)
  forest_importance = pd.DataFrame(model.feature_importances_, index=features, columns=['Mean Decrease Impurity']).sort_values('Mean Decrease Impurity', ascending=False).rename_axis('Feature')
  return forest_importance
