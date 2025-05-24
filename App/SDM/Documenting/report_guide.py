"""
This module contains a class for managing column descriptions used in exported workbooks.
"""

import pandas as pd
from collections import OrderedDict

class ReportGuide:
    def __init__(self):
        # Base curve feature descriptions (used in Features tab)
        self._region_definitions = {
            '_CURVE': 'The main TAC curve region where the alcohol concentration rises and falls',
            '_PERIPHERY': 'The region before and after the curve, used for quality assessment',
            '_REGION': 'The region consisting of CURVE + PERIPHERY',
        }
        self._curve_feature_descriptions = {
            # Basic identifiers
            'subid': 'Subject identifier',
            'dataset_id': 'Dataset identifier',
            'curve_id': 'Curve identifier',
            'curve_count': 'Number of curves for this subject',
            'curve_threshold': 'Threshold used for curve detection',
            
            # Device information
            'device_one_REGION': 'First device ID in the region',
            'device_two_REGION': 'Second device ID in the region',
            'device_count': 'Number of devices in the region',
            
            # TAC curve features
            'duration': 'Total duration in hours',
            'auc_total': 'Area under the curve (total) (µg/L/hour)',
            'auc_relative': 'Area under the curve (relative to baseline) (µg/L/hour)',
            'peak': 'Maximum TAC value (µg/L)',
            'relative_peak': 'Maximum TAC value relative to baseline (µg/L)',
            'rise_rate': 'Rate of TAC increase (Peak / Rise Duration) (µg/(L·h))',
            'rise_duration': 'Duration of TAC increase (hours)',
            'fall_rate': 'Rate of TAC decrease (Peak / Fall Duration) (µg/(L·h))',
            'fall_duration': 'Duration of TAC decrease (hours)',
            'CURVE_VALID': 'Whether the curve meets validity criteria (1=valid)',
            
            # Curve timing features
            'begin': 'Start time of the curve',
            'end': 'End time of the curve',
            'first_tac': 'First TAC value in the curve',
            'last_tac': 'Last TAC value in the curve',
            'mean_tac': 'Mean TAC value in the curve',
            'sd_tac': 'Standard deviation of TAC values in the curve',
            'sem_tac': 'Standard error of the mean TAC values in the curve',
            'rise_complete_perc': 'Percentage of rise phase that is complete (peak - first_tac)/relative_peak',
            'fall_complete_perc': 'Percentage of fall phase that is complete (peak - last_tac)/relative_peak',
            
            # Quality features
            'total_duration': 'Total duration of the region (hours)',
            'device_turned_on_duration': 'Duration device was turned on (hours)',
            'device_turned_on_percent': 'Percentage of time device was turned on',
            'device_worn_duration': 'Duration device was worn (hours)',
            'device_worn_percent': 'Percentage of time device was worn',
            'consecutive_non_wear_duration': 'Longest consecutive duration of non-wear (hours)',
            'consecutive_non_wear_percent': 'Percentage of consecutive non-wear',
            'flatline_max': 'Maximum duration of flatline (hours)',
            'flatlined_percent': 'Percentage of flatlined data',
            'jump_duration': 'Duration of jump-imputed data (hours)',
            'jump_percent': 'Percentage of jump-imputed data',
            'plummet_duration': 'Duration of plummet-imputed data (hours)',
            'plummet_percent': 'Percentage of plummet-imputed data',
            'imputed_duration': 'Duration of imputed data (hours)',
            'imputed_percent': 'Percentage of imputed data',
            'low_quality_duration': 'Duration of low quality data (hours)',
            'low_quality_percent': 'Percentage of low quality data',
            'unimputed_low_quality_duration': 'Duration of low quality data not imputed (hours)',
            'unimputed_low_quality_percent': 'Percentage of low quality data not imputed',
            
            # Negative value features
            'negative_duration': 'Duration of negative TAC values (hours)',
            'sub_negative_10_duration': 'Duration of TAC values below -10 (hours)',
            'sub_negative_10_percent': 'Percentage of TAC values below -10',
            'consecutive_sub_negative_10_duration': 'Longest consecutive duration of TAC values below -10 (hours)',
            'sub_negative_20_duration': 'Duration of TAC values below -20 (hours)',
            'sub_negative_20_percent': 'Percentage of TAC values below -20',
            'consecutive_sub_negative_20_duration': 'Longest consecutive duration of TAC values below -20 (hours)',
            'sub_negative_40_duration': 'Duration of TAC values below -40 (hours)',
            'sub_negative_40_percent': 'Percentage of TAC values below -40',
            'consecutive_sub_negative_40_duration': 'Longest consecutive duration of TAC values below -40 (hours)',
            
            # Curve counts
            'started_curve_count': 'Number of discrete curves within the final curve',
            'complete_curve_count': 'Number of discrete curves started and ended within the final curve',
            
            # Visualization paths
            'smoothed_curve_plot': 'Path to smoothed curve plot',
            'signal_processing_plot': 'Path to signal processing plot',
            'device_removal_plot': 'Path to device removal plot',
            'signal_processing_plot_wide': 'Path to wide signal processing plot',
            
            # Validity flags
            'FLAG_sub_negative_X_PERIPHERY_>P%_>Yhrs': 'Flag for >P% of values below -X for >Y hours in periphery',
            'FLAG_sub_negative_X_PERIPHERY_>Q%_>Yhrs': 'Flag for >Q% of values below -X for >Y hours in periphery',
            'FLAG_sub_negative_X_PERIPHERY_>R%_>Yhrs': 'Flag for >R% of values below -X for >Y hours in periphery',
            'FLAG_non_wear_PERIPHERY_>P%': 'Flag for >P% non-wear in periphery',
            'FLAG_flatlined_peak_CURVE_>P%flatline_peak>X': 'Flag for >P% flatline with peak >X',
            'FLAG_sub_negative_X_CURVE_>P%_>Y': 'Flag for >P% of values below -X for >Y hours in curve',
            'FLAG_rise_completion_CURVE_<P%': 'Flag for <P% rise completion',
            'FLAG_rise_rate_CURVE_>X': 'Flag for rise rate >X',
            'FLAG_fall_completion_CURVE_<P%': 'Flag for <P% fall completion',
            'FLAG_short_curve_duration_CURVE_<Xhrs': 'Flag for curve duration <X hours',
            'FLAG_imputed_CURVE_>P%_or_duration>Xhrs': 'Flag for >P% imputed or duration >X hours',
            'FLAG_unimputed_low_quality_CURVE_>P%': 'Flag for >P% unimputed low quality data',
            
            # Validity indicators
            'PERIPHERY_VALID': 'Whether the periphery meets validity criteria (1=valid)',
            
            # Baseline information
            'unadjusted_threshold': 'Unadjusted threshold value',
            'baseline_mean': 'Mean baseline value',
            'baseline_sd': 'Standard deviation of baseline values',
            
            # Event matching information
            'CURVE_event_match_before_buffer': 'Buffer time before curve for event matching',
            'CURVE_event_match_after_buffer': 'Buffer time after curve for event matching',
            'CURVE_MATCH_START': 'Start time of curve match window',
            'CURVE_MATCH_END': 'End time of curve match window',
            'event_matched_1': 'First matched event ID',
            'event_matched_2': 'Second matched event ID',
            'event_matched_3': 'Third matched event ID',
            'event_matched_4': 'Fourth matched event ID',
            'event_matched_5': 'Fifth matched event ID',
            'event_matched_6': 'Sixth matched event ID',
            'event_matched_7': 'Seventh matched event ID',
            'event_matched_8': 'Eighth matched event ID'
        }

        # Event-related feature descriptions (used in Events tab)
        self._event_feature_descriptions = {
            # Basic event identifiers
            'subid': 'Subject identifier',
            'dataset_identifier': 'Dataset identifier',
            'ema_id': 'EMA (Ecological Momentary Assessment) identifier',
            'event': 'Event number',
            'day_id': 'Study day identifier',
            'drink_total': 'Total number of drinks reported',
            
            # Event timestamps
            'earliest_timestamp': 'Earliest timestamp associated with the event',
            'latest_timestamp': 'Latest timestamp associated with the event',
            'matching_end_timestamp': 'End timestamp for event matching window',
            'self_report_start_time': 'Start time of self-reported event',
            
            # Curve matching information
            'matched': 'Whether the event matched to any curve (1=matched)',
            'num_curves_matched': 'Number of curves matched to this event',
            'has_shared_match': 'Whether the event shares a valid curve match with another event',
            'shared_curve_id': 'ID of the shared valid curve if event shares a match',
            'has_shared_first_match': 'Whether the event shares its first valid curve match with another event',
            'shared_first_curve_id': 'ID of the first shared valid curve if event shares a first match',
            
            # Curve match details (up to 5 possible matches)
            'curve_match_1': 'ID of the first matched curve',
            'curve_match_1_overlap': 'Proportion of overlap between event and first matched curve',
            'curve_match_2': 'ID of the second matched curve',
            'curve_match_2_overlap': 'Proportion of overlap between event and second matched curve',
            'curve_match_3': 'ID of the third matched curve',
            'curve_match_3_overlap': 'Proportion of overlap between event and third matched curve',
            'curve_match_4': 'ID of the fourth matched curve',
            'curve_match_4_overlap': 'Proportion of overlap between event and fourth matched curve',
            'curve_match_5': 'ID of the fifth matched curve',
            'curve_match_5_overlap': 'Proportion of overlap between event and fifth matched curve',
            
            # Valid curve match details
            'valid_curve_match_1': 'ID of the first valid matched curve',
            'valid_curve_match_2': 'ID of the second valid matched curve',
            'valid_curve_match_3': 'ID of the third valid matched curve',
            'valid_curve_match_4': 'ID of the fourth valid matched curve',
            'valid_curve_match_5': 'ID of the fifth valid matched curve',
            'valid_curve_match_1_overlap': 'ID of the first valid curve that overlaps with another valid curve',
            'valid_curve_match_2_overlap': 'ID of the second valid curve that overlaps with another valid curve',
            'valid_curve_match_3_overlap': 'ID of the third valid curve that overlaps with another valid curve',
            'valid_curve_match_4_overlap': 'ID of the fourth valid curve that overlaps with another valid curve',
            'valid_curve_match_5_overlap': 'ID of the fifth valid curve that overlaps with another valid curve',
            
            # Invalid curve match details
            'invalid_curve_match_1': 'ID of the first invalid matched curve',
            'invalid_curve_match_2': 'ID of the second invalid matched curve',
            'invalid_curve_match_3': 'ID of the third invalid matched curve',
            'invalid_curve_match_4': 'ID of the fourth invalid matched curve',
            'invalid_curve_match_5': 'ID of the fifth invalid matched curve',
            'invalid_curve_match_1_overlap': 'ID of the first invalid curve that overlaps with another invalid curve',
            'invalid_curve_match_2_overlap': 'ID of the second invalid curve that overlaps with another invalid curve',
            'invalid_curve_match_3_overlap': 'ID of the third invalid curve that overlaps with another invalid curve',
            'invalid_curve_match_4_overlap': 'ID of the fourth invalid curve that overlaps with another invalid curve',
            'invalid_curve_match_5_overlap': 'ID of the fifth invalid curve that overlaps with another invalid curve',
            
            # Curve validity information
            'CURVE_and_PERIPHERY_VALID_1': 'Whether the first matched curve and its periphery are valid (1=valid)',
            'CURVE_and_PERIPHERY_VALID_2': 'Whether the second matched curve and its periphery are valid (1=valid)',
            'CURVE_and_PERIPHERY_VALID_3': 'Whether the third matched curve and its periphery are valid (1=valid)',
            'CURVE_and_PERIPHERY_VALID_4': 'Whether the fourth matched curve and its periphery are valid (1=valid)',
            'CURVE_and_PERIPHERY_VALID_5': 'Whether the fifth matched curve and its periphery are valid (1=valid)',
            
            # Event region quality features
            'total_duration_EMA_REGION': 'Total duration of the EMA region (hours)',
            'TAC_max_EMA_REGION': 'Maximum TAC value in the EMA region (µg/L)',
            'TAC_avg_EMA_REGION': 'Average TAC value in the EMA region (µg/L)',
            'device_turned_on_duration_EMA_REGION': 'Duration device was turned on in EMA region (hours)',
            'device_turned_on_percent_EMA_REGION': 'Percentage of time device was turned on in EMA region',
            'device_worn_duration_EMA_REGION': 'Duration device was worn in EMA region (hours)',
            'device_worn_percent_EMA_REGION': 'Percentage of time device was worn in EMA region',
            'imputed_duration_EMA_REGION': 'Duration of imputed data in EMA region (hours)',
            'imputed_percent_EMA_REGION': 'Percentage of data that was imputed in EMA region',
            'low_quality_duration_EMA_REGION': 'Duration of low quality data in EMA region (hours)',
            'low_quality_percent_EMA_REGION': 'Percentage of low quality data in EMA region',
            'unimputed_low_quality_duration_EMA_REGION': 'Duration of low quality data not imputed in EMA region (hours)',
            'unimputed_low_quality_percent_EMA_REGION': 'Percentage of low quality data not imputed in EMA region',
            
            # Event region negative value features
            'negative_duration_EMA_REGION': 'Duration of negative TAC values in EMA region (hours)',
            'sub_negative_10_duration_EMA_REGION': 'Duration of TAC values below -10 in EMA region (hours)',
            'sub_negative_10_percent_EMA_REGION': 'Percentage of TAC values below -10 in EMA region',
            'consecutive_sub_negative_10_duration_EMA_REGION': 'Longest consecutive duration of TAC values below -10 in EMA region (hours)',
            'sub_negative_20_duration_EMA_REGION': 'Duration of TAC values below -20 in EMA region (hours)',
            'sub_negative_20_percent_EMA_REGION': 'Percentage of TAC values below -20 in EMA region',
            'consecutive_sub_negative_20_duration_EMA_REGION': 'Longest consecutive duration of TAC values below -20 in EMA region (hours)',
            'sub_negative_40_duration_EMA_REGION': 'Duration of TAC values below -40 in EMA region (hours)',
            'sub_negative_40_percent_EMA_REGION': 'Percentage of TAC values below -40 in EMA region',
            'consecutive_sub_negative_40_duration_EMA_REGION': 'Longest consecutive duration of TAC values below -40 in EMA region (hours)',
            
            # Event region visualization
            'device_removal_plot_EMA_REGION': 'Path to device removal plot for EMA region',
            'signal_processing_plot_EMA_REGION': 'Path to signal processing plot for EMA region',
            
        }

        # Person-level feature descriptions (used in Valid Matched by SubID tab)
        self._person_level_feature_descriptions = {
            # Continuous TAC features
            'duration_CURVE': 'Total duration in hours',
            'auc_total_CURVE': 'Area under the curve (total) (µg/L/hour)',
            'auc_relative_CURVE': 'Area under the curve (relative to baseline) (µg/L/hour)',
            'peak_CURVE': 'Maximum TAC value (µg/L)',
            'relative_peak_CURVE': 'Maximum TAC value relative to baseline (µg/L)',
            'rise_rate_CURVE': 'Rate of TAC increase (Peak / Rise Duration) (µg/(L·h))',
            'rise_duration_CURVE': 'Duration of TAC increase (hours)',
            'fall_rate_CURVE': 'Rate of TAC decrease (Peak / Fall Duration) (µg/(L·h))',
            'fall_duration_CURVE': 'Duration of TAC decrease (hours)',
            
            # Quality features
            'total_duration_CURVE': 'Total duration of the region (hours)',
            'device_turned_on_duration_CURVE': 'Duration device was turned on (hours)',
            'device_turned_on_percent_CURVE': 'Percentage of time device was turned on',
            'device_worn_duration_CURVE': 'Duration device was worn (hours)',
            'device_worn_percent_CURVE': 'Percentage of time device was worn',
            'consecutive_non_wear_duration_CURVE': 'Longest consecutive duration of non-wear (hours)',
            'consecutive_non_wear_percent_CURVE': 'Percentage of consecutive non-wear',
            'flatline_max_CURVE': 'Maximum duration of flatline (hours)',
            'flatlined_percent_CURVE': 'Percentage of flatlined data',
            'jump_duration_CURVE': 'Duration of jump-imputed data (hours)',
            'jump_percent_CURVE': 'Percentage of jump-imputed data',
            'plummet_duration_CURVE': 'Duration of plummet-imputed data (hours)',
            'plummet_percent_CURVE': 'Percentage of plummet-imputed data',
            'imputed_duration_CURVE': 'Duration of imputed data (hours)',
            'imputed_percent_CURVE': 'Percentage of imputed data',
            'low_quality_duration_CURVE': 'Duration of low quality data (hours)',
            'low_quality_percent_CURVE': 'Percentage of low quality data',
            'unimputed_low_quality_duration_CURVE': 'Duration of low quality data not imputed (hours)',
            'unimputed_low_quality_percent_CURVE': 'Percentage of low quality data not imputed',
            
            # Categorical features
            'CURVE_VALID': 'Whether the curve meets validity criteria (1=valid)',
            'device_count_REGION': 'Number of devices in the region'
        }

        # Person-level feature types
        self._person_level_feature_types = {
            # Continuous TAC features
            'duration_CURVE': 'numeric',
            'auc_total_CURVE': 'numeric',
            'auc_relative_CURVE': 'numeric',
            'peak_CURVE': 'numeric',
            'relative_peak_CURVE': 'numeric',
            'rise_rate_CURVE': 'numeric',
            'rise_duration_CURVE': 'numeric',
            'fall_rate_CURVE': 'numeric',
            'fall_duration_CURVE': 'numeric',
            
            # Quality features
            'total_duration_CURVE': 'numeric',
            'device_turned_on_duration_CURVE': 'numeric',
            'device_turned_on_percent_CURVE': 'numeric',
            'device_worn_duration_CURVE': 'numeric',
            'device_worn_percent_CURVE': 'numeric',
            'consecutive_non_wear_duration_CURVE': 'numeric',
            'consecutive_non_wear_percent_CURVE': 'numeric',
            'flatline_max_CURVE': 'numeric',
            'flatlined_percent_CURVE': 'numeric',
            'jump_duration_CURVE': 'numeric',
            'jump_percent_CURVE': 'numeric',
            'plummet_duration_CURVE': 'numeric',
            'plummet_percent_CURVE': 'numeric',
            'imputed_duration_CURVE': 'numeric',
            'imputed_percent_CURVE': 'numeric',
            'low_quality_duration_CURVE': 'numeric',
            'low_quality_percent_CURVE': 'numeric',
            'unimputed_low_quality_duration_CURVE': 'numeric',
            'unimputed_low_quality_percent_CURVE': 'numeric',
            
            # Categorical features
            'CURVE_VALID': 'categorical',
            'PERIPHERY_VALID': 'categorical',
            'device_count_REGION': 'categorical'
        }

        # Imputation feature descriptions (used in Imputations tab)
        self._imputation_feature_descriptions = {
            'region_start': 'Start time of the imputed region',
            'region_end': 'End time of the imputed region',
            'region_length': 'Length (duration) of the imputed region (minutes or hours)',
            'worn_minutes_before': 'Minutes device was worn before the imputed region',
            'worn_percent_before': 'Percent of time device was worn before the imputed region',
            'worn_minutes_after': 'Minutes device was worn after the imputed region',
            'worn_percent_after': 'Percent of time device was worn after the imputed region',
            'min_training_data_required': 'Minimum training data required for imputation',
            'was_imputed': 'Whether this region was imputed (1=True, 0=False)',
            'reason_not_imputed': 'Reason why the region was not imputed (if applicable)',
            'high_quality_before': 'High quality data points before the imputed region',
            'low_quality_before': 'Low quality data points before the imputed region',
            'high_quality_after': 'High quality data points after the imputed region',
            'low_quality_after': 'Low quality data points after the imputed region',
            'total_training_before': 'Total training data points before the imputed region',
            'total_training_after': 'Total training data points after the imputed region',
            'subid': 'Subject identifier',
            'dataset_identifier': 'Dataset identifier'
        }

        # Tab descriptions for different export types
        self._curve_features_tab_descriptions = {
            'Variable Key': 'Descriptions of all variables used in the workbook',
            'Stats': 'Statistical summaries of curve features',
            'Features': 'Curve features and quality metrics for each curve',
            'Person Level Stats': 'Person-level statistics for all curves',
            'Valid Curves': 'Visualization of curves that met validity criteria',
            'Invalid Curves': 'Visualization of curves that did not meet validity criteria',
            'Imputations': 'Information about imputed regions in the data',
            'Run Settings': 'Settings used to generate the curves',
        }

        self._curve_features_with_events_tab_descriptions = {
            'Variable Key': 'Descriptions of all variables used in the workbook',
            'STATS': 'Statistical summaries of curve features and event matching',
            'Features': 'Curve features and quality metrics for each curve',
            'Events': 'Event data and their matching information',
            'Valid Matched by SubID': 'Person-level statistics for valid curves with matched events',
            'Valid Curves': 'Visualization of curves that met validity criteria',
            'Invalid Curves': 'Visualization of curves that did not meet validity criteria',
            'No Curve - EMA Region': 'Visualization of events that did not match to any curve',
            'Imputations': 'Information about imputed regions in the data',
            'Run Settings': 'Settings used to generate the curves and match events',
        }

        # Default TAC and quality features for statistics
        self._stats_features = [
            # TAC curve features
            'duration_CURVE', 'auc_total_CURVE', 'auc_relative_CURVE', 
            'peak_CURVE', 'relative_peak_CURVE',
            'rise_rate_CURVE', 'rise_duration_CURVE',
            'fall_rate_CURVE',  'fall_duration_CURVE',
            
            # Quality features
            'total_duration_CURVE',
            'device_turned_on_duration_CURVE',
            'device_turned_on_percent_CURVE',
            'device_worn_duration_CURVE',
            'device_worn_percent_CURVE',
            'consecutive_non_wear_duration_CURVE',
            'consecutive_non_wear_percent_CURVE',
            'flatline_max_CURVE',
            'flatlined_percent_CURVE',
            'jump_duration_CURVE',
            'jump_percent_CURVE',
            'plummet_duration_CURVE',
            'plummet_percent_CURVE',
            'imputed_duration_CURVE',
            'imputed_percent_CURVE',
            'low_quality_duration_CURVE',
            'low_quality_percent_CURVE',
            'unimputed_low_quality_duration_CURVE',
            'unimputed_low_quality_percent_CURVE'
        ]

    @property
    def curve_feature_descriptions(self):
        """Get curve feature descriptions."""
        return self._curve_feature_descriptions

    @property
    def curve_features_descriptions(self):
        """Get curve feature descriptions."""
        return self._curve_feature_descriptions

    @property
    def event_feature_descriptions(self):
        """Get event feature descriptions."""
        return OrderedDict(self._event_feature_descriptions)

    @property
    def person_level_feature_descriptions(self):
        """Get person-level feature descriptions."""
        return self._person_level_feature_descriptions

    @property
    def imputation_feature_descriptions(self):
        """Get imputation feature descriptions."""
        return self._imputation_feature_descriptions

    @property
    def curve_features_with_events_descriptions(self):
        """Get all feature descriptions combined."""
        return {
            **self._curve_feature_descriptions,
            **self._person_level_feature_descriptions,
            **self._event_feature_descriptions,
            **self._imputation_feature_descriptions
        }

    @property
    def person_level_feature_types(self):
        """Get person-level feature types."""
        return self._person_level_feature_types

    @property
    def stats_features(self):
        """Get features used for statistical analysis."""
        return self._stats_features

    @property
    def region_definitions(self):
        """Get region definitions."""
        return self._region_definitions

    @classmethod
    def get_variable_key_dataframes(cls):
        """Get a list of (name, dataframe) tuples for variable keys in export order."""
        instance = cls()
        dfs = []
        
        # Region definitions
        region_df = pd.DataFrame({
            'Variable': list(instance.region_definitions.keys()),
            'Description': list(instance.region_definitions.values())
        })
        region_df.set_index('Variable', inplace=True)
        region_df.index.name = None
        region_df.columns = pd.MultiIndex.from_product([['Region Definitions'], region_df.columns])
        dfs.append(('Region Definitions', region_df))
        
        # Features tab
        features_df = pd.DataFrame({
            'Variable': list(instance.curve_feature_descriptions.keys()),
            'Description': list(instance.curve_feature_descriptions.values())
        })
        features_df.set_index('Variable', inplace=True)
        features_df.index.name = None
        features_df.columns = pd.MultiIndex.from_product([['Features'], features_df.columns])
        dfs.append(('Features', features_df))
        
        # Events tab
        events_df = pd.DataFrame({
            'Variable': list(instance.event_feature_descriptions.keys()),
            'Description': list(instance.event_feature_descriptions.values())
        })
        events_df.set_index('Variable', inplace=True)
        events_df.index.name = None
        events_df.columns = pd.MultiIndex.from_product([['Events'], events_df.columns])
        dfs.append(('Events', events_df))
        
        # Valid Matched by SubID tab
        person_df = pd.DataFrame({
            'Variable': list(instance.person_level_feature_descriptions.keys()),
            'Description': list(instance.person_level_feature_descriptions.values())
        })
        person_df.set_index('Variable', inplace=True)
        person_df.index.name = None
        person_df.columns = pd.MultiIndex.from_product([['Valid Matched by SubID'], person_df.columns])
        dfs.append(('Valid Matched by SubID', person_df))
        
        # Imputations tab
        imputations_df = pd.DataFrame({
            'Variable': list(instance.imputation_feature_descriptions.keys()),
            'Description': list(instance.imputation_feature_descriptions.values())
        })
        imputations_df.set_index('Variable', inplace=True)
        imputations_df.index.name = None
        imputations_df.columns = pd.MultiIndex.from_product([['Imputations'], imputations_df.columns])
        dfs.append(('Imputations', imputations_df))
        
        return dfs

    @classmethod
    def get_run_settings_dataframe(cls, smooth_and_impute_attrs=None, curve_attrs=None, event_attrs=None, day_attrs=None):
        """Get a DataFrame of run settings in the correct format for export."""
        run_settings = []
        
        # Helper function to add settings
        def add_setting(category, setting, value):
            run_settings.append({
                'Category': category,
                'Setting': setting,
                'Value': str(value)  # Convert all values to strings for consistent display
            })

        # Add Smooth and Impute settings
        if smooth_and_impute_attrs:
            for key, value in smooth_and_impute_attrs.items():
                add_setting('Smooth and Impute', key, value)
        
        # Add Curve settings
        if curve_attrs:
            for key, value in curve_attrs.items():
                if isinstance(value, dict):
                    for subkey, subvalue in value.items():
                        if isinstance(subvalue, dict):
                            for subsubkey, subsubvalue in subvalue.items():
                                add_setting(f'Curve - {key}', f"{subkey}.{subsubkey}", subsubvalue)
                        else:
                            add_setting(f'Curve - {key}', subkey, subvalue)
                else:
                    add_setting('Curve', key, value)

        # Add Event settings
        if event_attrs:
            for key, value in event_attrs.items():
                if isinstance(value, list):
                    add_setting('Event', key, ', '.join(str(v) for v in value))
                else:
                    add_setting('Event', key, value)

        # Add Day settings
        if day_attrs:
            for key, value in day_attrs.items():
                add_setting('Day', key, value)

        return pd.DataFrame(run_settings) if run_settings else None

    def get_tab_descriptions_dataframe(self, include_events=False):
        """
        Get a DataFrame describing the tabs in the exported workbook.
        
        Args:
            include_events (bool): Whether to include event-related tabs
            
        Returns:
            pd.DataFrame: DataFrame with tab names and descriptions
        """
        descriptions = self._curve_features_with_events_tab_descriptions if include_events else self._curve_features_tab_descriptions
        return pd.DataFrame({
            'Tab Name': list(descriptions.keys()),
            'Description': list(descriptions.values())
        })

# Create a singleton instance
report_guide = ReportGuide()

# Export the properties for backward compatibility
curve_feature_descriptions = report_guide.curve_feature_descriptions
event_feature_descriptions = report_guide.event_feature_descriptions
person_level_feature_descriptions = report_guide.person_level_feature_descriptions
imputation_feature_descriptions = report_guide.imputation_feature_descriptions
curve_features_descriptions = report_guide.curve_features_descriptions
curve_features_with_events_descriptions = report_guide.curve_features_with_events_descriptions
person_level_feature_types = report_guide.person_level_feature_types
stats_features = report_guide.stats_features 