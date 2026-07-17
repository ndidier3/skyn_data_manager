"""
Default curve analysis settings.
These settings are used by ACE, ARC, and LINC analysis scripts.
"""

from App.SDM.Run.default_settings.default_flag_settings import DEFAULT_FLAG_SELECTIONS

DEFAULT_CURVE_ATTRS = {
    'flag_selections': DEFAULT_FLAG_SELECTIONS,
    'curve_threshold': 'auto',
    'default_threshold': 8.0,
    'periphery_buffer_before': 2, 
    'periphery_buffer_after': 2,
    'merge_curves_within_duration': 2
} 