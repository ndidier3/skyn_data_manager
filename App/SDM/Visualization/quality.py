import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from scipy.stats import gaussian_kde

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
            'total_low_quality_percent_PERIPHERY',
            # 'total_low_quality_duration_REGION',
            'total_low_quality_duration_CURVE',
            'total_low_quality_duration_PERIPHERY',
            
            # Gap Features
            # 'total_gap_percent_REGION',
            'total_gap_percent_CURVE',
            'total_gap_percent_PERIPHERY',
            # 'total_gap_duration_REGION',
            'total_gap_duration_CURVE',
            # 'total_gap_duration_PERIPHERY',

            #Non-wear + Gap Features
            # 'total_non_wear_gap_percent_REGION',
            'total_non_wear_gap_percent_CURVE',
            'total_non_wear_gap_percent_PERIPHERY',
            # 'total_non_wear_gap_duration_REGION',
            'total_non_wear_gap_duration_CURVE',
            # 'total_non_wear_gap_duration_PERIPHERY',
            
            # Non-wear Features
            # 'total_non_wear_percent_REGION',
            'total_non_wear_percent_CURVE',
            'total_non_wear_percent_PERIPHERY',
            # 'total_non_wear_duration_REGION',
            'total_non_wear_duration_CURVE',
            # 'total_non_wear_duration_PERIPHERY',
            
            # Jump Features
            # 'total_jump_percent_REGION',
            'total_jump_percent_CURVE',
            # 'total_jump_percent_PERIPHERY',
            # 'total_jump_duration_REGION',
            'total_jump_duration_CURVE',
            # 'total_jump_duration_PERIPHERY',
            
            # Plummet Features
            # 'total_plummet_percent_REGION',
            'total_plummet_percent_CURVE',
            # 'total_plummet_percent_PERIPHERY',
            # 'total_plummet_duration_REGION',
            'total_plummet_duration_CURVE',
            # 'total_plummet_duration_PERIPHERY',
            
            # Extreme Negative Features
            # 'total_extreme_negative_percent_REGION',
            'total_extreme_negative_percent_CURVE',
            'total_extreme_negative_percent_PERIPHERY',
            # 'total_extreme_negative_duration_REGION',
            'total_extreme_negative_duration_CURVE',
            'total_extreme_negative_duration_PERIPHERY',

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
            
            # Create a separate plot for each quality feature
            for quality_feat in self.quality_features:
                try:
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
                        # Extract region type from quality feature name
                        region_type = quality_feat.split('_')[-1]  # Get last part after underscore
                        
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
        Create histograms for all TAC features, split by valid vs invalid curves.
        Uses specific thresholds for each feature type, with an overflow bin for values above threshold.
        Overflow bins are only used for AUC, rise rate, and fall rate.
        Peak uses its actual maximum value.
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
                
            print(f"Plotting TAC features: {available_tac_features}")
            
            # Create figure with subplots in a 2x2 grid
            fig, axes = plt.subplots(2, 2, figsize=(12, 8))
            axes = axes.flatten()
            n_features = len(available_tac_features)
            
            # Only plot as many features as available (in case fewer than 4)
            for ax in axes[n_features:]:
                ax.axis('off')
            
            # Define thresholds for each feature
            thresholds = {
                'auc_total_CURVE': 100000,
                'rise_rate_CURVE': 250,
                'fall_rate_CURVE': 250
            }
            
            # Define which features should use overflow bins
            use_overflow = {
                'auc_total_CURVE': True,
                'rise_rate_CURVE': True,
                'fall_rate_CURVE': True,
                'peak_CURVE': False
            }
            
            # Define bin widths for each feature
            bin_widths = {
                'auc_total_CURVE': 100,
                'rise_rate_CURVE': 10,
                'fall_rate_CURVE': 10,
                'peak_CURVE': 25
            }
            
            # Process each TAC feature
            for ax, tac_feat in zip(axes, available_tac_features):
                # Prepare data for each category
                valid_data = curve_features[
                    (curve_features['CURVE_VALID'] == 1)
                ][tac_feat]
                
                invalid_data = curve_features[
                    (curve_features['CURVE_VALID'] != 1)
                ][tac_feat]
                
                # Get threshold and bin width for this feature
                if tac_feat == 'peak_CURVE':
                    all_data = pd.concat([valid_data, invalid_data])
                    threshold = all_data.max() * 1.05
                else:
                    threshold = thresholds.get(tac_feat, 2000)
                bin_width = bin_widths.get(tac_feat, 10)
                
                # Create bins
                if tac_feat == 'auc_total_CURVE':
                    all_auc = pd.concat([valid_data, invalid_data])
                    min_positive = all_auc[all_auc > 0].min() if (all_auc > 0).any() else 0.1
                    min_bin = max(0.1, min_positive)
                    threshold = 100000  # Explicitly set for AUC
                    n_bins = 30  # Higher resolution: twice as many bins
                    log_bins = np.logspace(np.log10(min_bin), np.log10(threshold), n_bins)
                    bins = np.concatenate(([0, min_bin], log_bins, [np.inf]))  # Last bin is overflow
                    # Plot outlined histograms for all features with proportions
                    # Plot Low Quality first (so High Quality is on top)
                    ax.hist(invalid_data[invalid_data > 0] if tac_feat == 'auc_total_CURVE' else invalid_data,
                            bins=log_bins if tac_feat == 'auc_total_CURVE' else bins,
                            histtype='step', linewidth=2, color='red', label='Low Quality', zorder=2,
                            weights=np.ones_like(invalid_data[invalid_data > 0] if tac_feat == 'auc_total_CURVE' else invalid_data) / len(invalid_data))
                    ax.hist(valid_data[valid_data > 0] if tac_feat == 'auc_total_CURVE' else valid_data,
                            bins=log_bins if tac_feat == 'auc_total_CURVE' else bins,
                            histtype='step', linewidth=2, color='green', label='High Quality', zorder=3,
                            weights=np.ones_like(valid_data[valid_data > 0] if tac_feat == 'auc_total_CURVE' else valid_data) / len(valid_data))
                    # Plot zeros as a bar at left (for AUC only)
                    if tac_feat == 'auc_total_CURVE':
                        if (invalid_data == 0).any():
                            ax.bar(0.5 * min_bin, (invalid_data == 0).sum() / len(invalid_data), width=0.9 * min_bin, color='red', alpha=0.4, label='Low Quality (AUC=0)',
                                   edgecolor='darkred', linewidth=2, zorder=2)
                        if (valid_data == 0).any():
                            ax.bar(0.5 * min_bin, (valid_data == 0).sum() / len(valid_data), width=0.9 * min_bin, color='green', alpha=0.4, label='High Quality (AUC=0)',
                                   edgecolor='darkgreen', linewidth=2, zorder=3)
                    ax.set_xscale('log')
                    ax.set_xlim(left=10, right=100000)
                    tick_locations = 10 ** np.arange(1, 6)  # 10, 100, 1000, 10000, 100000
                    tick_labels = [f'{int(tick)}' if tick < 100000 else '100000+' for tick in tick_locations]
                    ax.set_xticks(tick_locations)
                    ax.set_xticklabels(tick_labels)

                    # Debug: print sum of histogram heights for each group
                    valid_hist, _ = np.histogram(valid_data[valid_data > 0] if tac_feat == 'auc_total_CURVE' else valid_data,
                                               bins=log_bins if tac_feat == 'auc_total_CURVE' else bins,
                                               weights=np.ones_like(valid_data[valid_data > 0] if tac_feat == 'auc_total_CURVE' else valid_data) / len(valid_data) if len(valid_data) > 0 else None)
                    invalid_hist, _ = np.histogram(invalid_data[invalid_data > 0] if tac_feat == 'auc_total_CURVE' else invalid_data,
                                                 bins=log_bins if tac_feat == 'auc_total_CURVE' else bins,
                                                 weights=np.ones_like(invalid_data[invalid_data > 0] if tac_feat == 'auc_total_CURVE' else invalid_data) / len(invalid_data) if len(invalid_data) > 0 else None)
                    print(f"{tac_feat} - High Quality sum: {valid_hist.sum()} | Low Quality sum: {invalid_hist.sum()}")
                else:
                    bins = np.arange(0, threshold + bin_width, bin_width)
                    if use_overflow.get(tac_feat, False):
                        bins = np.append(bins, threshold * 1.1)
                    # Plot outlined histograms for all features with proportions
                    # Plot Low Quality first (so High Quality is on top)
                    ax.hist(invalid_data[invalid_data > 0] if tac_feat == 'auc_total_CURVE' else invalid_data,
                            bins=log_bins if tac_feat == 'auc_total_CURVE' else bins,
                            histtype='step', linewidth=2, color='red', label='Low Quality', zorder=2,
                            weights=np.ones_like(invalid_data[invalid_data > 0] if tac_feat == 'auc_total_CURVE' else invalid_data) / len(invalid_data))
                    ax.hist(valid_data[valid_data > 0] if tac_feat == 'auc_total_CURVE' else valid_data,
                            bins=log_bins if tac_feat == 'auc_total_CURVE' else bins,
                            histtype='step', linewidth=2, color='green', label='High Quality', zorder=3,
                            weights=np.ones_like(valid_data[valid_data > 0] if tac_feat == 'auc_total_CURVE' else valid_data) / len(valid_data))
                
                # Customize subplot
                feature_label = self.feature_labels.get(tac_feat, tac_feat)
                ax.set_xlabel(feature_label)
                ax.set_ylabel('Proportion')
                ax.grid(True, linestyle='--', alpha=0.7, zorder=0)
                if show_legend:
                    ax.legend()
                ax.set_facecolor('white')
            
            # Adjust layout and save
            plt.tight_layout(rect=[0, 0, 1, 0.95])
            if output_dir:
                plt.savefig(f'{output_dir}/tac_distributions.png', dpi=300, bbox_inches='tight')
            else:
                plt.savefig('tac_distributions.png', dpi=300, bbox_inches='tight')
            
            # Clean up this figure
            plt.close(fig)
            del fig
            del axes
            
            # --- Compute summary statistics for each TAC feature, split by valid/invalid ---
            summary_rows = []
            for tac_feat in available_tac_features:
                for quality_label, mask in zip(['High Quality', 'Low Quality'],
                                               [(curve_features['CURVE_VALID'] == 1), (curve_features['CURVE_VALID'] != 1)]):
                    data = curve_features.loc[mask, tac_feat].dropna()
                    N = data.count()
                    mean = data.mean()
                    std = data.std()
                    se = data.sem()
                    median = data.median()
                    min_ = data.min()
                    max_ = data.max()
                    summary_rows.append({
                        'Feature': self.feature_labels.get(tac_feat, tac_feat),
                        'Curve_Quality': quality_label,
                        'N': N,
                        'Mean': mean,
                        'Std': std,
                        'SE': se,
                        'Median': median,
                        'Min': min_,
                        'Max': max_
                    })
            summary_df = pd.DataFrame(summary_rows)
            # Save to Excel
            excel_path = f'{output_dir}/tac_feature_summary.xlsx' if output_dir else 'tac_feature_summary.xlsx'
            summary_df.to_excel(excel_path, index=False)
            return summary_df
            
        except Exception as e:
            import traceback
            print(f"Error processing TAC features:")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            print("Full traceback:")
            traceback.print_exc()
            plt.close('all')
            
        finally:
            # Clean up any remaining figures
            plt.close('all')
            # Clear any remaining memory
            import gc
            gc.collect()

    def create_tac_density_plots(self, curve_features, output_dir=None, show_legend=False):
        """
        Create density plots (KDE, area=1) for all TAC features, split by valid vs invalid curves.
        Uses a smooth kernel density estimate (KDE) with shading, overlaid for both groups.
        Only uses scipy.stats.gaussian_kde and matplotlib (no seaborn).
        For the AUC plot, the red (Low Quality) KDE is plotted after the green (High Quality) KDE so the red line is always in front.
        Args:
            curve_features (pd.DataFrame): DataFrame containing curve features
            output_dir (str, optional): Directory to save plots. If None, saves in current directory.
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
            thresholds = {
                'auc_total_CURVE': 100000,
                'rise_rate_CURVE': 250,
                'fall_rate_CURVE': 250
            }
            for ax, tac_feat in zip(axes, available_tac_features):
                valid_data = curve_features[(curve_features['CURVE_VALID'] == 1)][tac_feat].dropna()
                invalid_data = curve_features[(curve_features['CURVE_VALID'] != 1)][tac_feat].dropna()
                if tac_feat == 'peak_CURVE':
                    all_data = pd.concat([valid_data, invalid_data])
                    threshold = all_data.max() * 1.05
                    x_min, x_max = all_data.min(), all_data.max()
                else:
                    threshold = thresholds.get(tac_feat, 2000)
                    x_min, x_max = 0, threshold
                # KDE plot using only scipy and matplotlib
                if tac_feat == 'auc_total_CURVE':
                    valid_data = valid_data[valid_data > 0]
                    invalid_data = invalid_data[invalid_data > 0]
                    ax.set_xscale('log')
                    x_grid = np.logspace(np.log10(max(10, valid_data.min() if not valid_data.empty else 10)), np.log10(threshold), 200)
                    # Plot High Quality (green) first (background)
                    if len(valid_data) > 1:
                        kde = gaussian_kde(valid_data)
                        y = kde(x_grid)
                        ax.plot(x_grid, y, color='green', label='High Quality', linewidth=2, zorder=1)
                        ax.fill_between(x_grid, y, color='green', alpha=0.3, zorder=1)
                    # Plot Low Quality (red) second (foreground)
                    if len(invalid_data) > 1:
                        kde = gaussian_kde(invalid_data)
                        y = kde(x_grid)
                        ax.plot(x_grid, y, color='red', label='Low Quality', linewidth=2, zorder=2)
                        ax.fill_between(x_grid, y, color='red', alpha=0.3, zorder=2)
                else:
                    x_grid = np.linspace(x_min, x_max, 200)
                    if len(invalid_data) > 1:
                        kde = gaussian_kde(invalid_data)
                        ax.plot(x_grid, kde(x_grid), color='red', label='Low Quality', linewidth=2)
                        ax.fill_between(x_grid, kde(x_grid), color='red', alpha=0.3)
                    if len(valid_data) > 1:
                        kde = gaussian_kde(valid_data)
                        ax.plot(x_grid, kde(x_grid), color='green', label='High Quality', linewidth=2)
                        ax.fill_between(x_grid, kde(x_grid), color='green', alpha=0.3)
                feature_label = self.feature_labels.get(tac_feat, tac_feat)
                ax.set_xlabel(feature_label)
                ax.set_ylabel('Density')
                ax.grid(True, linestyle='--', alpha=0.7, zorder=0)
                if show_legend:
                    ax.legend()
                ax.set_facecolor('white')
                if tac_feat == 'auc_total_CURVE':
                    ax.set_xlim(left=10, right=threshold)
                    tick_locations = 10 ** np.arange(1, 6)
                    tick_labels = [f'{int(tick)}' if tick < 100000 else '100000+' for tick in tick_locations]
                    ax.set_xticks(tick_locations)
                    ax.set_xticklabels(tick_labels)
                else:
                    ax.set_xlim(left=x_min, right=x_max)
            plt.tight_layout(rect=[0, 0, 1, 0.95])
            if output_dir:
                plt.savefig(f'{output_dir}/tac_density_distributions.png', dpi=300, bbox_inches='tight')
            else:
                plt.savefig('tac_density_distributions.png', dpi=300, bbox_inches='tight')
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
