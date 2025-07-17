"""
Default flag settings for curve analysis.
These settings are used by ACE, ARC, and LINC analysis scripts.
"""

DEFAULT_FLAG_SELECTIONS = {
    # Curve flags
    'flag_unimputed_low_quality_curve': { #if this is hit, there must be a lot of other low quality data
      'percent_cutoff': 0.05,
      'duration_cutoff': 0.5
    },
    'flag_imputed_limit_curve': {
      'percent_cutoff': 0.35,
      'duration_cutoff': 5.0
    },
    'flag_unimputed_jump_curve': { #if this is hit, there must be a lot of other low quality data
      'percent_cutoff': 0.000001
    },
    'flag_below_threshold_curve': {
      'percent_cutoff': 0.5,
    },
    # Start / End flags (using only percent)
    'flag_incomplete_curve_start_curve': {
        'percent_cutoff': 0.50
    },
    'flag_imputed_rise_curve': {
        'percent_cutoff': 0.50
    },
    'flag_incomplete_curve_end_curve': {
        'percent_cutoff': 0.50
    },
    'flag_imputed_fall_curve': {
        'percent_cutoff': 0.50
    },
    # Periphery Before flags (using only percent)
    'flag_gaps_and_non_wear_periphery_before': {
        'percent_cutoff': 0.60
    },
    'flag_extreme_negative_periphery_before': {
        'percent_cutoff': 0.95
    },
    'flag_unimputed_low_quality_periphery_before': {
      'percent_cutoff': 0.25,
    },
    # Periphery After flags (using only percent)
    'flag_gaps_and_non_wear_periphery_after': {
        'percent_cutoff': 0.60
    },
    'flag_extreme_negative_periphery_after': {
        'percent_cutoff': 0.95
    },
    'flag_unimputed_low_quality_periphery_after': {
      'percent_cutoff': 0.25,
    },
} 