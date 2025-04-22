import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from kneed import KneeLocator
from typing import Union, Tuple, Dict

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
  # optimal_k = 2
  return label_clusters(data, features, optimal_k, scaler), optimal_k

def determine_curve_threshold(df: pd.DataFrame, default_threshold: float = 10.0) -> Tuple[float, float, Union[float, None], Union[float, None]]:
    """
    Determine the threshold for identifying curves in TAC data using k-means clustering.
    
    Args:
        df (pd.DataFrame): DataFrame containing TAC data
        default_threshold (float): Default threshold to use if calculation fails or data is insufficient
        
    Returns:
        tuple[float, float, float | None, float | None]: 
            - First float: The actual threshold to use (capped between 1 and 10)
            - Second float: The calculated threshold before capping
            - Third float: Baseline mean (None if calculation failed)
            - Fourth float: Baseline standard deviation (None if calculation failed)
    """
    try:
        data = df.copy()
        
        # Validate input data
        if 'TAC' not in data.columns:
          print("WARNING: Curve threshold identification failed - No 'TAC' column found in data")
          return default_threshold, default_threshold, None, None
            
        # Check for minimum data requirement (4 hours)
        if (data['TAC'].count() / 60) < 4:
          print("WARNING: Curve threshold identification failed - Less than 4 hours of TAC data available")
          return default_threshold, default_threshold, None, None
            
        # Calculate features for clustering
        data['TAC_Change'] = data['TAC'].diff()
        data['TAC_RollingStd'] = data['TAC'].rolling(window=5, min_periods=1).std()

        # Clean and prepare data
        data.dropna(subset=['TAC', 'TAC_Change', 'TAC_RollingStd'], inplace=True)
        data['TAC'] = data['TAC'].clip(lower=0)

        features = ['TAC', 'TAC_Change', 'TAC_RollingStd']
        data, optimal_k = get_tac_clusters(data, features)

        # Identify baseline cluster and calculate threshold
        baseline_cluster = data.groupby('Cluster')['TAC'].mean().idxmin()
        baseline_mean = data[data['Cluster'] == baseline_cluster]['TAC'].mean()
        baseline_std = data[data['Cluster'] == baseline_cluster]['TAC'].std()
        
        # Calculate threshold using 2 standard deviations
        threshold = baseline_mean + (2 * baseline_std)

        # Log the results
        print(f"Curve Threshold Identification Results:")
        print(f"  Optimal K: {optimal_k}")
        print(f"  Baseline Mean TAC: {baseline_mean:.2f}")
        print(f"  Baseline Standard Deviation: {baseline_std:.2f}")
        print(f"  Curve Threshold (Mean + 2SD): {threshold:.2f}")

        # Cap threshold between 1 and 10
        capped_threshold = max(1.0, min(10.0, threshold))
        
        return capped_threshold, threshold, baseline_mean, baseline_std
        
    except Exception as e:
        print(f"ERROR: Curve threshold identification failed - {str(e)}")
        return default_threshold, default_threshold, None, None
  
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
        merged_curve_start_and_end_indices[-1][2] += 1  
      else:
        merged_curve_start_and_end_indices.append([curve_start, curve_end, 1])  
    else:
        merged_curve_start_and_end_indices.append([curve_start, curve_end, 1]) 
  return merged_curve_start_and_end_indices 

def get_curve_threshold_from_method(df: pd.DataFrame, curve_threshold_method: Union[str, float, int], default_threshold: float = 10.0) -> Tuple[float, float, Union[float, None], Union[float, None]]:
    """
    Determine the curve threshold based on the specified method.
    
    Args:
        df (pd.DataFrame): DataFrame containing TAC data
        curve_threshold_method (str | float | int): Either 'auto' or a numeric threshold
        default_threshold (float): Default threshold to use if calculation fails
        
    Returns:
        tuple[float, float, float | None, float | None]: 
            - First float: The actual threshold to use
            - Second float: The unadjusted threshold
            - Third float: Baseline mean (None if calculation failed)
            - Fourth float: Baseline standard deviation (None if calculation failed)
            
    Raises:
        ValueError: If curve_threshold_method is invalid
    """
    try:
        if curve_threshold_method == 'auto':
            result = determine_curve_threshold(df, default_threshold)
            if result is None or any(v is None for v in result):
                raise ValueError("Failed to automatically determine curve threshold")
            return result
        elif isinstance(curve_threshold_method, (int, float)):
            threshold = float(curve_threshold_method)
            return threshold, threshold, None, None
        else:
            raise ValueError(f"Invalid curve_threshold value: {curve_threshold_method}")
    except Exception as e:
        print(f"Error determining curve threshold: {str(e)}")
        return default_threshold, default_threshold, None, None
