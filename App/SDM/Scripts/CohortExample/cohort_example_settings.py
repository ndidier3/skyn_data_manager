"""
Configuration settings for CohortExample process and analysis scripts.

Layered on shared defaults under App/SDM/Run/default_settings/.
Override only what differs for this cohort.
"""

from App.SDM.Run.default_settings.default_smooth_impute_settings import (
    DEFAULT_SMOOTH_AND_IMPUTE_ATTRS,
)
from App.SDM.Run.default_settings.default_curve_settings import DEFAULT_CURVE_ATTRS

# ---------------------------------------------------------------------------
# Smooth / impute
# ---------------------------------------------------------------------------
smooth_and_impute_attrs = DEFAULT_SMOOTH_AND_IMPUTE_ATTRS.copy()
# Example override:
# smooth_and_impute_attrs['export_excel'] = False

# ---------------------------------------------------------------------------
# Gaps and non-wear
# ---------------------------------------------------------------------------
gaps_and_non_wear_attrs = {
    'export_excel': False,
}

# ---------------------------------------------------------------------------
# Curve detection / flagging
# ---------------------------------------------------------------------------
curve_attrs = DEFAULT_CURVE_ATTRS.copy()
# Example overrides:
# curve_attrs['default_threshold'] = 15.0
# curve_attrs['flag_selections']['flag_gaps_and_non_wear_periphery_before'] = {
#     'percent_cutoff': 0.90,
# }

# ---------------------------------------------------------------------------
# Day windows
# ---------------------------------------------------------------------------
day_attrs = {
    'day_start_hour': 6,   # hour at which a "study day" begins
    'make_graphs': True,
}

# ---------------------------------------------------------------------------
# Events (self-report / EMA) — leave empty if this cohort has none
# ---------------------------------------------------------------------------
event_attrs = {}
# Example when events are available:
# event_attrs = {
#     'data': event_dataframe,           # set in the process script after load
#     'subid_column': 'ID',
#     'drink_total': 'totdrinks_fin',
#     'ema_id': 'STUDYDAY',
#     'event_timestamp_columns': ['drinkStart', 'drinkFinish'],
# }
