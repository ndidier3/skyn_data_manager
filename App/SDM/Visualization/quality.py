import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from scipy.stats import gaussian_kde
from matplotlib.patches import Patch

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
        self.raw_curve_features = None
        
        # Dictionary to store curve IDs for each group and bin
        # Structure: {group_name: {bin_label: [(subid, curve_id), ...]}}
        self.group_bin_curve_ids = {}
        
        # Feature labels for nicer display
        self.feature_labels = {
            'auc_total_CURVE': 'Area Under TAC Curve',
            'peak_CURVE': 'Peak Value',
            'rise_rate_CURVE': 'Rise Rate',
            'fall_rate_CURVE': 'Fall Rate'
        }
        
        # Default quality features grouped by feature type, then region type, then metric type
        self.quality_features = quality_features or [
            # Low Quality Features
            # 'total_low_quality_percent_REGION',
            'total_low_quality_percent_CURVE',
            'total_low_quality_percent_PERIPHERY_BEFORE',
            'total_low_quality_percent_PERIPHERY_AFTER',
            # 'total_low_quality_duration_REGION',
            'total_low_quality_duration_CURVE',
            'total_low_quality_duration_PERIPHERY_BEFORE',
            'total_low_quality_duration_PERIPHERY_AFTER',
            
            # Gap Features
            # 'total_gap_percent_REGION',
            'total_gap_percent_CURVE',
            'total_gap_percent_PERIPHERY_BEFORE',
            'total_gap_percent_PERIPHERY_AFTER',
            # 'total_gap_duration_REGION',
            'total_gap_duration_CURVE',
            # 'total_gap_duration_PERIPHERY_BEFORE',
            # 'total_gap_duration_PERIPHERY_AFTER',

            #Non-wear + Gap Features
            # 'total_non_wear_gap_percent_REGION',
            'total_non_wear_gap_percent_CURVE',
            'total_non_wear_gap_percent_PERIPHERY_BEFORE',
            'total_non_wear_gap_percent_PERIPHERY_AFTER',
            # 'total_non_wear_gap_duration_REGION',
            'total_non_wear_gap_duration_CURVE',
            # 'total_non_wear_gap_duration_PERIPHERY_BEFORE',
            # 'total_non_wear_gap_duration_PERIPHERY_AFTER',
            
            # Non-wear Features
            # 'total_non_wear_percent_REGION',
            'total_non_wear_percent_CURVE',
            'total_non_wear_percent_PERIPHERY_BEFORE',
            'total_non_wear_percent_PERIPHERY_AFTER',
            # 'total_non_wear_duration_REGION',
            'total_non_wear_duration_CURVE',
            # 'total_non_wear_duration_PERIPHERY_BEFORE',
            # 'total_non_wear_duration_PERIPHERY_AFTER',
            
            # Jump Features
            # 'total_jump_percent_REGION',
            'total_jump_percent_CURVE',
            # 'total_jump_percent_PERIPHERY_BEFORE',
            # 'total_jump_percent_PERIPHERY_AFTER',
            # 'total_jump_duration_REGION',
            'total_jump_duration_CURVE',
            # 'total_jump_duration_PERIPHERY_BEFORE',
            # 'total_jump_duration_PERIPHERY_AFTER',
            
            # Plummet Features
            # 'total_plummet_percent_REGION',
            'total_plummet_percent_CURVE',
            # 'total_plummet_percent_PERIPHERY_BEFORE',
            # 'total_plummet_percent_PERIPHERY_AFTER',
            # 'total_plummet_duration_REGION',
            'total_plummet_duration_CURVE',
            # 'total_plummet_duration_PERIPHERY_BEFORE',
            # 'total_plummet_duration_PERIPHERY_AFTER',
            
            # Extreme Negative Features
            # 'total_extreme_negative_percent_REGION',
            'total_extreme_negative_percent_CURVE',
            'total_extreme_negative_percent_PERIPHERY_BEFORE',
            'total_extreme_negative_percent_PERIPHERY_AFTER',
            # 'total_extreme_negative_duration_REGION',
            'total_extreme_negative_duration_CURVE',
            'total_extreme_negative_duration_PERIPHERY_BEFORE',
            'total_extreme_negative_duration_PERIPHERY_AFTER',

            #completion features
            'rise_complete_percent_CURVE',
            'fall_complete_percent_CURVE'
        ]
        
        # Default TAC features
        self.tac_features = tac_features or [
            'auc_total_CURVE',
            'peak_CURVE',
            'rise_rate_CURVE',
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

    def _reverse_value(self, value):
        """
        Reverse a value between 0 and 1 (1 -> 0, 0 -> 1)
        
        Args:
            value (float): Value between 0 and 1
            
        Returns:
            float: Reversed value (1 - value)
        """
        return 1 - value

    def create_quality_mean_plots(self, curve_features, raw_curve_features=None, output_dir=None):
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
            raw_curve_features (pd.DataFrame, optional): DataFrame containing raw curve features before imputation
            output_dir (str, optional): Directory to save plots. If None, saves in current directory.
        """
        try:
            # Store the input DataFrame
            self.curve_features = curve_features.copy()
            self.raw_curve_features = raw_curve_features.copy() if raw_curve_features is not None else None
            
            # Check if 'perfect' column exists (may not be in exported Excel files)
            has_perfect_col = 'perfect' in self.curve_features.columns
            if not has_perfect_col:
                print("Note: 'perfect' column not found. Perfect curves will not be shown separately.")
            
            # Create a separate plot for each quality feature
            for quality_feat in self.quality_features:
                # Skip if quality feature doesn't exist in the DataFrame
                if quality_feat not in self.curve_features.columns:
                    print(f"Skipping quality feature '{quality_feat}' (not found in data)")
                    continue
                    
                try:
                    # Extract region type from quality feature name once per feature
                    # Handle PERIPHERY_BEFORE/PERIPHERY_AFTER correctly (need last 2 parts, not just last)
                    parts = quality_feat.split('_')
                    if parts[-1] in ['BEFORE', 'AFTER'] and len(parts) > 1:
                        region_type = '_'.join(parts[-2:])  # Get PERIPHERY_BEFORE or PERIPHERY_AFTER
                    else:
                        region_type = parts[-1]  # Get CURVE, REGION, etc.
                    
                    # Reverse completion values if needed
                    if quality_feat in ['rise_complete_percent_CURVE', 'fall_complete_percent_CURVE']:
                        self.curve_features[quality_feat] = self.curve_features[quality_feat].apply(self._reverse_value)
                    
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
                        
                        if 'low_quality' in quality_feat:
                            ratio_col = f'low_quality_imputation_ratio_{region_type}'
                        elif 'jump_imp_cand' in quality_feat:
                            ratio_col = f'jump_imputation_ratio_{region_type}'
                        elif 'plummet_imp_cand' in quality_feat:
                            ratio_col = f'plummet_imputation_ratio_{region_type}'
                        elif 'extreme_negative' in quality_feat:
                            ratio_col = f'extreme_negative_imputation_ratio_{region_type}'
                        elif 'gap' in quality_feat:
                            ratio_col = f'gap_imputation_ratio_{region_type}'
                        elif 'non_wear' in quality_feat:
                            ratio_col = f'non_wear_imputation_ratio_{region_type}'
                        else:
                            ratio_col = f'low_quality_imputation_ratio_{region_type}'  # default fallback

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
                    # Plot 'Perfect' at x=0 (if 'perfect' column exists)
                    has_perfect_col = 'perfect' in self.curve_features.columns
                    if has_perfect_col:
                        perfect_mask = self.curve_features['perfect'] == 1
                        perfect_data = self.curve_features[perfect_mask]
                        perfect_count = len(perfect_data)
                        hist_ax.bar(0, perfect_count, width=bar_width, alpha=0.3, color=na_color, label='NA')
                        if perfect_count > 0:
                            hist_ax.text(0, perfect_count, f'{perfect_count}', ha='center', va='bottom', color=na_color)
                    else:
                        hist_ax.bar(0, 0, width=bar_width, alpha=0.3, color=na_color, label='NA')
                    # Plot [0] at x=1
                    if has_perfect_col:
                        zero_mask = (self.curve_features['perfect'] != 1) & (self.curve_features[quality_feat] == 0)
                    else:
                        zero_mask = (self.curve_features[quality_feat] == 0)
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
                                ratio_col = f'low_quality_imputation_ratio_{region_type}'
                            elif 'jump_imp_cand' in quality_feat:
                                ratio_col = f'jump_imputation_ratio_{region_type}'
                            elif 'plummet_imp_cand' in quality_feat:
                                ratio_col = f'plummet_imputation_ratio_{region_type}'
                            elif 'extreme_negative' in quality_feat:
                                ratio_col = f'extreme_negative_imputation_ratio_{region_type}'
                            elif 'gap' in quality_feat:
                                ratio_col = f'gap_imputation_ratio_{region_type}'
                            elif 'non_wear' in quality_feat:
                                ratio_col = f'non_wear_imputation_ratio_{region_type}'
                            else:
                                ratio_col = f'low_quality_imputation_ratio_{region_type}'

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
                            # Mask for this bin (excluding perfect if column exists)
                            if has_perfect_col:
                                bin_mask = (self.curve_features['perfect'] != 1)
                            else:
                                bin_mask = pd.Series([True] * len(self.curve_features), index=self.curve_features.index)
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
                        '[100]': 'Imputed',
                        '[0,100)': 'Raw (Cannot Impute)'
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
                        # Plot 'Perfect' at x=0 (if 'perfect' column exists)
                        if has_perfect_col:
                            perfect_mask = self.curve_features['perfect'] == 1
                            perfect_data = self.curve_features[perfect_mask]
                            if not perfect_data.empty:
                                mean = perfect_data[tac_feat].mean()
                                std_err = perfect_data[tac_feat].std() / np.sqrt(len(perfect_data))
                                ax.errorbar(0, mean, yerr=std_err, fmt='o', color=na_color, label='NA')
                        
                        # Plot [0] at x=1
                        if has_perfect_col:
                            zero_mask = (self.curve_features['perfect'] != 1) & (self.curve_features[quality_feat] == 0)
                        else:
                            zero_mask = (self.curve_features[quality_feat] == 0)
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
                                    ratio_col = f'low_quality_imputation_ratio_{region_type}'
                                elif 'jump_imp_cand' in quality_feat:
                                    ratio_col = f'jump_imputation_ratio_{region_type}'
                                elif 'plummet_imp_cand' in quality_feat:
                                    ratio_col = f'plummet_imputation_ratio_{region_type}'
                                elif 'extreme_negative' in quality_feat:
                                    ratio_col = f'extreme_negative_imputation_ratio_{region_type}'
                                elif 'gap' in quality_feat:
                                    ratio_col = f'gap_imputation_ratio_{region_type}'
                                elif 'non_wear' in quality_feat:
                                    ratio_col = f'non_wear_imputation_ratio_{region_type}'
                                else:
                                    ratio_col = f'low_quality_imputation_ratio_{region_type}'
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
                                if has_perfect_col:
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
                            ax.errorbar(
                                x_bin_pos + x_offset, 
                                means, 
                                yerr=std_errs, 
                                fmt='o',
                                markerfacecolor='none' if group_name in ('[0,100)', '[0]') else color,
                                markeredgecolor=color,
                                capsize=5, 
                                capthick=1, 
                                elinewidth=1, 
                                color=color, 
                                label=group_name,
                                markersize=6 if group_name in ('[0,100)', '[0]') else None
                            )
                            
                            # Store curve IDs for this group and bin
                            if group_name not in self.group_bin_curve_ids:
                                self.group_bin_curve_ids[group_name] = {}
                            
                            # Store curve IDs for each bin
                            for bin_idx, (label, (min_val, max_val)) in enumerate(bins):
                                if label in na_bins:
                                    continue
                                # Create mask for this bin
                                if label.startswith('[') and label.endswith(')'):
                                    if min_val == max_val:
                                        bin_mask = (self.curve_features[quality_feat] == min_val)
                                    elif label == '(0,1)' or label == '(0,10)':
                                        bin_mask = (self.curve_features[quality_feat] > min_val) & (self.curve_features[quality_feat] < max_val)
                                    elif label == '[5+]':
                                        bin_mask = (self.curve_features[quality_feat] >= min_val)
                                    else:
                                        bin_mask = (self.curve_features[quality_feat] >= min_val) & (self.curve_features[quality_feat] < max_val)
                                elif label.startswith('('):
                                    bin_mask = (self.curve_features[quality_feat] > min_val) & (self.curve_features[quality_feat] < max_val)
                                else:
                                    if min_val == max_val:
                                        bin_mask = (self.curve_features[quality_feat] == min_val)
                                    else:
                                        bin_mask = (self.curve_features[quality_feat] >= min_val) & (self.curve_features[quality_feat] < max_val)
                                
                                # Store curve IDs for this bin
                                bin_data = self.curve_features[bin_mask & group_mask]
                                self.group_bin_curve_ids[group_name][label] = set(zip(bin_data['subid'], bin_data['curve_id']))
                            
                            # If this is the "Complete" group and we have raw data, plot the raw values
                            if group_name == '[100]' and self.raw_curve_features is not None:
                                raw_means = []
                                raw_std_errs = []
                                
                                # Now process raw data using stored curve IDs
                                for bin_idx, (label, (min_val, max_val)) in enumerate(bins):
                                    if label in na_bins:
                                        continue
                                    
                                    # Get raw data for curves in this bin using stored curve IDs
                                    curve_ids = self.group_bin_curve_ids[group_name][label]
                                    raw_data = self.raw_curve_features[
                                        self.raw_curve_features.apply(
                                            lambda x: (x['subid'], x['curve_id']) in curve_ids,
                                            axis=1
                                        )
                                    ]
                                    
                                    # Calculate statistics based on sample size
                                    if len(raw_data) < 5:
                                        raw_means.append(np.nan)
                                        raw_std_errs.append(np.nan)
                                    else:
                                        raw_means.append(raw_data[tac_feat].mean())
                                        raw_std_errs.append(raw_data[tac_feat].std() / np.sqrt(len(raw_data)))
                                    
                                    print(f"Raw means for bin {label}: {raw_means[-1]}")
                                
                                # Plot raw values with a different marker and color
                                raw_color = tuple(0.7 * c for c in color) if isinstance(color, tuple) else color  # Create lighter version of color
                                ax.errorbar(
                                    x_bin_pos + x_offset + 0.1,  # Add additional offset to separate from imputed data
                                    raw_means, 
                                    yerr=raw_std_errs, 
                                    fmt='o',  # Circle marker
                                    markerfacecolor='none',  # Make circles hollow
                                    markeredgecolor=raw_color,  # Use raw_color for circle edge
                                    capsize=5, 
                                    capthick=1, 
                                    elinewidth=1, 
                                    color=raw_color,  # Use lighter color for lines
                                    label='Raw (Can Impute)', 
                                    alpha=0.7,
                                    markersize=6  # Added smaller marker size
                                )
                        
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
                            # Add Raw (Can Impute) to legend if this is the Complete group
                            if group_name == '[100]' and self.raw_curve_features is not None:
                                raw_color = tuple(0.7 * c for c in color) if isinstance(color, tuple) else color
                                legend_labels.append((raw_color, 'Raw (Can Impute)'))
                        handles = []
                        for color, label in legend_labels:
                            if label == 'Raw (Can Impute)':
                                # Use hollow circle for Raw (Can Impute)
                                handles.append(Line2D([0], [0], marker='o', color='w', 
                                                    markerfacecolor='none', markeredgecolor=color, 
                                                    markersize=8, label=label))
                            else:
                                # Use filled circle for other groups
                                handles.append(Line2D([0], [0], marker='o', color='w', 
                                                    markerfacecolor=color, markersize=8, label=label))
                        ax.legend(handles=handles, title='Imputation Status')
                    
                    plt.tight_layout(rect=[0, 0, 1, 0.95])  # Restore original spacing
                    plt.savefig(f'{output_dir}/quality_tac_means_{quality_feat}_{self.group_suffix}.png', dpi=300, bbox_inches='tight')
                    plt.close(fig)  # Explicitly close the figure
                    plt.close('all')  # Close any other figures that might be open
                    
                except Exception as e:
                    print(f"Error processing quality feature {quality_feat}: {str(e)}")
                    plt.close('all')  # Ensure figures are closed even if there's an error
                    continue
                
        finally:
            # Clean up any remaining figures
            plt.close('all')
            # Clear any remaining memory
            import gc
            gc.collect()

    def get_binned_subgroups(self, df, quality_feat):
        """
        Given a DataFrame and a quality feature, return a list of DataFrames (one per bin, in order),
        using the same binning logic and order as the main mean plot. Always includes all bins,
        including 'Perfect' and '[0]'.
        Returns: (bin_labels, binned_dfs)
        """
        feature_bins = self._get_feature_bins(quality_feat)
        binned_dfs = []
        bin_labels = []
        for label, (min_val, max_val) in feature_bins:
            if self._is_duration_feature(quality_feat):
                if label == '[5+]':
                    mask = (df[quality_feat] >= min_val)
                elif min_val == max_val:
                    mask = (df[quality_feat] == min_val)
                else:
                    mask = (df[quality_feat] >= min_val) & (df[quality_feat] < max_val)
            else:
                if label == '[100]':
                    mask = (df[quality_feat] == 1.0)
                elif min_val == max_val:
                    mask = (df[quality_feat] == min_val)
                elif label == '(0,1)' or label == '(0,10)':
                    mask = (df[quality_feat] > min_val) & (df[quality_feat] < max_val)
                else:
                    mask = (df[quality_feat] >= min_val) & (df[quality_feat] < max_val)
            binned_dfs.append(df[mask])
            bin_labels.append(label)
        return bin_labels, binned_dfs

    def create_tac_boxplots(self, curve_features, output_dir=None, show_legend=False):
        """
        Create box and whisker plots for all TAC features, split by valid vs invalid curves.
        Includes jittered points showing the full distribution alongside box plots.
        Values beyond thresholds are marked with special markers at the threshold level.
        
        Args:
            curve_features (pd.DataFrame): DataFrame containing curve features
            output_dir (str, optional): Directory to save plots. If None, saves in current directory.
            show_legend (bool, optional): Whether to display legends on the plots. Default is False.
        """
        try:
            # Check which TAC features are available in the DataFrame
            available_tac_features = [feat for feat in self.tac_features if feat in curve_features.columns]
            if not available_tac_features:
                print("No TAC features found in the DataFrame. Available columns:", curve_features.columns.tolist())
                return
            
            print(f"Plotting TAC boxplot features: {available_tac_features}")
            
            # Create subplots (2x2 grid)
            fig, axes = plt.subplots(2, 2, figsize=(16, 12))  # Changed to 2x2 grid with appropriate size
            axes = axes.flatten()
            
            # Turn off any unused subplots
            n_features = len(available_tac_features)
            for ax in axes[n_features:]:
                ax.axis('off')
            
            # Define thresholds for outlier clipping
            thresholds = {
                'auc_total_CURVE': 100000,
                'rise_rate_CURVE': 500,
                'fall_rate_CURVE': 500
            }
            
            # Define plot parameters
            box_width = 0.35  # Decreased from 0.7
            jitter_std = 0.15  # Increased from 0.05
            point_size = 15  # Size for regular points
            beyond_threshold_size = 40  # Size for beyond-threshold markers
            
            # Create box plots for each feature
            for ax, tac_feat in zip(axes, available_tac_features):
                # Split data into valid and invalid curves
                valid_data = curve_features[(curve_features['CURVE_VALID'] == 1)][tac_feat].dropna()
                invalid_data = curve_features[(curve_features['CURVE_VALID'] != 1)][tac_feat].dropna()
                
                # Prepare data for plotting
                data = [valid_data, invalid_data]
                labels = ['High Quality', 'Low Quality']
                colors = ['green', 'red']
                
                # Handle special case for AUC (log scale)
                if tac_feat == 'auc_total_CURVE':
                    # Filter out non-positive values for log scale
                    data = [d[d > 0] for d in data]
                    ax.set_yscale('log')
                    threshold = thresholds.get(tac_feat, 100000)
                    ax.set_ylim(bottom=10, top=threshold * 1.1)  # Add 10% space for threshold markers
                    # Set custom y-axis ticks for log scale
                    tick_locations = 10 ** np.arange(1, 6)
                    tick_labels = [f'{int(tick)}' if tick < 100000 else '100000+' for tick in tick_locations]
                    ax.set_yticks(tick_locations)
                    ax.set_yticklabels(tick_labels)
                else:
                    # For other features, clip outliers at threshold
                    threshold = thresholds.get(tac_feat, 2000)
                    data = [np.clip(d, 0, threshold) for d in data]
                    ax.set_ylim(bottom=0, top=threshold * 1.1)  # Add 10% space for threshold markers
                
                # Create box plot without outliers
                bp = ax.boxplot(data,
                              labels=labels,
                              patch_artist=True,  # Fill boxes with color
                              medianprops={'color': 'black', 'linewidth': 1.5},  # Black median lines
                              showfliers=False,  # Don't show outliers (we'll plot all points manually)
                              widths=box_width,  # Narrower box width
                              zorder=2)  # Place boxes above grid but below points
                
                # Color the boxes
                for box, color in zip(bp['boxes'], colors):
                    box.set(facecolor=color, alpha=0.2)  # More transparent boxes
                    box.set(edgecolor=color, linewidth=1.5)
                
                # Plot all points with jitter
                for idx, (d, color) in enumerate(zip(data, colors)):
                    # Get the original data before clipping
                    original_data = valid_data if idx == 0 else invalid_data
                    threshold = thresholds.get(tac_feat, 2000)
                    
                    # Split data into within-threshold and beyond-threshold
                    within_threshold = original_data[original_data <= threshold]
                    beyond_threshold = original_data[original_data > threshold]
                    
                    if len(within_threshold) > 0:
                        # Create jitter for all points
                        jitter = np.random.normal(0, jitter_std, size=len(within_threshold))
                        x_pos = np.full_like(jitter, idx + 1) + jitter
                        
                        # Plot all points
                        ax.scatter(x_pos, within_threshold,
                                 color=color,
                                 alpha=0.5,
                                 s=point_size,
                                 marker='o',
                                 zorder=3)  # Points above boxes
                    
                    # Handle beyond-threshold values
                    if len(beyond_threshold) > 0:
                        # Create jitter for threshold markers
                        jitter = np.random.normal(0, jitter_std, size=len(beyond_threshold))
                        x_pos = np.full_like(jitter, idx + 1) + jitter
                        
                        # Plot triangle markers at threshold level
                        ax.scatter(x_pos, [threshold * 1.05] * len(beyond_threshold),
                                 color=color,
                                 alpha=0.7,
                                 s=beyond_threshold_size,
                                 marker='^',  # Triangle pointing up
                                 label=f'{len(beyond_threshold)} values > {threshold}',
                                 zorder=4)  # Beyond-threshold markers on top
                
                # Set labels and grid
                feature_label = self.feature_labels.get(tac_feat, tac_feat)
                ax.set_title(feature_label, pad=10)  # Added padding between title and plot
                ax.grid(True, linestyle='--', alpha=0.7, zorder=1)  # Grid below everything
                ax.set_facecolor('white')
                
                # Add legend if there are beyond-threshold values
                if show_legend or any(len(d[d > thresholds.get(tac_feat, 2000)]) > 0 for d in [valid_data, invalid_data]):
                    ax.legend(fontsize='small', loc='upper right')
                
                # Rotate x-axis labels for better readability
                ax.tick_params(axis='x', rotation=45)
                
                # Set x-axis limits to accommodate wider jitter
                ax.set_xlim(0.5, len(data) + 0.5)
            
            # Adjust layout with more space between subplots
            plt.tight_layout(rect=[0, 0, 1, 0.98], h_pad=1.0, w_pad=1.0)  # Added w_pad for horizontal spacing
            
            # Save the plot
            if output_dir:
                plt.savefig(f'{output_dir}/tac_boxplot_distributions.png', dpi=300, bbox_inches='tight')
            else:
                plt.savefig('tac_boxplot_distributions.png', dpi=300, bbox_inches='tight')
            
            plt.close(fig)
            del fig
            del axes
            
        except Exception as e:
            import traceback
            print(f"Error processing TAC boxplot features:")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            print("Full traceback:")
            traceback.print_exc()
            plt.close('all')
            
        finally:
            plt.close('all')
            import gc
            gc.collect()
  
    def create_tac_density_plots(self, curve_features, output_filename='tac_density_distributions.png', show_legend=False):
        """
        Create density plots (KDE, area=1) for all TAC features, split by valid vs invalid curves.
        Uses a smooth kernel density estimate (KDE) with shading, overlaid for both groups.
        Only uses scipy.stats.gaussian_kde and matplotlib (no seaborn).
        
        Args:
            curve_features (pd.DataFrame): DataFrame containing curve features
            output_filename (str, optional): Filename for the output plot.
            show_legend (bool, optional): Whether to display legends on the plots. Default is False.
        """
        import matplotlib.pyplot as plt
        import numpy as np
        from scipy.stats import gaussian_kde
        try:
            available_tac_features = [feat for feat in self.tac_features if feat in curve_features.columns]
            if not available_tac_features:
                print("No TAC features found in the DataFrame. Available columns:", curve_features.columns.tolist())
                return
            print(f"Plotting TAC KDE density features: {available_tac_features}")
            fig, axes = plt.subplots(2, 2, figsize=(12, 8))
            axes = axes.flatten()
            n_features = len(available_tac_features)
            for ax in axes[n_features:]:
                ax.axis('off')
            
            # Define thresholds for each feature
            thresholds = {
                'auc_total_CURVE': 15000,
                'peak_CURVE': 800,        # Added specific threshold
                'rise_rate_CURVE': 400,
                'fall_rate_CURVE': 400
            }
            
            for i, (ax, tac_feat) in enumerate(zip(axes, available_tac_features)):
                valid_data = curve_features[(curve_features['CURVE_VALID'] == 1)][tac_feat].dropna()
                invalid_data = curve_features[(curve_features['CURVE_VALID'] != 1)][tac_feat].dropna()
                
                # Get threshold for this feature
                threshold = thresholds.get(tac_feat, 2000)
                
                # Clip data to threshold
                valid_data = valid_data[valid_data > 0]  # Remove non-positive values
                invalid_data = invalid_data[invalid_data > 0]  # Remove non-positive values
                valid_data = np.clip(valid_data, 0, threshold)
                invalid_data = np.clip(invalid_data, 0, threshold)
                
                # Calculate means before KDE
                valid_mean = valid_data.mean() if len(valid_data) > 0 else None
                invalid_mean = invalid_data.mean() if len(invalid_data) > 0 else None
                
                # Create linear space for x values
                x_grid = np.linspace(0, threshold, 200)
                
                # Plot Low Quality (red) first
                if len(invalid_data) > 1:
                    kde = gaussian_kde(invalid_data)
                    y = kde(x_grid)
                    ax.plot(x_grid, y, color='red', label='Low Quality', linewidth=2, zorder=2)
                    ax.fill_between(x_grid, y, color='red', alpha=0.3, zorder=2)
                    # Add vertical line at mean
                    if invalid_mean is not None:
                        ax.axvline(x=invalid_mean, color='red', linestyle='--', linewidth=1.5, 
                                 alpha=0.8, zorder=4)
                
                # Plot High Quality (green) second
                if len(valid_data) > 1:
                    kde = gaussian_kde(valid_data)
                    y = kde(x_grid)
                    ax.plot(x_grid, y, color='green', label='High Quality', linewidth=2, zorder=3)
                    ax.fill_between(x_grid, y, color='green', alpha=0.3, zorder=3)
                    # Add vertical line at mean
                    if valid_mean is not None:
                        ax.axvline(x=valid_mean, color='green', linestyle='--', linewidth=1.5, 
                                 alpha=0.8, zorder=4)
                
                feature_label = self.feature_labels.get(tac_feat, tac_feat)
                ax.set_xlabel(feature_label)
                ax.set_ylabel(None)
                ax.set_yticks([])
                ax.grid(True, linestyle='--', alpha=0.7, zorder=1)
                if show_legend and i == 0:
                    legend_elements = [
                        Line2D([0], [0], color='green', lw=2, label='High Quality'),
                        Line2D([0], [0], color='red', lw=2, label='Low Quality'),
                        Line2D([0], [0], color='black', linestyle='--', linewidth=1.5, label='Mean')
                    ]
                    ax.legend(handles=legend_elements)
                ax.set_facecolor('white')
                
                # Set axis limits
                ax.set_xlim(left=0, right=threshold)
            
            plt.tight_layout(rect=[0, 0, 1, 0.95])
            plt.savefig(output_filename, dpi=300, bbox_inches='tight')
            plt.close(fig)
            del fig
            del axes
        except Exception as e:
            import traceback
            print(f"Error processing TAC density features:")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            print("Full traceback:")
            traceback.print_exc()
            plt.close('all')
        finally:
            plt.close('all')
            import gc
            gc.collect()

    def create_tac_violin_plots(self, curve_features, output_filename='tac_violin_plots.png', show_legend=False):
        """
        Create violin plots for all TAC features, split by valid vs invalid curves.
        
        Args:
            curve_features (pd.DataFrame): DataFrame containing curve features
            output_filename (str, optional): Filename for the output plot.
            show_legend (bool, optional): Whether to display legends on the plots. Default is False.
        """
        import matplotlib.pyplot as plt
        import numpy as np
        from matplotlib.patches import Patch

        try:
            available_tac_features = [feat for feat in self.tac_features if feat in curve_features.columns]
            if not available_tac_features:
                print("No TAC features found in the DataFrame. Available columns:", curve_features.columns.tolist())
                return
            
            print(f"Plotting TAC violin plots for features: {available_tac_features}")
            fig, axes = plt.subplots(2, 2, figsize=(12, 8))
            axes = axes.flatten()
            n_features = len(available_tac_features)
            for ax in axes[n_features:]:
                ax.axis('off')
            
            thresholds = {
                'auc_total_CURVE': 25000,
                'peak_CURVE': 1000,
                'rise_rate_CURVE': 500,
                'fall_rate_CURVE': 500
            }
            
            for i, (ax, tac_feat) in enumerate(zip(axes, available_tac_features)):
                valid_data = curve_features[(curve_features['CURVE_VALID'] == 1)][tac_feat].dropna()
                invalid_data = curve_features[(curve_features['CURVE_VALID'] != 1)][tac_feat].dropna()
                
                threshold = thresholds.get(tac_feat, 2000)
                
                valid_data = valid_data[valid_data > 0]
                invalid_data = invalid_data[invalid_data > 0]
                valid_data = np.clip(valid_data, 0, threshold)
                invalid_data = np.clip(invalid_data, 0, threshold)
                
                datasets = []
                labels = []
                colors = []
                
                if len(invalid_data) > 1:
                    datasets.append(invalid_data)
                    labels.append('Low Quality')
                    colors.append('red')

                if len(valid_data) > 1:
                    datasets.append(valid_data)
                    labels.append('High Quality')
                    colors.append('green')
                
                if not datasets:
                    feature_label = self.feature_labels.get(tac_feat, tac_feat)
                    ax.text(0.5, 0.5, 'No data to plot', ha='center', va='center')
                    ax.set_title(feature_label)
                    continue

                parts = ax.violinplot(datasets, showmeans=True, showmedians=False, showextrema=True)

                for idx, pc in enumerate(parts['bodies']):
                    pc.set_facecolor(colors[idx])
                    pc.set_edgecolor('black')
                    pc.set_alpha(0.6)

                for partname in ('cbars', 'cmins', 'cmaxes', 'cmeans'):
                    vp = parts[partname]
                    vp.set_edgecolor('black')
                    vp.set_linewidth(1)
                
                feature_label = self.feature_labels.get(tac_feat, tac_feat)
                ax.set_ylabel(feature_label)
                ax.set_xlabel(None)
                ax.set_xticks(np.arange(1, len(datasets) + 1))
                ax.set_xticklabels(labels)
                ax.grid(True, linestyle='--', alpha=0.7, zorder=1)

                if show_legend and i == 0:
                    legend_elements = [
                        Patch(facecolor='green', alpha=0.6, edgecolor='black', label='High Quality'),
                        Patch(facecolor='red', alpha=0.6, edgecolor='black', label='Low Quality')
                    ]
                    ax.legend(handles=legend_elements, loc='upper right')
                
                ax.set_facecolor('white')
                ax.set_ylim(bottom=0, top=threshold)
            
            plt.tight_layout(rect=[0, 0, 1, 0.95])
            plt.savefig(output_filename, dpi=300, bbox_inches='tight')
            plt.close(fig)

        except Exception as e:
            import traceback
            print(f"Error processing TAC violin plots:")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            print("Full traceback:")
            traceback.print_exc()
            plt.close('all')
        finally:
            plt.close('all')
            import gc
            gc.collect()
