"""
Default flag settings for curve analysis.
These settings are used by ACE, ARC, and LINC analysis scripts.
"""

DEFAULT_FLAG_SELECTIONS = {
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
    # 'flag_sub_negative_40_periphery': {'percent_cutoff': 0.20, 'duration_cutoff': 0.5},
    'flag_sub_negative_40_periphery': {},
    'flag_non_wear_periphery': {'percent_cutoff': 0.40}
} 