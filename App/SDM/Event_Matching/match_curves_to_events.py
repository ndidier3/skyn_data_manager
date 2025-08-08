import pandas as pd
from typing import List, Dict, Any, Tuple

def _initialize_columns(events_df: pd.DataFrame, curve_features: pd.DataFrame, event_ranges: List[Dict[str, Any]], buffer_before: int, buffer_after: int) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Initialize all required columns for curve-event matching.
    
    Args:
        events_df: DataFrame containing event data
        curve_features: DataFrame containing curve features
        buffer_before: Buffer in hours to add before curve start
        buffer_after: Buffer in hours to add after curve end
    
    Returns:
        Tuple containing initialized events_df and curve_features
    """
    # Initialize curve matching columns in events_df for all events
    for event_range in event_ranges:
        events_df.loc[events_df['ema_id'] == event_range['ema_id'], 'num_curves_matched'] = 0
    
    # Initialize valid/invalid curve match columns (up to 5 matches)
    for i in range(1, 6):
        events_df[f'valid_curve_match_{i}'] = None
        events_df[f'invalid_curve_match_{i}'] = None
    
    # Initialize curve match columns (up to 5 matches)
    for i in range(1, 6):
        events_df[f'curve_match_{i}'] = None
        events_df[f'curve_match_{i}_overlap'] = None
        events_df[f'curve_match_{i}_raw_overlap'] = None
        events_df[f'curve_match_{i}_adjusted_overlap'] = None
        events_df[f'CURVE_and_PERIPHERY_VALID_{i}'] = None
    
    # Initialize shared match columns
    events_df['has_shared_match'] = False
    events_df['shared_curve_id'] = None
    events_df['has_shared_first_match'] = False
    events_df['shared_first_curve_id'] = None
    
    # Initialize matched column
    events_df['matched'] = 0
    
    # Initialize count and flag columns
    events_df['num_valid_curves_matched'] = 0
    events_df['num_invalid_curves_matched'] = 0
    events_df['multiple_valid_curves_matched'] = False
    events_df['multiple_invalid_curves_matched'] = False
    events_df['multiple_mixed_curves_matched'] = False
    
    # Initialize event_matched columns (up to 10 events per curve)
    for i in range(1, 11):
        curve_features[f'event_matched_{i}'] = None
    
    # Initialize all curve_features columns upfront
    curve_features['CURVE_event_match_before_buffer'] = buffer_before
    curve_features['CURVE_event_match_after_buffer'] = buffer_after
    curve_features['CURVE_MATCH_START'] = pd.NaT
    curve_features['CURVE_MATCH_END'] = pd.NaT
    curve_features['num_events_matched'] = 0
    curve_features['matched_ema_ids'] = ''
    curve_features['matched_event_raw_overlaps'] = ''
    curve_features['matched_event_adjusted_overlaps'] = ''
    curve_features['matched_events_valid'] = ''
    curve_features['matched_events_invalid'] = ''
    
    return events_df, curve_features

def match_curves_to_events(
    events_df: pd.DataFrame,
    curve_features: pd.DataFrame,
    event_ranges: List[Dict[str, Any]],
    buffer_before: int = 2,
    buffer_after: int = 0
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Match curves to events based on temporal overlap.
    
    Args:
        events_df: DataFrame containing event data with ema_id column
        curve_features: DataFrame containing curve features with subid, begin_CURVE, end_CURVE columns
        event_ranges: List of dictionaries containing event range data
        buffer_before: Buffer in hours to add before curve start (default: 2)
        buffer_after: Buffer in hours to add after curve end (default: 0)
    
    Returns:
        Tuple containing:
        - Updated events_df with curve matching information, validity flags, and shared match detection
        - Updated curve_features with event matching information and event_matched columns
    """
    # Validate input data
    if not isinstance(events_df, pd.DataFrame) or not isinstance(curve_features, pd.DataFrame):
        raise TypeError("events_df and curve_features must be pandas DataFrames")
    
    if len(events_df) == 0:
        raise ValueError("events_df cannot be empty")
    
    required_event_cols = ['ema_id']
    missing_event_cols = [col for col in required_event_cols if col not in events_df.columns]
    if missing_event_cols:
        raise ValueError(f"Missing required columns in events_df: {missing_event_cols}")
    
    if len(curve_features) > 0:
        required_curve_cols = ['subid', 'curve_id', 'begin_CURVE', 'end_CURVE', 'CURVE_VALID', 'PERIPHERY_VALID']
        missing_curve_cols = [col for col in required_curve_cols if col not in curve_features.columns]
        if missing_curve_cols:
            raise ValueError(f"Missing required columns in curve_features: {missing_curve_cols}")
    
    # Initialize all required columns
    events_df, curve_features = _initialize_columns(events_df, curve_features, event_ranges, buffer_before, buffer_after)
    
    if len(curve_features) > 0:
        # Update curve match timestamps if curves exist
        curve_features['CURVE_MATCH_START'] = pd.to_datetime(curve_features['begin_CURVE']) - pd.Timedelta(hours=buffer_before)
        curve_features['CURVE_MATCH_END'] = pd.to_datetime(curve_features['end_CURVE']) + pd.Timedelta(hours=buffer_after)
        
        # Debug: Print curve information
        print(f"\n=== CURVE DEBUG INFO ===")
        print(f"Total curves: {len(curve_features)}")
        print(f"Curve features DataFrame indices: {curve_features.index.tolist()}")
        print(f"Curve features DataFrame shape: {curve_features.shape}")
        print(f"Buffer before: {buffer_before} hours, Buffer after: {buffer_after} hours")
        print("Curve time ranges:")
        for idx, curve in curve_features.iterrows():
            print(f"  Curve {curve['curve_id']} (DataFrame index {idx}): {curve['begin_CURVE']} to {curve['end_CURVE']} (duration: {(curve['end_CURVE'] - curve['begin_CURVE']).total_seconds()/3600:.1f}h)")
            print(f"    Match range: {curve['CURVE_MATCH_START']} to {curve['CURVE_MATCH_END']} (duration: {(curve['CURVE_MATCH_END'] - curve['CURVE_MATCH_START']).total_seconds()/3600:.1f}h)")
        
        # Debug: Print event ranges
        print(f"\n=== EVENT RANGES DEBUG INFO ===")
        print(f"Total event ranges: {len(event_ranges)}")
        for i, event_range in enumerate(event_ranges):
            print(f"  Event {i+1} (ema_id: {event_range['ema_id']}):")
            print(f"    Original: {event_range['earliest_timestamp']} to {event_range['latest_timestamp']}")
            print(f"    Match range: {event_range['event_match_start']} to {event_range['event_match_end']}")
            print(f"    Duration: {(event_range['event_match_end'] - event_range['event_match_start']).total_seconds()/3600:.1f}h)")
        
        # Track curve-event matches in a dictionary to avoid accumulation issues
        curve_event_matches = {idx: {'ema_ids': [], 'raw_overlaps': [], 'adjusted_overlaps': [], 'valid_ema_ids': [], 'invalid_ema_ids': [], 'count': 0} 
                             for idx in curve_features.index}
        
        for event_range in event_ranges:
            print(f"\n=== PROCESSING EVENT {event_range['ema_id']} ===")
            print(f"Event time range: {event_range['event_match_start']} to {event_range['event_match_end']}")
            print(f"Event duration: {(event_range['event_match_end'] - event_range['event_match_start']).total_seconds()/3600:.2f}h")
            
            # Debug: Show all curves and their temporal relationship to this event
            print(f"\nChecking temporal relationships with {len(curve_features)} curves:")
            for idx, curve in curve_features.iterrows():
                curve_start = curve['CURVE_MATCH_START']
                curve_end = curve['CURVE_MATCH_END']
                event_start = event_range['event_match_start']
                event_end = event_range['event_match_end']
                
                # Check overlap conditions
                no_overlap_condition1 = curve_end < event_start
                no_overlap_condition2 = curve_start > event_end
                has_overlap = not (no_overlap_condition1 or no_overlap_condition2)
                
                print(f"  Curve {curve['curve_id']}: {curve_start} to {curve_end}")
                print(f"    Event: {event_start} to {event_end}")
                print(f"    Condition 1 (curve_end < event_start): {curve_end} < {event_start} = {no_overlap_condition1}")
                print(f"    Condition 2 (curve_start > event_end): {curve_start} > {event_end} = {no_overlap_condition2}")
                print(f"    Has overlap: {has_overlap}")
                print()
            
            # Find curves that overlap with this event's time range using event_match_end
            overlapping_curves = curve_features[
              ~(
                (curve_features['CURVE_MATCH_END'] < event_range['event_match_start']) |  
                (curve_features['CURVE_MATCH_START'] > event_range['event_match_end'])
              )
            ].sort_values('CURVE_MATCH_START')  # Sort by start time to get earliest first
            
            print(f"Found {len(overlapping_curves)} overlapping curves:")
            print(f"Overlapping curves indices: {overlapping_curves.index.tolist()}")
            for idx, curve in overlapping_curves.iterrows():
                overlap_start = max(event_range['event_match_start'], curve['CURVE_MATCH_START'])
                overlap_end = min(event_range['event_match_end'], curve['CURVE_MATCH_END'])
                overlap_duration = (overlap_end - overlap_start).total_seconds() / 3600
                event_duration = (event_range['event_match_end'] - event_range['event_match_start']).total_seconds() / 3600
                curve_duration = (curve['CURVE_MATCH_END'] - curve['CURVE_MATCH_START']).total_seconds() / 3600
                overlap_percentage_of_event = (overlap_duration / event_duration) * 100 if event_duration > 0 else 0
                overlap_percentage_of_curve = (overlap_duration / curve_duration) * 100 if curve_duration > 0 else 0
                
                print(f"  Curve {curve['curve_id']} (original index {idx}): {curve['CURVE_MATCH_START']} to {curve['CURVE_MATCH_END']}")
                print(f"    Overlap: {overlap_start} to {overlap_end} ({overlap_duration:.2f}h)")
                print(f"    Event duration: {event_duration:.2f}h, Curve duration: {curve_duration:.2f}h")
                print(f"    Overlap is {overlap_percentage_of_event:.1f}% of event and {overlap_percentage_of_curve:.1f}% of curve")
            
            matching_curve_ids = overlapping_curves['curve_id'].tolist()
            events_df.loc[events_df['ema_id'] == event_range['ema_id'], 'num_curves_matched'] = len(matching_curve_ids)
            
            # Mark events that have matched to any curve (1 if matched, 0 if not)
            if len(matching_curve_ids) > 0:
                events_df.loc[events_df['ema_id'] == event_range['ema_id'], 'matched'] = 1
            
            # Calculate overlap proportions for each matching curve
            valid_curve_count = 0
            invalid_curve_count = 0
            
            for curve_idx, curve_data in overlapping_curves.iterrows():
                # curve_idx is already the original DataFrame index from curve_features
                curve_id = curve_data['curve_id']  # Get the actual curve_id value
                
                # Calculate raw overlap (original event timestamps vs curve timestamps)
                raw_overlap_start = max(event_range['earliest_timestamp'], curve_data['begin_CURVE'])
                raw_overlap_end = min(event_range['latest_timestamp'], curve_data['end_CURVE'])
                raw_overlap_duration = (raw_overlap_end - raw_overlap_start).total_seconds() if (raw_overlap_end - raw_overlap_start).total_seconds() > 0 else 0
                raw_curve_duration = (curve_data['end_CURVE'] - curve_data['begin_CURVE']).total_seconds()
                raw_overlap_proportion = raw_overlap_duration / raw_curve_duration if raw_curve_duration > 0 else None
                
                # Calculate adjusted overlap (adjusted event timestamps vs curve match timestamps)
                adjusted_overlap_start = max(event_range['event_match_start'], curve_data['CURVE_MATCH_START'])
                adjusted_overlap_end = min(event_range['event_match_end'], curve_data['CURVE_MATCH_END'])
                adjusted_overlap_duration = (adjusted_overlap_end - adjusted_overlap_start).total_seconds() if (adjusted_overlap_end - adjusted_overlap_start).total_seconds() > 0 else 0
                adjusted_curve_duration = (curve_data['CURVE_MATCH_END'] - curve_data['CURVE_MATCH_START']).total_seconds()
                adjusted_overlap_proportion = adjusted_overlap_duration / adjusted_curve_duration if adjusted_curve_duration > 0 else None
                
                # Check if curve is valid
                is_valid_curve = (curve_data.get('CURVE_VALID', 0) == 1 and curve_data.get('PERIPHERY_VALID', 0) == 1)
                
                # Assign to appropriate valid/invalid match column based on validity
                if is_valid_curve:
                    valid_curve_count += 1
                    valid_key = f'valid_curve_match_{valid_curve_count}'
                    events_df.loc[events_df['ema_id'] == event_range['ema_id'], valid_key] = curve_id
                else:
                    invalid_curve_count += 1
                    invalid_key = f'invalid_curve_match_{invalid_curve_count}'
                    events_df.loc[events_df['ema_id'] == event_range['ema_id'], invalid_key] = curve_id
                
                # Store overlap information in the appropriate match column
                match_num = valid_curve_count if is_valid_curve else invalid_curve_count
                match_key = f'curve_match_{match_num}'
                overlap_key = f'curve_match_{match_num}_overlap'
                raw_overlap_key = f'curve_match_{match_num}_raw_overlap'
                adjusted_overlap_key = f'curve_match_{match_num}_adjusted_overlap'
                validity_flag_key = f'CURVE_and_PERIPHERY_VALID_{match_num}'
                
                # Store results in events_df
                events_df.loc[events_df['ema_id'] == event_range['ema_id'], match_key] = curve_id
                events_df.loc[events_df['ema_id'] == event_range['ema_id'], overlap_key] = adjusted_overlap_proportion
                events_df.loc[events_df['ema_id'] == event_range['ema_id'], raw_overlap_key] = raw_overlap_proportion
                events_df.loc[events_df['ema_id'] == event_range['ema_id'], adjusted_overlap_key] = adjusted_overlap_proportion
                events_df.loc[events_df['ema_id'] == event_range['ema_id'], validity_flag_key] = 1 if is_valid_curve else 0
                
                # Track curve-event matches in dictionary using DataFrame index as key
                new_ema_id = str(event_range['ema_id'])
                new_raw_overlap = f"{raw_overlap_proportion:.3f}" if raw_overlap_proportion is not None else "None"
                new_adjusted_overlap = f"{adjusted_overlap_proportion:.3f}" if adjusted_overlap_proportion is not None else "None"
                
                print(f"    Updating curve {curve_id} (index {curve_idx}) with event {new_ema_id}")
                print(f"      Current matched_ema_ids: '{curve_event_matches[curve_idx]['ema_ids']}'")
                print(f"      Adding new ema_id: '{new_ema_id}'")
                
                # Add to dictionary using DataFrame index
                curve_event_matches[curve_idx]['ema_ids'].append(new_ema_id)
                curve_event_matches[curve_idx]['raw_overlaps'].append(new_raw_overlap)
                curve_event_matches[curve_idx]['adjusted_overlaps'].append(new_adjusted_overlap)
                curve_event_matches[curve_idx]['count'] += 1
                
                if is_valid_curve:
                    curve_event_matches[curve_idx]['valid_ema_ids'].append(new_ema_id)
                else:
                    curve_event_matches[curve_idx]['invalid_ema_ids'].append(new_ema_id)
                
                print(f"      New matched_ema_ids: '{curve_event_matches[curve_idx]['ema_ids']}'")
        
        # Apply the accumulated curve-event matches to the DataFrame
        print(f"\n=== FINAL CURVE-EVENT MATCHES ===")
        for curve_idx, matches in curve_event_matches.items():
            if matches['count'] > 0:
                print(f"Curve index {curve_idx}: {matches['count']} events matched")
                print(f"  ema_ids: {matches['ema_ids']}")
                print(f"  valid_ema_ids: {matches['valid_ema_ids']}")
                print(f"  invalid_ema_ids: {matches['invalid_ema_ids']}")
        
        for curve_idx, matches in curve_event_matches.items():
            if matches['count'] > 0:
                curve_features.loc[curve_idx, 'matched_ema_ids'] = ';'.join(matches['ema_ids'])
                curve_features.loc[curve_idx, 'matched_event_raw_overlaps'] = ';'.join(matches['raw_overlaps'])
                curve_features.loc[curve_idx, 'matched_event_adjusted_overlaps'] = ';'.join(matches['adjusted_overlaps'])
                curve_features.loc[curve_idx, 'matched_events_valid'] = ';'.join(matches['valid_ema_ids'])
                curve_features.loc[curve_idx, 'matched_events_invalid'] = ';'.join(matches['invalid_ema_ids'])
                curve_features.loc[curve_idx, 'num_events_matched'] = matches['count']
                print(f"Applied to curve index {curve_idx}: num_events_matched = {matches['count']}")
    
    # Calculate counts and binary flags for each event (optimized)
    valid_cols = [f'valid_curve_match_{i}' for i in range(1, 6)]
    invalid_cols = [f'invalid_curve_match_{i}' for i in range(1, 6)]
    
    # Count non-null values for each event
    events_df['num_valid_curves_matched'] = events_df[valid_cols].notna().sum(axis=1)
    events_df['num_invalid_curves_matched'] = events_df[invalid_cols].notna().sum(axis=1)
    
    # Set binary flags
    events_df['multiple_valid_curves_matched'] = (events_df['num_valid_curves_matched'] > 1) & (events_df['num_invalid_curves_matched'] == 0)
    events_df['multiple_invalid_curves_matched'] = (events_df['num_invalid_curves_matched'] > 1) & (events_df['num_valid_curves_matched'] == 0)
    events_df['multiple_mixed_curves_matched'] = (events_df['num_valid_curves_matched'] > 0) & (events_df['num_invalid_curves_matched'] > 0) & ((events_df['num_valid_curves_matched'] + events_df['num_invalid_curves_matched']) > 1)
    
    # Process shared matches between events for this participant (single ID/SubID)
    # Check if multiple events share the same first valid curve match
    if 'valid_curve_match_1' in events_df.columns:
        first_valid_curve_ids = events_df['valid_curve_match_1'].dropna()
        if len(first_valid_curve_ids) > 0:
            # Find curve IDs that appear multiple times (shared between multiple events)
            shared_first_valid_curves = first_valid_curve_ids[first_valid_curve_ids.duplicated(keep=False)]
            # Mark events that share first valid curve match
            shared_first_mask = events_df['valid_curve_match_1'].isin(shared_first_valid_curves)
            events_df.loc[events_df.index, 'has_shared_first_match'] = shared_first_mask
            events_df.loc[events_df.index[shared_first_mask], 'shared_first_curve_id'] = events_df.loc[events_df.index[shared_first_mask], 'valid_curve_match_1']

    # Get all valid curve match columns
    valid_curve_cols = [col for col in events_df.columns if col.startswith('valid_curve_match_') and not col.endswith('_overlap')]
    
    # Check for any shared curves between pairs of events
    # Create a mapping of curve_id to list of event indices
    curve_to_events = {}
    for idx, row in events_df.iterrows():
        for col in valid_curve_cols:
            curve_id = row[col]
            if pd.notna(curve_id):
                if curve_id not in curve_to_events:
                    curve_to_events[curve_id] = []
                curve_to_events[curve_id].append(idx)
    
    # Find shared curves and mark events
    for curve_id, event_indices in curve_to_events.items():
        if len(event_indices) > 1:  # Multiple events share this curve
            events_df.loc[event_indices, 'has_shared_match'] = True
            events_df.loc[event_indices, 'shared_curve_id'] = curve_id
    
    # Create event_matched columns from matched_ema_ids
    if len(curve_features) > 0 and 'matched_ema_ids' in curve_features.columns:
        max_events = curve_features['num_events_matched'].max() if 'num_events_matched' in curve_features.columns else 0
        
        # Limit to reasonable number of events per curve (up to 10)
        max_events = min(max_events, 10)
        
        for i in range(1, max_events + 1):
            col_name = f'event_matched_{i}'
            
            def extract_nth_ema_id(ema_ids_str, n):
                if pd.isna(ema_ids_str) or ema_ids_str == '':
                    return None
                ema_ids = ema_ids_str.split(';')
                return ema_ids[n-1] if n <= len(ema_ids) else None
            
            curve_features[col_name] = curve_features['matched_ema_ids'].apply(
                lambda x: extract_nth_ema_id(x, i)
            )
    
    return events_df, curve_features 