import pandas as pd
import numpy as np

class DataQualityAnalyzer:
    """Object-oriented analyzer for data quality metrics with caching for improved performance."""
    
    def __init__(self, df: pd.DataFrame, tac_column: str = 'TAC', intended_duration_hours=None):
        """
        Initialize the analyzer with a dataframe.
        
        Args:
            df: DataFrame containing the data
            tac_column: Column name for TAC values (default: 'TAC')
            intended_duration_hours: Optional expected window length in hours
                (e.g. periphery buffer). When set, gap/missing metrics treat
                shortfall vs this duration as missing gap data and use it as
                the percent denominator.
        """
        self.df = df
        self.tac_column = tac_column
        self.intended_duration_hours = (
            float(intended_duration_hours)
            if intended_duration_hours is not None else None
        )
        self._cache = {}

    def _buffer_missing_hours(self) -> float:
        """Hours missing relative to intended_duration_hours (0 if unset)."""
        if self.intended_duration_hours is None or self.intended_duration_hours <= 0:
            return 0.0
        observed = len(self.df) / 60.0
        return max(0.0, self.intended_duration_hours - observed)

    def _gap_percent_denominator(self) -> float:
        """Row count, or intended duration in minutes when a buffer is set."""
        if self.intended_duration_hours is not None and self.intended_duration_hours > 0:
            return self.intended_duration_hours * 60.0
        return float(len(self.df))
        
    def _get_cached(self, key, compute_func):
        """Get cached value or compute and cache it."""
        if key not in self._cache:
            self._cache[key] = compute_func()
        return self._cache[key]
    
    def _has_imp_cand(self):
        """Whether all five *_imp_cand columns are present (from impute_low_quality_data)."""
        required = {'gap_imp_cand', 'non_wear_imp_cand', 'jump_imp_cand', 
                    'plummet_imp_cand', 'extreme_negative_imp_cand'}
        return required.issubset(self.df.columns)
    
    @property
    def low_quality_mask(self):
        """Cached boolean mask for low quality data (union of all five types)."""
        def compute():
            if self._has_imp_cand():
                return (
                    (self.df['gap_imp_cand'] == 1) | (self.df['non_wear_imp_cand'] == 1) |
                    (self.df['jump_imp_cand'] == 1) | (self.df['plummet_imp_cand'] == 1) |
                    (self.df['extreme_negative_imp_cand'] == 1)
                )
            return (
                (self.df['gap'] == 1) | (self.df['non_wear'] == 1) | (self.df['jump'] == 1) |
                (self.df['plummet'] == 1) | (self.df['extreme_negative'] == 1)
            )
        return self._get_cached('low_quality_mask', compute)
    
    @property
    def imputed_mask(self):
        """Cached boolean mask for imputed data."""
        return self._get_cached('imputed_mask', lambda: self.df['imputed'] == 1)
    
    def _exclusive_masks(self):
        """Mutually exclusive masks with precedence: gap > non_wear > jump > plummet > extreme_negative.
        Uses *_imp_cand when available (from impute_low_quality_data); otherwise falls back to
        exclusive masks computed from raw flags."""
        def compute():
            if self._has_imp_cand():
                gap_excl = self.df['gap_imp_cand'] == 1
                non_wear_excl = self.df['non_wear_imp_cand'] == 1
                jump_excl = self.df['jump_imp_cand'] == 1
                plummet_excl = self.df['plummet_imp_cand'] == 1
                extreme_excl = self.df['extreme_negative_imp_cand'] == 1
                return (gap_excl, non_wear_excl, jump_excl, plummet_excl, extreme_excl)
            gap_raw = self.df['gap'] == 1
            non_wear_raw = self.df['non_wear'] == 1
            jump_raw = self.df['jump'] == 1
            plummet_raw = self.df['plummet'] == 1
            extreme_raw = self.df['extreme_negative'] == 1
            gap_excl = gap_raw
            non_wear_excl = non_wear_raw & ~gap_excl
            jump_excl = jump_raw & ~gap_excl & ~non_wear_excl
            plummet_excl = plummet_raw & ~gap_excl & ~non_wear_excl & ~jump_excl
            extreme_excl = extreme_raw & ~gap_excl & ~non_wear_excl & ~jump_excl & ~plummet_excl
            return (gap_excl, non_wear_excl, jump_excl, plummet_excl, extreme_excl)
        return self._get_cached('_exclusive_masks', compute)
    
    @property
    def gap_mask(self):
        """Cached boolean mask for gap data (exclusive: gap takes precedence)."""
        return self._exclusive_masks()[0]
    
    @property
    def non_wear_mask(self):
        """Cached boolean mask for non-wear data (exclusive: non-wear after gap)."""
        return self._exclusive_masks()[1]
    
    @property
    def jump_mask(self):
        """Cached boolean mask for jump data (exclusive: jump after gap, non-wear)."""
        return self._exclusive_masks()[2]
    
    @property
    def plummet_mask(self):
        """Cached boolean mask for plummet data (exclusive: plummet after gap, non-wear, jump)."""
        return self._exclusive_masks()[3]
    
    @property
    def extreme_negative_mask(self):
        """Cached boolean mask for extreme negative data (exclusive: lowest precedence)."""
        return self._exclusive_masks()[4]

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
        # Buffer shortfall is unobserved → count as unimputed gap
        return (self.gap_mask & (~self.imputed_mask)).sum() / 60 + self._buffer_missing_hours()

    def get_unimputed_gap_percent(self):
        """Calculate percentage of unimputed gap data."""
        denom = self._gap_percent_denominator()
        if denom <= 0:
            return 0.0
        unimp_min = (self.gap_mask & (~self.imputed_mask)).sum() + self._buffer_missing_hours() * 60
        return unimp_min / denom

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

    def get_total_gap_duration(self):
        """Total gap duration in hours (exclusive), plus buffer shortfall if intended duration set."""
        return self.gap_mask.sum() / 60 + self._buffer_missing_hours()

    def get_total_gap_percent(self):
        """Total gap percent (exclusive); uses intended duration as denom when provided."""
        denom = self._gap_percent_denominator()
        if denom <= 0:
            return 0.0
        gap_min = self.gap_mask.sum() + self._buffer_missing_hours() * 60
        return gap_min / denom

    def get_total_non_wear_duration(self):
        """Total non-wear duration in hours (exclusive)."""
        return self.non_wear_mask.sum() / 60

    def get_total_non_wear_percent(self):
        """Total non-wear percent (exclusive)."""
        if len(self.df) == 0:
            return 0.0
        return self.non_wear_mask.sum() / len(self.df)

    def get_total_jump_duration(self):
        """Total jump duration in hours (exclusive)."""
        return self.jump_mask.sum() / 60

    def get_total_jump_percent(self):
        """Total jump percent (exclusive)."""
        if len(self.df) == 0:
            return 0.0
        return self.jump_mask.sum() / len(self.df)

    def get_total_plummet_duration(self):
        """Total plummet duration in hours (exclusive)."""
        return self.plummet_mask.sum() / 60

    def get_total_plummet_percent(self):
        """Total plummet percent (exclusive)."""
        if len(self.df) == 0:
            return 0.0
        return self.plummet_mask.sum() / len(self.df)

    def get_total_extreme_negative_duration(self):
        """Total extreme negative duration in hours (exclusive)."""
        return self.extreme_negative_mask.sum() / 60

    def get_total_extreme_negative_percent(self):
        """Total extreme negative percent (exclusive)."""
        if len(self.df) == 0:
            return 0.0
        return self.extreme_negative_mask.sum() / len(self.df)

    def _inclusive_mask(self, col):
        """Raw inclusive mask (flag==1) for the given column. Handles missing column."""
        if col not in self.df.columns:
            return pd.Series(False, index=self.df.index)
        return self.df[col] == 1

    def get_total_gap_duration_inclusive(self):
        """Total gap duration in hours (inclusive: gap==1, no mutual exclusivity)."""
        return self._inclusive_mask('gap').sum() / 60 + self._buffer_missing_hours()

    def get_total_gap_percent_inclusive(self):
        """Total gap percent (inclusive: gap==1)."""
        denom = self._gap_percent_denominator()
        if denom <= 0:
            return 0.0
        gap_min = self._inclusive_mask('gap').sum() + self._buffer_missing_hours() * 60
        return gap_min / denom

    def get_total_non_wear_duration_inclusive(self):
        """Total non-wear duration in hours (inclusive: non_wear==1)."""
        return self._inclusive_mask('non_wear').sum() / 60

    def get_total_non_wear_percent_inclusive(self):
        """Total non-wear percent (inclusive: non_wear==1)."""
        if len(self.df) == 0:
            return 0.0
        return self._inclusive_mask('non_wear').sum() / len(self.df)

    def get_total_jump_duration_inclusive(self):
        """Total jump duration in hours (inclusive: jump==1)."""
        return self._inclusive_mask('jump').sum() / 60

    def get_total_jump_percent_inclusive(self):
        """Total jump percent (inclusive: jump==1)."""
        if len(self.df) == 0:
            return 0.0
        return self._inclusive_mask('jump').sum() / len(self.df)

    def get_total_plummet_duration_inclusive(self):
        """Total plummet duration in hours (inclusive: plummet==1)."""
        return self._inclusive_mask('plummet').sum() / 60

    def get_total_plummet_percent_inclusive(self):
        """Total plummet percent (inclusive: plummet==1)."""
        if len(self.df) == 0:
            return 0.0
        return self._inclusive_mask('plummet').sum() / len(self.df)

    def get_total_extreme_negative_duration_inclusive(self):
        """Total extreme negative duration in hours (inclusive: extreme_negative==1)."""
        return self._inclusive_mask('extreme_negative').sum() / 60

    def get_total_extreme_negative_percent_inclusive(self):
        """Total extreme negative percent (inclusive: extreme_negative==1)."""
        if len(self.df) == 0:
            return 0.0
        return self._inclusive_mask('extreme_negative').sum() / len(self.df)

    def get_sub_negative_10_sum(self):
        """Sum of TAC values where extreme_negative (exclusive mask)."""
        if len(self.df) == 0:
            return 0.0
        return self.df.loc[self.extreme_negative_mask, self.tac_column].sum()

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
        if self.intended_duration_hours is not None:
            return self.get_total_gap_percent() + self.get_total_non_wear_percent()
        if len(self.df) == 0:
            return 0.0
        total_low_quality = self.gap_mask | self.non_wear_mask
        return total_low_quality.sum() / len(self.df)

    def get_below_threshold_percent(self, threshold=0):
        """Calculate percentage of TAC values that are below a given threshold."""
        if len(self.df) == 0:
            return 0.0
            
        return (self.df[self.tac_column] <= threshold).sum() / len(self.df)

    def get_unimputed_gaps_and_non_wear_percent(self):
        """Calculate the total percentage of data that is either an unimputed gap or unimputed non-wear period."""
        if self.intended_duration_hours is not None:
            return self.get_unimputed_gap_percent() + self.get_unimputed_non_wear_percent()
        if len(self.df) == 0:
            return 0.0
        unimputed_gaps_and_non_wear = (self.gap_mask & (~self.imputed_mask)) | (self.non_wear_mask & (~self.imputed_mask))
        return unimputed_gaps_and_non_wear.sum() / len(self.df)

    def get_high_quality_duration(self):
        """Calculate duration of high-quality data (non-low quality) in hours.
        
        High-quality data is defined as data points that are NOT flagged as low quality.
        This is the inverse of low_quality_mask. Imputation status does not affect
        high quality classification.
        
        Returns:
            float: Duration of high-quality data in hours
        """
        high_quality_count = (~self.low_quality_mask).sum()
        duration_hours = high_quality_count / 60.0  # Convert minutes to hours
        return duration_hours

    def get_high_quality_percent(self):
        """Calculate percentage of high-quality data within the curve.
        
        High-quality data is defined as data points that are NOT flagged as low quality.
        This is the inverse of low_quality_mask. Imputation status does not affect
        high quality classification.
        
        Returns:
            float: Percentage of high-quality data (0-100)
        """
        if len(self.df) == 0:
            return 0.0
        
        high_quality_count = (~self.low_quality_mask).sum()
        percent = (high_quality_count / len(self.df)) * 100
        return percent 

    def get_high_quality_above_threshold_duration(self, threshold: float):
        """Calculate duration (hours) of high-quality data at or above the provided TAC threshold.
        
        High-quality data is the inverse of low_quality_mask. Imputation status does not affect
        high quality classification.
        """
        def compute():
            if len(self.df) == 0:
                return 0.0

            above_threshold_mask = self.df[self.tac_column] >= threshold
            qualifying_mask = (~self.low_quality_mask) & above_threshold_mask

            return qualifying_mask.sum() / 60.0

        cache_key = f'high_quality_above_threshold_duration_{float(threshold):.4f}'
        return self._get_cached(cache_key, compute)
