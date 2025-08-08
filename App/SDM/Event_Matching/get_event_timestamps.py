import pandas as pd
from typing import List, Dict, Any, Optional, Tuple

def process_event_timestamps(
    events_df: pd.DataFrame,
    event_timestamp_columns: List[str],
    drink_total_column: str,
    ema_id_column: str,
    max_event_duration: int = 6
) -> Tuple[pd.DataFrame, pd.DataFrame, List[Dict[str, Any]]]:
    """
    Process event timestamps and create event ranges with labels.
    
    Args:
        events_df: DataFrame containing event data
        event_timestamp_columns: List of column names containing timestamp data
        drink_total_column: Column name for drink total data
        ema_id_column: Column name for EMA ID data
        max_event_duration: Maximum duration in hours for events (default: 6)
    
    Returns:
        Tuple containing:
        - events_df: Updated DataFrame with additional columns
        - event_labels: DataFrame with timestamp labels
        - event_ranges: List of dictionaries with event range data
    """
    # Initialize event labels DataFrame
    event_labels = pd.DataFrame(columns=['timestamp', 'label'])
    
    # Add new columns to events DataFrame
    events_df['earliest_timestamp'] = None
    events_df['latest_timestamp'] = None
    events_df['earliest_timestamp_column'] = None
    events_df['latest_timestamp_column'] = None
    events_df['event_match_start'] = None
    events_df['event_match_end'] = None
    events_df['drink_total'] = None
    events_df['end_timestamp_modified'] = False
    events_df['modification_note'] = None
    if 'ema_id' not in events_df.columns:
        events_df['ema_id'] = None
    
    event_ranges = []
    
    for i, row in events_df.iterrows():
        valid_timestamps = [
            row[col] for col in event_timestamp_columns 
            if pd.notna(row[col]) and isinstance(row[col], pd.Timestamp)
        ]
        
        # Check if earliest and latest timestamps are equal and adjust if needed
        timestamp_modified = False
        modification_note = None
        
        if valid_timestamps:
            earliest_timestamp = min(valid_timestamps)
            latest_timestamp = max(valid_timestamps)
            
            # Find the column names for earliest and latest timestamps
            earliest_timestamp_column = None
            latest_timestamp_column = None
            
            for col in event_timestamp_columns:
                if pd.notna(row[col]) and isinstance(row[col], pd.Timestamp):
                    if row[col] == earliest_timestamp:
                        earliest_timestamp_column = col
                    if row[col] == latest_timestamp:
                        latest_timestamp_column = col
            
            # Create adjusted timestamps for curve matching (initially same as original)
            event_match_start = earliest_timestamp
            event_match_end = latest_timestamp
            
            # Check if earliest and latest timestamps are equal and adjust curve match timestamps if needed
            if earliest_timestamp == latest_timestamp:
                event_match_start = earliest_timestamp - pd.Timedelta(hours=1)
                event_match_end = latest_timestamp + pd.Timedelta(hours=1)
                timestamp_modified = True
                modification_note = 'event_match_start adjusted -1 hour, event_match_end adjusted +1 hour; timestamps were equal'
            # Ensure event_match_end is no longer than 12 hours after event_match_start
            elif event_match_end > event_match_start + pd.Timedelta(hours=12):
                event_match_end = event_match_start + pd.Timedelta(hours=12)
                timestamp_modified = True
                modification_note = 'event_match_end constrained to 12 hours from start'
            
            # Add timestamps to events_df
            events_df.loc[i, 'earliest_timestamp'] = earliest_timestamp
            events_df.loc[i, 'latest_timestamp'] = latest_timestamp
            events_df.loc[i, 'earliest_timestamp_column'] = earliest_timestamp_column
            events_df.loc[i, 'latest_timestamp_column'] = latest_timestamp_column
            events_df.loc[i, 'event_match_start'] = event_match_start
            events_df.loc[i, 'event_match_end'] = event_match_end
            events_df.loc[i, 'drink_total'] = row[drink_total_column]
            events_df.loc[i, 'end_timestamp_modified'] = timestamp_modified
            if events_df.loc[i, 'ema_id'] is None:
                events_df.loc[i, 'ema_id'] = row[ema_id_column]
            
            if timestamp_modified:
                events_df.loc[i, 'modification_note'] = modification_note
            
            # Creating labels for curve plots
            # Add earliest timestamp label
            # Get drink total suffix if it exists
            drink_suffix = f'_{row[drink_total_column]}drks' if pd.notna(row[drink_total_column]) else '_NAdrks'
            
            earliest_label = f'{earliest_timestamp_column}_{row[ema_id_column]}{drink_suffix}'
            event_labels = pd.concat([event_labels, pd.DataFrame({'timestamp': [earliest_timestamp], 'label': [earliest_label]})], ignore_index=True)
            
            # Get middle timestamps (excluding earliest and latest, and only including valid timestamps)
            middle_timestamps = [
                row[col] for col in event_timestamp_columns 
                if col not in [earliest_timestamp_column, latest_timestamp_column] 
                and pd.notna(row[col]) 
                and isinstance(row[col], pd.Timestamp)
            ]
            middle_abbreviated_labels = [f'EMA' for i in range(len(middle_timestamps))]
            
            # Only add middle timestamps if there are any
            if middle_timestamps:
                event_labels = pd.concat([event_labels, pd.DataFrame({'timestamp': middle_timestamps, 'label': middle_abbreviated_labels})], ignore_index=True)

            latest_label = f'{latest_timestamp_column}_{row[ema_id_column]}{drink_suffix}'
            event_labels = pd.concat([event_labels, pd.DataFrame({'timestamp': [latest_timestamp], 'label': [latest_label]})], ignore_index=True)

            event_ranges.append({
                'ema_id': row[ema_id_column],
                'drink_total': row[drink_total_column],
                'earliest_timestamp': earliest_timestamp,
                'latest_timestamp': latest_timestamp,
                'event_match_start': event_match_start,
                'event_match_end': event_match_end
            })
    
    return events_df, event_labels, event_ranges
