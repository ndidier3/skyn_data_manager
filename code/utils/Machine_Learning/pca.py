import numpy as np
from sklearn.decomposition import PCA

def PCA_with_features(features, selected_features, version):
  features = features[features['valid_occasion'] == 1]
  X = features[selected_features]
  y = features['condition']
  pca = PCA(n_components=len(selected_features))
  pca.fit(X)
  print(pca.components_)
  print(pca.explained_variance_ratio_)
  return pca.explained_variance_ratio_