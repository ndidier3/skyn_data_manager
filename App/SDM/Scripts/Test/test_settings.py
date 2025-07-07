"""
Configuration settings for LINC analysis and stats scripts.
These settings are used by both run_curve_analysis.py and run_curve_stats.py.
"""

from App.SDM.Run.default_settings.default_smooth_impute_settings import DEFAULT_SMOOTH_AND_IMPUTE_ATTRS
from App.SDM.Run.default_settings.default_curve_settings import DEFAULT_CURVE_ATTRS

# Smooth and impute settings
smooth_and_impute_attrs = DEFAULT_SMOOTH_AND_IMPUTE_ATTRS

# Curve analysis settings
curve_attrs = DEFAULT_CURVE_ATTRS

# Event settings
# event_attrs = {
#     'subid_column': 'ID',
#     'drink_total_column': 'totdrinks_fin',
#     'ema_id_column': 'sub_episode_id',
#     'event_timestamp_columns': [
#         'drinkStart', 'drinkFinish', 'concenStart', 'edibleStart', 'flowerStart',
#         'edibleFinish', 'concenFinish', 'flowerFinish', 'earliest_cannabis_fin',
#         'surveyStart', 'surveyFinish', 'fu_A', 'fu_B', 'fu_C', 'fu_D'
#     ]
# }

# Day settings
day_attrs = {
    'day_start_hour': 0,
    'make_graphs': True
}