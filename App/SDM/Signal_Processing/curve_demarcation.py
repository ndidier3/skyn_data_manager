import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
from kneed import KneeLocator
from typing import Union, Tuple, Dict
import traceback

# Constants
MIN_DATA_POINTS = 240  # 4 hours at 1-minute intervals
MIN_THRESHOLD = 1.0    # Minimum allowed threshold value (μg/L)
SD_MULTIPLIER = 2.5    # Standard deviation multiplier for threshold calculation
SAFETY_THRESHOLD = 10.0  # TAC threshold (μg/L) for safety rule activation

# Legacy functions - commented out as they are not used in the current implementation
# def get_distortions(data, features, k_max=10):
#   distortions = []
#   k_values_to_test = range(1, k_max)
#   scaler = StandardScaler()
#   data_scaled = scaler.fit_transform(data[features])
# 
#   for k in k_values_to_test:
#     kmeansModel = KMeans(n_clusters=k, random_state=42, n_init=10)
#     kmeansModel.fit(data_scaled)
#     distortions.append(kmeansModel.inertia_)
#     
#   return distortions, k_values_to_test, scaler
# 
# def get_knee(distortions, k_values_to_test):
#   kn = KneeLocator(k_values_to_test, distortions, curve='convex', direction='decreasing')
#   return kn.knee if kn.knee else 2  # Default to 2 if knee is not found
# 
# def label_clusters(data, features, optimal_k, scaler):
#   data_scaled = scaler.transform(data[features])
#   kmeans = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
#   prediction = kmeans.fit_predict(data_scaled)
#   data['Cluster'] = prediction
#   return data
# 
# def get_tac_clusters(data, features):
#   distortions, k_values_to_test, scaler = get_distortions(data, features, 10)
#   optimal_k = get_knee(distortions, k_values_to_test)
#   # optimal_k = 2
#   return label_clusters(data, features, optimal_k, scaler), optimal_k

def calculate_time_series_features(data: pd.DataFrame, TAC_column: str = 'TAC', window_size: int = 10) -> pd.DataFrame:
    """
    Calculate time-series features for TAC data using a rolling window approach.
    
    Args:
        data (pd.DataFrame): DataFrame containing TAC data
        TAC_column (str): Name of the TAC column
        window_size (int): Size of the rolling window
        
    Returns:
        pd.DataFrame: DataFrame with additional time-series features
    """
    data = data.copy()
    
    # Calculate consecutive indices
    data['consecutive'] = (data.index.to_series().diff() == 1)
    data.loc[data.index[0], 'consecutive'] = True  # First row is always consecutive
    
    # Rolling window features - only calculate for consecutive rows
    data['mean_TAC'] = data[TAC_column].rolling(
        window=window_size, 
        min_periods=window_size
    ).mean()
    
    data['std_TAC'] = data[TAC_column].rolling(
        window=window_size, 
        min_periods=window_size
    ).std()
    
    # Slope calculation using linear regression on the window
    def calculate_slope(x):
        if len(x) < 2:
            return np.nan
        y = np.arange(len(x))
        slope = np.polyfit(y, x, 1)[0]
        return slope
    
    data['slope'] = data[TAC_column].rolling(
        window=window_size, 
        min_periods=window_size
    ).apply(calculate_slope)
    
    # Mean absolute difference
    data['d1'] = data[TAC_column].rolling(
        window=window_size, 
        min_periods=window_size
    ).apply(lambda x: np.mean(np.abs(np.diff(x))))
    
    # Range (max - min)
    data['range'] = data[TAC_column].rolling(
        window=window_size, 
        min_periods=window_size
    ).apply(lambda x: np.max(x) - np.min(x))
    
    # Create a mask for windows where all points are consecutive
    consecutive_mask_throughout_window = data['consecutive'].rolling(
        window=window_size,
        min_periods=window_size
    ).apply(lambda x: x.all()).astype(bool)
    
    # Set all features to NaN where the window contains non-consecutive points
    feature_columns = ['mean_TAC', 'std_TAC', 'slope', 'd1', 'range']
    for col in feature_columns:
        data.loc[~consecutive_mask_throughout_window, col] = np.nan
    
    return data

