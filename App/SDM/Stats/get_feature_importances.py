import pandas as pd
import pickle

def get_feature_importances(model, features):
  #std = np.std([model.feature_importances_ for tree in model.estimators_], axis=0)
  forest_importance = pd.DataFrame(model.feature_importances_, index=features, columns=['feature importance']).sort_values('feature importance', ascending=False)
  return forest_importance
