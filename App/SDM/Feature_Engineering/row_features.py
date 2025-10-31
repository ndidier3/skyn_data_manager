import numpy as np

def generate_row_features(skyn_dataset, include_tac = False):
  try:
    # Store original DataFrame
    df = skyn_dataset.dataset.copy()
    
    # Flag sequences where current and next 4 temps are all > 34
    temp_above = df['Temperature_C'] > 34
    # Also consider cold sequences: current and next 4 temps all < 26
    temp_below = df['Temperature_C'] < 26
    hot5 = (
      temp_above
      & temp_above.shift(-1, fill_value=False)
      & temp_above.shift(-2, fill_value=False)
      & temp_above.shift(-3, fill_value=False)
      & temp_above.shift(-4, fill_value=False)
    )
    cold5 = (
      temp_below
      & temp_below.shift(-1, fill_value=False)
      & temp_below.shift(-2, fill_value=False)
      & temp_below.shift(-3, fill_value=False)
      & temp_below.shift(-4, fill_value=False)
    )
    # Stable high/low temperature flags - only compute for rows where device is turned on
    df['temp_high_stable'] = np.nan
    df['temp_low_stable'] = np.nan
    df['non_wear_pred_needed'] = np.nan
    
    if 'device_turned_on' in df.columns:
      device_on_mask = df['device_turned_on'] == 1
      # Only compute temperature stability flags where device is on
      df.loc[device_on_mask, 'temp_high_stable'] = hot5[device_on_mask].astype(int)
      df.loc[device_on_mask, 'temp_low_stable'] = cold5[device_on_mask].astype(int)
      # Need prediction only when neither stable-high nor stable-low applies
      df.loc[device_on_mask, 'non_wear_pred_needed'] = ((df.loc[device_on_mask, 'temp_high_stable'] == 0) & (df.loc[device_on_mask, 'temp_low_stable'] == 0)).astype(int)
    else:
      # If device_turned_on column doesn't exist, compute for all rows
      df['temp_high_stable'] = hot5.astype(int)
      df['temp_low_stable'] = cold5.astype(int)
      df['non_wear_pred_needed'] = ((df['temp_high_stable'] == 0) & (df['temp_low_stable'] == 0)).astype(int)

    # Vectorized feature computation
    # These compute current value, pre/post differences, and mean-based changes using rolling ops
    # Only compute derived features where prediction is needed to save computational energy
    on_mask = df['device_turned_on'] == 1 if 'device_turned_on' in df.columns else np.ones(len(df), dtype=bool)
    pred_needed_mask = df['non_wear_pred_needed'] == 1 if 'non_wear_pred_needed' in df.columns else np.ones(len(df), dtype=bool)

    def add_vectorized_features(col_name, prefix):
      s = df[col_name]
      s_on = s.where(on_mask)

      # Current value - always compute (needed for plotting/analysis)
      df[f'{prefix}'] = s

      # Initialize derived features as NaN
      df[f'{prefix}_change_pre'] = np.nan
      df[f'{prefix}_change_post'] = np.nan
      df[f'{prefix}_mean_change_pre'] = np.nan
      df[f'{prefix}_mean_change_post'] = np.nan

      # Only compute derived features where prediction is needed
      if pred_needed_mask.sum() > 0:
        # Differences with prior/next (only where needed)
        df.loc[pred_needed_mask, f'{prefix}_change_pre'] = s - s.shift(1)
        df.loc[pred_needed_mask, f'{prefix}_change_post'] = s.shift(-1) - s

        # Rolling means over previous/next 10 on-device samples (NaNs ignored)
        mean_before = s_on.shift(1).rolling(window=10, min_periods=1).mean()
        s_on_rev = s_on.iloc[::-1]
        mean_after_rev = s_on_rev.shift(1).rolling(window=10, min_periods=1).mean()
        mean_after = mean_after_rev.iloc[::-1]

        df.loc[pred_needed_mask, f'{prefix}_mean_change_pre'] = s - mean_before
        df.loc[pred_needed_mask, f'{prefix}_mean_change_post'] = s - mean_after

    add_vectorized_features('Temperature_C', 'temp')
    add_vectorized_features('Motion', 'motion')
    if include_tac:
      add_vectorized_features('TAC', 'tac')

    # Rolling quadratic coefficients (a,b,c) matching old skynDatapoint logic
    # Old version uses time-based x coordinates and variable windows of on-device samples only
    # This is complex to vectorize exactly, so we compute per-row but match the exact logic
    from scipy.optimize import curve_fit

    def quadratic_model(x, a, b, c):
      return a * x**2 + b * x + c

    def compute_quad_coeffs_per_row(idx, col_name, prefix, extension_range, sampling_rate):
      """Compute quadratic coefficients matching skynDatapoint logic exactly"""
      if idx not in df.index:
        return np.nan, np.nan, np.nan, np.nan, np.nan, np.nan
      
      # Skip if non_wear_pred_needed == 0 (matching old code where use_before/use_after=False)
      if 'non_wear_pred_needed' in df.columns and df.loc[idx, 'non_wear_pred_needed'] != 1:
        return np.nan, np.nan, np.nan, np.nan, np.nan, np.nan
      
      current_value = df.loc[idx, col_name]
      current_time = df.loc[idx, 'datetime']
      
      # Get prior values (only on-device samples, up to extension_range)
      values_before = []
      indices_before = []
      for i in range(1, extension_range + 1):
        prior_idx = idx - i
        if prior_idx in df.index:
          if 'device_turned_on' in df.columns:
            if df.loc[prior_idx, 'device_turned_on'] == 1:
              values_before.append(df.loc[prior_idx, col_name])
              indices_before.append(prior_idx)
          else:
            values_before.append(df.loc[prior_idx, col_name])
            indices_before.append(prior_idx)
      
      # Get post values
      values_after = []
      indices_after = []
      for i in range(1, extension_range + 1):
        post_idx = idx + i
        if post_idx in df.index:
          if 'device_turned_on' in df.columns:
            if df.loc[post_idx, 'device_turned_on'] == 1:
              values_after.append(df.loc[post_idx, col_name])
              indices_after.append(post_idx)
          else:
            values_after.append(df.loc[post_idx, col_name])
            indices_after.append(post_idx)
      
      prior_n = len(values_before)
      after_n = len(values_after)
      
      a_pre = b_pre = c_pre = np.nan
      a_post = b_post = c_post = np.nan
      
      # Pre coefficients
      if prior_n > 0:
        # Match old logic: use idx - prior_n (assumes sequential integer indices)
        # This matches skynDatapoint's self.index - self.prior_n
        first_prior_idx = idx - prior_n
        if first_prior_idx in df.index:
          duration_minutes_before = (current_time - df.loc[first_prior_idx, 'datetime']).total_seconds() / 60
          actual_first_idx = first_prior_idx
        else:
          # Fallback: use actual first index if sequential assumption fails
          actual_first_idx = indices_before[0]
          duration_minutes_before = (current_time - df.loc[actual_first_idx, 'datetime']).total_seconds() / 60
          first_prior_idx = actual_first_idx
        x_time_before = [duration_minutes_before * (i - prior_n) / prior_n for i in range(prior_n)]
        x_pre = np.array(x_time_before + [0])
        y_pre = np.array(values_before + [current_value])
        
        # Remove any NaN values before fitting (old code doesn't explicitly check, but curve_fit may handle it)
        valid_mask = ~(np.isnan(x_pre) | np.isnan(y_pre))
        if valid_mask.sum() > 5:
          try:
            params, _ = curve_fit(quadratic_model, x_pre[valid_mask], y_pre[valid_mask])
            a_pre, b_pre, c_pre = params[0], params[1], params[2]
          except (ValueError, RuntimeError):
            pass
      
      # Post coefficients
      if after_n > 0:
        # Match old logic: use idx + after_n (assumes sequential integer indices)
        # This matches skynDatapoint's self.index + self.after_n
        last_post_idx = idx + after_n
        if last_post_idx in df.index:
          duration_minutes_after = (df.loc[last_post_idx, 'datetime'] - current_time).total_seconds() / 60
          actual_last_idx = last_post_idx
        else:
          # Fallback: use actual last index if sequential assumption fails
          actual_last_idx = indices_after[-1]
          duration_minutes_after = (df.loc[actual_last_idx, 'datetime'] - current_time).total_seconds() / 60
          last_post_idx = actual_last_idx
        x_time_after = [duration_minutes_after * i / after_n for i in range(1, after_n + 1)]
        x_post = np.array([0] + x_time_after)
        y_post = np.array([current_value] + values_after)
        
        # Remove any NaN values before fitting
        valid_mask = ~(np.isnan(x_post) | np.isnan(y_post))
        if valid_mask.sum() > 5:
          try:
            params, _ = curve_fit(quadratic_model, x_post[valid_mask], y_post[valid_mask])
            a_post, b_post, c_post = params[0], params[1], params[2]
          except (ValueError, RuntimeError):
            pass
      
      return (a_pre, b_pre, c_pre, a_post, b_post, c_post)

    def add_quadratic_coeffs(col_name, prefix, extension_range, sampling_rate):
      # Compute for all rows
      results = [compute_quad_coeffs_per_row(i, col_name, prefix, extension_range, sampling_rate) 
                 for i in df.index]
      a_pre_vals = [r[0] for r in results]
      b_pre_vals = [r[1] for r in results]
      c_pre_vals = [r[2] for r in results]
      a_post_vals = [r[3] for r in results]
      b_post_vals = [r[4] for r in results]
      c_post_vals = [r[5] for r in results]
      
      df[f'{prefix}_a_pre'] = a_pre_vals
      df[f'{prefix}_b_pre'] = b_pre_vals
      df[f'{prefix}_c_pre'] = c_pre_vals
      df[f'{prefix}_a_post'] = a_post_vals
      df[f'{prefix}_b_post'] = b_post_vals
      df[f'{prefix}_c_post'] = c_post_vals

    try:
      add_quadratic_coeffs('Temperature_C', 'temp', 10, skyn_dataset.sampling_rate)
      add_quadratic_coeffs('Motion', 'motion', 10, skyn_dataset.sampling_rate)
      if include_tac:
        add_quadratic_coeffs('TAC', 'tac', 10, skyn_dataset.sampling_rate)
    except Exception:
      pass

    # Set all columns to NaN where device_turned_on == 0
    if 'device_turned_on' in df.columns:
      columns_to_nan = [
        'temp', 'temp_a_pre', 'temp_b_pre', 'temp_c_pre', 'temp_a_post', 'temp_b_post', 'temp_c_post', 'temp_mean_change_pre', 'temp_mean_change_post', 'temp_change_pre', 'temp_change_post',
        'motion', 'motion_a_pre', 'motion_b_pre', 'motion_c_pre', 'motion_a_post', 'motion_b_post', 'motion_c_post', 'motion_mean_change_pre', 'motion_mean_change_post', 'motion_change_pre', 'motion_change_post',
      ]
      if include_tac:
        columns_to_nan = columns_to_nan + [
          'tac', 'tac_a_pre', 'tac_b_pre', 'tac_c_pre', 'tac_a_post', 'tac_b_post', 'tac_c_post', 'tac_mean_change_pre', 'tac_mean_change_post', 'tac_change_pre', 'tac_change_post'
        ]
      df.loc[df['device_turned_on'] == 0, columns_to_nan] = np.nan

    # Additionally, set DERIVED features to NaN where non_wear_pred_needed == 0
    # NOTE: Keep basic values (temp, motion, tac) as they are needed for plotting and analysis
    if 'non_wear_pred_needed' in df.columns:
      mask_needed = df['non_wear_pred_needed'] == 1
      cols = [
        'temp_a_pre', 'temp_b_pre', 'temp_c_pre', 'temp_a_post', 'temp_b_post', 'temp_c_post', 'temp_mean_change_pre', 'temp_mean_change_post', 'temp_change_pre', 'temp_change_post',
        'motion_a_pre', 'motion_b_pre', 'motion_c_pre', 'motion_a_post', 'motion_b_post', 'motion_c_post', 'motion_mean_change_pre', 'motion_mean_change_post', 'motion_change_pre', 'motion_change_post',
      ]
      if include_tac:
        cols = cols + [
          'tac_a_pre', 'tac_b_pre', 'tac_c_pre', 'tac_a_post', 'tac_b_post', 'tac_c_post', 'tac_mean_change_pre', 'tac_mean_change_post', 'tac_change_pre', 'tac_change_post'
        ]
      df.loc[~mask_needed, cols] = np.nan

  except Exception:
    raise  # Re-raise to let caller handle it

  return df