def evaluate_clustering_quality(data: pd.DataFrame, features: list, k_values: list) -> Dict[int, Dict[str, float]]:
    """
    Evaluate clustering quality using multiple metrics.
    
    Args:
        data (pd.DataFrame): DataFrame with features
        features (list): List of feature column names
        k_values (list): List of k values to evaluate
        
    Returns:
        Dict[int, Dict[str, float]]: Dictionary with k as key and metrics as values
    """
    results = {}
    
    # Prepare data
    scaler = StandardScaler()
    data_scaled = scaler.fit_transform(data[features])
    
    for k in k_values:
        if k < 2:
            continue
            
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10, init='k-means++')
        cluster_labels = kmeans.fit_predict(data_scaled)
        
        # Calculate metrics
        try:
            silhouette = silhouette_score(data_scaled, cluster_labels)
        except Exception as e:
            print(f"  Warning: Could not calculate silhouette score for k={k}: {e}")
            silhouette = np.nan
            
        try:
            calinski_harabasz = calinski_harabasz_score(data_scaled, cluster_labels)
        except Exception as e:
            print(f"  Warning: Could not calculate Calinski-Harabasz score for k={k}: {e}")
            calinski_harabasz = np.nan
            
        try:
            davies_bouldin = davies_bouldin_score(data_scaled, cluster_labels)
        except Exception as e:
            print(f"  Warning: Could not calculate Davies-Bouldin score for k={k}: {e}")
            davies_bouldin = np.nan
            
        results[k] = {
            'silhouette': silhouette,
            'calinski_harabasz': calinski_harabasz,
            'davies_bouldin': davies_bouldin,
            'inertia': kmeans.inertia_
        }
    
    return results

