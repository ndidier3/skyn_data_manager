import numpy as np
import pandas as pd
import statistics as stats_package
from sklearn.metrics import r2_score

class TACAnalyzer:
    """Object-oriented analyzer for TAC-related features with caching for improved performance."""
    
    def __init__(self, df: pd.DataFrame, tac_column: str = 'TAC'):
        """
        Initialize the analyzer with a dataframe.
        
        Args:
            df: DataFrame containing the data
            tac_column: Column name for TAC values (default: 'TAC')
        """
        self.df = df
        self.tac_column = tac_column
        self._cache = {}
        
    def _get_cached(self, key, compute_func):
        """Get cached value or compute and cache it."""
        if key not in self._cache:
            self._cache[key] = compute_func()
        return self._cache[key]

    def get_auc(self):
        """Area under TAC (µg/L·min) via trapezoid on 1-minute rows (dx=1)."""
        def compute():
            if len(self.df) == 0:
                return None
            try:
                tac = self.df[self.tac_column].dropna().astype(float)
                if len(tac) == 0:
                    return None
                total_auc = np.trapz(tac, dx=1.0)
                return total_auc
            except Exception as e:
                print(f"Error calculating AUC: {e}")
                return None
        
        return self._get_cached('auc', compute)

    def get_mean_stdev_sem(self):
        """Calculate mean, standard deviation, and standard error of the mean."""
        def compute():
            if len(self.df) == 0:
                return None, None, None
            tac = self.df[self.tac_column]
            return tac.mean(), tac.std(), tac.sem()
        
        return self._get_cached('mean_stdev_sem', compute)

    def get_peak(self, window={}):
        """Get peak TAC value, optionally within a specified window."""
        def compute():
            if len(self.df) == 0:
                return None
            if len(window) > 0:
                window_length = window['window']
                index = window['index']
                previous_window = window_length if (index - window_length) > 0 else (index - 1)
                post_window = window_length if (index + window_length) < len(self.df) else ((len(self.df) - window_length) - 1)
                peak = self.df.loc[index-previous_window:index+post_window, self.tac_column].max()
            else:
                tac = self.df[self.tac_column]
                peak = tac.max()
            return peak if peak > 0.5 else 0.5  # prevent extremely low peaks for division purposes
        
        cache_key = f'peak_{str(window)}'
        return self._get_cached(cache_key, compute)

    def get_peak_index(self):
        """Get index of peak TAC value."""
        def compute():
            if len(self.df) == 0:
                return None
            data_series = self.df[self.tac_column]
            return self.df.index[self.df[self.tac_column] == data_series.max()].tolist()[0]
        
        return self._get_cached('peak_index', compute)

    def get_baseline_mean_stdev(self, baseline_count=10):
        """Calculate baseline mean and standard deviation from first N values."""
        def compute():
            if len(self.df) <= baseline_count:
                return None, None
            data_series = self.df[self.tac_column]
            baseline_values = data_series.loc[0:baseline_count]
            baseline_mean = baseline_values.mean()
            baseline_stdev = baseline_values.std()
            return baseline_mean, baseline_stdev
        
        cache_key = f'baseline_{baseline_count}'
        return self._get_cached(cache_key, compute)

    def get_rise_duration(self, time_variable, curve_threshold):
        """Calculate rise duration and related metrics."""
        def compute():
            if len(self.df) == 0:
                return 0, None, None
            
            peak_index = self.get_peak_index()
            if peak_index is None:
                return 0, None, None
                
            curve_threshold_reached = False
            index_count = 1
            while not curve_threshold_reached:
                if peak_index == 0:
                    curve_begins_index = 0
                    break
                if (peak_index - index_count) == 0:
                    curve_begins_index = 0
                    break
                if self.df.loc[peak_index - index_count, self.tac_column] < curve_threshold:
                    curve_begins_index = peak_index - index_count
                    curve_threshold_reached = True
                index_count += 1

            rise_duration = self.df.loc[peak_index, time_variable] - self.df.loc[curve_begins_index, time_variable]
            curve_begins_time = self.df.loc[curve_begins_index, 'Duration_Hrs']
            
            return rise_duration, curve_begins_index, curve_begins_time
        
        cache_key = f'rise_duration_{time_variable}_{curve_threshold}'
        return self._get_cached(cache_key, compute)

    def get_fall_duration(self, time_variable, curve_threshold):
        """Calculate fall duration and related metrics."""
        def compute():
            if len(self.df) == 0:
                return 0, None, None
            
            peak_index = self.get_peak_index()
            if peak_index is None:
                return 0, None, None
                
            post_peak_data = self.df.loc[peak_index:]
            unadjusted_curve_threshold = curve_threshold
            curve_threshold_reached = False
            index_count = 1
            
            if (index_count + peak_index) < len(self.df):
                if peak_index == len(self.df[self.tac_column].tolist())-1:
                    curve_ends_index = len(self.df[self.tac_column].tolist())-1
                else:  
                    while not curve_threshold_reached:
                        if (peak_index + index_count) == (len(self.df[self.tac_column]) - 1):
                            curve_ends_index = (len(self.df[self.tac_column]) - 1)
                            break
                        if self.df[self.tac_column].loc[peak_index + index_count] < curve_threshold:
                            curve_ends_index = peak_index + index_count
                            curve_threshold_reached = True
                        index_count += 1
                        # slightly increase curve threshold if it hasn't increased more than 5 TAC
                        if unadjusted_curve_threshold + 5 > curve_threshold:
                            curve_threshold += 0.005
            else:
                curve_ends_index = (len(self.df) - 1)

            fall_duration = post_peak_data.loc[curve_ends_index, time_variable] - post_peak_data.loc[peak_index, time_variable]

            if fall_duration == 0:
                fall_duration = 0

            return fall_duration, curve_ends_index, curve_threshold
        
        cache_key = f'fall_duration_{time_variable}_{curve_threshold}'
        return self._get_cached(cache_key, compute)

    def get_fall_completion(self, curve_ends_index, relative_peak, curve_fall_threshold):
        """Calculate fall completion percentage."""
        relative_tac_curve_end = (self.df.loc[curve_ends_index, self.tac_column] - curve_fall_threshold)
        unfinished_fall = relative_tac_curve_end > 0
        if unfinished_fall:
            return (relative_peak - relative_tac_curve_end) / relative_peak
        else:
            return 1

    def get_rise_completion(self, curve_start_index, relative_peak, curve_threshold):
        """Calculate rise completion percentage."""
        relative_tac_curve_start = (self.df.loc[curve_start_index, self.tac_column] - curve_threshold)
        unfinished_rise = relative_tac_curve_start > 0
        if unfinished_rise:
            return (relative_peak - relative_tac_curve_start) / relative_peak
        else:
            return 1

    def get_rise_rate(self, rise_duration, relative_peak, curve_threshold):
        """Calculate rise rate (peak-based) using curve threshold as baseline.
        
        Args:
            rise_duration: Duration of rise period in hours
            relative_peak: Peak TAC minus curve threshold (already calculated)
            curve_threshold: The curve threshold value (unused, kept for compatibility)
            
        Returns:
            float: Rise rate from curve threshold to peak
        """
        if rise_duration and (relative_peak is not None):
            rise_rate = relative_peak / rise_duration
            return rise_rate
        elif rise_duration == 0:
            return 0
        else:
            return None

    def get_point_to_point_rise_rate(self, curve_start_index):
        """Calculate average of all ascending point-to-point TAC changes.
        
        Based on: ΔTAC_{t,t-1} / ΔHours_{t,t-1} > 0
        This calculates the rate of change for all consecutive points where TAC increases,
        starting from the first curve value.
        
        Args:
            curve_start_index: Index where the curve starts (unused, kept for compatibility)
            
        Returns:
            float: Average rise rate across all ascending segments
        """
        def compute():
            tac_diff, _, mask = self._get_point_to_point_rise_components()
            if mask.any():
                return float(tac_diff[mask].mean())
            return 0.0
        
        cache_key = f'point_to_point_rise_rate_{curve_start_index}'
        return self._get_cached(cache_key, compute)

    def get_point_to_point_rise_duration(self, curve_start_index):
        """Calculate total duration (hours) of ascending point-to-point TAC changes."""
        def compute():
            _, step_minutes, mask = self._get_point_to_point_rise_components()
            if mask.any():
                total_minutes = step_minutes[mask].sum()
                return float(total_minutes / 60.0)
            return 0.0

        cache_key = f'point_to_point_rise_duration_{curve_start_index}'
        return self._get_cached(cache_key, compute)

    def _get_point_to_point_rise_components(self):
        """Vectorized helper returning (tac_diff, step_minutes, mask) for rising pairs."""
        tac_series = self.df[self.tac_column]
        if tac_series.size < 2:
            empty = tac_series.iloc[:0]
            return empty, empty, empty.astype(bool)

        tac_diff = tac_series.diff()

        if 'Duration_Hrs' in self.df.columns:
            step_minutes = self.df['Duration_Hrs'].diff() * 60.0
        else:
            index_series = pd.Series(self.df.index, index=self.df.index)
            if np.issubdtype(index_series.dtype, np.number):
                step_minutes = index_series.diff()
            else:
                step_minutes = pd.Series(1.0, index=self.df.index)

        step_minutes = step_minutes.astype(float).fillna(1.0)
        step_minutes = step_minutes.mask(step_minutes <= 0, 1.0)

        mask = (
            (tac_diff > 0)
            & (~tac_series.isna())
            & (~tac_series.shift(1).isna())
        )

        return tac_diff, step_minutes, mask

    def get_point_to_point_fall_rate(self, peak_index):
        """Calculate average of all descending point-to-point TAC rates."""
        def compute():
            tac_diff, _, mask = self._get_point_to_point_fall_components()
            if mask.any():
                return float((-tac_diff[mask]).mean())
            return 0.0

        cache_key = f'point_to_point_fall_rate_{peak_index}'
        return self._get_cached(cache_key, compute)

    def get_point_to_point_fall_duration(self, peak_index):
        """Calculate total duration (hours) of descending point-to-point TAC changes."""
        def compute():
            _, step_minutes, mask = self._get_point_to_point_fall_components()
            if mask.any():
                total_minutes = step_minutes[mask].sum()
                return float(total_minutes / 60.0)
            return 0.0

        cache_key = f'point_to_point_fall_duration_{peak_index}'
        return self._get_cached(cache_key, compute)

    def _get_point_to_point_fall_components(self):
        """Vectorized helper returning (tac_diff, step_minutes, mask) for descending pairs."""
        tac_series = self.df[self.tac_column]
        if tac_series.size < 2:
            empty = tac_series.iloc[:0]
            return empty, empty, empty.astype(bool)

        tac_diff = tac_series.diff()

        if 'Duration_Hrs' in self.df.columns:
            step_minutes = self.df['Duration_Hrs'].diff() * 60.0
        else:
            index_series = pd.Series(self.df.index, index=self.df.index)
            if np.issubdtype(index_series.dtype, np.number):
                step_minutes = index_series.diff()
            else:
                step_minutes = pd.Series(1.0, index=self.df.index)

        step_minutes = step_minutes.astype(float).fillna(1.0)
        step_minutes = step_minutes.mask(step_minutes <= 0, 1.0)

        mask = (
            (tac_diff < 0)
            & (~tac_series.isna())
            & (~tac_series.shift(1).isna())
        )

        return tac_diff, step_minutes, mask

    def get_rise_rate_1hr(self, curve_start_index, peak_index, curve_threshold):
        """Calculate rise rate over 1 hour period, bounded by peak time.
        
        Computes TAC change from curve threshold to the median 
        of the last 5 values within 1 hour of curve start, but not beyond peak time.
        
        Args:
            curve_start_index: Index where the curve starts
            peak_index: Index where the peak occurs
            curve_threshold: The curve threshold value
            
        Returns:
            float: Rise rate over 1 hour period (or None if insufficient data)
        """
        def compute():
            if len(self.df) < 2:
                return None
            
            # Find end index: min of (1-hour window, peak time)
            # 1-hour window = 60 data points from curve start
            hour_window_end = curve_start_index + 60
            end_index = min(hour_window_end, peak_index, len(self.df) - 1)
            
            # Ensure we have at least 5 values in the rise period
            rise_length = end_index - curve_start_index + 1
            if rise_length < 5:
                return None
            
            # Calculate actual time duration in hours
            time_diff_hours = rise_length / 60.0  # Convert minutes to hours
            
            # Get last 5 values within the bounded window
            if rise_length < 5:
                return None
            
            last_5_values = self.df.iloc[end_index-4:end_index+1][self.tac_column]
            median_tac = last_5_values.median()
            
            # Calculate rise rate from curve threshold to median
            tac_change = median_tac - curve_threshold
            rise_rate = tac_change / time_diff_hours
            
            return rise_rate
        
        cache_key = f'rise_rate_1hr_{curve_start_index}_{peak_index}_{curve_threshold}'
        return self._get_cached(cache_key, compute)

    def get_rise_rate_2hr(self, curve_start_index, peak_index, curve_threshold):
        """Calculate rise rate over 2 hour period, bounded by peak time.
        
        Computes TAC change from curve threshold to the median 
        of the last 5 values within 2 hours of curve start, but not beyond peak time.
        
        Args:
            curve_start_index: Index where the curve starts
            peak_index: Index where the peak occurs
            curve_threshold: The curve threshold value
            
        Returns:
            float: Rise rate over 2 hour period (or None if insufficient data)
        """
        def compute():
            if len(self.df) < 2:
                return None
            
            # Find end index: min of (2-hour window, peak time)
            # 2-hour window = 120 data points from curve start
            hour_window_end = curve_start_index + 120
            end_index = min(hour_window_end, peak_index, len(self.df) - 1)
            
            # Ensure we have at least 5 values in the rise period
            rise_length = end_index - curve_start_index + 1
            if rise_length < 5:
                return None
            
            # Calculate actual time duration in hours
            time_diff_hours = rise_length / 60.0  # Convert minutes to hours
            
            # Get last 5 values within the bounded window
            if rise_length < 5:
                return None
            
            last_5_values = self.df.iloc[end_index-4:end_index+1][self.tac_column]
            median_tac = last_5_values.median()
            
            # Calculate rise rate from curve threshold to median
            tac_change = median_tac - curve_threshold
            rise_rate = tac_change / time_diff_hours
            
            return rise_rate
        
        cache_key = f'rise_rate_2hr_{curve_start_index}_{peak_index}_{curve_threshold}'
        return self._get_cached(cache_key, compute)

    def get_fall_rate(self, fall_duration, relative_peak):
        """Calculate fall rate."""
        if fall_duration and (relative_peak is not None):
            return relative_peak / fall_duration
        elif fall_duration == 0:
            return 0
        else:
            return None

    def get_point_to_point_fall_rate(self, peak_index):
        """Calculate average of all descending point-to-point TAC rates.
        
        Based on: ΔTAC_{t,t-1} / ΔHours_{t,t-1} < 0
        This calculates the rate of change for all consecutive points where TAC decreases,
        starting from the peak.
        
        Args:
            peak_index: Index where the peak occurs
            
        Returns:
            float: Average fall rate across all descending segments
        """
        def compute():
            if len(self.df) < 2:
                return None
            
            fall_rates = []
            tac_values = self.df[self.tac_column].dropna()
            
            if len(tac_values) < 2:
                return None
            
            # Calculate point-to-point differences from peak onwards
            for i in range(peak_index + 1, len(tac_values)):
                current_tac = tac_values.iloc[i]
                previous_tac = tac_values.iloc[i-1]
                tac_diff = current_tac - previous_tac
                
                # Only include negative changes (descending rates)
                if tac_diff < 0:
                    fall_rates.append(abs(tac_diff))  # Use absolute value for consistency
            
            if len(fall_rates) == 0:
                return 0  # No descending segments found
            
            return np.mean(fall_rates)
        
        cache_key = f'point_to_point_fall_rate_{peak_index}'
        return self._get_cached(cache_key, compute)

    def get_fall_rate_1hr(self, peak_index, curve_threshold):
        """Calculate fall rate over last 1 hour period.
        
        Computes TAC change from curve threshold to the median 
        of the first 5 values within 1 hour before curve end.
        
        Args:
            peak_index: Index where the peak occurs
            curve_threshold: The curve threshold value
            
        Returns:
            float: Fall rate over last 1 hour period (or None if insufficient data)
        """
        def compute():
            if len(self.df) < 2:
                return None
            
            # Find start index: max of (1-hour window from end, peak time)
            # 1-hour window = 60 data points from curve end
            hour_window_start = len(self.df) - 60
            start_index = max(hour_window_start, peak_index)
            
            # Ensure we have at least 5 values in the fall period
            fall_length = len(self.df) - start_index
            if fall_length < 5:
                return None
            
            # Calculate actual time duration in hours
            time_diff_hours = fall_length / 60.0  # Convert minutes to hours
            
            # Get first 5 values within the bounded window
            if fall_length < 5:
                return None
            
            first_5_values = self.df.iloc[start_index:start_index+5][self.tac_column]
            median_tac = first_5_values.median()
            
            # Calculate fall rate from median to curve threshold
            tac_change = curve_threshold - median_tac
            fall_rate = tac_change / time_diff_hours
            
            return fall_rate
        
        cache_key = f'fall_rate_1hr_{peak_index}_{curve_threshold}'
        return self._get_cached(cache_key, compute)

    def get_fall_rate_2hr(self, peak_index, curve_threshold):
        """Calculate fall rate over last 2 hour period.
        
        Computes TAC change from curve threshold to the median 
        of the first 5 values within 2 hours before curve end.
        
        Args:
            peak_index: Index where the peak occurs
            curve_threshold: The curve threshold value
            
        Returns:
            float: Fall rate over last 2 hour period (or None if insufficient data)
        """
        def compute():
            if len(self.df) < 2:
                return None
            
            # Find start index: max of (2-hour window from end, peak time)
            # 2-hour window = 120 data points from curve end
            hour_window_start = len(self.df) - 120
            start_index = max(hour_window_start, peak_index)
            
            # Ensure we have at least 5 values in the fall period
            fall_length = len(self.df) - start_index
            if fall_length < 5:
                return None
            
            # Calculate actual time duration in hours
            time_diff_hours = fall_length / 60.0  # Convert minutes to hours
            
            # Get first 5 values within the bounded window
            if fall_length < 5:
                return None
            
            first_5_values = self.df.iloc[start_index:start_index+5][self.tac_column]
            median_tac = first_5_values.median()
            
            # Calculate fall rate from median to curve threshold
            tac_change = curve_threshold - median_tac
            fall_rate = tac_change / time_diff_hours
            
            return fall_rate
        
        cache_key = f'fall_rate_2hr_{peak_index}_{curve_threshold}'
        return self._get_cached(cache_key, compute)

    def get_curve_duration(self, rise_duration, fall_duration):
        """Calculate total curve duration."""
        return rise_duration + fall_duration

    def get_curve_auc(self, curve_threshold):
        """Calculate area under curve relative to threshold."""
        def compute():
            if len(self.df) == 0:
                return None
            try:
                tac = self.df[self.tac_column].dropna().astype(float)
                if len(tac) == 0:
                    return None
                relative_tac = np.maximum(tac - curve_threshold, 0)  # Ensure values below threshold become 0
                relative_tac = np.clip(relative_tac, 0, None)
                relative_auc = np.trapz(relative_tac, dx=1.0)
                return relative_auc
            except Exception as e:
                print(f"Error calculating relative AUC: {e}")
                return None
        
        cache_key = f'curve_auc_{curve_threshold}'
        return self._get_cached(cache_key, compute)

    def get_curve_auc_per_hour(self, curve_auc, curve_duration):
        """Calculate AUC per hour."""
        if curve_auc and curve_duration:
            return curve_auc / curve_duration
        else:
            return None

    def get_avg_tac_diff(self):
        """Calculate average absolute difference between consecutive TAC values."""
        def compute():
            if len(self.df) == 0:
                return None, None
            tac = self.df[self.tac_column]
            differences = []
            for i, value in enumerate(tac):
                if i >= 1:
                    absolute_difference = abs(value - tac.iloc[i-1])
                    differences.append(absolute_difference)
            if len(differences) == 0:
                return None, None
            return stats_package.fmean(differences), differences
        
        return self._get_cached('avg_tac_diff', compute)

    def get_tac_directional_alterations(self):
        """Calculate number of directional changes in TAC."""
        def compute():
            if len(self.df) == 0:
                return None, None
            tac = self.df[self.tac_column].tolist()

            alterations = 0
            changes = []
            for i, value in enumerate(tac):
                if i > 0:
                    difference = value - tac[i-1]
                    if difference >= 0:
                        current_change = 'positive'
                    else:
                        current_change = 'negative'
                    changes.append(current_change)
                if i > 1:
                    prior_change = changes[i-2]
                    if current_change != prior_change:
                        alterations += 1

            return alterations, len(changes)
        
        return self._get_cached('tac_directional_alterations', compute)

    def get_tac_directional_alteration_percent(self):
        """Calculate percentage of TAC changes that reverse direction."""
        alterations, n_datapoints = self.get_tac_directional_alterations()
        if alterations is None or n_datapoints is None or n_datapoints == 0:
            return None
        alteration_percent = (alterations / n_datapoints) * 100
        return alteration_percent

    def get_discrete_curve_count(self, sampling_rate, curve_threshold, min_curve_duration_hours, max_curve_separation_hours=0.1, min_relative_peak=5):
        """Count discrete curves above threshold."""
        def compute():
            curve_count = 0
            current_curve_duration = 0
            df_tac_curves = self.df[self.df[self.tac_column] > curve_threshold]
            
            if len(df_tac_curves) == 0:
                return 0
                
            previous_index = df_tac_curves.index.tolist()[0]-1
            curve_begin_index = df_tac_curves.index.tolist()[0]-1

            for i, row in df_tac_curves.iterrows():
                if (((i - previous_index) * sampling_rate) / 60) < max_curve_separation_hours:
                    current_curve_duration += ((sampling_rate * (i - previous_index))  / 60)
                else:
                    if (current_curve_duration >= min_curve_duration_hours) and (self.df.loc[curve_begin_index:i, self.tac_column].max() > min_relative_peak):
                        curve_count += 1
                    current_curve_duration = 0
                    curve_begin_index = i
                previous_index = i

            return curve_count
        
        cache_key = f'discrete_curve_count_{sampling_rate}_{curve_threshold}_{min_curve_duration_hours}_{max_curve_separation_hours}_{min_relative_peak}'
        return self._get_cached(cache_key, compute)

    def get_value_proportion(self, value, variable):
        """Calculate proportion of column that equals provided value."""
        if len(self.df) == 0:
            return None
        return len(self.df[self.df[variable] == value][variable]) / len(self.df)

    def get_r2(self, truth, test):
        """Calculate R-squared (coefficient of determination)."""
        if len(self.df) == 0:
            return None
        return r2_score(self.df[truth].tolist(), self.df[test].tolist())

    def count_complete_curves(self, threshold=10, min_length=5):
        """Count occurrences where values exceed threshold for minimum duration and then drop below."""
        def compute():
            data = self.df[self.tac_column]
            
            above_threshold = False
            crossing_count = 0
            duration = 0  # Track how many consecutive rows are above the threshold
            
            for value in data:
                if value > threshold:
                    if not above_threshold:
                        above_threshold = True  # Start of a new potential curve
                        duration = 1  # Reset duration counter
                    else:
                        duration += 1  # Continue counting rows above the threshold
                elif above_threshold:  # value <= threshold and currently above
                    if duration >= min_length:
                        crossing_count += 1  # Only count if the curve lasted long enough
                    above_threshold = False  # Reset for the next potential curve
                    duration = 0  # Reset duration counter

            return crossing_count
        
        cache_key = f'complete_curves_{threshold}_{min_length}'
        return self._get_cached(cache_key, compute)

    def count_started_curves(self, threshold=10, min_length=5):
        """Count occurrences where values exceed threshold for minimum duration."""
        def compute():
            data = self.df[self.tac_column]
            
            above_threshold = False
            crossing_count = 0
            duration = 0  # Track how many consecutive rows are above the threshold
            
            for value in data:
                if value > threshold:
                    if not above_threshold:
                        above_threshold = True  # Start of a new potential curve
                        duration = 1  # Reset duration counter
                    else:
                        duration += 1  # Continue counting rows above the threshold
                elif above_threshold:  # value <= threshold and currently above
                    if duration >= min_length:
                        crossing_count += 1  # Only count if the curve lasted long enough
                    above_threshold = False  # Reset for the next potential curve
                    duration = 0  # Reset duration counter

            return crossing_count
        
        cache_key = f'started_curves_{threshold}_{min_length}'
        return self._get_cached(cache_key, compute) 