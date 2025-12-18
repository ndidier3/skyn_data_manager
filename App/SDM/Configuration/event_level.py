import pandas as pd
from datetime import timedelta, datetime, date, time

def get_study_date_range(event_df: pd.DataFrame, subid_column: str, study_day_id_column: str, 
                         datetime_column: str, max_study_day_id: int, day_start_hour: int):
    """
    Calculate the first and last study datetime boundaries for each subject based on their study day IDs.
    
    For each subject:
    - Finds the earliest study day ID and extracts the corresponding date
    - Adjusts the date backward if earliest_day_id != 1 (e.g., if earliest is 3, subtracts 2 days)
    - Adds day_start_hour to create the first study datetime
    - Finds the latest study day ID and adjusts the date forward to correspond to max_study_day_id
    - Adds day_start_hour + 1 day to create the end study datetime (exclusive boundary)
    
    Args:
        event_df: DataFrame containing event data
        subid_column: Column name for subject ID
        study_day_id_column: Column name for study day ID (e.g., 'emadayn')
        datetime_column: Column name for datetime (e.g., 'surveytime_first')
        max_study_day_id: Maximum expected study day ID
        day_start_hour: Hour at which each day starts (e.g., 7 for 7:00 AM)
    
    Returns:
        Dictionary mapping subid to (first_study_datetime, end_study_datetime) tuple where both are datetime objects.
        end_study_datetime is exclusive (data < end_study_datetime will be included).
    """
    # Convert datetime column to datetime if it's not already
    event_df = event_df.copy()
    event_df[datetime_column] = pd.to_datetime(event_df[datetime_column], errors='coerce')
    
    # Extract date from datetime column
    event_df['_extracted_date'] = event_df[datetime_column].dt.date
    
    # Dictionary to store results: {subid: (first_study_datetime, end_study_datetime)}
    study_date_ranges = {}
    
    # Process each unique subject
    for subid in event_df[subid_column].unique():
        # Normalize subid to integer string for consistent key matching
        # This handles cases where subid might be float64 (e.g., 1028.0) from CSV
        subid_normalized = str(int(float(subid)))
        
        subid_data = event_df[event_df[subid_column] == subid].copy()
        
        # Filter out rows with missing study_day_id or datetime
        subid_data = subid_data[
            subid_data[study_day_id_column].notna() & 
            subid_data['_extracted_date'].notna()
        ]
        
        if subid_data.empty:
            continue
        
        # Find earliest study day ID for this subject
        earliest_day_id = int(subid_data[study_day_id_column].min())
        
        # Get the date associated with the earliest study day ID
        earliest_day_data = subid_data[subid_data[study_day_id_column] == earliest_day_id]
        earliest_date = earliest_day_data['_extracted_date'].iloc[0]
        
        # Adjust first study date: if earliest_day_id != 1, subtract the difference
        days_to_subtract = earliest_day_id - 1
        first_study_date = earliest_date - timedelta(days=days_to_subtract)
        
        # Create first study datetime with day_start_hour
        first_study_datetime = datetime.combine(first_study_date, time(hour=day_start_hour, minute=0, second=0))
        
        # Find latest study day ID for this subject
        latest_day_id = int(subid_data[study_day_id_column].max())
        
        # Get the date associated with the latest study day ID
        latest_day_data = subid_data[subid_data[study_day_id_column] == latest_day_id]
        latest_date = latest_day_data['_extracted_date'].iloc[0]
        
        # Adjust end study date: add days so it corresponds to max_study_day_id
        days_to_add = max_study_day_id - latest_day_id
        end_study_date = latest_date + timedelta(days=days_to_add)
        
        # Create end study datetime with day_start_hour + 1 day (exclusive boundary)
        end_study_datetime = datetime.combine(end_study_date, time(hour=day_start_hour, minute=0, second=0)) + timedelta(days=1)
        
        # Store subid as normalized integer string for consistent key matching
        study_date_ranges[subid_normalized] = (first_study_datetime, end_study_datetime)
    
    return study_date_ranges