def identify_baseline_cluster(data: pd.DataFrame, features: list, k: int = 2) -> Tuple[int, pd.DataFrame]:
    """
    Identify the baseline cluster using k-means clustering with Z-score normalized criteria.
    
    Args:
        data (pd.DataFrame): DataFrame with features
        features (list): List of feature column names
        k (int): Number of clusters to use
        
    Returns:
        Tuple[int, pd.DataFrame]: Baseline cluster ID and DataFrame with cluster labels
    """
    # Prepare data
    scaler = StandardScaler()
    data_scaled = scaler.fit_transform(data[features])
    
    # Perform k-means clustering
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10, init='k-means++')
    cluster_labels = kmeans.fit_predict(data_scaled)
    data['Cluster'] = cluster_labels
    
    # Analyze each cluster
    cluster_stats = []
    for cluster_id in range(k):
        cluster_data = data[data['Cluster'] == cluster_id]
        
        # Calculate cluster characteristics
        mean_tac = cluster_data['TAC'].mean()
        std_tac = cluster_data['std_TAC'].mean()
        mean_slope = cluster_data['slope'].mean()
        
        # Calculate time continuity (optional sanity check)
        # Count consecutive stretches
        consecutive_stretches = 0
        current_stretch = 0
        for idx in cluster_data.index:
            if cluster_data.loc[idx, 'consecutive']:
                current_stretch += 1
            else:
                if current_stretch > 0:
                    consecutive_stretches += 1
                    current_stretch = 0
        if current_stretch > 0:
            consecutive_stretches += 1
        
        cluster_stats.append({
            'cluster_id': cluster_id,
            'mean_tac': mean_tac,
            'std_tac': std_tac,
            'mean_slope': mean_slope,
            'consecutive_stretches': consecutive_stretches,
            'size': len(cluster_data)
        })
    
    # Calculate Z-score normalization across all clusters for fair comparison
    all_means = [stats['mean_tac'] for stats in cluster_stats]
    all_stds = [stats['std_tac'] for stats in cluster_stats]
    all_slopes = [abs(stats['mean_slope']) for stats in cluster_stats]
    
    # Calculate means and standard deviations across all clusters
    mean_mean = np.mean(all_means)
    mean_std = np.std(all_means) if np.std(all_means) > 0 else 1e-8
    std_mean = np.mean(all_stds)
    std_std = np.std(all_stds) if np.std(all_stds) > 0 else 1e-8
    slope_mean = np.mean(all_slopes)
    slope_std = np.std(all_slopes) if np.std(all_slopes) > 0 else 1e-8
    
    # Check if any cluster has mean TAC > SAFETY_THRESHOLD (safety rule)
    high_tac_clusters = [stats for stats in cluster_stats if stats['mean_tac'] > SAFETY_THRESHOLD]
    use_safety_rule = len(high_tac_clusters) > 0
    
    if use_safety_rule:
        print(f"  SAFETY RULE ACTIVATED: Found {len(high_tac_clusters)} cluster(s) with mean TAC > 10")
        for cluster in high_tac_clusters:
            print(f"    Cluster {cluster['cluster_id']}: mean_TAC = {cluster['mean_tac']:.2f}")
        
        # Default to cluster with lowest TAC when safety rule is active
        baseline_scores = []
        for stats in cluster_stats:
            baseline_scores.append({
                'cluster_id': stats['cluster_id'],
                'selection_method': 'safety_rule_lowest_tac',
                'raw_mean_tac': stats['mean_tac'],
                'raw_std_tac': stats['std_tac'],
                'raw_mean_slope': stats['mean_slope']
            })
        
        # Sort by raw TAC (lowest first)
        baseline_scores.sort(key=lambda x: x['raw_mean_tac'])
        baseline_cluster_id = baseline_scores[0]['cluster_id']
        print(f"  Safety rule selected Cluster {baseline_cluster_id} (lowest TAC: {baseline_scores[0]['raw_mean_tac']:.2f})")
        
    else:
        print(f"  No safety rule needed - all clusters have mean TAC ≤ 10")
        
        # Calculate Z-score normalized baseline scores
        baseline_scores = []
        for stats in cluster_stats:
            # Z-score each metric (lower is better for baseline)
            tac_zscore = abs(stats['mean_tac'] - mean_mean) / mean_std
            std_zscore = (stats['std_tac'] - std_mean) / std_std
            slope_zscore = (abs(stats['mean_slope']) - slope_mean) / slope_std
            
            # Combined normalized score (lower is better)
            normalized_score = tac_zscore + std_zscore + slope_zscore
            
            baseline_scores.append({
                'cluster_id': stats['cluster_id'],
                'selection_method': 'z_score_normalized',
                'normalized_score': normalized_score,
                'tac_zscore': tac_zscore,
                'std_zscore': std_zscore,
                'slope_zscore': slope_zscore,
                'raw_mean_tac': stats['mean_tac'],
                'raw_std_tac': stats['std_tac'],
                'raw_mean_slope': stats['mean_slope']
            })
        
        # Sort by normalized score and select the best
        baseline_scores.sort(key=lambda x: x['normalized_score'])
        baseline_cluster_id = baseline_scores[0]['cluster_id']
        print(f"  Z-score assessment selected Cluster {baseline_cluster_id}")
    
    print(f"Baseline Cluster Identification Results:")
    print(f"  Selected Cluster ID: {baseline_cluster_id}")
    
    if use_safety_rule:
        print(f"  Selection Method: {baseline_scores[0]['selection_method']}")
        print(f"  Cluster Details (Safety Rule Active):")
        for score_info in baseline_scores:
            print(f"    Cluster {score_info['cluster_id']}: mean_TAC={score_info['raw_mean_tac']:.4f}, "
                  f"std_TAC={score_info['raw_std_tac']:.4f}, slope={score_info['raw_mean_slope']:.4f}")
    else:
        print(f"  Selection Method: {baseline_scores[0]['selection_method']}")
        print(f"  Normalization Reference (across all clusters):")
        print(f"    TAC: mean={mean_mean:.4f}, std={mean_std:.4f}")
        print(f"    STD: mean={std_mean:.4f}, std={std_std:.4f}")
        print(f"    Slope: mean={slope_mean:.4f}, std={slope_std:.4f}")
        print(f"  Cluster Scores (Z-Score Normalized):")
        for score_info in baseline_scores:
            print(f"    Cluster {score_info['cluster_id']}: Normalized_Score={score_info['normalized_score']:.4f}")
            print(f"      TAC_ZScore={score_info['tac_zscore']:.4f} (raw={score_info['raw_mean_tac']:.4f})")
            print(f"      STD_ZScore={score_info['std_zscore']:.4f} (raw={score_info['raw_std_tac']:.4f})")
            print(f"      Slope_ZScore={score_info['slope_zscore']:.4f} (raw={score_info['raw_mean_slope']:.4f})")
    
    return baseline_cluster_id, data

