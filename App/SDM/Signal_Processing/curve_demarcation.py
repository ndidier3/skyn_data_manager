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
FEATURE_COLUMNS = ['mean_TAC', 'std_TAC', 'slope', 'd1', 'range']


def _json_safe(value):
    """Convert numpy scalars/containers to plain Python for pickle and Excel."""
    if value is None:
        return None
    if isinstance(value, (np.floating, float)):
        return None if pd.isna(value) else float(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


def empty_curve_threshold_results(**overrides) -> Dict:
    """Dataset-level threshold record. Scalar keys are safe to copy onto curve rows."""
    results = {
        'curve_threshold': None,
        'unadjusted_threshold': None,
        'baseline_mean': None,
        'baseline_sd': None,
        'next_cluster_mean': None,
        'threshold_method': None,
        'threshold_calculation_method': None,
        'threshold_rule_applied': None,
        'fallback_threshold': None,
        'beta_value': None,
        'threshold_capped': False,
        'capped_reason': None,
        'optimal_k': None,
        'k_values_tested': None,
        'window_size': None,
        'feature_columns': None,
        'n_minutes_clustered': None,
        'n_minutes_baseline': None,
        'baseline_cluster_id': None,
        'selection_method': None,
        'use_safety_rule': None,
        'n_clusters_mean_tac_gt_10': None,
        'cluster_stats': None,
        'baseline_scores': None,
        'quality_metrics_by_k': None,
        'clustering_quality_silhouette': None,
        'clustering_quality_calinski_harabasz': None,
        'clustering_quality_davies_bouldin': None,
        'clustering_quality_inertia': None,
    }
    results.update(overrides)
    return results


def _metrics_for_k(quality_metrics: Dict, k) -> Dict:
    if not quality_metrics:
        return {}
    if k in quality_metrics:
        return quality_metrics[k] or {}
    return quality_metrics.get(str(k), {}) or {}


def _store_threshold_details(df: pd.DataFrame, attrs_key: str = 'curve_threshold_details', **fields) -> None:
    """Write dataset-level threshold details onto the minute-level frame (pickled with .sdp)."""
    existing = getattr(df, 'attrs', {}).get(attrs_key, {}) or {}
    existing.update(fields)
    df.attrs[attrs_key] = existing
    if attrs_key == 'curve_threshold_details':
        df.attrs['quality_metrics'] = existing.get('quality_metrics_by_k')
        df.attrs['optimal_k'] = existing.get('optimal_k')

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

def identify_baseline_cluster(data: pd.DataFrame, features: list, k: int = 2, tac_column: str = 'TAC') -> Tuple[int, pd.DataFrame, Dict]:
    """
    Identify the baseline cluster using k-means clustering with Z-score normalized criteria.
    
    Args:
        data (pd.DataFrame): DataFrame with features
        features (list): List of feature column names
        k (int): Number of clusters to use
        
    Returns:
        Tuple[int, pd.DataFrame, Dict]: Baseline cluster ID, labeled data, and selection details
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
        mean_tac = cluster_data[tac_column].mean()
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
    
    details = {
        'baseline_cluster_id': int(baseline_cluster_id),
        'selection_method': baseline_scores[0]['selection_method'],
        'use_safety_rule': bool(use_safety_rule),
        'n_clusters_mean_tac_gt_10': int(len(high_tac_clusters)),
        'cluster_stats': _json_safe(cluster_stats),
        'baseline_scores': _json_safe(baseline_scores),
    }
    return baseline_cluster_id, data, details

def determine_curve_threshold(df: pd.DataFrame, default_threshold: float = 8.0, 
                                k_values: list = [3, 4, 5, 6], window_size: int = 15,
                                TAC_column: str = 'TAC',
                                details_attrs_key: str = 'curve_threshold_details',
                                label_main_dataframe: bool = True) -> Tuple[float, float, Union[float, None], Union[float, None]]:
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
            - Fourth float: Baseline standard deviation (None if calculation failed)
    """
    try:
        data = df.copy()
        
        # Validate input data
        if TAC_column not in data.columns:
            print(f"WARNING: Curve threshold identification failed - No '{TAC_column}' column found in data")
            _store_threshold_details(df, attrs_key=details_attrs_key, failure_reason='no_tac_column')
            return default_threshold, default_threshold, None, None
            
        # Check for minimum data requirement (4 hours)
        if (data[TAC_column].count() / 60) < 4:
            print("WARNING: Curve threshold identification failed - Less than 4 hours of TAC data available")
            _store_threshold_details(df, attrs_key=details_attrs_key, failure_reason='insufficient_tac_hours')
            return default_threshold, default_threshold, None, None
            
        # Clean and prepare data
        # Drop non-wear periods
        data = data[data['device_worn_model'] == 1].copy()
        
        # Calculate time-series features for all rows (including negative TAC values)
        data = calculate_time_series_features(data, TAC_column, window_size)
        
        # Store original data for labeling
        original_data = data.copy()
        
        # Drop rows with TAC < -10 before clustering
        clustering_data = data[data[TAC_column] >= -10].copy()
        
        # Drop any remaining NaN values
        feature_columns = list(FEATURE_COLUMNS)
        clustering_data = clustering_data.dropna(subset=feature_columns).copy()
        
        # Verify we still have enough data after cleaning
        if len(clustering_data) < MIN_DATA_POINTS:  # Less than 4 hours of data
            print("WARNING: Curve threshold identification failed - Insufficient data after cleaning")
            _store_threshold_details(df, attrs_key=details_attrs_key, failure_reason='insufficient_data_after_cleaning')
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
        quality_metrics_by_k = _json_safe(quality_metrics)
        
        # Perform clustering and identify baseline cluster
        baseline_cluster_id, clustering_data, baseline_details = identify_baseline_cluster(
            clustering_data, feature_columns, optimal_k, tac_column=TAC_column
        )
        
        # Calculate baseline cluster statistics
        baseline_data = clustering_data[clustering_data['Cluster'] == baseline_cluster_id]
        baseline_mean = baseline_data[TAC_column].mean()
        baseline_std = baseline_data[TAC_column].std()
        
        # Calculate threshold using baseline + SD_MULTIPLIER*SD approach
        threshold = baseline_mean + (SD_MULTIPLIER * baseline_std)
        print(f"  Baseline Standard Deviation: {baseline_std:.2f}")
        print(f"  Threshold (Mean + {SD_MULTIPLIER}SD): {threshold:.2f}")

        # Label the main dataframe with cluster information (imputed pipeline only)
        if label_main_dataframe:
            original_data = label_main_dataframe_with_clusters(original_data, clustering_data, baseline_cluster_id)
            df.attrs['labeled_cluster_data'] = original_data

        # Log the results
        print(f"Curve Threshold Identification Results:")
        print(f"  Optimal K: {optimal_k}")
        print(f"  Baseline Cluster ID: {baseline_cluster_id}")
        print(f"  Baseline Mean TAC: {baseline_mean:.2f}")
        print(f"  Baseline Standard Deviation: {baseline_data[TAC_column].std():.2f}")
        print(f"  Curve Threshold (Mean + {SD_MULTIPLIER}SD): {threshold:.2f}")

        # Progressive fallback approach for threshold capping
        fallback_threshold = baseline_mean + 6.0
        if threshold < default_threshold:
            # Use the calculated 2.5SD threshold
            capped_threshold = max(MIN_THRESHOLD, threshold)
            if threshold < MIN_THRESHOLD:
                threshold_rule_applied = 'below_minimum'
            else:
                threshold_rule_applied = 'mean_plus_2.5sd'
            print(f"  Using calculated threshold: {capped_threshold:.2f}")
        else:
            print(f"  Calculated threshold exceeds default. Trying fallback (baseline + 6): {fallback_threshold:.2f}")
            
            if fallback_threshold < default_threshold:
                capped_threshold = fallback_threshold
                threshold_rule_applied = 'baseline_plus_6'
                print(f"  Using fallback threshold: {capped_threshold:.2f}")
            else:
                capped_threshold = default_threshold
                threshold_rule_applied = 'default_cap'
                print(f"  Fallback also exceeds default. Using default threshold: {capped_threshold:.2f}")

        _store_threshold_details(
            df,
            attrs_key=details_attrs_key,
            tac_column=TAC_column,
            window_size=window_size,
            feature_columns=list(feature_columns),
            n_minutes_clustered=int(len(clustering_data)),
            n_minutes_baseline=int(len(baseline_data)),
            optimal_k=int(optimal_k),
            k_values_tested=list(k_values),
            quality_metrics_by_k=quality_metrics_by_k,
            clustering_quality_silhouette=_json_safe(selected_k_metrics.get('silhouette')),
            clustering_quality_calinski_harabasz=_json_safe(selected_k_metrics.get('calinski_harabasz')),
            clustering_quality_davies_bouldin=_json_safe(selected_k_metrics.get('davies_bouldin')),
            clustering_quality_inertia=_json_safe(selected_k_metrics.get('inertia')),
            baseline_mean=_json_safe(baseline_mean),
            baseline_sd=_json_safe(baseline_std),
            unadjusted_threshold=_json_safe(threshold),
            curve_threshold=_json_safe(capped_threshold),
            fallback_threshold=_json_safe(fallback_threshold),
            threshold_rule_applied=threshold_rule_applied,
            **baseline_details,
        )
        
        return capped_threshold, threshold, baseline_mean, baseline_std
        
    except Exception as e:
        print(f"ERROR: Curve threshold identification failed - {str(e)}")
        print("Full traceback:")
        print(traceback.format_exc())
        try:
            _store_threshold_details(df, attrs_key=details_attrs_key, failure_reason=str(e))
        except Exception:
            pass
        return default_threshold, default_threshold, None, None
  
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
      
      # Determine merge distance based on sum of most recent discrete curve + incoming curve
      # This prevents accumulation and keeps decisions local to neighboring curves
      current_curve_duration = curve_end - curve_start

      # Get the duration of the most recent discrete curve in the prior merged segment
      prior_original_indices = original_curve_mapping[-1]
      if prior_original_indices:
        last_orig_idx = prior_original_indices[-1]
        last_orig_start, last_orig_end = approved_curve_start_and_end_indices[last_orig_idx][:2]
        most_recent_discrete_duration = last_orig_end - last_orig_start
      else:
        # Fallback: if no discrete curves tracked, use the merged curve duration
        most_recent_discrete_duration = merged_curve_start_and_end_indices[-1][1] - merged_curve_start_and_end_indices[-1][0]

      # Sum the two neighboring curves (most recent + current) with cap
      effective_merge_distance = min(most_recent_discrete_duration + current_curve_duration, max_curve_separation_minutes)
      
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
    
    # Keep the curve if the merged span (including gaps) is ≥15 min
    # Note: If any anchor curve was ≥15 min, the merged duration must also be ≥15 min
    # since the merged duration includes all anchor curves plus any gaps
    if merged_duration >= min_curve_length:
      filtered_merged_curves.append([merged_start, merged_end, curve_count])
  
  return filtered_merged_curves 

def get_curve_threshold_from_method(df: pd.DataFrame, curve_threshold_method: Union[str, float, int], default_threshold: float = 8.0, 
                                  k_values: list = [3, 4, 5, 6], window_size: int = 15,
                                  TAC_column: str = 'TAC',
                                  details_attrs_key: str = 'curve_threshold_details',
                                  results_attrs_key: str = 'curve_threshold_results',
                                  label_main_dataframe: bool = True) -> Tuple[float, Dict]:
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
            result = determine_curve_threshold(
                df, default_threshold, k_values, window_size,
                TAC_column=TAC_column,
                details_attrs_key=details_attrs_key,
                label_main_dataframe=label_main_dataframe,
            )
            if result is None or result[0] is None or result[1] is None or result[2] is None:
                raise ValueError("Failed to automatically determine curve threshold")
            
            capped_threshold, unadjusted_threshold, baseline_mean, baseline_sd = result
            details = getattr(df, 'attrs', {}).get(details_attrs_key, {}) or {}
            quality_metrics = details.get('quality_metrics_by_k') or getattr(df, 'attrs', {}).get('quality_metrics', {}) or {}
            optimal_k = details.get('optimal_k', getattr(df, 'attrs', {}).get('optimal_k', k_values[0]))
            selected_k_metrics = _metrics_for_k(quality_metrics, optimal_k)

            results_dict = empty_curve_threshold_results(
                curve_threshold=capped_threshold,
                unadjusted_threshold=unadjusted_threshold,
                baseline_mean=baseline_mean,
                baseline_sd=baseline_sd,
                next_cluster_mean=None,
                threshold_method=curve_threshold_method,
                threshold_calculation_method='baseline_2.5sd',
                threshold_rule_applied=details.get('threshold_rule_applied'),
                fallback_threshold=details.get('fallback_threshold'),
                beta_value=None,
                threshold_capped=capped_threshold != unadjusted_threshold,
                capped_reason=None,
                optimal_k=optimal_k,
                k_values_tested=details.get('k_values_tested', k_values),
                window_size=details.get('window_size', window_size),
                feature_columns=details.get('feature_columns', list(FEATURE_COLUMNS)),
                n_minutes_clustered=details.get('n_minutes_clustered'),
                n_minutes_baseline=details.get('n_minutes_baseline'),
                baseline_cluster_id=details.get('baseline_cluster_id'),
                selection_method=details.get('selection_method'),
                use_safety_rule=details.get('use_safety_rule'),
                n_clusters_mean_tac_gt_10=details.get('n_clusters_mean_tac_gt_10'),
                cluster_stats=details.get('cluster_stats'),
                baseline_scores=details.get('baseline_scores'),
                quality_metrics_by_k=quality_metrics,
                clustering_quality_silhouette=selected_k_metrics.get(
                    'silhouette', details.get('clustering_quality_silhouette', np.nan)
                ),
                clustering_quality_calinski_harabasz=selected_k_metrics.get(
                    'calinski_harabasz', details.get('clustering_quality_calinski_harabasz', np.nan)
                ),
                clustering_quality_davies_bouldin=selected_k_metrics.get(
                    'davies_bouldin', details.get('clustering_quality_davies_bouldin', np.nan)
                ),
                clustering_quality_inertia=selected_k_metrics.get(
                    'inertia', details.get('clustering_quality_inertia', np.nan)
                ),
            )
            
            if capped_threshold != unadjusted_threshold:
                if unadjusted_threshold < MIN_THRESHOLD:
                    results_dict['capped_reason'] = f'below_minimum_{MIN_THRESHOLD}'
                elif unadjusted_threshold > default_threshold:
                    results_dict['capped_reason'] = f'above_maximum_{default_threshold}'
            
            df.attrs[results_attrs_key] = results_dict
            return capped_threshold, results_dict
            
        elif isinstance(curve_threshold_method, (int, float)):
            threshold = float(curve_threshold_method)
            results_dict = empty_curve_threshold_results(
                curve_threshold=threshold,
                unadjusted_threshold=threshold,
                threshold_method=curve_threshold_method,
                threshold_calculation_method='manual',
                threshold_rule_applied='manual',
                threshold_capped=False,
            )
            df.attrs[results_attrs_key] = results_dict
            return threshold, results_dict
        else:
            raise ValueError(f"Invalid curve_threshold value: {curve_threshold_method}")
    except Exception as e:
        print(f"Error determining curve threshold: {str(e)}")
        fallback_dict = empty_curve_threshold_results(
            curve_threshold=default_threshold,
            unadjusted_threshold=default_threshold,
            threshold_method='fallback',
            threshold_calculation_method='error_fallback',
            threshold_rule_applied='error_fallback',
        )
        try:
            df.attrs[results_attrs_key] = fallback_dict
        except Exception:
            pass
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
    
    # Mark rows excluded due to TAC < -10
    tac_excluded_mask = labeled_data['TAC'] < -10
    labeled_data.loc[tac_excluded_mask, 'exclusion_reason'] = 'TAC < -10'
    
    # Mark rows excluded due to missing features (NaN values)
    feature_columns = list(FEATURE_COLUMNS)
    nan_excluded_mask = labeled_data[feature_columns].isna().any(axis=1)
    labeled_data.loc[nan_excluded_mask, 'exclusion_reason'] = 'missing_features'
    
    # Mark rows excluded due to non-wear periods
    non_wear_mask = labeled_data['device_worn_model'] != 1
    labeled_data.loc[non_wear_mask, 'exclusion_reason'] = 'non_wear_period'
    
    # For rows that were excluded but have valid TAC values, check if they were excluded due to features
    valid_tac_mask = (labeled_data['TAC'] >= -10) & (labeled_data['device_worn_model'] == 1)
    excluded_by_features = valid_tac_mask & (labeled_data['cluster_label'] == 'excluded')
    labeled_data.loc[excluded_by_features, 'exclusion_reason'] = 'missing_features'
    
    return labeled_data
    
def adjust_curve_demarcation_for_raw_tac(
    dataset, 
    curve_start_and_end_indices, 
    curve_threshold,
    max_curve_separation_minutes,
    TAC_column='TAC_pre_imputation',
):
    adjusted_indices = []
    
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


def _curve_window_seconds(begin, end) -> float:
    """Duration in seconds for a curve window (inclusive minute endpoints)."""
    if pd.isna(begin) or pd.isna(end):
        return 0.0
    return max(0.0, (pd.Timestamp(end) - pd.Timestamp(begin)).total_seconds())


def attach_imputed_curve_matches(raw_features: pd.DataFrame, imputed_features: pd.DataFrame) -> pd.DataFrame:
    """
    For each raw curve, set curve_id_imputed_match to the imputed curve_id with the
    highest fraction of the raw window overlapped by time (overlap / raw duration).
    """
    if raw_features is None or raw_features.empty:
        return raw_features
    raw_out = raw_features.copy()
    if imputed_features is None or imputed_features.empty:
        raw_out['curve_id_imputed_match'] = np.nan
        raw_out['imputed_match_overlap_percent'] = np.nan
        return raw_out
    if 'begin_CURVE' not in raw_out.columns or 'end_CURVE' not in imputed_features.columns:
        raise ValueError('begin_CURVE/end_CURVE required for overlap matching')

    match_ids = []
    match_pcts = []
    for _, raw_row in raw_out.iterrows():
        raw_start = raw_row['begin_CURVE']
        raw_end = raw_row['end_CURVE']
        raw_dur = _curve_window_seconds(raw_start, raw_end)
        if raw_dur <= 0:
            match_ids.append(np.nan)
            match_pcts.append(np.nan)
            continue
        best_id = np.nan
        best_pct = -1.0
        for _, imp_row in imputed_features.iterrows():
            overlap_start = max(pd.Timestamp(raw_start), pd.Timestamp(imp_row['begin_CURVE']))
            overlap_end = min(pd.Timestamp(raw_end), pd.Timestamp(imp_row['end_CURVE']))
            overlap = max(0.0, (overlap_end - overlap_start).total_seconds())
            if overlap <= 0:
                continue
            pct = overlap / raw_dur
            imp_id = imp_row['curve_id']
            if pct > best_pct or (pct == best_pct and not pd.isna(imp_id) and (pd.isna(best_id) or imp_id < best_id)):
                best_pct = pct
                best_id = imp_id
        if best_pct < 0:
            match_ids.append(np.nan)
            match_pcts.append(np.nan)
        else:
            match_ids.append(best_id)
            match_pcts.append(best_pct)

    raw_out['curve_id_imputed_match'] = match_ids
    raw_out['imputed_match_overlap_percent'] = match_pcts
    return raw_out

    