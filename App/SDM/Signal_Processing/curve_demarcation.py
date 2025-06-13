import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from kneed import KneeLocator
from typing import Union, Tuple, Dict
import traceback

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
            
        # Clean and prepare data
        # Drop non-wear periods
        data = data[data['device_worn_model'] == 1].copy()
        
        # Handle negative values
        mask = data['TAC'] < 0
        if mask.any():
            data.loc[mask, 'TAC'] = np.random.normal(loc=1.0, scale=0.3, size=mask.sum()).clip(0, 2)
        
        # Calculate consecutive indices
        data['consecutive'] = (data.index.to_series().diff() == 1)
        data.loc[data.index[0], 'consecutive'] = True  # First row is always consecutive
        
        # TAC_Change - only calculate for consecutive rows
        data['TAC_Change'] = data['TAC'].diff()
        data.loc[~data['consecutive'], 'TAC_Change'] = np.nan
        
        # TAC_RollingStd - use trailing window and ensure all points in window are consecutive
        window_size = 5
        data['TAC_RollingStd'] = data['TAC'].rolling(
            window=window_size,
            min_periods=window_size  # Require full window for calculation
        ).std()
        
        # Create a mask for windows where all points are consecutive
        consecutive_mask_throughout_window = data['consecutive'].rolling(
            window=window_size,
            min_periods=window_size
        ).apply(lambda x: x.all()).astype(bool)
        
        # Set TAC_RollingStd to NaN where the window contains non-consecutive points
        data.loc[~consecutive_mask_throughout_window, 'TAC_RollingStd'] = np.nan
        
        # Drop any remaining NaN values
        data = data.dropna(subset=['TAC', 'TAC_Change', 'TAC_RollingStd']).copy()
        
        # Verify we still have enough data after cleaning
        if len(data) < 240:  # Less than 4 hours of data
            print("WARNING: Curve threshold identification failed - Insufficient data after cleaning")
            return default_threshold, default_threshold, None, None

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
        print("Full traceback:")
        print(traceback.format_exc())
        return default_threshold, default_threshold, None, None
  
def get_start_and_end_of_discrete_curves(df, curve_threshold, TAC_column = 'TAC'):
  above_threshold = np.sort(df[df[TAC_column] > curve_threshold].index)
  gaps = np.diff(above_threshold)
  split_points = np.where(gaps > 1)[0]
  consecutive_sequences = np.split(above_threshold, split_points + 1)
  curve_start_and_end_indices = [[seq[0], seq[-1]] for seq in consecutive_sequences if len(seq) > 0]
  #filtering out curves that are less than 15 minutes long
  curve_start_and_end_indices = [
    sublist for sublist in curve_start_and_end_indices if (sublist[1] - sublist[0]) > 15
  ]
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
    
def adjust_curve_demarcation_for_raw_tac(
    dataset, 
    curve_start_and_end_indices, 
    curve_threshold,
    max_curve_separation_minutes,
):
    adjusted_indices = []
    TAC_column = 'TAC_pre_imputation'
    
    for curve_start, curve_end, curve_count in curve_start_and_end_indices:
        # Find the peak TAC within the original segment
        segment_data = dataset.loc[curve_start:curve_end, TAC_column]
        peak_idx = segment_data.idxmax()
        
        # Initialize new boundaries at the peak
        new_start = peak_idx
        new_end = peak_idx
        
        # First find the threshold crossing points
        # Extend left (earlier in time) until we find the first point above threshold
        while new_start > dataset.index[0]:
            prev_idx = dataset.index[dataset.index.get_loc(new_start) - 1]
            prev_tac = dataset.loc[prev_idx, TAC_column]
            if pd.isna(prev_tac):
                break
            if prev_tac <= curve_threshold:
                # Found the threshold crossing point
                break
            new_start = prev_idx
            
        # Extend right (later in time) until we find the first point below threshold
        while new_end < dataset.index[-1]:
            next_idx = dataset.index[dataset.index.get_loc(new_end) + 1]
            next_tac = dataset.loc[next_idx, TAC_column]
            if pd.isna(next_tac):
                break
            if next_tac <= curve_threshold:
                # Found the threshold crossing point
                break
            new_end = next_idx
            
        # Now look for any TAC>threshold within max_curve_separation_minutes of the boundaries
        # Keep looking left until we don't find any more points above threshold
        if max_curve_separation_minutes > 0:
            while True:
                lookback_start = max(0, dataset.index.get_loc(new_start) - max_curve_separation_minutes)
                lookback_indices = dataset.index[lookback_start:dataset.index.get_loc(new_start)]
                lookback_tac = dataset.loc[lookback_indices, TAC_column]
                if lookback_tac.empty:
                    break
                    
                above_threshold = lookback_tac[lookback_tac > curve_threshold]
                if above_threshold.empty:
                    break
                    
                new_start = above_threshold.index[0]  # Take the earliest point above threshold
                
        # Keep looking right until we don't find any more points above threshold
            while True:
                lookahead_end = min(len(dataset), dataset.index.get_loc(new_end) + max_curve_separation_minutes + 1)
                lookahead_indices = dataset.index[dataset.index.get_loc(new_end) + 1:lookahead_end]
                lookahead_tac = dataset.loc[lookahead_indices, TAC_column]
                if lookahead_tac.empty:
                    break
                    
                above_threshold = lookahead_tac[lookahead_tac > curve_threshold]
                if above_threshold.empty:
                    break
                    
                new_end = above_threshold.index[-1]  # Take the latest point above threshold
            
        # Count discrete intervals above threshold within the final boundaries
        curve_data = dataset.loc[new_start:new_end, TAC_column]
        above_threshold = curve_data > curve_threshold
        # Find where the signal crosses the threshold
        threshold_crossings = above_threshold.astype(int).diff().fillna(0)
        # Count the number of times we cross from below to above threshold
        new_curve_count = (threshold_crossings == 1).sum()
            
        # Add the adjusted curve with the new curve count
        adjusted_indices.append([new_start, new_end, new_curve_count])
    
    return adjusted_indices

    