def determine_curve_threshold(df: pd.DataFrame, default_threshold: float = 8.0, 
                                k_values: list = [3, 4, 5, 6], window_size: int = 15) -> Tuple[float, float, Union[float, None], Union[float, None]]:
    """
    Determine the curve threshold using k-means clustering with time-series features.
    
    Args:
        df (pd.DataFrame): DataFrame containing TAC data
        default_threshold (float): Default threshold to use if calculation fails
        k_values (list): List of k values to test
        window_size (int): Size of the rolling window for time-series features (default: 15)
        
    Returns:
        tuple[float, float, float | None, float | None]: 
            - First float: The actual threshold to use (capped between 1 and default_threshold)
            - Second float: The calculated threshold before capping
            - Third float: Baseline mean (None if calculation failed)
            - Fourth float: Always None (kept for compatibility)
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
        
        # Calculate time-series features for all rows (including negative TAC values)
        data = calculate_time_series_features(data, 'TAC', window_size)
        
        # Store original data for labeling
        original_data = data.copy()
        
        # Drop rows with TAC < -5 before clustering
        clustering_data = data[data['TAC'] >= -5].copy()
        
        # Drop any remaining NaN values
        feature_columns = ['mean_TAC', 'std_TAC', 'slope', 'd1', 'range']  # Removed 'TAC' as feature
        clustering_data = clustering_data.dropna(subset=feature_columns).copy()
        
        # Verify we still have enough data after cleaning
        if len(clustering_data) < MIN_DATA_POINTS:  # Less than 4 hours of data
            print("WARNING: Curve threshold identification failed - Insufficient data after cleaning")
            return default_threshold, default_threshold, None, None

        # Evaluate clustering quality for different k values
        print(f"Evaluating clustering quality for k values: {k_values}")
        quality_metrics = evaluate_clustering_quality(clustering_data, feature_columns, k_values)
        
        for k, metrics in quality_metrics.items():
            print(f"  k={k}: Silhouette={metrics['silhouette']:.4f}, "
                  f"Calinski-Harabasz={metrics['calinski_harabasz']:.4f}, "
                  f"Davies-Bouldin={metrics['davies_bouldin']:.4f}")
        
        # Select optimal k using silhouette score (higher is better)
        best_k = None
        best_silhouette = -1
        
        for k, metrics in quality_metrics.items():
            silhouette = metrics.get('silhouette', -1)
            if not np.isnan(silhouette) and silhouette > best_silhouette:
                best_silhouette = silhouette
                best_k = k
        
        # Fallback to first k value if no valid silhouette scores found
        if best_k is None:
            optimal_k = k_values[0]
            print(f"WARNING: No valid silhouette scores found, using k={optimal_k}")
        else:
            optimal_k = best_k
            print(f"Selected k={optimal_k} based on best silhouette score: {best_silhouette:.4f}")
        
        # Store clustering quality metrics for the selected k
        selected_k_metrics = quality_metrics.get(optimal_k, {})
        
        # Store quality metrics in clustering_data for later access
        clustering_data.attrs['quality_metrics'] = quality_metrics
        clustering_data.attrs['optimal_k'] = optimal_k
        
        # Perform clustering and identify baseline cluster
        baseline_cluster_id, clustering_data = identify_baseline_cluster(clustering_data, feature_columns, optimal_k)
        
        # Calculate baseline cluster statistics
        baseline_data = clustering_data[clustering_data['Cluster'] == baseline_cluster_id]
        baseline_mean = baseline_data['TAC'].mean()
        
        # Calculate threshold using baseline + SD_MULTIPLIER*SD approach
        baseline_std = baseline_data['TAC'].std()
        threshold = baseline_mean + (SD_MULTIPLIER * baseline_std)
        print(f"  Baseline Standard Deviation: {baseline_std:.2f}")
        print(f"  Threshold (Mean + {SD_MULTIPLIER}SD): {threshold:.2f}")

        # Label the main dataframe with cluster information
        original_data = label_main_dataframe_with_clusters(original_data, clustering_data, baseline_cluster_id)
        
        # Store the labeled data back to the main dataframe
        df.attrs['labeled_cluster_data'] = original_data

        # Log the results
        print(f"Curve Threshold Identification Results:")
        print(f"  Optimal K: {optimal_k}")
        print(f"  Baseline Cluster ID: {baseline_cluster_id}")
        print(f"  Baseline Mean TAC: {baseline_mean:.2f}")
        print(f"  Baseline Standard Deviation: {baseline_data['TAC'].std():.2f}")
        print(f"  Curve Threshold (Mean + {SD_MULTIPLIER}SD): {threshold:.2f}")

        # Cap threshold between MIN_THRESHOLD and default_threshold
        # This ensures the calculated threshold respects the analysis-specific upper bound
        capped_threshold = max(MIN_THRESHOLD, min(default_threshold, threshold))
        
        return capped_threshold, threshold, baseline_mean, None
        
    except Exception as e:
        print(f"ERROR: Curve threshold identification failed - {str(e)}")
        print("Full traceback:")
        print(traceback.format_exc())
        return default_threshold, default_threshold, None, None

# Legacy function removed - replaced by the new determine_curve_threshold function above
# def determine_curve_threshold(df: pd.DataFrame, default_threshold: float = 10.0) -> Tuple[float, float, Union[float, None], Union[float, None]]:
#     """
#     Determine the threshold for identifying curves in TAC data using k-means clustering.
#     
#     Args:
#         df (pd.DataFrame): DataFrame containing TAC data
#         default_threshold (float): Default threshold to use if calculation fails or data is insufficient
#         
#     Returns:
#         tuple[float, float, float | None, float | None]: 
#             - First float: The actual threshold to use (capped between 1 and 10)
#             - Second float: The calculated threshold before capping
#             - Third float: Baseline mean (None if calculation failed)
#             - Fourth float: Baseline standard deviation (None if calculation failed)
#     """
#     try:
#         data = df.copy()
#         
#         # Validate input data
#         if 'TAC' not in data.columns:
#             print("WARNING: Curve threshold identification failed - No 'TAC' column found in data")
#             return default_threshold, default_threshold, None, None
#             
#         # Check for minimum data requirement (4 hours)
#         if (data['TAC'].count() / 60) < 4:
#             print("WARNING: Curve threshold identification failed - Less than 4 hours of TAC data available")
#             return default_threshold, default_threshold, None, None
#             
#         # Clean and prepare data
#         # Drop non-wear periods
#         data = data[data['device_worn_model'] == 1].copy()
#         
#         # Handle negative values
#         mask = data['TAC'] < 0
#         if mask.any():
#             data.loc[mask, 'TAC'] = np.random.normal(loc=1.0, scale=0.3, size=mask.sum()).clip(0, 2)
#         
#         # Calculate consecutive indices
#         data['consecutive'] = (data.index.to_series().diff() == 1)
#         data.loc[data.index[0], 'consecutive'] = True  # First row is always consecutive
#         
#         # TAC_Change - only calculate for consecutive rows
#         data['TAC_Change'] = data['TAC'].diff()
#         data.loc[~data['consecutive'], 'TAC_Change'] = np.nan
#         
#         # TAC_RollingStd - use trailing window and ensure all points in window are consecutive
#         window_size = 5
#         data['TAC_RollingStd'] = data['TAC'].rolling(
#             window=window_size,
#             min_periods=window_size  # Require full window for calculation
#         ).std()
#         
#         # Create a mask for windows where all points are consecutive
#         consecutive_mask_throughout_window = data['consecutive'].rolling(
#             window=window_size,
#             min_periods=window_size
#         ).apply(lambda x: x.all()).astype(bool)
#         
#         # Set TAC_RollingStd to NaN where the window contains non-consecutive points
#         data.loc[~consecutive_mask_throughout_window, 'TAC_RollingStd'] = np.nan
#         
#         # Drop any remaining NaN values
#         data = data.dropna(subset=['TAC', 'TAC_Change', 'TAC_RollingStd']).copy()
#         
#         # Verify we still have enough data after cleaning
#         if len(data) < 240:  # Less than 4 hours of data
#             print("WARNING: Curve threshold identification failed - Insufficient data after cleaning")
#             return default_threshold, default_threshold, None, None
# 
#         features = ['TAC', 'TAC_Change', 'TAC_RollingStd']
#         data, optimal_k = get_tac_clusters(data, features)
# 
#         # Identify baseline cluster and calculate threshold
#         baseline_cluster = data.groupby('Cluster')['TAC'].mean().idxmin()
#         baseline_mean = data[data['Cluster'] == baseline_cluster]['TAC'].mean()
#         baseline_std = data[data['Cluster'] == baseline_cluster]['TAC'].std()
#         
#         # Calculate threshold using 2 standard deviations
#         threshold = baseline_mean + (2 * baseline_std)
# 
#         # Log the results
#         print(f"Curve Threshold Identification Results:")
#         print(f"  Optimal K: {optimal_k}")
#         print(f"  Baseline Mean TAC: {baseline_mean:.2f}")
#         print(f"  Baseline Standard Deviation: {baseline_std:.2f}")
#         print(f"  Curve Threshold (Mean + 2SD): {threshold:.2f}")
# 
#         # Cap threshold between 1 and 10
#         capped_threshold = max(1.0, min(10.0, threshold))
#         
#         return capped_threshold, threshold, baseline_mean, baseline_std
#         
#     except Exception as e:
#         print(f"ERROR: Curve threshold identification failed - {str(e)}")
#         print("Full traceback:")
#         print(traceback.format_exc())
#         return default_threshold, default_threshold, None, None
  
