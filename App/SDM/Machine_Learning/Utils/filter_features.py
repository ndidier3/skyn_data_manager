import pandas as pd

def filter_features(features, filter):
  excluded = pd.DataFrame(columns=features.columns)
  for column, values_to_exclude in filter.items():
    excluded_rows = features[features[column].isin(values_to_exclude)]
    excluded = pd.concat([excluded, excluded_rows])
  excluded = excluded.drop_duplicates()

  features = features[~features.isin(excluded)].dropna(how='all')
  features = features.drop_duplicates()

  return features, excluded