def get_study_date_range_from_start_date(event_df: pd.DataFrame, subid_column: str, 
                                         start_date_column: str, max_study_day_id: int, 
                                         day_start_hour: int):
    """
    Calculate the first and last study datetime boundaries for each subject based on a start date column.
    
    This is a simpler version of get_study_date_range for cases where the start date is directly available
    (e.g., B1STARTDATE for ARC Burst 1).
    
    For each subject:
    - Uses the start_date_column value as STUDYDAY 1's date
    - Adds day_start_hour to create the first study datetime
    - Adds max_study_day_id days to get the end study date (the day after the last study day)
    - Adds day_start_hour to create the end study datetime (exclusive boundary)
    
    Args:
        event_df: DataFrame containing event data
        subid_column: Column name for subject ID
        start_date_column: Column name for start date (e.g., 'B1STARTDATE')
        max_study_day_id: Maximum expected study day ID (e.g., 28)
        day_start_hour: Hour at which each day starts (e.g., 7 for 7:00 AM)
    
    Returns:
        Dictionary mapping subid to (first_study_datetime, end_study_datetime) tuple where both are datetime objects.
        end_study_datetime is exclusive (data < end_study_datetime will be included).
    """
    event_df = event_df.copy()
    
    # Verify that the start_date_column exists in the DataFrame
    if start_date_column not in event_df.columns:
        raise ValueError(
            f"Required column '{start_date_column}' not found in event_data. "
            f"Available columns: {list(event_df.columns)}. "
            f"Please ensure this column is preserved when processing event data."
        )
    
    # Convert start_date_column to datetime if it's not already
    event_df[start_date_column] = pd.to_datetime(event_df[start_date_column], errors='coerce')
    
    # Dictionary to store results: {subid: (first_study_datetime, end_study_datetime)}
    study_date_ranges = {}
    
    # Process each unique subject
    for subid in event_df[subid_column].unique():
        # Normalize subid to integer string for consistent key matching
        # This handles cases where subid might be float64 (e.g., 1028.0) from CSV
        subid_normalized = str(int(float(subid)))
        
        subid_data = event_df[event_df[subid_column] == subid].copy()
        
        # Get the start date for this subject (should be the same across all rows)
        start_dates = subid_data[start_date_column].dropna().unique()
        
        if len(start_dates) == 0:
            # No valid start date for this subject
            continue
        
        # Use the first (should be only) start date
        first_study_date = start_dates[0]
        
        # Convert to datetime if it's a numpy.datetime64 or Timestamp
        if hasattr(first_study_date, 'date'):
            study_date = first_study_date.date()
        elif hasattr(first_study_date, 'to_pydatetime'):
            study_date = first_study_date.to_pydatetime().date()
        else:
            # Try converting to datetime first
            first_study_date = pd.to_datetime(first_study_date)
            study_date = first_study_date.date()
        
        # Create first study datetime with day_start_hour (STUDYDAY 1)
        first_study_datetime = datetime.combine(study_date, time(hour=day_start_hour, minute=0, second=0))
        
        # Calculate end study date: start_date + max_study_day_id days (the day after the last study day)
        # STUDYDAY 1 = B1STARTDATE, STUDYDAY max_study_day_id = B1STARTDATE + (max_study_day_id - 1) days
        # Exclusive boundary = B1STARTDATE + max_study_day_id days at day_start_hour
        # Ensure first_study_date is a datetime for timedelta operations
        if not isinstance(first_study_date, datetime):
            first_study_date_dt = pd.to_datetime(first_study_date)
        else:
            first_study_date_dt = first_study_date
        end_study_date = first_study_date_dt + timedelta(days=max_study_day_id)
        
        # Convert end_study_date to date for datetime.combine
        if hasattr(end_study_date, 'date'):
            end_study_date_obj = end_study_date.date()
        elif hasattr(end_study_date, 'to_pydatetime'):
            end_study_date_obj = end_study_date.to_pydatetime().date()
        else:
            end_study_date_dt = pd.to_datetime(end_study_date)
            end_study_date_obj = end_study_date_dt.date()
        
        # Create end study datetime with day_start_hour (exclusive boundary)
        end_study_datetime = datetime.combine(end_study_date_obj, time(hour=day_start_hour, minute=0, second=0))
        
        # Store subid as normalized integer string for consistent key matching
        study_date_ranges[subid_normalized] = (first_study_datetime, end_study_datetime)
    
    return study_date_ranges
