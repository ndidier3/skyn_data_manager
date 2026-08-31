"""Unit tests for independent raw curve demarcation helpers."""

import pandas as pd
import numpy as np

from App.SDM.Signal_Processing.curve_demarcation import attach_imputed_curve_matches


def _curve_row(curve_id, begin, end):
    return {
        'curve_id': curve_id,
        'begin_CURVE': pd.Timestamp(begin),
        'end_CURVE': pd.Timestamp(end),
    }


def test_attach_imputed_curve_matches_picks_highest_overlap():
    imputed = pd.DataFrame([
        _curve_row(0, '2024-01-01 10:00', '2024-01-01 11:00'),
        _curve_row(1, '2024-01-01 12:00', '2024-01-01 14:00'),
    ])
    raw = pd.DataFrame([
        _curve_row(0, '2024-01-01 10:30', '2024-01-01 12:30'),
    ])
    out = attach_imputed_curve_matches(raw, imputed)
    assert out.loc[0, 'curve_id_imputed_match'] == 0
    assert out.loc[0, 'imputed_match_overlap_percent'] > 0


def test_attach_imputed_curve_matches_tie_breaks_to_lower_id():
    imputed = pd.DataFrame([
        _curve_row(1, '2024-01-01 10:00', '2024-01-01 11:00'),
        _curve_row(0, '2024-01-01 10:00', '2024-01-01 11:00'),
    ])
    raw = pd.DataFrame([
        _curve_row(0, '2024-01-01 10:15', '2024-01-01 10:45'),
    ])
    out = attach_imputed_curve_matches(raw, imputed)
    assert out.loc[0, 'curve_id_imputed_match'] == 0


def test_attach_imputed_curve_matches_no_overlap():
    imputed = pd.DataFrame([
        _curve_row(0, '2024-01-01 10:00', '2024-01-01 11:00'),
    ])
    raw = pd.DataFrame([
        _curve_row(0, '2024-01-01 12:00', '2024-01-01 13:00'),
    ])
    out = attach_imputed_curve_matches(raw, imputed)
    assert pd.isna(out.loc[0, 'curve_id_imputed_match'])


def test_raw_threshold_attrs_do_not_clobber_imputed():
    """Raw k-means details must use separate attrs keys on the dataset frame."""
    from App.SDM.Signal_Processing.curve_demarcation import get_curve_threshold_from_method

    n = 300
    df = pd.DataFrame({
        'TAC': np.linspace(1, 20, n),
        'TAC_smoothed_unimputed': np.linspace(1, 18, n),
        'device_worn_model': 1,
    })
    get_curve_threshold_from_method(df, 'auto', default_threshold=8.0, TAC_column='TAC')
    imputed_results = dict(df.attrs['curve_threshold_results'])

    get_curve_threshold_from_method(
        df,
        'auto',
        default_threshold=8.0,
        TAC_column='TAC_smoothed_unimputed',
        details_attrs_key='raw_curve_threshold_details',
        results_attrs_key='raw_curve_threshold_results',
        label_main_dataframe=False,
    )
    assert 'raw_curve_threshold_results' in df.attrs
    assert df.attrs['curve_threshold_results'] == imputed_results
    assert 'raw_curve_threshold_details' in df.attrs
    assert 'curve_threshold_details' in df.attrs
