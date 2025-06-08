import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

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
            'low_quality_percent_REGION',
            # 'total_gap_percent_REGION',
            # 'total_non_wear_percent_REGION',
            # 'total_jump_percent_REGION',
            # 'total_plummet_percent_REGION',
            # 'total_extreme_negative_percent_REGION'
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
            self.imputation_ratio_groups = [
                (0, 0, '[0]'),  # Exactly 0
                (0, 1, '(0,100)'),  # Between 0 and 1
                (1, 1, '[100]')  # Exactly 1
            ]
            self.group_colors = ['blue', 'green', 'red']
            self.group_suffix = 'three_groups'
        else:
            self.imputation_ratio_groups = [
                (0, 1, '[0,100)'),  # Between 0 and 1 (inclusive of 0, exclusive of 1)
                (1, 1, '[100]')  # Exactly 1
            ]
            self.group_colors = ['blue', 'red']
            self.group_suffix = 'two_groups'
        
        # Define binning designations for device_worn_percent (higher is better)
        self.device_worn_bins = [
            ('[0,50)', (0, 0.5)),
            ('[50,60)', (0.5, 0.6)),
            ('[60,70)', (0.6, 0.7)),
            ('[70,80)', (0.7, 0.8)),
            ('[80,90)', (0.8, 0.9)),
            ('[90,100)', (0.9, 1.0)),
            ('[100]', (1.0, 1.0))
        ]
        
        # Define binning designations for other features (lower is better)
        self.other_feature_bins = [
            ('[0]', (0, 0)),
            ('(0,10)', (0, 0.1)),
            ('[10-20)', (0.1, 0.2)),
            ('[20-30)', (0.2, 0.3)),
            ('[30-40)', (0.3, 0.4)),
            ('[40-50)', (0.4, 0.5)),
            ('[50-100)', (0.5, 1.0)),
            ('[100]', (1.0, 1.0))
        ]

    def compute_total_features(self, curve_features):
        """
        Compute total features by summing imputed and unimputed values if they don't already exist.
        
        Args:
            curve_features (pd.DataFrame): DataFrame containing curve features
            
        Returns:
            pd.DataFrame: DataFrame with added total features
        """
        # Store the input DataFrame
        self.curve_features = curve_features.copy()
        
        # Compute total features for each quality metric
        quality_metrics = [
            'low_quality',
            # 'jump',
            # 'plummet',
            # 'extreme_negative',
            # 'gap',
            # 'non_wear'
        ]
        
        for metric in quality_metrics:
            # Duration totals
            duration_col = f'total_{metric}_duration_REGION'
            if duration_col not in self.curve_features.columns:
                imputed_duration = self.curve_features[f'imputed_{metric}_duration_REGION']
                unimputed_duration = self.curve_features[f'unimputed_{metric}_duration_REGION']
                self.curve_features[duration_col] = imputed_duration + unimputed_duration
            
            # Percent totals
            percent_col = f'total_{metric}_percent_REGION'
            if percent_col not in self.curve_features.columns:
                imputed_percent = self.curve_features[f'imputed_{metric}_percent_REGION']
                unimputed_percent = self.curve_features[f'unimputed_{metric}_percent_REGION']
                self.curve_features[percent_col] = imputed_percent + unimputed_percent
        
        return self.curve_features

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
        if self.curve_features is None or not all(f in self.curve_features.columns for f in self.quality_features):
            self.compute_total_features(curve_features)
        
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

    def create_quality_boxplots(self, curve_features, output_dir=None):
        """
        Create box and whisker plots for every 5% increase in quality features.
        Uses the same arrangement of quality and TAC features as in create_quality_correlation_plots.
        Plots are saved in the output_dir if provided, otherwise in the current directory.
        
        The plots are split vertically by imputation ratio to show how imputation affects the quality metrics.
        Groups are split into [0], (0,100), [100] for imputation ratios.
        
        Args:
            curve_features (pd.DataFrame): DataFrame containing curve features
            output_dir (str, optional): Directory to save plots. If None, saves in current directory.
        """
        # Create a separate plot for each quality feature
        for quality_feat in self.quality_features:
            # Create a figure with subplots for each imputation ratio group
            fig, axes = plt.subplots(len(self.imputation_ratio_groups), 2, figsize=(20, 16))
            fig.suptitle(f'Quality Feature: {quality_feat}', fontsize=16, y=0.98)
            
            # Process each imputation ratio group
            for group_idx, (min_ratio, max_ratio, group_name) in enumerate(self.imputation_ratio_groups):
                # Filter data for this imputation ratio group
                if min_ratio == max_ratio:
                    # For exact matches ([0] and [100])
                    group_mask = (self.curve_features['low_quality_imputation_ratio_REGION'] == min_ratio)
                else:
                    # For range (0,100)
                    group_mask = (
                        (self.curve_features['low_quality_imputation_ratio_REGION'] > min_ratio) & 
                        (self.curve_features['low_quality_imputation_ratio_REGION'] < max_ratio)
                    )
                group_data = self.curve_features[group_mask]
                
                # Get perfect curves data for this group
                perfect_mask = group_data['perfect'] == 1
                perfect_y = group_data[self.tac_features][perfect_mask]
                
                # Get non-perfect curves data for this group
                non_perfect_mask = ~perfect_mask
                non_perfect_x = group_data[quality_feat][non_perfect_mask]
                non_perfect_y = group_data[self.tac_features][non_perfect_mask]
                
                # Create boxplots for each TAC feature
                for i, tac_feat in enumerate(self.tac_features):
                    ax = axes[group_idx, i]
                    
                    if 'device_worn_percent' in quality_feat:
                        # For device_worn_percent, higher is better
                        boxplot_data = []
                        boxplot_labels = []
                        
                        # Add data for each bin
                        for label, (min_val, max_val) in self.device_worn_bins:
                            if min_val == max_val:
                                mask = non_perfect_x == min_val
                            else:
                                mask = (non_perfect_x >= min_val) & (non_perfect_x < max_val)
                            boxplot_data.append(non_perfect_y[tac_feat][mask])
                            boxplot_labels.append(label)
                        
                        # Add perfect curves at the end
                        boxplot_data.append(perfect_y[tac_feat])
                        boxplot_labels.append('Perfect')
                        
                    else:
                        # For other features, lower is better
                        boxplot_data = []
                        boxplot_labels = []
                        
                        # Add perfect curves first
                        boxplot_data.append(perfect_y[tac_feat])
                        boxplot_labels.append('Perfect')
                        
                        # Add data for each bin
                        for label, (min_val, max_val) in self.other_feature_bins:
                            if min_val == max_val:
                                mask = non_perfect_x == min_val
                            else:
                                mask = (non_perfect_x >= min_val) & (non_perfect_x < max_val)
                            boxplot_data.append(non_perfect_y[tac_feat][mask])
                            boxplot_labels.append(label)
                    
                    # Create boxplot
                    ax.boxplot(boxplot_data, labels=boxplot_labels)
                    
                    # Add count text above each boxplot
                    for j, data in enumerate(boxplot_data):
                        if len(data) > 0:  # Only add text if there's data in the bin
                            ax.text(j + 1, ax.get_ylim()[1], f'n={len(data)}', 
                                   horizontalalignment='center', verticalalignment='bottom',
                                   bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))
                    
                    # Add group name as ylabel for first column
                    if i == 0:
                        ax.set_ylabel(f'{group_name}\n{quality_feat}')
                    else:
                        ax.set_ylabel(quality_feat)
                        
                    ax.set_xlabel(tac_feat)
                    
                    # Use log scale for y-axis for specific metrics
                    if tac_feat in ['auc_total_CURVE', 'rise_rate_CURVE', 'fall_rate_CURVE']:
                        ax.set_yscale('log')
                        
                    ax.tick_params(axis='x', rotation=45)
                    ax.grid(True, linestyle='--', alpha=0.7)
            
            plt.tight_layout(rect=[0, 0, 1, 0.95])  # Adjust layout to leave space for title
            plt.savefig(f'{output_dir}/quality_tac_boxplots_{quality_feat}.png', dpi=300, bbox_inches='tight')
            plt.close()

    def create_quality_mean_plots(self, curve_features, output_dir=None):
        """
        Create plots showing mean ± standard error for TAC features across quality feature bins.
        Uses the same arrangement of quality and TAC features as in create_quality_boxplots.
        Plots are saved in the output_dir if provided, otherwise in the current directory.
        
        Imputation ratio groups are shown on the same plot with different colors.
        TAC feature plots are stacked vertically for better comparison.
        A mini histogram at the bottom shows the distribution of samples across bins.
        Perfect curves (no low quality regions) are shown in black.
        
        Args:
            curve_features (pd.DataFrame): DataFrame containing curve features
            output_dir (str, optional): Directory to save plots. If None, saves in current directory.
        """
        # Store the input DataFrame
        self.curve_features = curve_features.copy()
        
        # Create a separate plot for each quality feature
        for quality_feat in self.quality_features:
            # Calculate number of rows needed for TAC features
            n_rows = len(self.tac_features)
            
            # Create a figure with subplots for each TAC feature, stacked vertically
            fig, axes = plt.subplots(n_rows, 1, figsize=(12, 5*n_rows))
            fig.suptitle(f'Quality Feature: {quality_feat}', fontsize=16, y=0.98)
            
            # Process each TAC feature
            for i, tac_feat in enumerate(self.tac_features):
                ax = axes[i]
                
                # Create a twin axis for the histogram
                ax_hist = ax.twinx()
                ax_hist.set_ylabel('Sample Count', color='gray')
                ax_hist.tick_params(axis='y', labelcolor='gray')
                
                # Process each imputation ratio group
                for group_idx, ((min_ratio, max_ratio, group_name), color) in enumerate(zip(self.imputation_ratio_groups, self.group_colors)):
                    # Filter data for this imputation ratio group
                    if min_ratio == max_ratio:
                        # For exact matches ([0] or [100])
                        group_mask = (self.curve_features['low_quality_imputation_ratio_REGION'] == min_ratio)
                    else:
                        # For ranges (0,100) or [0,100)
                        if min_ratio == 0 and max_ratio == 1:
                            if self.group_suffix == 'two_groups':
                                # For [0,100) in two-group mode
                                group_mask = (
                                    (self.curve_features['low_quality_imputation_ratio_REGION'] >= min_ratio) & 
                                    (self.curve_features['low_quality_imputation_ratio_REGION'] < max_ratio)
                                )
                            else:
                                # For (0,100) in three-group mode
                                group_mask = (
                                    (self.curve_features['low_quality_imputation_ratio_REGION'] > min_ratio) & 
                                    (self.curve_features['low_quality_imputation_ratio_REGION'] < max_ratio)
                                )
                        else:
                            # For (0,100) in three-group mode
                            group_mask = (
                                (self.curve_features['low_quality_imputation_ratio_REGION'] > min_ratio) & 
                                (self.curve_features['low_quality_imputation_ratio_REGION'] < max_ratio)
                            )
                    group_data = self.curve_features[group_mask]
                    
                    # Get perfect curves data for this group
                    perfect_mask = group_data['perfect'] == 1
                    perfect_y = group_data[self.tac_features][perfect_mask]
                    
                    # Get non-perfect curves data for this group
                    non_perfect_mask = ~perfect_mask
                    non_perfect_x = group_data[quality_feat][non_perfect_mask]
                    non_perfect_y = group_data[self.tac_features][non_perfect_mask]
                    
                    if 'device_worn_percent' in quality_feat:
                        # For device_worn_percent, higher is better
                        means = []
                        std_errs = []
                        counts = []
                        boxplot_labels = []
                        
                        # Add data for each bin
                        for label, (min_val, max_val) in self.device_worn_bins:
                            if min_val == max_val:
                                mask = non_perfect_x == min_val
                            else:
                                mask = (non_perfect_x >= min_val) & (non_perfect_x < max_val)
                            data = non_perfect_y[tac_feat][mask]
                            means.append(data.mean())
                            std_errs.append(data.std() / np.sqrt(len(data)))
                            counts.append(len(data))
                            boxplot_labels.append(label)
                        
                        # Add perfect curves at the end
                        means.append(perfect_y[tac_feat].mean())
                        std_errs.append(perfect_y[tac_feat].std() / np.sqrt(len(perfect_y)))
                        counts.append(len(perfect_y))
                        boxplot_labels.append('Perfect')
                        
                    else:
                        # For other features, lower is better
                        means = []
                        std_errs = []
                        counts = []
                        boxplot_labels = []
                        
                        # Add perfect curves first
                        means.append(perfect_y[tac_feat].mean())
                        std_errs.append(perfect_y[tac_feat].std() / np.sqrt(len(perfect_y)))
                        counts.append(len(perfect_y))
                        boxplot_labels.append('Perfect')
                        
                        # Add data for each bin
                        for label, (min_val, max_val) in self.other_feature_bins:
                            if min_val == max_val:
                                mask = non_perfect_x == min_val
                            else:
                                mask = (non_perfect_x >= min_val) & (non_perfect_x < max_val)
                            data = non_perfect_y[tac_feat][mask]
                            means.append(data.mean())
                            std_errs.append(data.std() / np.sqrt(len(data)))
                            counts.append(len(data))
                            boxplot_labels.append(label)
                    
                    # Create mean ± standard error plot
                    x_pos = np.arange(len(means))
                    # Offset x positions for each group to avoid overlap
                    x_offset = (group_idx - (len(self.imputation_ratio_groups) - 1) / 2) * 0.2
                    ax.errorbar(x_pos + x_offset, means, yerr=std_errs, fmt='o', capsize=5, capthick=1, 
                              elinewidth=1, color=color, label=group_name)
                    
                    # Create histogram bars
                    bar_width = 0.2
                    bars = ax_hist.bar(x_pos + x_offset, counts, width=bar_width, alpha=0.3, color=color)
                    
                    # Add N values above each bar
                    for bar, count in zip(bars, counts):
                        if count > 0:  # Only add text if there's data in the bin
                            height = bar.get_height()
                            ax_hist.text(bar.get_x() + bar.get_width()/2., height,
                                       f'{count}',
                                       ha='center', va='bottom',
                                       color=color)
                
                # Add perfect curves histogram (black bars)
                perfect_mask = self.curve_features['perfect'] == 1
                perfect_data = self.curve_features[perfect_mask]
                
                if 'device_worn_percent' in quality_feat:
                    # For device_worn_percent, higher is better
                    perfect_counts = []
                    for label, (min_val, max_val) in self.device_worn_bins:
                        if min_val == max_val:
                            mask = perfect_data[quality_feat] == min_val
                        else:
                            mask = (perfect_data[quality_feat] >= min_val) & (perfect_data[quality_feat] < max_val)
                        perfect_counts.append(len(perfect_data[mask]))
                else:
                    # For other features, lower is better
                    perfect_counts = []
                    for label, (min_val, max_val) in self.other_feature_bins:
                        if min_val == max_val:
                            mask = perfect_data[quality_feat] == min_val
                        else:
                            mask = (perfect_data[quality_feat] >= min_val) & (perfect_data[quality_feat] < max_val)
                        perfect_counts.append(len(perfect_data[mask]))
                
                # Add perfect curves bar
                perfect_bar = ax_hist.bar(x_pos[-1], perfect_counts[-1], width=bar_width, alpha=0.3, color='black')
                if perfect_counts[-1] > 0:
                    ax_hist.text(x_pos[-1], perfect_counts[-1],
                               f'{perfect_counts[-1]}',
                               ha='center', va='bottom',
                               color='black')
                
                ax.set_xlabel(quality_feat)
                ax.set_ylabel(tac_feat)
                ax.set_xticks(x_pos)
                ax.set_xticklabels(boxplot_labels, rotation=45)
                
                # Use log scale for y-axis for specific metrics
                if tac_feat in ['auc_total_CURVE', 'rise_rate_CURVE', 'fall_rate_CURVE']:
                    ax.set_yscale('log')
                    
                ax.grid(True, linestyle='--', alpha=0.7)
                ax.legend()
                
                # Adjust histogram y-axis to be proportional to the main plot
                ax_hist.set_ylim(0, ax_hist.get_ylim()[1] * 1.2)  # Add 20% padding
            
            plt.tight_layout(rect=[0, 0, 1, 0.95])  # Adjust layout to leave space for title
            plt.savefig(f'{output_dir}/quality_tac_means_{quality_feat}_{self.group_suffix}.png', dpi=300, bbox_inches='tight')
            plt.close() 