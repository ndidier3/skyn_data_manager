"""
Configuration settings for SDM Processor GUI.
These settings mirror those in test_settings.py.
"""

from App.SDM.Run.default_settings.default_flag_settings import DEFAULT_FLAG_SELECTIONS

# Smooth and impute settings
smooth_and_impute_attrs = {
    'median_smooth': True,
    'impute_gaps': True,
    'impute_non_wear': True,
    'impute_jumps': True,
    'impute_plummets': True,
    'savgol_smooth': False,
}

# Curve analysis settings
curve_attrs = {
    'flag_selections': DEFAULT_FLAG_SELECTIONS,
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