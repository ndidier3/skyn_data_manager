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
        """Calculate area under the curve using trapezoidal rule."""
        def compute():
            if len(self.df) == 0:
                return None
            try:
                tac = self.df[self.tac_column].dropna().astype(float)
                if len(tac) == 0:
                    return None
                total_auc = np.trapz(tac, dx=0.1)
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

    def get_rise_rate(self, rise_duration, relative_peak):
        """Calculate rise rate."""
        if rise_duration and (relative_peak is not None):
            return relative_peak / rise_duration
        elif rise_duration == 0:
            return 0
        else:
            return None

    def get_fall_rate(self, fall_duration, relative_peak):
        """Calculate fall rate."""
        if fall_duration and (relative_peak is not None):
            return relative_peak / fall_duration
        elif fall_duration == 0:
            return 0
        else:
            return None

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
                relative_auc = np.trapz(relative_tac, dx=0.1)
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