import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

class QualityVisualizer:
    def __init__(self, quality_features=None, tac_features=None, use_three_imputation_ratio_groups=False):
        """
        Initialize the QualityVisualizer with configurable features.
        
        Args:
            quality_features (list, optional): List of quality feature column names.
                If None, uses default features that end with _REGION.
            tac_features (list, optional): List of TAC feature column names.
                If None, uses default features.
            use_three_imputation_ratio_groups (bool, optional): If True, uses three imputation ratio groups ([0], (0,100), [100]).
                If False, uses two groups ([0,100), [100]). Default is False.
        """
        # Store curve features
        self.curve_features = None
        
        # Default quality features (only _REGION features)
        self.quality_features = quality_features or [
            'total_low_quality_percent_REGION',
            'total_gap_percent_REGION',
            'total_non_wear_percent_REGION',
            'total_jump_percent_REGION',
            'total_plummet_percent_REGION',
            'total_extreme_negative_percent_REGION',
            'total_low_quality_duration_REGION',
            'total_gap_duration_REGION',
            'total_non_wear_duration_REGION',
            'total_jump_duration_REGION',
            'total_plummet_duration_REGION',
            'total_extreme_negative_duration_REGION'
        ]
        
        # Default TAC features
        self.tac_features = tac_features or [
            'auc_total_CURVE',
            'rise_rate_CURVE',
            'peak_CURVE',
            'fall_rate_CURVE'
        ]
        
        # Define imputation ratio groups based on grouping scheme
        if use_three_imputation_ratio_groups:
            # [0] = None (red), (0,100) = Partial (green), [100] = Complete (blue)
            self.imputation_ratio_groups = [
                (0, 0, '[0]'),        # None
                (0, 1, '(0,100)'),    # Partial
                (1, 1, '[100]')       # Complete
            ]
            self.group_colors = ['red', 'green', 'blue']
            self.group_suffix = 'three_groups'
        else:
            # [0,100) = Incomplete (red), [100] = Complete (blue)
            self.imputation_ratio_groups = [
                (0, 1, '[0,100)'),    # Incomplete
                (1, 1, '[100]')       # Complete
            ]
            self.group_colors = ['red', 'blue']
            self.group_suffix = 'two_groups'
        
        # Define binning designations for percent features (lower is better)
        self.percent_feature_bins = [
            ('[0]', (0, 0)),
            ('(0,10)', (0, 0.1)),
            ('[10-20)', (0.1, 0.2)),
            ('[20-30)', (0.2, 0.3)),
            ('[30-40)', (0.3, 0.4)),
            ('[40-50)', (0.4, 0.5)),
            ('[50-100)', (0.5, 1.0)),
            ('[100]', (1.0, 1.0))
        ]

        # Define binning designations for duration features (in hours)
        self.duration_feature_bins = [
            ('[0]', (0, 0)),
            ('(0,1)', (0, 1)),
            ('[1-2)', (1, 2)),
            ('[2-3)', (2, 3)),
            ('[3-4)', (3, 4)),
            ('[4-5)', (4, 5)),
            ('[5+]', (5, float('inf')))
        ]

    def _is_duration_feature(self, feature_name):
        """
        Determine if a feature is a duration feature based on its name.
        
        Args:
            feature_name (str): Name of the feature
            
        Returns:
            bool: True if the feature is a duration feature, False otherwise
        """
        return 'duration' in feature_name.lower()

    def _get_feature_bins(self, feature_name):
        """
        Get the appropriate binning scheme for a feature based on its type.
        
        Args:
            feature_name (str): Name of the feature
            
        Returns:
            list: List of tuples containing bin labels and ranges
        """
        if self._is_duration_feature(feature_name):
            return self.duration_feature_bins
        return self.percent_feature_bins

    def create_quality_correlation_plots(self, curve_features, output_dir=None):
        """
        Create correlation scatterplots between quality features and TAC features.
        Creates separate plots for each quality feature, with all TAC features shown in each plot.
        Uses matplotlib for plotting.
        Plots are saved in the output_dir if provided, otherwise in the current directory.
        
        Args:
            curve_features (pd.DataFrame): DataFrame containing curve features
            output_dir (str, optional): Directory to save plots. If None, saves in current directory.
        """
        # Compute total features before creating plots if needed
        # if self.curve_features is None or not all(f in self.curve_features.columns for f in self.quality_features):
        #     self.compute_total_features(curve_features)
        
        # Create a separate plot for each quality feature
        for quality_feat in self.quality_features:
            fig, axes = plt.subplots(2, 2, figsize=(20, 16))
            fig.suptitle(f'Quality Feature: {quality_feat}', fontsize=16, y=0.95)
            axes = axes.flatten()
            for i, tac_feat in enumerate(self.tac_features):
                ax = axes[i]
                # Filter out rows where quality feature is 0
                x = self.curve_features[quality_feat]
                y = self.curve_features[tac_feat]
                # Fit a quadratic polynomial
                coeffs = np.polyfit(x, y, 3)
                x_fit = np.linspace(x.min(), x.max(), 100)
                y_fit = np.polyval(coeffs, x_fit)
                ax.scatter(x, y, alpha=0.5, color='blue')
                ax.plot(x_fit, y_fit, color='red', linewidth=2)
                ax.text(
                    0.05, 0.95,
                    f'Quadratic Fit',
                    transform=ax.transAxes,
                    bbox=dict(facecolor='white', alpha=0.8)
                )
                ax.set_xlabel(quality_feat)
                ax.set_ylabel(tac_feat)
                # Use log scale for y-axis for specific metrics
                if tac_feat in ['auc_total_CURVE', 'rise_rate_CURVE', 'fall_rate_CURVE']:
                    ax.set_yscale('log')
                ax.tick_params(axis='x', rotation=45)
                ax.grid(True, linestyle='--', alpha=0.7)
            plt.tight_layout()
            plt.savefig(f'{output_dir}/quality_tac_correlations_{quality_feat}.png', dpi=300, bbox_inches='tight')
            plt.close()

    def create_quality_mean_plots(self, curve_features, output_dir=None):
        """
        Create plots showing mean ± standard error for TAC features across quality feature bins.
        Uses the same arrangement of quality and TAC features as in create_quality_boxplots.
        Plots are saved in the output_dir if provided, otherwise in the current directory.
        
        Imputation ratio groups are shown on the same plot with different colors.
        TAC feature plots are stacked vertically for better comparison.
        A histogram at the top shows the distribution of samples across bins.
        Perfect curves (no low quality regions) are shown in black.
        
        Args:
            curve_features (pd.DataFrame): DataFrame containing curve features
            output_dir (str, optional): Directory to save plots. If None, saves in current directory.
        """
        # Store the input DataFrame
        self.curve_features = curve_features.copy()
        
        # Create a separate plot for each quality feature
        for quality_feat in self.quality_features:
            # Get appropriate bins for this feature
            feature_bins = self._get_feature_bins(quality_feat)
            
            # Calculate number of rows needed for TAC features plus histogram
            n_rows = len(self.tac_features) + 1  # +1 for histogram
            
            # Create a figure with subplots for histogram and each TAC feature
            fig, axes = plt.subplots(n_rows, 1, figsize=(12, 5*n_rows))
            fig.suptitle(f'Quality Feature: {quality_feat}', fontsize=16, y=0.98)
            
            # Get histogram data first
            hist_ax = axes[0]
            all_counts = []
            all_labels = []
            
            # Process each imputation ratio group for histogram
            for group_idx, ((min_ratio, max_ratio, group_name), color) in enumerate(zip(self.imputation_ratio_groups, self.group_colors)):
                # Get the appropriate imputation ratio column based on the quality feature
                if 'low_quality' in quality_feat:
                    ratio_col = 'low_quality_imputation_ratio_REGION'
                elif 'jump' in quality_feat:
                    ratio_col = 'jump_imputation_ratio_REGION'
                elif 'plummet' in quality_feat:
                    ratio_col = 'plummet_imputation_ratio_REGION'
                elif 'extreme_negative' in quality_feat:
                    ratio_col = 'extreme_negative_imputation_ratio_REGION'
                elif 'gap' in quality_feat:
                    ratio_col = 'gap_imputation_ratio_REGION'
                elif 'non_wear' in quality_feat:
                    ratio_col = 'non_wear_imputation_ratio_REGION'
                else:
                    ratio_col = 'low_quality_imputation_ratio_REGION'  # default fallback

                if min_ratio == max_ratio:
                    group_mask = (self.curve_features[ratio_col] == min_ratio)
                else:
                    if min_ratio == 0 and max_ratio == 1:
                        if self.group_suffix == 'two_groups':
                            group_mask = (
                                (self.curve_features[ratio_col] >= min_ratio) & 
                                (self.curve_features[ratio_col] < max_ratio)
                            )
                        else:
                            group_mask = (
                                (self.curve_features[ratio_col] > min_ratio) & 
                                (self.curve_features[ratio_col] < max_ratio)
                            )
                    else:
                        group_mask = (
                            (self.curve_features[ratio_col] > min_ratio) & 
                            (self.curve_features[ratio_col] < max_ratio)
                        )
                group_data = self.curve_features[group_mask]
                
                for label, (min_val, max_val) in feature_bins:
                    if min_val == max_val:
                        mask = group_data[quality_feat] == min_val
                    elif label == '(0,1)' or label == '(0,10)':
                        mask = (group_data[quality_feat] > min_val) & (group_data[quality_feat] < max_val)
                    elif label == '[5+]':
                        mask = group_data[quality_feat] >= min_val
                    else:
                        mask = (group_data[quality_feat] >= min_val) & (group_data[quality_feat] < max_val)
                    all_counts.append(len(group_data[mask]))
                    all_labels.append(f"{label}\n({group_name})")
            
            # Create histogram
            bins = feature_bins
            n_bins = len(bins)
            x_pos = np.arange(n_bins + 1)  # +1 for 'Perfect'
            bar_width = 0.2
            bars = []

            # Plot the 'Perfect' and '[0]' bins as 'NA' (black/gray) in both histogram and mean subplots
            na_bins = ['Perfect', '[0]']
            na_color = 'black'

            # Histogram: plot 'Perfect' and '[0]' as NA
            # Plot 'Perfect' at x=0
            perfect_mask = self.curve_features['perfect'] == 1
            perfect_data = self.curve_features[perfect_mask]
            perfect_count = len(perfect_data)
            hist_ax.bar(0, perfect_count, width=bar_width, alpha=0.3, color=na_color, label='NA')
            if perfect_count > 0:
                hist_ax.text(0, perfect_count, f'{perfect_count}', ha='center', va='bottom', color=na_color)
            # Plot [0] at x=1
            zero_mask = (self.curve_features['perfect'] != 1) & (self.curve_features[quality_feat] == 0)
            zero_count = np.sum(zero_mask)
            hist_ax.bar(1, zero_count, width=bar_width, alpha=0.3, color=na_color)
            if zero_count > 0:
                hist_ax.text(1, zero_count, f'{zero_count}', ha='center', va='bottom', color=na_color)

            # For each bin (excluding 'Perfect' and '[0]'), plot one bar per imputation ratio group
            for bin_idx, (label, (min_val, max_val)) in enumerate(bins):
                if label in na_bins:
                    continue
                for group_idx, ((min_ratio, max_ratio, group_name), color) in enumerate(zip(self.imputation_ratio_groups, self.group_colors)):
                    # Mask for this group
                    if 'low_quality' in quality_feat:
                        ratio_col = 'low_quality_imputation_ratio_REGION'
                    elif 'jump' in quality_feat:
                        ratio_col = 'jump_imputation_ratio_REGION'
                    elif 'plummet' in quality_feat:
                        ratio_col = 'plummet_imputation_ratio_REGION'
                    elif 'extreme_negative' in quality_feat:
                        ratio_col = 'extreme_negative_imputation_ratio_REGION'
                    elif 'gap' in quality_feat:
                        ratio_col = 'gap_imputation_ratio_REGION'
                    elif 'non_wear' in quality_feat:
                        ratio_col = 'non_wear_imputation_ratio_REGION'
                    else:
                        ratio_col = 'low_quality_imputation_ratio_REGION'

                    if min_ratio == max_ratio:
                        group_mask = (self.curve_features[ratio_col] == min_ratio)
                    else:
                        if min_ratio == 0 and max_ratio == 1:
                            if self.group_suffix == 'two_groups':
                                group_mask = (
                                    (self.curve_features[ratio_col] >= min_ratio) &
                                    (self.curve_features[ratio_col] < max_ratio)
                                )
                            else:
                                group_mask = (
                                    (self.curve_features[ratio_col] > min_ratio) &
                                    (self.curve_features[ratio_col] < max_ratio)
                                )
                        else:
                            group_mask = (
                                (self.curve_features[ratio_col] > min_ratio) &
                                (self.curve_features[ratio_col] < max_ratio)
                            )
                    # Mask for this bin (excluding perfect)
                    bin_mask = (self.curve_features['perfect'] != 1)
                    x = self.curve_features[quality_feat]
                    if label.startswith('[') and label.endswith(')'):
                        if min_val == max_val:
                            bin_mask &= (x == min_val)
                        elif label == '(0,1)' or label == '(0,10)':
                            bin_mask &= (x > min_val) & (x < max_val)
                        elif label == '[5+]':
                            bin_mask &= (x >= min_val)
                        else:
                            bin_mask &= (x >= min_val) & (x < max_val)
                    elif label.startswith('('):
                        bin_mask &= (x > min_val) & (x < max_val)
                    else:
                        if min_val == max_val:
                            bin_mask &= (x == min_val)
                        else:
                            bin_mask &= (x >= min_val) & (x < max_val)
                    count = len(self.curve_features[group_mask & bin_mask])
                    x_offset = (group_idx - (len(self.imputation_ratio_groups) - 1) / 2) * bar_width
                    hist_ax.bar(bin_idx + 1 + x_offset, count, width=bar_width, alpha=0.3, color=color)
                    if count > 0:
                        hist_ax.text(bin_idx + 1 + x_offset, count, f'{count}', ha='center', va='bottom', color=color)

            # Set x-axis labels to match subplots
            bin_labels = na_bins + [label for label, _ in bins if label not in na_bins]
            hist_ax.set_title('Sample Distribution Across Quality Bins')
            hist_ax.set_xticks(np.arange(len(bin_labels)))
            hist_ax.set_xticklabels(bin_labels, rotation=45)
            hist_ax.set_ylabel('Sample Count')
            hist_ax.grid(True, linestyle='--', alpha=0.7)
            
            # For histogram legend
            group_label_map = {
                '[0]': 'None',
                '(0,100)': 'Partial',
                '[100]': 'Complete',
                '[0,100)': 'Incomplete'
            }
            legend_labels = [(na_color, 'NA')]
            for (min_ratio, max_ratio, group_name), color in zip(self.imputation_ratio_groups, self.group_colors):
                if group_name in ('[0]',):  # [0] is handled as NA
                    continue
                label = group_label_map.get(group_name, group_name)
                legend_labels.append((color, label))
            handles = [Line2D([0], [0], marker='o', color='w', markerfacecolor=color, markersize=8, label=label) for color, label in legend_labels]
            hist_ax.legend(handles=handles, title='Imputation Status')
            
            # Process each TAC feature
            for i, tac_feat in enumerate(self.tac_features):
                ax = axes[i + 1]  # +1 because first axis is histogram
                
                # Plot the 'Perfect' and '[0]' bins as 'NA' (black/gray) in both histogram and mean subplots
                na_bins = ['Perfect', '[0]']
                na_color = 'black'

                # Histogram: plot 'Perfect' and '[0]' as NA
                # Plot 'Perfect' at x=0
                perfect_mask = self.curve_features['perfect'] == 1
                perfect_data = self.curve_features[perfect_mask]
                if not perfect_data.empty:
                    mean = perfect_data[tac_feat].mean()
                    std_err = perfect_data[tac_feat].std() / np.sqrt(len(perfect_data))
                    ax.errorbar(0, mean, yerr=std_err, fmt='o', color=na_color, label='NA')
                # Plot [0] at x=1
                zero_mask = (self.curve_features['perfect'] != 1) & (self.curve_features[quality_feat] == 0)
                zero_data = self.curve_features[zero_mask]
                if not zero_data.empty:
                    mean = zero_data[tac_feat].mean()
                    std_err = zero_data[tac_feat].std() / np.sqrt(len(zero_data))
                    ax.errorbar(1, mean, yerr=std_err, fmt='o', color=na_color)
                
                # Loop over bins for the rest of the x-axis (start at x=2)
                for group_idx, ((min_ratio, max_ratio, group_name), color) in enumerate(zip(self.imputation_ratio_groups, self.group_colors)):
                    means = []
                    std_errs = []
                    for bin_idx, (label, (min_val, max_val)) in enumerate(bins):
                        if label in na_bins:
                            continue
                        # Mask for this group and bin (excluding perfect)
                        if 'low_quality' in quality_feat:
                            ratio_col = 'low_quality_imputation_ratio_REGION'
                        elif 'jump' in quality_feat:
                            ratio_col = 'jump_imputation_ratio_REGION'
                        elif 'plummet' in quality_feat:
                            ratio_col = 'plummet_imputation_ratio_REGION'
                        elif 'extreme_negative' in quality_feat:
                            ratio_col = 'extreme_negative_imputation_ratio_REGION'
                        elif 'gap' in quality_feat:
                            ratio_col = 'gap_imputation_ratio_REGION'
                        elif 'non_wear' in quality_feat:
                            ratio_col = 'non_wear_imputation_ratio_REGION'
                        else:
                            ratio_col = 'low_quality_imputation_ratio_REGION'
                        if min_ratio == max_ratio:
                            group_mask = (self.curve_features[ratio_col] == min_ratio)
                        else:
                            if min_ratio == 0 and max_ratio == 1:
                                if self.group_suffix == 'two_groups':
                                    group_mask = (
                                        (self.curve_features[ratio_col] >= min_ratio) &
                                        (self.curve_features[ratio_col] < max_ratio)
                                    )
                                else:
                                    group_mask = (
                                        (self.curve_features[ratio_col] > min_ratio) &
                                        (self.curve_features[ratio_col] < max_ratio)
                                    )
                            else:
                                group_mask = (
                                    (self.curve_features[ratio_col] > min_ratio) &
                                    (self.curve_features[ratio_col] < max_ratio)
                                )
                        group_mask = group_mask & (self.curve_features['perfect'] != 1)
                        x = self.curve_features[quality_feat]
                        y = self.curve_features[tac_feat]
                        if label.startswith('[') and label.endswith(')'):
                            if min_val == max_val:
                                mask = (x == min_val)
                            elif label == '(0,1)' or label == '(0,10)':
                                mask = (x > min_val) & (x < max_val)
                            elif label == '[5+]':
                                mask = (x >= min_val)
                            else:
                                mask = (x >= min_val) & (x < max_val)
                        elif label.startswith('('):
                            mask = (x > min_val) & (x < max_val)
                        else:
                            if min_val == max_val:
                                mask = (x == min_val)
                            else:
                                mask = (x >= min_val) & (x < max_val)
                        final_mask = group_mask & mask
                        data = y[final_mask]
                        if len(data) < 5:
                            data = pd.Series([])  # Empty series will result in NaN for mean and std
                        means.append(data.mean())
                        std_errs.append(data.std() / np.sqrt(len(data)))
                    # Plot at x=2,3,...
                    x_bin_pos = np.arange(2, len(bins) + 1)
                    x_offset = (group_idx - (len(self.imputation_ratio_groups) - 1) / 2) * 0.2
                    ax.errorbar(x_bin_pos + x_offset, means, yerr=std_errs, fmt='o', capsize=5, capthick=1, elinewidth=1, color=color, label=group_name)
                # Set x-ticks and labels
                ax.set_xticks(np.arange(len(bins) + 1))
                ax.set_xticklabels(na_bins + [label for label, _ in bins if label not in na_bins], rotation=45)
                ax.set_ylabel(tac_feat)
                ax.set_xlabel(quality_feat)
                ax.grid(True, linestyle='--', alpha=0.7)
            
                # For subplot legends
                legend_labels = [(na_color, 'NA')]
                for (min_ratio, max_ratio, group_name), color in zip(self.imputation_ratio_groups, self.group_colors):
                    if group_name in ('[0]',):
                        continue
                    label = group_label_map.get(group_name, group_name)
                    legend_labels.append((color, label))
                handles = [Line2D([0], [0], marker='o', color='w', markerfacecolor=color, markersize=8, label=label) for color, label in legend_labels]
                ax.legend(handles=handles, title='Imputation Status')
            
            plt.tight_layout(rect=[0, 0, 1, 0.95])  # Restore original spacing
            plt.savefig(f'{output_dir}/quality_tac_means_{quality_feat}_{self.group_suffix}.png', dpi=300, bbox_inches='tight')
            plt.close() 