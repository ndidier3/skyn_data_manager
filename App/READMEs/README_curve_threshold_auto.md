AUTOMATIC CURVE THRESHOLD COMPUTATION
====================================

OVERVIEW:
Automatically determines optimal threshold for identifying TAC (Transdermal Alcohol 
Concentration) curves using k-means clustering with time-series features. The system 
analyzes TAC data patterns to distinguish between baseline (normal) TAC levels and 
elevated TAC levels representing drinking events. Uses Z-score normalization for 
fair baseline cluster assessment across different TAC ranges, with safety rule to 
prevent selection of high-TAC clusters as baseline.

PSEUDOCODE:
===========

1. DATA PREPARATION:
   Filter dataset for device_worn_model == 1 (device being worn)
   Calculate consecutive indices to maintain temporal relationships
   Verify minimum 4 hours of TAC data available
   
2. FEATURE ENGINEERING (5 total features):
   mean_TAC = rolling_mean(TAC, window=15)
   std_TAC = rolling_std(TAC, window=15)
   slope = linear_regression_slope(TAC_window)
   d1 = mean(|ΔTAC|) over window
   range = max(TAC_window) - min(TAC_window)
   
   Note: Time-series features only calculated for consecutive data points
   
3. CLUSTERING EVALUATION:
   For k in [3, 4, 5, 6]:
       kmeans = KMeans(n_clusters=k, init='k-means++', n_init=10)
       cluster_labels = kmeans.fit_predict(scaled_features)
       
       Calculate metrics:
       - silhouette_score
       - calinski_harabasz_score  
       - davies_bouldin_score
       - inertia
   
   Select optimal k based on highest silhouette score:
   optimal_k = argmax(silhouette_score for each k)
   
4. BASELINE CLUSTER IDENTIFICATION:
   For each cluster:
       Calculate: mean_TAC, std_TAC, mean_slope, consecutive_stretches
       
   SAFETY RULE: If any cluster has mean_TAC > 10, default to lowest TAC cluster
   Otherwise, use Z-score normalized criteria:
       - TAC_ZScore: |mean_TAC - overall_mean| / overall_std (minimize)
       - STD_ZScore: (std_TAC - overall_std_mean) / overall_std_std (minimize)
       - Slope_ZScore: (|mean_slope| - overall_slope_mean) / overall_slope_std (minimize)
       - Combined normalized score = TAC_ZScore + STD_ZScore + Slope_ZScore (minimize)
   
5. THRESHOLD CALCULATION:
   baseline_mean = mean(TAC of baseline_cluster)
   baseline_std = std(TAC of baseline_cluster)
   threshold = baseline_mean + (2.5 × baseline_std)
   
   Apply bounds: threshold = max(1.0, min(10.0, threshold))

DETECTION CRITERIA:
==================
- Minimum data requirement: 4 hours of TAC data
- Window size: 15 consecutive TAC readings
- Clustering: k-means++ with n_init≥10
- K values tested: [3, 4, 5, 6]
- K selection: Based on highest silhouette score (best clustering quality)
- Baseline selection: Cluster with TAC nearest zero and lowest variance
- Threshold formula: baseline_mean + (2.5 × baseline_std)
- Threshold bounds: [1.0, 10.0] μg/L

FEATURE CALCULATION:
===================
- mean_TAC: Rolling average over 15-point window
- std_TAC: Rolling standard deviation over 15-point window  
- slope: Linear regression slope over window
- d1: Mean absolute difference between consecutive points
- range: Maximum minus minimum TAC in window

BASELINE IDENTIFICATION:
=======================
- SAFETY RULE: If any cluster mean_TAC > 10, default to lowest TAC cluster
- Z-score normalization across all clusters for fair comparison (when safety rule not active)
- TAC_ZScore: Minimize distance from overall TAC mean (normalized)
- STD_ZScore: Minimize deviation from overall standard deviation mean (normalized)
- Slope_ZScore: Minimize deviation from overall slope mean (normalized)
- Combined normalized score: Sum of all Z-scores (lower is better)
- Optional: Time continuity (consecutive stretches count)
- Cluster selection: Safety rule or best normalized score ranking

THRESHOLD CALCULATION:
======================
- Method: Baseline + 2.5 Standard Deviations
- Formula: threshold = baseline_mean + (2.5 × baseline_std)
- Rationale: 2.5 SD represents statistically significant deviation from baseline
- Advantages: Simple, statistically sound, no dependency on other clusters
- No more beta positioning or next cluster identification needed

THRESHOLD BOUNDS:
=================
- Lower bound: 1.0 μg/L (minimum biologically relevant threshold)
- Upper bound: 10.0 μg/L (maximum reasonable threshold)
- Capping: Applied after calculation to ensure reasonable bounds

FALLBACK BEHAVIOR:
==================
- Insufficient data: < 4 hours TAC data → default_threshold = 10.0
- Missing columns: No 'TAC' column → default_threshold = 10.0
- Calculation errors: Any exception → default_threshold = 10.0
- Insufficient data after cleaning: < 240 points → default_threshold = 10.0