def get_start_and_end_of_discrete_curves(df, curve_threshold, TAC_column = 'TAC'):
  above_threshold = np.sort(df[df[TAC_column] > curve_threshold].index)
  gaps = np.diff(above_threshold)
  split_points = np.where(gaps > 1)[0]
  consecutive_sequences = np.split(above_threshold, split_points + 1)
  curve_start_and_end_indices = [[seq[0], seq[-1]] for seq in consecutive_sequences if len(seq) > 0]
  
  # Filter out blip curves (<5 min) and short curves (<60 min) with quality issues
  filtered_curves = []
  
  for start_idx, end_idx in curve_start_and_end_indices:
    # Filter out blip curves
    if (end_idx - start_idx) < 5:
      continue
    
    # # Apply additional quality filters to short curves (<60 min)
    # curve_length = end_idx - start_idx + 1
    # if curve_length < 60:
    #   curve_data = df.loc[start_idx:end_idx].reset_index(drop=True)
    #   
    #   # Filter out curves where rise or fall is ≥90% imputed
    #   if len(curve_data) > 0:
    #     peak_index = curve_data[TAC_column].idxmax()
    #     
    #     # Check rise portion (start to peak)
    #     rise_portion = curve_data.loc[:peak_index]
    #     if len(rise_portion) > 0:
    #       rise_imputed_count = (rise_portion['imputed'] == 1).sum()
    #       rise_imputed_percent = rise_imputed_count / len(rise_portion)
    #       
    #       if rise_imputed_percent >= 0.90:
    #         continue
    #     
    #     # Check fall portion (peak to end)
    #     fall_portion = curve_data.loc[peak_index:]
    #     if len(fall_portion) > 0:
    #       fall_imputed_count = (fall_portion['imputed'] == 1).sum()
    #       fall_imputed_percent = fall_imputed_count / len(fall_portion)
    #       
    #       if fall_imputed_percent >= 0.90:
    #         continue
    
    filtered_curves.append([start_idx, end_idx])
  
  return filtered_curves

