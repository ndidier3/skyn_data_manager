"""
Visualization functions for density plots comparing matched valid and invalid curves.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os
from scipy import stats


def create_matched_valid_invalid_density_plots(valid_df, invalid_df, output_path=None, show_legend=True):
    """
    Create density plots for TAC features comparing Passed vs Flagged curves.
    
    Design:
    - X-axis: TAC feature values
    - Y-axis: Density
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
    fig, axes = plt.subplots(n_features, 1, figsize=(10, 3 * n_features))
    
    # Handle single subplot case
    if n_features == 1:
        axes = [axes]
    
    # Define colors
    passed_color = 'green'  # Valid curves = Passed
    flagged_color = 'red'   # Invalid curves = Flagged
    
    # Define plot parameters
    alpha_fill = 0.3  # Transparency for filled area
    line_width = 2  # Line width for density curves
    
    # Create density plots for each feature
    for ax, (feature_col, feature_name) in zip(axes, available_features.items()):
        # Extract data for valid (Passed) and invalid (Flagged) curves
        passed_data = valid_df[feature_col].dropna() if feature_col in valid_df.columns else pd.Series(dtype=float)
        flagged_data = invalid_df[feature_col].dropna() if feature_col in invalid_df.columns else pd.Series(dtype=float)
        
        # Handle log scale for AUC, Rise Rate, and Fall Rate
        log_scale_features = ['auc_total_CURVE', 'rise_rate_CURVE', 'fall_rate_CURVE']
        use_log_scale = feature_col in log_scale_features
        
        if use_log_scale:
            # Filter out non-positive values for log scale
            passed_data = passed_data[passed_data > 0]
            flagged_data = flagged_data[flagged_data > 0]
        
        # Prepare data arrays
        passed_values = passed_data.values if len(passed_data) > 0 else np.array([])
        flagged_values = flagged_data.values if len(flagged_data) > 0 else np.array([])
        
        # Determine x-axis range for density estimation
        if len(passed_values) > 0 or len(flagged_values) > 0:
            all_values = np.concatenate([passed_values, flagged_values]) if (len(passed_values) > 0 and len(flagged_values) > 0) else (passed_values if len(passed_values) > 0 else flagged_values)
            
            if use_log_scale:
                # For log scale, create range in log space but plot in original space
                log_all_values = np.log10(all_values)
                x_min_log = np.min(log_all_values)
                x_max_log = np.max(log_all_values)
                # Add padding in log space
                log_range = x_max_log - x_min_log
                x_min_log = x_min_log - log_range * 0.1
                x_max_log = x_max_log + log_range * 0.1
                # Convert back to original space for plotting
                x_min = 10**x_min_log
                x_max = 10**x_max_log
                x_plot = np.logspace(np.log10(x_min), np.log10(x_max), 200)
            else:
                # For linear scale
                x_min = np.min(all_values)
                x_max = np.max(all_values)
                x_range = x_max - x_min
                x_min = x_min - x_range * 0.1
                x_max = x_max + x_range * 0.1
                x_plot = np.linspace(x_min, x_max, 200)
        else:
            # No data - set default range
            x_plot = np.linspace(0, 1, 200) if not use_log_scale else np.logspace(-1, 2, 200)
        
        # Calculate density for Passed data
        if len(passed_values) > 0:
            if use_log_scale:
                # For log scale, calculate KDE on log-transformed data
                log_passed_values = np.log10(passed_values)
                kde_passed = stats.gaussian_kde(log_passed_values)
                # Evaluate on log-transformed x_plot
                log_x_plot = np.log10(x_plot)
                density_passed = kde_passed(log_x_plot)
                # Transform density to account for log transformation
                # d/dx of log10(x) = 1/(x*ln(10)), so we need to scale by x
                density_passed = density_passed / (x_plot * np.log(10))
            else:
                kde_passed = stats.gaussian_kde(passed_values)
                density_passed = kde_passed(x_plot)
        else:
            density_passed = np.zeros_like(x_plot)
        
        # Calculate density for Flagged data
        if len(flagged_values) > 0:
            if use_log_scale:
                # For log scale, calculate KDE on log-transformed data
                log_flagged_values = np.log10(flagged_values)
                kde_flagged = stats.gaussian_kde(log_flagged_values)
                # Evaluate on log-transformed x_plot
                log_x_plot = np.log10(x_plot)
                density_flagged = kde_flagged(log_x_plot)
                # Transform density to account for log transformation
                density_flagged = density_flagged / (x_plot * np.log(10))
            else:
                kde_flagged = stats.gaussian_kde(flagged_values)
                density_flagged = kde_flagged(x_plot)
        else:
            density_flagged = np.zeros_like(x_plot)
        
        # Set log scale if needed
        if use_log_scale and (len(passed_values) > 0 or len(flagged_values) > 0):
            ax.set_xscale('log')
        
        # Plot density curves with filled areas
        if len(passed_values) > 0:
            ax.fill_between(x_plot, 0, density_passed, alpha=alpha_fill, color=passed_color, label='Passed')
            ax.plot(x_plot, density_passed, color=passed_color, linewidth=line_width)
        
        if len(flagged_values) > 0:
            ax.fill_between(x_plot, 0, density_flagged, alpha=alpha_fill, color=flagged_color, label='Flagged')
            ax.plot(x_plot, density_flagged, color=flagged_color, linewidth=line_width)
        
        # Set labels - feature name on left (y-axis label, vertically oriented)
        ax.set_title('', fontsize=0)  # Remove individual plot titles
        ax.set_xlabel('', fontsize=12)  # Remove x-axis label
        ax.set_ylabel('Density', fontsize=12)  # Y-axis shows density
        # Add feature name as text on the left side (similar to boxplot style)
        ax.text(-0.12, 0.5, feature_name, transform=ax.transAxes, rotation=90, 
                ha='center', va='center', fontsize=12, fontweight='bold')
        ax.grid(True, axis='x', linestyle='--', alpha=0.3, zorder=0)
        
        # Set y-axis to start at 0
        ax.set_ylim(bottom=0)
        
        # Remove x-axis label for all but the bottom plot
        if ax != axes[-1]:
            ax.set_xlabel('')
        
        # Set x-axis limits
        if len(passed_values) > 0 or len(flagged_values) > 0:
            if use_log_scale:
                ax.set_xlim(left=x_min, right=x_max)
            else:
                ax.set_xlim(left=x_min, right=x_max)
    
    # Add overall title at the top
    fig.suptitle('TAC Features: Passed vs Flagged Curves (Density)', 
                 fontsize=16, fontweight='bold', y=0.995)
    
    # Add legend if requested (positioned in top right of first plot)
    if show_legend:
        # Add legend to the first subplot (top plot)
        axes[0].legend(loc='upper right', bbox_to_anchor=(0.98, 0.98), fontsize=11, framealpha=0.9)
    
    plt.tight_layout(rect=[0.12, 0, 1, 0.98])  # Leave more space on left for feature names and top for suptitle
    plt.subplots_adjust(hspace=0.15)  # Reduced padding between subplots
    
    # Save or return figure
    if output_path:
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        fig.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close(fig)
        print(f"Density plot saved to: {output_path}")
        return None
    else:
        return fig
