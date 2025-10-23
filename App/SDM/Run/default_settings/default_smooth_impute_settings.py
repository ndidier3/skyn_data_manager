"""
Default smooth and impute settings for signal processing.
These settings are used by ACE, ARC, and LINC analysis scripts.
"""

DEFAULT_SMOOTH_AND_IMPUTE_ATTRS = {
    'median_smooth': False,
    'impute_low_quality': True,
    'savgol_smooth': False,
    'export_excel': False
} 