def merge_nearby_curves(approved_curve_start_and_end_indices, max_curve_separation_minutes = 60, curve_minutes_limit = (60*24)):
  # First, perform the merging operation as before
  merged_curve_start_and_end_indices = []
  original_curve_mapping = []  # Track which original curves are merged together
  
  for i, (curve_start, curve_end) in enumerate(approved_curve_start_and_end_indices):
    if i > 0:
      prior_curve_start = merged_curve_start_and_end_indices[-1][0]  # Use start, not end
      prior_curve_end = merged_curve_start_and_end_indices[-1][1]
      merged_curve_minutes = curve_end - prior_curve_start
      
      # Determine merge distance based on curve length
      # Short curves (5-15 min) use half the merge distance
      current_curve_duration = curve_end - curve_start
      current_is_short = current_curve_duration < 15

      # Determine if the prior merged curve contains any short curves
      # Examine the most recent discrete curve that fed into the merged segment
      prior_original_indices = original_curve_mapping[-1]
      prior_is_short = False
      if prior_original_indices:
        last_orig_idx = prior_original_indices[-1]
        last_orig_start, last_orig_end = approved_curve_start_and_end_indices[last_orig_idx][:2]
        prior_is_short = (last_orig_end - last_orig_start) < 15

      if current_is_short or prior_is_short:
        # Any involvement of a short curve halves the allowable merge distance
        effective_merge_distance = max_curve_separation_minutes / 2
      else:
        # Only substantial curves involved: use full merge distance
        effective_merge_distance = max_curve_separation_minutes
      
      if (curve_start - prior_curve_end) < effective_merge_distance and (merged_curve_minutes < curve_minutes_limit):
        # Merge with previous curve
        merged_curve_start_and_end_indices[-1][1] = curve_end
        merged_curve_start_and_end_indices[-1][2] += 1
        # Track that this curve was merged
        original_curve_mapping[-1].append(i)
      else:
        # Start new curve
        merged_curve_start_and_end_indices.append([curve_start, curve_end, 1])
        original_curve_mapping.append([i])
    else:
        # First curve
        merged_curve_start_and_end_indices.append([curve_start, curve_end, 1])
        original_curve_mapping.append([i])
  
  # Now filter out short standalone curves
  filtered_merged_curves = []
  min_curve_length = 15  # Minimum curve length in minutes
  
  for i, (merged_start, merged_end, curve_count) in enumerate(merged_curve_start_and_end_indices):
    merged_duration = merged_end - merged_start
    
    # Check if this merged curve is substantial (≥15 min)
    is_substantial = merged_duration >= min_curve_length
    
    # Check if any of the original curves that formed this merged curve were substantial
    original_curve_indices = original_curve_mapping[i]
    has_substantial_anchor = False
    
    for orig_idx in original_curve_indices:
      if orig_idx < len(approved_curve_start_and_end_indices):
        orig_start, orig_end = approved_curve_start_and_end_indices[orig_idx][:2]
        orig_duration = orig_end - orig_start
        if orig_duration >= min_curve_length:
          has_substantial_anchor = True
          break
    
    # Keep the curve if:
    # 1. The merged curve itself is substantial (≥15 min), OR
    # 2. It contains at least one substantial anchor curve (≥15 min)
    if is_substantial or has_substantial_anchor:
      filtered_merged_curves.append([merged_start, merged_end, curve_count])
  
  return filtered_merged_curves 

