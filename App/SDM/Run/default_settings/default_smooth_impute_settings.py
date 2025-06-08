"""
Default smooth and impute settings for signal processing.
These settings are used by ACE, ARC, and LINC analysis scripts.
"""

DEFAULT_SMOOTH_AND_IMPUTE_ATTRS = {
    'median_smooth': True,
    'impute_gaps': True,
    'impute_non_wear': True,
    'impute_jumps': True,
    'impute_plummets': True,
    'savgol_smooth': False,
    'export_excel': False
} 