"""
Default flag settings for curve analysis.
These settings are used by ACE, ARC, and LINC analysis scripts.
"""

DEFAULT_FLAG_SELECTIONS = {
    # Curve flags (using both percent and duration)
    'flag_unimputed_low_quality_curve': {
      'percent_cutoff': 0.05,
      'duration_cutoff': 0.5
    },
    'flag_imputed_low_quality_curve': {
      'percent_cutoff': 0.30,
      'duration_cutoff': 3.0
    },
    'flag_below_threshold_curve': {
      'percent_cutoff': 0.5,
    },
    # Periphery flags (using only percent)
    'flag_gaps_and_non_wear_periphery': {
        'percent_cutoff': 0.40
    },
    'flag_extreme_negative_periphery': {
        'percent_cutoff': 0.40
    },
    'flag_low_quality_periphery': {
      'percent_cutoff': 0.50
    },
    'flag_unimputed_low_quality_periphery': {
      'percent_cutoff': 0.20,
    },
    # Rise / Fall flags (using only percent)
    'flag_incomplete_curve_start_curve': {
        'percent_cutoff': 0.50
    },
    'flag_low_quality_rise_curve': {
        'percent_cutoff': 0.50
    },
    'flag_incomplete_curve_end_curve': {
        'percent_cutoff': 0.50
    },
    'flag_low_quality_fall_curve': {
        'percent_cutoff': 0.50
    },
} 