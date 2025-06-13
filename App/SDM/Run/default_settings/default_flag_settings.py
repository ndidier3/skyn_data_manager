"""
Default flag settings for curve analysis.
These settings are used by ACE, ARC, and LINC analysis scripts.
"""

DEFAULT_FLAG_SELECTIONS = {
    # Curve flags (using both percent and duration)
    'flag_unimputed_gaps_and_non_wear_region': {
        'percent_cutoff': 0.20,
        'duration_cutoff': 2.0
    },
    #this flag may be loosened but peak_TAC will always be invalid if jump is preset
    'flag_unimputed_jump_curve': {
        'percent_cutoff': 0.0,
        'duration_cutoff': 0.0
    },
    'flag_unimputed_plummet_curve': {
        'percent_cutoff': 0.20,
        'duration_cutoff': 2.0
    },
    'flag_unimputed_extreme_negative_curve': {
        'percent_cutoff': 0.10,
        'duration_cutoff': 1.0
    },
    'flag_imputed_low_quality_curve': {
      'percent_cutoff': 0.40,
      'duration_cutoff': 3.0
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
    # Curve completion flags (using only percent)
    'flag_incomplete_curve_start_curve': {
        'percent_cutoff': 0.50
    },
    'flag_incomplete_curve_end_curve': {
        'percent_cutoff': 0.50
    }
} 