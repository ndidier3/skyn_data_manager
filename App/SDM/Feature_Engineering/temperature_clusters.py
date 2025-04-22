import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

def get_temperature_clusters(df):
    """
    Calculate temperature cluster features for non-wear detection.
    Uses 3 clusters to identify low, medium, and high temperature ranges.
    Returns features for the low cluster and aggregated features for medium+high clusters.
    """
    # Get temperature values and reshape for clustering
    temps = df['Temperature_C'].dropna().values.reshape(-1, 1)
    
    # Fit K-means with 3 clusters
    kmeans = KMeans(n_clusters=3, random_state=42)
    clusters = kmeans.fit_predict(temps)
    
    # Sort clusters by temperature (low to high)
    cluster_means = [temps[clusters == i].mean() for i in range(3)]
    sorted_cluster_indices = np.argsort(cluster_means)
    
    # Calculate cluster statistics
    features = {}
    
    # Low cluster features
    low_cluster_idx = sorted_cluster_indices[0]
    low_cluster_temps = temps[clusters == low_cluster_idx]
    features['temp_cluster_low_mean'] = low_cluster_temps.mean()
    features['temp_cluster_low_std'] = low_cluster_temps.std()
    features['temp_cluster_low_percent'] = len(low_cluster_temps) / len(temps)
    
    # Find longest consecutive sequence in low cluster
    low_cluster_indices = np.where(clusters == low_cluster_idx)[0]
    max_duration = 1
    current_duration = 1
    for j in range(1, len(low_cluster_indices)):
        if low_cluster_indices[j] == low_cluster_indices[j-1] + 1:
            current_duration += 1
            max_duration = max(max_duration, current_duration)
        else:
            current_duration = 1
    features['temp_cluster_low_max_duration'] = max_duration
    
    # Aggregate medium and high clusters
    med_high_cluster_indices = np.isin(clusters, sorted_cluster_indices[1:])
    med_high_temps = temps[med_high_cluster_indices]
    features['temp_cluster_med_high_mean'] = med_high_temps.mean()
    features['temp_cluster_med_high_std'] = med_high_temps.std()
    features['temp_cluster_med_high_percent'] = len(med_high_temps) / len(temps)
    
    # Find longest consecutive sequence in medium+high clusters
    med_high_indices = np.where(med_high_cluster_indices)[0]
    max_duration = 1
    current_duration = 1
    for j in range(1, len(med_high_indices)):
        if med_high_indices[j] == med_high_indices[j-1] + 1:
            current_duration += 1
            max_duration = max(max_duration, current_duration)
        else:
            current_duration = 1
    features['temp_cluster_med_high_max_duration'] = max_duration
    
    return features

