def identify_overlapping_curves(features):
  features['begin_matches_prior_CURVE'] = (
    (features['begin_CURVE'] == features['begin_CURVE'].shift()) & 
    (features['subid'] == features['subid'].shift())
  ).astype(int)

  features['end_matches_prior_CURVE'] = (
    (features['end_CURVE'] == features['end_CURVE'].shift()) & 
    (features['subid'] == features['subid'].shift())
  ).astype(int)

  features['overlaps_with_prior_CURVE'] = 0

  for i in range(1, len(features)):
    previous_row = features.iloc[i - 1]
    current_row = features.iloc[i]

    if (
      current_row["begin_CURVE"] and previous_row["end_CURVE"] 
      and current_row["end_CURVE"] and previous_row["begin_CURVE"]
      ):

      if (
        current_row["subid"] == previous_row["subid"]
        and current_row["begin_CURVE"] < previous_row["end_CURVE"]
        and current_row["end_CURVE"] > previous_row["begin_CURVE"]
      ):
        
        features.loc[i, "overlaps_with_prior_CURVE"] = 1
  
  return features
