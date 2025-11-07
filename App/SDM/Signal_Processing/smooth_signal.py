from scipy.signal import savgol_filter

def smooth_savgol(df, window_length = 15, polyorder = 2, tac_variable = 'TAC'):
    """
    Apply Savgol filter to non-imputed TAC data, smoothing each contiguous segment separately.
    This prevents smoothing from:
    1. Reaching across null gaps (device off, gaps, etc.)
    2. Modifying imputed values (which should remain as the imputation model generated them)
    """
    import numpy as np
    
    # Create masks for data that should be smoothed
    non_null_mask = df[tac_variable].notnull()
    
    # Only smooth non-imputed data (if 'imputed' column exists)
    if 'imputed' in df.columns:
        non_imputed_mask = (df['imputed'] == 0)
        smoothable_mask = non_null_mask & non_imputed_mask
    else:
        # Backward compatibility: if no 'imputed' column, smooth all non-null data
        smoothable_mask = non_null_mask
    
    # Find contiguous segments of smoothable data
    # Create a group identifier that increments at each transition where data becomes non-smoothable
    segment_id = (~smoothable_mask).cumsum()
    
    # Apply savgol filter to each contiguous segment separately
    for seg_id in segment_id[smoothable_mask].unique():
        segment_mask = (segment_id == seg_id) & smoothable_mask
        segment_length = segment_mask.sum()
        
        # Only smooth if segment is long enough for the window
        if segment_length >= window_length:
            segment_data = df.loc[segment_mask, tac_variable]
            smoothed_segment = savgol_filter(segment_data, window_length=window_length, 
                                            polyorder=polyorder, mode='mirror')
            df.loc[segment_mask, tac_variable] = smoothed_segment
        # If segment is too short, leave it unsmoothed
        
    return df