def get_curve_threshold_from_method(df: pd.DataFrame, curve_threshold_method: Union[str, float, int], default_threshold: float = 8.0, 
                                  k_values: list = [3, 4, 5, 6], window_size: int = 15) -> Tuple[float, Dict]:
    """
    Determine the curve threshold based on the specified method.
    
    Args:
        df (pd.DataFrame): DataFrame containing TAC data
        curve_threshold_method (str | float | int): Either 'auto' or a numeric threshold
        k_values (list): List of k values to test for clustering (used when method is 'auto')
        window_size (int): Size of the rolling window for time-series features (used when method is 'auto')
        
    Returns:
        tuple[float, Dict]: 
            - First float: The actual threshold to use
            - Second Dict: Comprehensive results dictionary with all threshold determination details
            
    Raises:
        ValueError: If curve_threshold_method is invalid
    """
    try:
        if curve_threshold_method == 'auto':
            result = determine_curve_threshold(df, default_threshold, k_values, window_size)
            if result is None or result[0] is None or result[1] is None or result[2] is None:
                raise ValueError("Failed to automatically determine curve threshold")
            
            # Unpack the result
            capped_threshold, unadjusted_threshold, baseline_mean, next_mean = result
            
            # Get clustering metrics from the data attributes
            quality_metrics = getattr(df, 'attrs', {}).get('quality_metrics', {})
            optimal_k = getattr(df, 'attrs', {}).get('optimal_k', k_values[0])
            selected_k_metrics = quality_metrics.get(optimal_k, {})
            
            # Create comprehensive results dictionary
            results_dict = {
                'curve_threshold': capped_threshold,
                'unadjusted_threshold': unadjusted_threshold,
                'baseline_mean': baseline_mean,
                'next_cluster_mean': None,  # No longer used with 2.5SD approach
                'threshold_method': curve_threshold_method,
                'threshold_calculation_method': 'baseline_2.5sd',
                'beta_value': None,  # No longer used
                'threshold_capped': capped_threshold != unadjusted_threshold,
                'capped_reason': None,
                'optimal_k': optimal_k,
                'k_values_tested': k_values,
                'clustering_quality_silhouette': selected_k_metrics.get('silhouette', np.nan),
                'clustering_quality_calinski_harabasz': selected_k_metrics.get('calinski_harabasz', np.nan),
                'clustering_quality_davies_bouldin': selected_k_metrics.get('davies_bouldin', np.nan),
                'clustering_quality_inertia': selected_k_metrics.get('inertia', np.nan)
            }
            
            # Determine why threshold was capped
            if capped_threshold != unadjusted_threshold:
                if unadjusted_threshold < MIN_THRESHOLD:
                    results_dict['capped_reason'] = f'below_minimum_{MIN_THRESHOLD}'
                elif unadjusted_threshold > default_threshold:
                    results_dict['capped_reason'] = f'above_maximum_{default_threshold}'
            
            return capped_threshold, results_dict
            
        elif isinstance(curve_threshold_method, (int, float)):
            threshold = float(curve_threshold_method)
            
            # Create results dictionary for manual threshold
            results_dict = {
                'curve_threshold': threshold,
                'unadjusted_threshold': threshold,
                'baseline_mean': None,
                'next_cluster_mean': None,
                'threshold_method': curve_threshold_method,
                'threshold_calculation_method': 'manual',
                'beta_value': None,
                'threshold_capped': False,
                'capped_reason': None,
                'optimal_k': None,
                'k_values_tested': None,
                'clustering_quality_silhouette': None,
                'clustering_quality_calinski_harabasz': None,
                'clustering_quality_davies_bouldin': None,
                'clustering_quality_inertia': None
            }
            
            return threshold, results_dict
        else:
            raise ValueError(f"Invalid curve_threshold value: {curve_threshold_method}")
    except Exception as e:
        print(f"Error determining curve threshold: {str(e)}")
        
        # Create fallback results dictionary
        fallback_dict = {
            'curve_threshold': default_threshold,
            'unadjusted_threshold': default_threshold,
            'baseline_mean': None,
            'next_cluster_mean': None,
            'threshold_method': 'fallback',
            'threshold_calculation_method': 'error_fallback',
            'beta_value': None,
            'threshold_capped': False,
            'capped_reason': None,
            'optimal_k': None,
            'k_values_tested': None,
            'clustering_quality_silhouette': None,
            'clustering_quality_calinski_harabasz': None,
            'clustering_quality_davies_bouldin': None,
            'clustering_quality_inertia': None
        }
        
        return default_threshold, fallback_dict

