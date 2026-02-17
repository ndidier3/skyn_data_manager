"""
Bar plot: percentage of events with a curve match by week (Week 1–4).

Uses the same export pattern as feature_scatterbox_plots: accept output_path,
create parent directory if needed, save with savefig(..., dpi=300, bbox_inches='tight').
Callers should use folder/filename structure consistent with other ARC plots, e.g.:
  Results/ARC/barplots/event_match_pct_by_week_<date>.png
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os


def _derive_week(series, day_col='STUDYDAY', fallback_col='emadayn'):
    """
    Map day values to week 1–4 (days 1–7 -> 1, 8–14 -> 2, 15–21 -> 3, 22–28+ -> 4).
    Prefer day_col; if missing or null, use fallback_col.
    """
    day = series.get(day_col)
    if day is None or (hasattr(day, 'isna') and pd.isna(day)):
        day = series.get(fallback_col)
    if day is None or (hasattr(day, 'isna') and pd.isna(day)):
        return np.nan
    try:
        d = int(float(day))
    except (TypeError, ValueError):
        return np.nan
    if d <= 0:
        return np.nan
    return min(4, (d - 1) // 7 + 1)


def create_event_match_pct_by_week_barplot(
    event_df,
    output_path=None,
    week_column=None,
    match_column=None,
    x_labels=None,
):
    """
    Bar plot: x-axis = Week 1, Week 2, Week 3, Week 4; y-axis = % of events with a curve match.

    Args:
        event_df (pd.DataFrame): Event-level data. Must have one row per event.
            If week_column is None, week is derived from STUDYDAY or emadayn (1–7 -> Week 1, etc.).
            If match_column is None, "had match" = (num_valid_curves_matched + num_invalid_curves_matched) >= 1,
            or column 'matched' == 1 if present.
        output_path (str, optional): Full path to save the plot. If None, returns the figure.
        week_column (str, optional): Column name for week (1–4). If None, derived from STUDYDAY/emadayn.
        match_column (str, optional): Column name for "had curve match" (bool or 0/1). If None, inferred from
            num_valid_curves_matched / num_invalid_curves_matched or 'matched'.
        x_labels (list, optional): Labels for x-axis, e.g. ['Week 1', 'Week 2', 'Week 3', 'Week 4']. Default used if None.

    Returns:
        matplotlib.figure.Figure or None: The figure if output_path is None, else None.
    """
    if event_df is None or (hasattr(event_df, 'empty') and event_df.empty):
        print("Warning: event_df is empty; no bar plot created.")
        return None

    # One row per event (dedupe by ema_id, ID if needed)
    if 'ema_id' in event_df.columns and 'ID' in event_df.columns:
        ev = event_df.drop_duplicates(subset=['ema_id', 'ID']).copy()
    else:
        ev = event_df.copy()

    # Week
    if week_column and week_column in ev.columns:
        ev['_week'] = ev[week_column].astype(int).clip(1, 4)
    else:
        ev['_week'] = ev.apply(_derive_week, axis=1)
    ev = ev[ev['_week'].notna() & (ev['_week'] >= 1) & (ev['_week'] <= 4)]

    if ev.empty:
        print("Warning: No events with week 1–4; no bar plot created.")
        return None

    # Had curve match
    if match_column and match_column in ev.columns:
        ev['_matched'] = (ev[match_column].fillna(0).astype(int) >= 1)
    elif 'matched' in ev.columns:
        ev['_matched'] = (ev['matched'].fillna(0).astype(int) >= 1)
    elif 'num_valid_curves_matched' in ev.columns or 'num_invalid_curves_matched' in ev.columns:
        nv = ev.get('num_valid_curves_matched', pd.Series(0, index=ev.index)).fillna(0).astype(int)
        ni = ev.get('num_invalid_curves_matched', pd.Series(0, index=ev.index)).fillna(0).astype(int)
        ev['_matched'] = (nv + ni) >= 1
    else:
        print("Warning: No match column found; assuming no matches.")
        ev['_matched'] = False

    # Percent by week
    weeks = [1, 2, 3, 4]
    labels = x_labels or [f'Week {w}' for w in weeks]
    pcts = []
    for w in weeks:
        sub = ev[ev['_week'] == w]
        n = len(sub)
        if n == 0:
            pcts.append(0.0)
        else:
            pcts.append(100.0 * sub['_matched'].sum() / n)

    # Plot
    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(weeks))
    bars = ax.bar(x, pcts, color='steelblue', edgecolor='black', linewidth=1.2)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel('Percentage of events with a curve match', fontsize=12)
    ax.set_xlabel('')
    ax.set_ylim(0, 105)
    ax.set_title('Event–curve match rate by week', fontsize=14, fontweight='bold')
    for i, (bar, p) in enumerate(zip(bars, pcts)):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2, f'{p:.1f}%',
                ha='center', va='bottom', fontsize=11, fontweight='bold')
    ax.grid(axis='y', linestyle='--', alpha=0.5)
    plt.tight_layout()

    if output_path:
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        fig.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close(fig)
        print(f"Bar plot saved to: {output_path}")
        return None
    return fig
