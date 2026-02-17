"""
Visualization functions for ARC-specific comparisons between matched valid and invalid curves.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os


def create_matched_valid_invalid_boxplots(valid_df, invalid_df, output_path=None, show_legend=True):
    """
    Create horizontal box and whisker plots for TAC features comparing Passed vs Flagged curves.
    
    Design:
    - Y-axis: Categories (Passed, Flagged)
    - X-axis: TAC feature values
    - Features plotted (stacked vertically, top to bottom):
      - Peak
      - AUC
      - Rise Duration
      - Fall Duration
      - Rise Rate
      - Fall Rate
    
    Args:
        valid_df (pd.DataFrame): DataFrame containing matched valid (Passed) curves with TAC features
        invalid_df (pd.DataFrame): DataFrame containing matched invalid (Flagged) curves with TAC features
        output_path (str, optional): Full path to save the plot. If None, returns the figure.
        show_legend (bool): Whether to display legend. Default: True
    
    Returns:
        matplotlib.figure.Figure: The figure object if output_path is None, otherwise None
    """
    # Define the features to plot and their display names
    features = {
        'peak_CURVE': 'Peak',
        'auc_total_CURVE': 'AUC',
        'rise_duration_CURVE': 'Rise Duration',
        'fall_duration_CURVE': 'Fall Duration',
        'rise_rate_CURVE': 'Rise Rate',
        'fall_rate_CURVE': 'Fall Rate'
    }
    
    # Filter to only include features that exist in the dataframes
    available_features = {}
    for col, name in features.items():
        if col in valid_df.columns or col in invalid_df.columns:
            available_features[col] = name
    
    if not available_features:
        print("Warning: No TAC features found in the dataframes")
        return None
    
    # Create figure with subplots arranged vertically (stacked)
    n_features = len(available_features)
    fig, axes = plt.subplots(n_features, 1, figsize=(10, 3 * n_features))  # Reduced vertical spacing
    
    # Handle single subplot case
    if n_features == 1:
        axes = [axes]
    
    # Define colors and labels
    passed_color = 'green'  # Valid curves = Passed
    flagged_color = 'red'   # Invalid curves = Flagged
    colors = [passed_color, flagged_color]
    category_labels = ['Passed', 'Flagged']  # Y-axis labels
    
    # Define plot parameters
    box_height = 0.5
    point_size = 20
    point_alpha = 0.5
    
    # First pass: Calculate shared x-axis limits for duration and rate pairs
    duration_features = ['rise_duration_CURVE', 'fall_duration_CURVE']
    rate_features = ['rise_rate_CURVE', 'fall_rate_CURVE']
    
    # Calculate shared limits for duration pair
    duration_min = None
    duration_max = None
    for feature_col in duration_features:
        if feature_col in available_features:
            passed_data = valid_df[feature_col].dropna() if feature_col in valid_df.columns else pd.Series(dtype=float)
            flagged_data = invalid_df[feature_col].dropna() if feature_col in invalid_df.columns else pd.Series(dtype=float)
            all_values = pd.concat([passed_data, flagged_data]) if len(passed_data) > 0 or len(flagged_data) > 0 else pd.Series(dtype=float)
            if len(all_values) > 0:
                feat_min = float(all_values.min())
                feat_max = float(all_values.max())
                if duration_min is None or feat_min < duration_min:
                    duration_min = feat_min
                if duration_max is None or feat_max > duration_max:
                    duration_max = feat_max
    
    # Calculate shared limits for rate pair (accounting for log scale)
    rate_min = None
    rate_max = None
    for feature_col in rate_features:
        if feature_col in available_features:
            passed_data = valid_df[feature_col].dropna() if feature_col in valid_df.columns else pd.Series(dtype=float)
            flagged_data = invalid_df[feature_col].dropna() if feature_col in invalid_df.columns else pd.Series(dtype=float)
            # Filter for positive values (required for log scale)
            passed_data = passed_data[passed_data > 0]
            flagged_data = flagged_data[flagged_data > 0]
            all_values = pd.concat([passed_data, flagged_data]) if len(passed_data) > 0 or len(flagged_data) > 0 else pd.Series(dtype=float)
            if len(all_values) > 0:
                feat_min = float(all_values.min())
                feat_max = float(all_values.max())
                if rate_min is None or feat_min < rate_min:
                    rate_min = feat_min
                if rate_max is None or feat_max > rate_max:
                    rate_max = feat_max
    
    # Create horizontal box plots for each feature
    for ax, (feature_col, feature_name) in zip(axes, available_features.items()):
        # Extract data for valid (Passed) and invalid (Flagged) curves
        passed_data = valid_df[feature_col].dropna() if feature_col in valid_df.columns else pd.Series(dtype=float)
        flagged_data = invalid_df[feature_col].dropna() if feature_col in invalid_df.columns else pd.Series(dtype=float)
        
        # Prepare data for plotting (order: Flagged first at y=1, Passed second at y=2 for top position)
        # With vert=False, first element goes to y=1 (bottom), second to y=2 (top)
        # So we reverse to put Passed on top
        data = [flagged_data, passed_data]
        
        # Handle log scale for AUC, Rise Rate, and Fall Rate
        log_scale_features = ['auc_total_CURVE', 'rise_rate_CURVE', 'fall_rate_CURVE']
        use_log_scale = feature_col in log_scale_features
        
        # Step 1: Filter out non-positive values for log scale if needed
        if use_log_scale:
            data = [d[d > 0] for d in data]
        
        # Step 2: Set log scale on axis BEFORE creating boxplot
        # This ensures matplotlib uses the correct coordinate transformation from the start
        if use_log_scale and (len(data[0]) > 0 or len(data[1]) > 0):
            ax.set_xscale('log')
        
        # Step 3: Create boxplot with original (linear) data
        # Use matplotlib's native boxplot with conventional 1.5*IQR rule
        # Whiskers extend to most extreme points within 1.5*IQR from box edges
        # Note: showfliers=False because we plot all points manually as scatter overlay
        bp = ax.boxplot(data,
                       labels=['Flagged', 'Passed'],  # Reversed to match data order
                       vert=False,  # Horizontal box plot: categories on y-axis, values on x-axis
                       patch_artist=True,
                       medianprops={'color': 'black', 'linewidth': 2},
                       showfliers=False,  # Don't show outliers separately (scatter overlay shows all points)
                       whis=1.5,  # Whiskers extend to 1.5*IQR (conventional boxplot)
                       widths=box_height,
                       zorder=2)
        
        # Diagnostic: Print actual data min/max vs whisker positions
        print(f"\n  {feature_name} - Diagnostic Info:")
        for idx, (d, label) in enumerate(zip(data, ['Flagged', 'Passed'])):
            if len(d) > 0:
                data_min = float(d.min())
                data_max = float(d.max())
                # Get whisker positions from matplotlib
                whisker_idx_left = idx * 2
                whisker_idx_right = idx * 2 + 1
                whiskers = bp['whiskers']
                if len(whiskers) > whisker_idx_right:
                    whisker_left_x = whiskers[whisker_idx_left].get_xdata()
                    whisker_right_x = whiskers[whisker_idx_right].get_xdata()
                    whisker_left_min = float(min(whisker_left_x)) if len(whisker_left_x) > 0 else None
                    whisker_right_max = float(max(whisker_right_x)) if len(whisker_right_x) > 0 else None
                    print(f"    {label}: Data min={data_min:.2f}, max={data_max:.2f}")
                    left_str = f"{whisker_left_min:.2f}" if whisker_left_min is not None else "None"
                    right_str = f"{whisker_right_max:.2f}" if whisker_right_max is not None else "None"
                    print(f"           Whisker left min={left_str}, right max={right_str}")
                    if whisker_left_min is not None and abs(whisker_left_min - data_min) > 0.01:
                        print(f"           WARNING: Whisker left ({whisker_left_min:.2f}) != data min ({data_min:.2f})")
                    if whisker_right_max is not None and abs(whisker_right_max - data_max) > 0.01:
                        print(f"           WARNING: Whisker right ({whisker_right_max:.2f}) != data max ({data_max:.2f})")
        
        # Step 4: Extract actual whisker positions from matplotlib (after creation) to set limits
        # This ensures perfect coordination between whiskers and scatter points
        if len(data[0]) > 0 or len(data[1]) > 0:
            # Get actual min/max from the DATA (same source as scatter points)
            all_values = pd.concat([d for d in data if len(d) > 0])
            if len(all_values) > 0:
                data_min = float(all_values.min())
                data_max = float(all_values.max())
                
                # Also check whisker extents from matplotlib
                whisker_x_coords = []
                for whisker in bp['whiskers']:
                    whisker_x_coords.extend(whisker.get_xdata())
                for cap in bp['caps']:
                    whisker_x_coords.extend(cap.get_xdata())
                
                if whisker_x_coords:
                    whisker_min = float(min(whisker_x_coords))
                    whisker_max = float(max(whisker_x_coords))
                    print(f"    Combined: Data range=[{data_min:.2f}, {data_max:.2f}], Whisker range=[{whisker_min:.2f}, {whisker_max:.2f}]")
                    # Use the wider of the two ranges to ensure everything is visible
                    x_min_to_use = min(data_min, whisker_min) if whisker_x_coords else data_min
                    x_max_to_use = max(data_max, whisker_max) if whisker_x_coords else data_max
                else:
                    x_min_to_use = data_min
                    x_max_to_use = data_max
                
                # Check if this feature should use shared limits
                use_shared_limits = False
                shared_min = None
                shared_max = None
                
                if feature_col in duration_features and duration_min is not None and duration_max is not None:
                    # Use shared duration limits
                    use_shared_limits = True
                    shared_min = duration_min
                    shared_max = duration_max
                    use_log_scale_shared = False
                elif feature_col in rate_features and rate_min is not None and rate_max is not None:
                    # Use shared rate limits
                    use_shared_limits = True
                    shared_min = rate_min
                    shared_max = rate_max
                    use_log_scale_shared = True  # Rates use log scale
                
                if use_shared_limits:
                    # Use shared limits with appropriate padding
                    if use_log_scale_shared:
                        # For log scale, minimal padding
                        x_min = max(0.1, shared_min * 0.5)
                        x_max = shared_max * 1.5
                    else:
                        # For linear scale, minimal padding
                        x_range = shared_max - shared_min
                        x_min = max(0, shared_min - x_range * 0.02) if x_range > 0 else max(0, shared_min - 1)
                        x_max = shared_max + x_range * 0.02 if x_range > 0 else shared_max + 1
                    print(f"    Setting xlim (shared): [{x_min:.2f}, {x_max:.2f}]")
                else:
                    # Use individual limits
                    if use_log_scale:
                        # For log scale, minimal padding
                        x_min = max(0.1, x_min_to_use * 0.5)
                        x_max = x_max_to_use * 1.5
                    else:
                        # For linear scale, minimal padding
                        x_range = x_max_to_use - x_min_to_use
                        x_min = max(0, x_min_to_use - x_range * 0.02) if x_range > 0 else max(0, x_min_to_use - 1)
                        x_max = x_max_to_use + x_range * 0.02 if x_range > 0 else x_max_to_use + 1
                    print(f"    Setting xlim (individual): [{x_min:.2f}, {x_max:.2f}]")
                
                ax.set_xlim(left=x_min, right=x_max)
        
        # Color the boxes (reverse colors to match reversed data order)
        for box, color in zip(bp['boxes'], [flagged_color, passed_color]):
            box.set(facecolor=color, alpha=0.3)
            box.set(edgecolor=color, linewidth=2)
        
        # Plot all points: spread horizontally (left-to-right) along x-axis with vertical jitter (up/down) for y-position
        # Data order: [flagged_data, passed_data] so idx 0=Flagged (y=1, bottom), idx 1=Passed (y=2, top)
        for idx, (d, color) in enumerate(zip(data, [flagged_color, passed_color])):
            if len(d) > 0:
                # Base Y position at box plot center (1 for Flagged, 2 for Passed)
                base_y = idx + 1
                
                # Spread points horizontally (left-to-right) along x-axis - this is the actual data spread
                # The x-position is the actual feature value
                # NOTE: No horizontal jitter to ensure points align with whiskers (whiskers are at exact min/max)
                x_values = d.values
                x_pos = x_values  # Use exact data values, no horizontal jitter
                
                # Diagnostic: verify scatter points are within whisker range
                category_label = ['Flagged', 'Passed'][idx]
                if idx == 0 and feature_name == 'Peak':  # Print for first feature only
                    print(f"    Scatter points for {category_label}: min={x_pos.min():.2f}, max={x_pos.max():.2f} (should match data min/max)")
                
                # Apply vertical jitter (up/down) to y-position for visualization
                # This spreads points vertically around their category position
                vertical_jitter = np.random.normal(0, box_height * 0.2, size=len(d))
                vertical_jitter = np.clip(vertical_jitter, -box_height * 0.3, box_height * 0.3)
                y_pos = base_y + vertical_jitter
                
                # Plot points: x-axis shows feature values (spread left-to-right), y-axis shows category with jitter
                ax.scatter(x_pos, y_pos, 
                          color=color, alpha=point_alpha, s=point_size, 
                          zorder=1, edgecolors='none')
        
        # Set labels - feature name on left (y-axis, vertically oriented)
        ax.set_title('', fontsize=0)  # Remove individual plot titles
        ax.set_xlabel('', fontsize=12)  # Remove x-axis label
        ax.set_ylabel(feature_name, fontsize=12, rotation=90, ha='center', va='center', fontweight='bold', labelpad=15)  # Feature name on left, vertically oriented, bold, increased spacing
        # Remove y-axis labels but keep y-axis line (legend shows Passed/Flagged meaning)
        ax.set_yticks([1, 2])
        ax.set_yticklabels(['', ''])  # Empty labels
        ax.tick_params(axis='y', which='both', length=0)  # Remove tick marks
        # Keep y-axis line (spine) visible
        ax.spines['left'].set_visible(True)
        ax.grid(True, axis='x', linestyle='--', alpha=0.3, zorder=0)
    
    # Add overall title at the top
    fig.suptitle('TAC Features: Passed vs Flagged Curves', 
                 fontsize=16, fontweight='bold', y=0.995)
    
    # Add legend if requested (positioned in top right of first plot)
    if show_legend:
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor=passed_color, alpha=0.3, edgecolor=passed_color, label='Passed'),
            Patch(facecolor=flagged_color, alpha=0.3, edgecolor=flagged_color, label='Flagged')
        ]
        # Add legend to the first subplot (top plot)
        axes[0].legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(0.98, 0.98), fontsize=11, framealpha=0.9)
    
    plt.tight_layout(rect=[0.12, 0, 1, 0.98])  # Leave more space on left for feature names and top for suptitle
    plt.subplots_adjust(hspace=0.15)  # Further reduced padding between subplots
    
    # Save or return figure
    if output_path:
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        fig.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close(fig)
        print(f"Box plot saved to: {output_path}")
        return None
    else:
        return fig
