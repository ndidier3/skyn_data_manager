import pandas as pd
import numpy as np

class DataQualityAnalyzer:
    """Object-oriented analyzer for data quality metrics with caching for improved performance."""
    
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
    
    @property
    def low_quality_mask(self):
        """Cached boolean mask for low quality data (jumps, plummets, extreme negatives, non-wear, gaps)."""
        return self._get_cached('low_quality_mask', lambda: (
            (self.df['jump'] == 1) | (self.df['plummet'] == 1) | 
            (self.df['extreme_negative'] == 1) | (self.df['non_wear'] == 1) | 
            (self.df['gap'] == 1)
        ))
    
    @property
    def imputed_mask(self):
        """Cached boolean mask for imputed data."""
        return self._get_cached('imputed_mask', lambda: self.df['imputed'] == 1)
    
    @property
    def jump_mask(self):
        """Cached boolean mask for jump data."""
        return self._get_cached('jump_mask', lambda: self.df['jump'] == 1)
    
    @property
    def plummet_mask(self):
        """Cached boolean mask for plummet data."""
        return self._get_cached('plummet_mask', lambda: self.df['plummet'] == 1)
    
    @property
    def extreme_negative_mask(self):
        """Cached boolean mask for extreme negative data."""
        return self._get_cached('extreme_negative_mask', lambda: self.df['extreme_negative'] == 1)
    
    @property
    def gap_mask(self):
        """Cached boolean mask for gap data."""
        return self._get_cached('gap_mask', lambda: self.df['gap'] == 1)
    
    @property
    def non_wear_mask(self):
        """Cached boolean mask for non-wear data."""
        return self._get_cached('non_wear_mask', lambda: self.df['non_wear'] == 1)

    def count_longest_tac_flatline(self, threshold=10, tolerance=0.1):
        """Count the longest period where TAC values remain flat (within tolerance) above threshold."""
        def compute():
            if len(self.df) == 0:
                return 0
            flatline_mask = (
                self.df[self.tac_column].shift().sub(self.df[self.tac_column]).abs() <= tolerance
            ) & (self.df[self.tac_column] > threshold)
            streak_lengths = (flatline_mask != flatline_mask.shift()).cumsum()
            streak_data = flatline_mask.groupby(streak_lengths).sum()
            return streak_data.max() if not streak_data.empty else 0
        
        cache_key = f'flatline_{threshold}_{tolerance}'
        return self._get_cached(cache_key, compute)

    def count_longest_consecutive_non_wear(self, variable='device_worn_model'):
        """Count the longest consecutive period of non-wear time."""
        def compute():
            if len(self.df) == 0:
                return 0
            df_copy = self.df.copy()
            df_copy['non_wear_group'] = (df_copy[variable] != 0).cumsum()
            non_wear_lengths = df_copy[df_copy[variable] == 0].groupby('non_wear_group').size()
            return non_wear_lengths.max() if not non_wear_lengths.empty else 0
        
        cache_key = f'longest_non_wear_{variable}'
        return self._get_cached(cache_key, compute)

    def count_longest_consecutive_below(self, X=-15):
        """Count the longest consecutive period where values are below threshold."""
        def compute():
            if len(self.df) == 0:
                return 0
            mask = self.df[self.tac_column] <= X
            df_copy = self.df.copy()
            df_copy['sub_negative'] = (mask != mask.shift()).cumsum() * mask
            sub_negative_lengths = df_copy[mask].groupby('sub_negative').size()
            return sub_negative_lengths.max() if not sub_negative_lengths.empty else 0
        
        cache_key = f'longest_below_{X}'
        return self._get_cached(cache_key, compute)

    def get_low_quality_duration(self):
        """Calculate total duration of low quality data in hours."""
        return self.low_quality_mask.sum() / 60

    def get_low_quality_percent(self):
        """Calculate percentage of low quality data."""
        if len(self.df) == 0:
            return 0.0
        return self.low_quality_mask.sum() / len(self.df)

    def get_unimputed_low_quality_duration(self):
        """Calculate total duration of unimputed low quality data in hours."""
        return (self.low_quality_mask & (~self.imputed_mask)).sum() / 60

    def get_unimputed_low_quality_percent(self):
        """Calculate percentage of unimputed low quality data."""
        if len(self.df) == 0:
            return 0.0
        return (self.low_quality_mask & (~self.imputed_mask)).sum() / len(self.df)

    def get_imputed_low_quality_duration(self):
        """Calculate total duration of imputed low quality data in hours."""
        return (self.low_quality_mask & self.imputed_mask).sum() / 60

    def get_imputed_low_quality_percent(self):
        """Calculate percentage of imputed low quality data."""
        if len(self.df) == 0:
            return 0.0
        return (self.low_quality_mask & self.imputed_mask).sum() / len(self.df)

    def get_imputed_jump_duration(self):
        """Calculate duration of imputed jump data in hours."""
        return (self.jump_mask & self.imputed_mask).sum() / 60

    def get_imputed_jump_percent(self):
        """Calculate percentage of imputed jump data."""
        if len(self.df) == 0:
            return 0.0
        return (self.jump_mask & self.imputed_mask).sum() / len(self.df)

    def get_unimputed_jump_duration(self):
        """Calculate duration of unimputed jump data in hours."""
        return (self.jump_mask & (~self.imputed_mask)).sum() / 60

    def get_unimputed_jump_percent(self):
        """Calculate percentage of unimputed jump data."""
        if len(self.df) == 0:
            return 0.0
        return (self.jump_mask & (~self.imputed_mask)).sum() / len(self.df)

    def get_imputed_plummet_duration(self):
        """Calculate duration of imputed plummet data in hours."""
        return (self.plummet_mask & self.imputed_mask).sum() / 60

    def get_imputed_plummet_percent(self):
        """Calculate percentage of imputed plummet data."""
        if len(self.df) == 0:
            return 0.0
        return (self.plummet_mask & self.imputed_mask).sum() / len(self.df)

    def get_unimputed_plummet_duration(self):
        """Calculate duration of unimputed plummet data in hours."""
        return (self.plummet_mask & (~self.imputed_mask)).sum() / 60

    def get_unimputed_plummet_percent(self):
        """Calculate percentage of unimputed plummet data."""
        if len(self.df) == 0:
            return 0.0
        return (self.plummet_mask & (~self.imputed_mask)).sum() / len(self.df)

    def get_imputed_extreme_negative_duration(self):
        """Calculate duration of imputed extreme negative data in hours."""
        return (self.extreme_negative_mask & self.imputed_mask).sum() / 60

    def get_imputed_extreme_negative_percent(self):
        """Calculate percentage of imputed extreme negative data."""
        if len(self.df) == 0:
            return 0.0
        return (self.extreme_negative_mask & self.imputed_mask).sum() / len(self.df)

    def get_unimputed_extreme_negative_duration(self):
        """Calculate duration of unimputed extreme negative data in hours."""
        return (self.extreme_negative_mask & (~self.imputed_mask)).sum() / 60

    def get_unimputed_extreme_negative_percent(self):
        """Calculate percentage of unimputed extreme negative data."""
        if len(self.df) == 0:
            return 0.0
        return (self.extreme_negative_mask & (~self.imputed_mask)).sum() / len(self.df)

    def get_imputed_gap_duration(self):
        """Calculate duration of imputed gap data in hours."""
        return (self.gap_mask & self.imputed_mask).sum() / 60

    def get_imputed_gap_percent(self):
        """Calculate percentage of imputed gap data."""
        if len(self.df) == 0:
            return 0.0
        return (self.gap_mask & self.imputed_mask).sum() / len(self.df)

    def get_unimputed_gap_duration(self):
        """Calculate duration of unimputed gap data in hours."""
        return (self.gap_mask & (~self.imputed_mask)).sum() / 60

    def get_unimputed_gap_percent(self):
        """Calculate percentage of unimputed gap data."""
        if len(self.df) == 0:
            return 0.0
        return (self.gap_mask & (~self.imputed_mask)).sum() / len(self.df)

    def get_imputed_non_wear_duration(self):
        """Calculate duration of imputed non-wear data in hours."""
        return (self.non_wear_mask & self.imputed_mask).sum() / 60

    def get_imputed_non_wear_percent(self):
        """Calculate percentage of imputed non-wear data."""
        if len(self.df) == 0:
            return 0.0
        return (self.non_wear_mask & self.imputed_mask).sum() / len(self.df)

    def get_unimputed_non_wear_duration(self):
        """Calculate duration of unimputed non-wear data in hours."""
        return (self.non_wear_mask & (~self.imputed_mask)).sum() / 60

    def get_unimputed_non_wear_percent(self):
        """Calculate percentage of unimputed non-wear data."""
        if len(self.df) == 0:
            return 0.0
        return (self.non_wear_mask & (~self.imputed_mask)).sum() / len(self.df)

    def get_jump_imputation_ratio(self):
        """Calculate ratio of imputed jump data."""
        total_jumps = self.jump_mask.sum()
        if total_jumps == 0:
            return None
        return (self.jump_mask & self.imputed_mask).sum() / total_jumps

    def get_plummet_imputation_ratio(self):
        """Calculate ratio of imputed plummet data."""
        total_plummets = self.plummet_mask.sum()
        if total_plummets == 0:
            return None
        return (self.plummet_mask & self.imputed_mask).sum() / total_plummets

    def get_extreme_negative_imputation_ratio(self):
        """Calculate ratio of imputed extreme negative data."""
        total_extreme_negatives = self.extreme_negative_mask.sum()
        if total_extreme_negatives == 0:
            return None
        return (self.extreme_negative_mask & self.imputed_mask).sum() / total_extreme_negatives

    def get_gap_imputation_ratio(self):
        """Calculate ratio of imputed gap data."""
        total_gaps = self.gap_mask.sum()
        if total_gaps == 0:
            return None
        return (self.gap_mask & self.imputed_mask).sum() / total_gaps

    def get_non_wear_imputation_ratio(self):
        """Calculate ratio of imputed non-wear data."""
        total_non_wear = self.non_wear_mask.sum()
        if total_non_wear == 0:
            return None
        return (self.non_wear_mask & self.imputed_mask).sum() / total_non_wear

    def get_low_quality_imputation_ratio(self):
        """Calculate ratio of imputed low quality data."""
        total_low_quality = self.low_quality_mask.sum()
        if total_low_quality == 0:
            return None
        return (self.low_quality_mask & self.imputed_mask).sum() / total_low_quality

    def get_start_to_peak_interval(self):
        """
        Returns the number of TAC values between the first TAC and the first occurrence of the peak TAC value.
        """
        if len(self.df) == 0:
            return 0
        # Since curve is reset_index(drop=True), index is positional
        max_tac = self.df[self.tac_column].max()
        if pd.isna(max_tac):
            return 0
        start_to_peak_count = self.df.index[self.df[self.tac_column] == max_tac].tolist()[0]
        return start_to_peak_count

    def get_rise_imputed_percent(self):
        """Calculate percentage of imputed data in the rise portion of a curve."""
        if len(self.df) == 0:
            return 0.0
            
        peak_index = self.df[self.tac_column].idxmax()
        rise_portion = self.df.loc[:peak_index]
        
        if len(rise_portion) == 0:
            return 0.0
            
        imputed_mask_rise = rise_portion['imputed'] == 1
        return imputed_mask_rise.sum() / len(rise_portion)

    def get_fall_imputed_percent(self):
        """Calculate percentage of imputed data in the fall portion of a curve."""
        if len(self.df) == 0:
            return 0.0
            
        peak_index = self.df[self.tac_column].idxmax()
        fall_portion = self.df.loc[peak_index:]
        
        if len(fall_portion) == 0:
            return 0.0
            
        imputed_mask_fall = fall_portion['imputed'] == 1
        return imputed_mask_fall.sum() / len(fall_portion)

    def get_ascending_imputed_percent(self):
        """Calculate percentage of ascending TAC pairs that contain imputed values."""
        if len(self.df) < 2:
            return 0.0

        tac_values = self.df[self.tac_column].to_numpy()
        imputed_values = self.df['imputed'].to_numpy()

        asc_mask = tac_values[1:] > tac_values[:-1]
        if not asc_mask.any():
            return 0.0

        asc_total = asc_mask.sum()
        asc_imputed = np.logical_or(imputed_values[1:], imputed_values[:-1])[asc_mask].sum()

        return asc_imputed / asc_total if asc_total > 0 else 0.0

    def get_descending_imputed_percent(self):
        """Calculate percentage of descending TAC pairs that contain imputed values."""
        if len(self.df) < 2:
            return 0.0

        tac_values = self.df[self.tac_column].to_numpy()
        imputed_values = self.df['imputed'].to_numpy()

        desc_mask = tac_values[1:] < tac_values[:-1]
        if not desc_mask.any():
            return 0.0

        desc_total = desc_mask.sum()
        desc_imputed = np.logical_or(imputed_values[1:], imputed_values[:-1])[desc_mask].sum()

        return desc_imputed / desc_total if desc_total > 0 else 0.0

    def get_total_gaps_and_non_wear_percent(self):
        """Calculate the total percentage of data that is either a gap or non-wear period."""
        if len(self.df) == 0:
            return 0.0
            
        # Combine gap and non-wear masks
        total_low_quality = self.gap_mask | self.non_wear_mask
        return total_low_quality.sum() / len(self.df)

    def get_below_threshold_percent(self, threshold=0):
        """Calculate percentage of TAC values that are below a given threshold."""
        if len(self.df) == 0:
            return 0.0
            
        return (self.df[self.tac_column] <= threshold).sum() / len(self.df)

    def get_unimputed_gaps_and_non_wear_percent(self):
        """Calculate the total percentage of data that is either an unimputed gap or unimputed non-wear period."""
        if len(self.df) == 0:
            return 0.0
            
        # Combine unimputed gap and unimputed non-wear masks
        unimputed_gaps_and_non_wear = (self.gap_mask & (~self.imputed_mask)) | (self.non_wear_mask & (~self.imputed_mask))
        return unimputed_gaps_and_non_wear.sum() / len(self.df)

    def get_high_quality_duration(self):
        """Calculate duration of high-quality data (non-low quality) in hours.
        
        High-quality data is defined as data points that are NOT flagged as low quality.
        This includes data that is not imputed, not gapped, not non-wear, not jumped, 
        not plummeted, and not extreme negative.
        
        Returns:
            float: Duration of high-quality data in hours
        """
        def compute():
            if len(self.df) == 0:
                return 0.0
            
            # Count high-quality data points (not flagged as any quality issue)
            high_quality_mask = (
                (self.df.get('imputed', 0) == 0) &  # Not imputed
                (self.df.get('gap', 0) == 0) &      # Not gapped
                (self.df.get('non_wear', 0) == 0) & # Not non-wear
                (self.df.get('jump', 0) == 0) &     # Not jumped
                (self.df.get('plummet', 0) == 0) &  # Not plummeted
                (self.df.get('extreme_negative', 0) == 0)  # Not extreme negative
            )
            
            high_quality_count = high_quality_mask.sum()
            duration_hours = high_quality_count / 60.0  # Convert minutes to hours
            
            return duration_hours
        
        return self._get_cached('high_quality_duration', compute)

    def get_high_quality_percent(self):
        """Calculate percentage of high-quality data within the curve.
        
        High-quality data is defined as data points that are NOT flagged as low quality.
        
        Returns:
            float: Percentage of high-quality data (0-100)
        """
        def compute():
            if len(self.df) == 0:
                return 0.0
            
            # Count high-quality data points (not flagged as any quality issue)
            high_quality_mask = (
                (self.df.get('imputed', 0) == 0) &  # Not imputed
                (self.df.get('gap', 0) == 0) &      # Not gapped
                (self.df.get('non_wear', 0) == 0) & # Not non-wear
                (self.df.get('jump', 0) == 0) &     # Not jumped
                (self.df.get('plummet', 0) == 0) &  # Not plummeted
                (self.df.get('extreme_negative', 0) == 0)  # Not extreme negative
            )
            
            high_quality_count = high_quality_mask.sum()
            total_count = len(self.df)
            percent = (high_quality_count / total_count) * 100 if total_count > 0 else 0.0
            
            return percent
        
        return self._get_cached('high_quality_percent', compute) 