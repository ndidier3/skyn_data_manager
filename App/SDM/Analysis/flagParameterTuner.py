import itertools
import pandas as pd
from App.SDM.Analysis.curveFeaturesWithEvents import curveFeaturesWithEvents
from App.SDM.Analysis.featureFlagger import featureFlagger
import os

class flagParameterTuner(curveFeaturesWithEvents):
    def __init__(self, processed_data_folder, ema_id_column, base_config, event_type_column='', event_type_settings={}):
        super().__init__(processed_data_folder, ema_id_column, event_type_column, event_type_settings)
        self.base_config = base_config
        self.comparison_df = None  # Initialize comparison_df as None
        self.parameter_ranges = {
            # Curve Shape Parameters
            'flag_extreme_rise_rate_curve': {
                'rise_rate_cutoff': [380, 400, 420, 440, 460, 480]
            },
            'flag_incomplete_curve_start_curve': {
                'percent_cutoff': [0.3, 0.4, 0.5, 0.6, 0.7]
            },
            'flag_incomplete_curve_end_curve': {
                'percent_cutoff': [0.3, 0.4, 0.5, 0.6, 0.7]
            },
            'flag_flatlined_peak_curve': {
                'flatline_percent_cutoff': [0.10, 0.15, 0.20, 0.25, 0.30],
                'peak_above': [250, 300, 350, 400, 450]
            },
            'flag_short_curve_duration_curve': {
                'duration_cutoff': [0.20, 0.25, 0.30, 0.35, 0.40, 0.45]
            },
            
            # Data Quality Parameters
            'flag_unimputed_low_quality_percent_curve': {
                'percent_cutoff': [0.10, 0.15, 0.20, 0.25, 0.30]
            },
            'flag_too_much_imputation_curve': {
                'percent_cutoff': [0.2, 0.3, 0.4, 0.5, 0.6],
                'duration_cutoff': [1, 2, 3, 4, 5]
            },
            
            # Negative Value Parameters
            'flag_sub_negative_10_curve': {
                'percent_cutoff': [0.10, 0.15, 0.20, 0.25, 0.30],
                'duration_cutoff': [0.25, 0.5, 0.75, 1.0, 1.25, 1.5]
            },
            
            # Periphery flags
            'flag_sub_negative_10_periphery': {
                'percent_cutoff': [0.6, 0.7, 0.8, 0.9],
                'duration_cutoff': [1.5, 2.0, 2.5, 3.0]
            },
            'flag_sub_negative_20_periphery': {
                'percent_cutoff': [0.3, 0.4, 0.5, 0.6],
                'duration_cutoff': [1.0, 1.5, 2.0, 2.5]
            },
            'flag_sub_negative_40_periphery': {
                'percent_cutoff': [0.15, 0.20, 0.25, 0.30],
                'duration_cutoff': [0.25, 0.5, 0.75, 1.0]
            },
            'flag_non_wear_periphery': {
                'percent_cutoff': [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60]
            }
        }

    def print_parameter_ranges(self):
        print("\nParameter Ranges Being Tested:")
        for flag, params in self.parameter_ranges.items():
            print(f"\n{flag}:")
            for param, values in params.items():
                print(f"  {param}: {values}")

    def generate_flag_configurations(self, flag_name):
        configs = []
        flag_params = self.parameter_ranges[flag_name]
        
        # Generate all combinations of parameters for this flag
        param_combinations = list(itertools.product(*flag_params.values()))
        print(f"\nProcessing {flag_name}: {len(param_combinations)} configurations")
        
        for params in param_combinations:
            # Create a deep copy of the base configuration
            config = {
                'flag_selections': {
                    flag: self.base_config['flag_selections'][flag].copy()
                    for flag in self.parameter_ranges.keys()
                }
            }
            
            # Update the parameters for this flag
            config['flag_selections'][flag_name] = dict(zip(flag_params.keys(), params))
            configs.append(config)
        
        return configs

    def compare_flag_configurations(self):
        """
        Compare different flag configurations and their impact on curve validation
        """
        print("\n=== Starting Flag Configuration Comparison ===")
        print(f"Total flags to compare: {len(self.parameter_ranges)}")
        
        comparison_results = []
        
        # Use curve_with_event from parent class
        curves_with_events = self.curve_with_event.copy()
        
        # Get base validation counts for curves with events
        base_flagger = featureFlagger(curves_with_events, self.base_config['flag_selections'])
        base_flags = base_flagger.run_flags_and_validation()
        base_valid_count = curves_with_events['CURVE_VALID'].sum()
        base_invalid_count = len(curves_with_events) - base_valid_count
        print(f"Base valid curves: {base_valid_count}")
        print(f"Base invalid curves: {base_invalid_count}")
        
        # Store base flag columns for comparison
        base_flag_columns = base_flags['curve_flags']
        
        for flag_name in self.parameter_ranges.keys():
            flag_configs = self.generate_flag_configurations(flag_name)
            
            for config in flag_configs:
                # Create a fresh copy of curves_with_events for each test
                test_curves = curves_with_events.copy()
                
                # Apply new configuration
                flagger = featureFlagger(test_curves, config['flag_selections'])
                flags = flagger.run_flags_and_validation()
                
                # Get validation counts
                valid_count = test_curves['CURVE_VALID'].sum()
                invalid_count = len(test_curves) - valid_count
                
                # Calculate changes
                valid_change = valid_count - base_valid_count
                invalid_change = invalid_count - base_invalid_count
                
                # Get the specific flag column for this configuration
                current_flag_column = flags['curve_flags'][-1]
                
                # Find the corresponding base flag column
                base_flag_column = None
                for col in base_flag_columns:
                    if flag_name in col:
                        base_flag_column = col
                        break
                
                if base_flag_column is None:
                    print(f"Warning: Could not find base flag column for {flag_name}")
                    # Create a default base flag column with all zeros
                    base_flag_column = f"BASE_{flag_name}"
                    test_curves[base_flag_column] = 0
                
                # Calculate flag-specific changes
                flag_specific_changes = {
                    'flag_specific_valid_to_invalid': len(test_curves[
                        (test_curves[base_flag_column] == 0) & 
                        (test_curves[current_flag_column] == 1) &
                        (test_curves['CURVE_VALID'] == 0)
                    ]),
                    'flag_specific_invalid_to_valid': len(test_curves[
                        (test_curves[base_flag_column] == 1) & 
                        (test_curves[current_flag_column] == 0) &
                        (test_curves['CURVE_VALID'] == 1)
                    ]),
                    'flag_specific_total_changed': len(test_curves[
                        test_curves[base_flag_column] != test_curves[current_flag_column]
                    ]),
                    # Event-specific metrics
                    'events_affected': len(test_curves[
                        test_curves[base_flag_column] != test_curves[current_flag_column]
                    ]['event_matched_1'].unique()),
                    'events_lost_valid_curves': len(test_curves[
                        (test_curves[base_flag_column] == 0) & 
                        (test_curves[current_flag_column] == 1) &
                        (test_curves['CURVE_VALID'] == 0)
                    ]['event_matched_1'].unique()),
                    'events_gained_valid_curves': len(test_curves[
                        (test_curves[base_flag_column] == 1) & 
                        (test_curves[current_flag_column] == 0) &
                        (test_curves['CURVE_VALID'] == 1)
                    ]['event_matched_1'].unique())
                }
                
                # Store results with parameter values as separate columns
                result = {
                    'flag_name': flag_name,
                    'base_valid_count': base_valid_count,
                    'base_invalid_count': base_invalid_count,
                    'new_valid_count': valid_count,
                    'new_invalid_count': invalid_count,
                    'valid_change': valid_change,
                    'invalid_change': invalid_change,
                    'percent_valid_change': (valid_change / base_valid_count) * 100 if base_valid_count > 0 else 0,
                    'percent_invalid_change': (invalid_change / base_invalid_count) * 100 if base_invalid_count > 0 else 0,
                    **flag_specific_changes
                }
                
                # Add parameter values as separate columns
                for param_name, param_value in config['flag_selections'][flag_name].items():
                    result[f'param_{param_name}'] = param_value
                
                comparison_results.append(result)
        
        # Save results to class attribute
        self.comparison_df = pd.DataFrame(comparison_results)
        print(f"\nTotal results stored: {len(self.comparison_df)}")
        
        return self.comparison_df

    def export_comparison_report(self, output_path):
        """
        Export comparison results to Excel with multiple sheets
        """
        if self.comparison_df is None or len(self.comparison_df) == 0:
            raise ValueError("No comparison results available. Run compare_flag_configurations() first.")
            
        # Validate required columns exist
        required_columns = ['flag_name', 'valid_change', 'invalid_change', 'percent_valid_change', 
                          'percent_invalid_change', 'flag_specific_valid_to_invalid', 
                          'flag_specific_invalid_to_valid', 'flag_specific_total_changed',
                          'events_affected', 'events_lost_valid_curves', 'events_gained_valid_curves']
        
        missing_columns = [col for col in required_columns if col not in self.comparison_df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns in comparison results: {missing_columns}")
            
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
        with pd.ExcelWriter(output_path) as writer:
            # Create Variable Key sheet
            variable_key = pd.DataFrame({
                'Column Name': [
                    'flag_name',
                    'parameters',
                    'base_valid_count',
                    'base_invalid_count',
                    'new_valid_count',
                    'new_invalid_count',
                    'valid_change',
                    'invalid_change',
                    'percent_valid_change',
                    'percent_invalid_change',
                    'flag_specific_valid_to_invalid',
                    'flag_specific_invalid_to_valid',
                    'flag_specific_total_changed',
                    'events_affected',
                    'events_lost_valid_curves',
                    'events_gained_valid_curves'
                ],
                'Description': [
                    'Name of the flag being tested',
                    'Parameter values used for this flag configuration',
                    'Number of valid curves in the base configuration',
                    'Number of invalid curves in the base configuration',
                    'Number of valid curves with the new configuration',
                    'Number of invalid curves with the new configuration',
                    'Change in number of valid curves (new - base)',
                    'Change in number of invalid curves (new - base)',
                    'Percentage change in valid curves relative to base',
                    'Percentage change in invalid curves relative to base',
                    'Number of curves that changed from valid to invalid',
                    'Number of curves that changed from invalid to valid',
                    'Total number of curves that changed flag status',
                    'Number of unique events affected by flag changes',
                    'Number of events that lost valid curves',
                    'Number of events that gained valid curves'
                ]
            })
            variable_key.to_excel(writer, sheet_name='Variable Key', index=False)
            
            # Summary sheet
            summary = self.comparison_df.groupby('flag_name').agg({
                'valid_change': ['mean', 'min', 'max'],
                'invalid_change': ['mean', 'min', 'max'],
                'percent_valid_change': ['mean', 'min', 'max'],
                'percent_invalid_change': ['mean', 'min', 'max'],
                'flag_specific_valid_to_invalid': ['mean', 'min', 'max'],
                'flag_specific_invalid_to_valid': ['mean', 'min', 'max'],
                'flag_specific_total_changed': ['mean', 'min', 'max'],
                'events_affected': ['mean', 'min', 'max'],
                'events_lost_valid_curves': ['mean', 'min', 'max'],
                'events_gained_valid_curves': ['mean', 'min', 'max']
            }).round(2)
            summary.to_excel(writer, sheet_name='Summary')
            
            # Detailed results sheet
            self.comparison_df.to_excel(writer, sheet_name='Detailed Results', index=False)
            
            # Per-flag sheets
            for flag_name in self.comparison_df['flag_name'].unique():
                flag_data = self.comparison_df[self.comparison_df['flag_name'] == flag_name]
                
                # Create a shorter sheet name that's still unique
                # Remove 'flag_' prefix and '_curve' or '_periphery' suffix
                sheet_name = flag_name.replace('flag_', '').replace('_curve', '').replace('_periphery', '')
                # Truncate to 31 characters if needed
                sheet_name = sheet_name[:31]
                
                # Ensure sheet name is unique by adding a number if needed
                base_sheet_name = sheet_name
                counter = 1
                while sheet_name in writer.sheets:
                    sheet_name = f"{base_sheet_name[:28]}_{counter}"
                    counter += 1
                
                flag_data.to_excel(writer, sheet_name=sheet_name, index=False)
