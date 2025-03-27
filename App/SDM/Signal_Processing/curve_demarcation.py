import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from kneed import KneeLocator

def get_distortions(data, features, k_max=10):
  distortions = []
  k_values_to_test = range(1, k_max)
  scaler = StandardScaler()
  data_scaled = scaler.fit_transform(data[features])

  for k in k_values_to_test:
    kmeansModel = KMeans(n_clusters=k, random_state=42, n_init=10)
    kmeansModel.fit(data_scaled)
    distortions.append(kmeansModel.inertia_)
    
  return distortions, k_values_to_test, scaler

def get_knee(distortions, k_values_to_test):
  kn = KneeLocator(k_values_to_test, distortions, curve='convex', direction='decreasing')
  return kn.knee if kn.knee else 2  # Default to 2 if knee is not found

def label_clusters(data, features, optimal_k, scaler):
  data_scaled = scaler.transform(data[features])
  kmeans = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
  prediction = kmeans.fit_predict(data_scaled)
  data['Cluster'] = prediction
  return data

def get_tac_clusters(data, features):
  distortions, k_values_to_test, scaler = get_distortions(data, features, 10)
  optimal_k = get_knee(distortions, k_values_to_test)
  return label_clusters(data, features, optimal_k, scaler), optimal_k

def determine_curve_threshold(df: pd.DataFrame, default_threshold = 10):
  data = df.copy()
  #if less than 12 hours of data, not enough data to use k means
  if (data['TAC'].count() / 60) < 12:
    return default_threshold, default_threshold
  else:
    data.dropna(subset=['TAC'], inplace=True)
    data['TAC'] = data['TAC'].clip(lower=0)

    data['TAC_Change'] = data['TAC'].diff()
    data['TAC_RollingStd'] = data['TAC'].rolling(window=5, min_periods=1).std()
    data.fillna(0, inplace=True)

    features = ['TAC', 'TAC_Change', 'TAC_RollingStd']

    data, optimal_k = get_tac_clusters(data, features)

    baseline_cluster = data.groupby('Cluster')['TAC'].mean().idxmin()

    baseline_mean = data[data['Cluster'] == baseline_cluster]['TAC'].mean()
    baseline_std = data[data['Cluster'] == baseline_cluster]['TAC'].std()

    # If optimal_k is < 4, use the 3SD approach
    if optimal_k < 4:
      threshold = baseline_mean + (3 * baseline_std)

      print(f"Optimal K: {optimal_k}")
      print(f"Baseline Mean TAC: {baseline_mean:.2f}")
      print(f"Baseline Standard Deviation: {baseline_std:.2f}")
      print(f"Curve Threshold (Mean + 3SD): {threshold:.2f}")

    # If optimal_k >= 4, use the mean+1SD of the TAC cluster just above baseline
    elif optimal_k >= 4:
      cluster_means = data.groupby('Cluster')['TAC'].mean()
      sorted_clusters = cluster_means.sort_values()
      baseline_idx = sorted_clusters.index.get_loc(baseline_cluster)
      second_cluster = sorted_clusters.index[baseline_idx + 1]
      second_cluster_mean = data[data['Cluster'] == second_cluster]['TAC'].mean()
      second_cluster_std = data[data['Cluster'] == second_cluster]['TAC'].std()
      threshold = second_cluster_mean + second_cluster_std

      print(f"Optimal K: {optimal_k}")
      print(f"Baseline Mean TAC: {baseline_mean:.2f}")
      print(f"Threshold set to the mean TAC of the next cluster: {threshold:.2f}")

    # Return the threshold based on the logic
    if threshold > 30:
      return 15, threshold  
    elif threshold > 10:
      return 10, threshold
    elif threshold < 1:
      return threshold + 1, threshold
    else:
      return threshold, threshold
  
def get_start_and_end_of_discrete_curves(df, curve_threshold):
  above_threshold = np.sort(df[df['TAC'] > curve_threshold].index)
  gaps = np.diff(above_threshold)
  split_points = np.where(gaps > 1)[0]
  consecutive_sequences = np.split(above_threshold, split_points + 1)
  curve_start_and_end_indices = [[seq[0], seq[-1]] for seq in consecutive_sequences if len(seq) > 0]
  curve_start_and_end_indices = [sublist for sublist in curve_start_and_end_indices if (sublist[1] - sublist[0]) >= 3]
  return curve_start_and_end_indices

def merge_nearby_curves(approved_curve_start_and_end_indices, max_curve_separation_minutes = 60, curve_minutes_limit = (60*24)):
  i = 0
  merged_curve_start_and_end_indices = []
  for i, (curve_start, curve_end) in enumerate(approved_curve_start_and_end_indices):
    if i > 0:
      prior_curve_start = merged_curve_start_and_end_indices[-1][1] 
      prior_curve_end = merged_curve_start_and_end_indices[-1][1]
      merged_curve_minutes = curve_end - prior_curve_start
      if (curve_start - prior_curve_end) < max_curve_separation_minutes and (merged_curve_minutes < curve_minutes_limit):
        merged_curve_start_and_end_indices[-1][1] = curve_end  
      else:
        merged_curve_start_and_end_indices.append([curve_start, curve_end])  
    else:
        merged_curve_start_and_end_indices.append([curve_start, curve_end]) 
  return merged_curve_start_and_end_indices 
