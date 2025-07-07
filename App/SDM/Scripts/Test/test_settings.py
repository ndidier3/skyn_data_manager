"""
Configuration settings for Test analysis scripts.
These settings are used by default_analysis.py and other test-related scripts.
"""

from App.SDM.Run.default_settings.default_smooth_impute_settings import DEFAULT_SMOOTH_AND_IMPUTE_ATTRS
from App.SDM.Run.default_settings.default_curve_settings import DEFAULT_CURVE_ATTRS

# Smooth and impute settings - using defaults for consistency
smooth_and_impute_attrs = DEFAULT_SMOOTH_AND_IMPUTE_ATTRS

# Curve analysis settings - using defaults for consistency
curve_attrs = DEFAULT_CURVE_ATTRS

# Event settings (placeholder for future use if test event data becomes available)
event_attrs = {
    'subid_column': 'ID',
    'event_timestamp_columns': ['drinkStart', 'drinkEnd']
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