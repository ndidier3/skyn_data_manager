import pandas as pd


# def get_sampling_rate_mode(df: pd.DataFrame, timestamp_column: str) -> float:
#     """Estimate sampling rate (readings per minute) using mode of readings per minute.

#     Works well for irregular data by grouping to minute buckets and counting rows.
#     """
#     df_copy = df.copy()
#     # Minute-level key, drop seconds
#     df_copy['minute_key'] = df_copy[timestamp_column].dt.strftime('%Y-%m-%d %H:%M')
#     readings_per_minute = df_copy['minute_key'].value_counts()
#     if readings_per_minute.empty:
#         return 1
#     mode_count = readings_per_minute.mode().iloc[0]
#     # Map typical modes to expected readings/min
#     if mode_count == 3:
#         return 3
#     if mode_count == 1:
#         return 1
#     if mode_count <= 0.2:
#         return 0.2
#     return float(mode_count)


# def get_sampling_rate_avg(df: pd.DataFrame, timestamp_column: str) -> float:
#     """Estimate sampling rate by average time delta between rows.

#     readings_per_minute = 60 / average_seconds_between_rows
#     """
#     time_diff = df[timestamp_column].diff()
#     try:
#         avg_seconds = time_diff.mean().total_seconds()
#         if avg_seconds <= 0 or pd.isna(avg_seconds):
#             return 1
#         return round(60 / avg_seconds)
#     except Exception:
#         return 1

def get_sampling_rate_avg(df: pd.DataFrame, timestamp_column: str) -> float:
    """Estimate sampling rate by average time delta between rows.

    readings_per_minute = 60 / average_seconds_between_rows
    """
    time_diff = df[timestamp_column].diff()
    # Only change: remove time_diffs greater than 5 minutes
    time_diff = time_diff[time_diff <= pd.Timedelta(minutes=5)]
    try:
        avg_seconds = time_diff.mean().total_seconds()
        if avg_seconds <= 0 or pd.isna(avg_seconds):
            return 1
        return round(60 / avg_seconds)
    except Exception:
        return 1

def reduce_sampling_rate(df: pd.DataFrame, timestamp_column: str) -> pd.DataFrame:
    """Reduce to one reading per minute by keeping the first row within each minute bucket."""
    df_copy = df.copy()
    df_copy['minute_key'] = df_copy[timestamp_column].dt.strftime('%Y-%m-%d %H:%M')
    reduced = df_copy.groupby('minute_key').first().reset_index(drop=True)
    # Remove helper if present
    if 'minute_key' in reduced.columns:
        reduced = reduced.drop(columns=['minute_key'], errors='ignore')
    return reduced


