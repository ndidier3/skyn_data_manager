"""
Configuration settings for Test analysis scripts.
These settings are used by default_analysis.py and other test-related scripts.
"""

# Smooth and impute settings
smooth_and_impute_attrs = {
    'median_smooth': True,
    'impute_gaps': True,
    'impute_non_wear': True,
    'impute_jumps': True,
    'impute_plummets': True,
    'savgol_smooth': False,
    'export_excel': False
}

# Curve analysis settings
curve_attrs = {
    'flag_selections': {
        # Curve flags
        'flag_extreme_rise_rate_curve': {
            'rise_rate_cutoff': 430
        },
        'flag_incomplete_curve_start_curve': {
            'percent_cutoff': 0.5
        },
        'flag_incomplete_curve_end_curve': {
            'percent_cutoff': 0.5
        },
        'flag_flatlined_peak_curve': {
            'flatline_percent_cutoff': 0.20,
            'peak_above': 350
        },
        'flag_sub_negative_10_curve': {
            'percent_cutoff': 0.20,
            'duration_cutoff': 1.0,
        },
        'flag_unimputed_low_quality_percent_curve': {
            'percent_cutoff': 0.20
        },
        'flag_too_much_imputation_curve': { 
            'percent_cutoff': 0.4,
            'duration_cutoff': 3
        },
        'flag_low_quality_curve': {},
        'flag_device_non_wear_curve': {},
        'flag_device_worn_duration_curve': {},
        'flag_low_flat_curves_curve': {},
        'flag_curve_start_too_late_curve': {},
        'flag_device_turned_on_percent_curve': {},
        'flag_starting_non_wear_perc_curve': {},
        'flag_ending_non_wear_perc_curve': {},
        'flag_short_curve_duration_curve': {'duration_cutoff': 0.25},  # 15 minutes
        
        # Periphery flags
        'flag_sub_negative_10_periphery': {'percent_cutoff': 0.80, 'duration_cutoff': 2},
        'flag_sub_negative_20_periphery': {'percent_cutoff': 0.40, 'duration_cutoff': 1.5},
        'flag_sub_negative_40_periphery': {'percent_cutoff': 0.20, 'duration_cutoff': 0.5},
        'flag_non_wear_periphery': {'percent_cutoff': 0.40}
    },
    'curve_threshold': 'auto',
    'periphery_buffer_before': 2,
    'periphery_buffer_after': 2,
    'merge_curves_within_duration': 2
}

# Day settings
day_attrs = {
    'day_start_hour': 0,
    'make_graphs': True
}

# Gaps and non-wear settings
gaps_and_non_wear_attrs = {
    'export_excel': False
} 