def label_main_dataframe_with_clusters(original_data: pd.DataFrame, clustering_data: pd.DataFrame, baseline_cluster_id: int) -> pd.DataFrame:
    """
    Label the main dataframe with cluster information, clearly marking baseline cluster and excluded values.
    
    Args:
        original_data (pd.DataFrame): Original dataframe with all rows and features
        clustering_data (pd.DataFrame): Dataframe used for clustering (filtered data)
        baseline_cluster_id (int): ID of the baseline cluster
        
    Returns:
        pd.DataFrame: Original dataframe with cluster labels added
    """
    # Create a copy to avoid modifying the original
    labeled_data = original_data.copy()
    
    # Initialize cluster column with 'excluded' for all rows
    labeled_data['cluster_label'] = 'excluded'
    labeled_data['cluster_id'] = np.nan
    labeled_data['is_baseline'] = False
    
    # Get the indices that were used in clustering
    clustering_indices = clustering_data.index
    
    # Label rows that were used in clustering
    for idx in clustering_indices:
        if idx in labeled_data.index:
            cluster_id = clustering_data.loc[idx, 'Cluster']
            labeled_data.loc[idx, 'cluster_id'] = cluster_id
            labeled_data.loc[idx, 'cluster_label'] = f'cluster_{cluster_id}'
            
            # Mark baseline cluster
            if cluster_id == baseline_cluster_id:
                labeled_data.loc[idx, 'cluster_label'] = 'baseline'
                labeled_data.loc[idx, 'is_baseline'] = True
    
    # Add reason for exclusion
    labeled_data['exclusion_reason'] = 'none'
    
    # Mark rows excluded due to TAC < -5
    tac_excluded_mask = labeled_data['TAC'] < -5
    labeled_data.loc[tac_excluded_mask, 'exclusion_reason'] = 'TAC < -5'
    
    # Mark rows excluded due to missing features (NaN values)
    feature_columns = ['mean_TAC', 'std_TAC', 'slope', 'd1', 'range']
    nan_excluded_mask = labeled_data[feature_columns].isna().any(axis=1)
    labeled_data.loc[nan_excluded_mask, 'exclusion_reason'] = 'missing_features'
    
    # Mark rows excluded due to non-wear periods
    non_wear_mask = labeled_data['device_worn_model'] != 1
    labeled_data.loc[non_wear_mask, 'exclusion_reason'] = 'non_wear_period'
    
    # For rows that were excluded but have valid TAC values, check if they were excluded due to features
    valid_tac_mask = (labeled_data['TAC'] >= -5) & (labeled_data['device_worn_model'] == 1)
    excluded_by_features = valid_tac_mask & (labeled_data['cluster_label'] == 'excluded')
    labeled_data.loc[excluded_by_features, 'exclusion_reason'] = 'missing_features'
    
    return labeled_data
    
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

    