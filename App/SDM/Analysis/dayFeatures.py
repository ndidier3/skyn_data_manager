from App.SDM.Analysis.statModel import statModel
from App.SDM.Configuration.file_management import load, save_to_computer
from App.SDM.Documenting.embed_graphs import embed_graphs_into_workbook_tab
from App.SDM.Configuration.file_management import extract_subid
import os
import pandas as pd
from openpyxl import Workbook
from openpyxl.drawing.image import Image

class dayFeatures():
    def __init__(self, processed_data_folder, subids=None):
        print(f"Looking for files in: {processed_data_folder}")
        files = [f for f in os.listdir(processed_data_folder) if 'processed' in f]
        
        # Filter files by subid if specified
        if subids is not None:
            subids_str = set(str(s) for s in subids)
            files = [file for file in files if extract_subid(file) in subids_str]
            if not files:
                raise ValueError(f"No processed files found for subids {subids}")
            print(f"Filtered to files for subids {subids}: {files}")
        else:
            print(f"Found files: {files}")
        
        self.processors = [load(file[:-4], processed_data_folder) for file in files]
        print(f"Found {len(self.processors)} processor files")
        
        self.processors = [processor for processor in self.processors if hasattr(processor, 'day_level_data')]
        print(f"Found {len(self.processors)} processors with day_level_data")
        
        if len(self.processors) == 0:
            raise ValueError("No processors with day_level_data found")
            
        # Print summary about processors
        print(f"Loaded {len(self.processors)} processors with day-level data")
            
        self.day_features = pd.concat([processor.day_level_data for processor in self.processors])
            
        self.day_features[['SubID', 'day_no']] = self.day_features[['SubID', 'day_no']].astype(int)
        self.day_features.drop_duplicates(subset=['SubID', 'day_no'], inplace=True)
        self.day_stat_frames = []

        # Split data into valid and invalid days if there's a validity column
        if 'DAY_VALID' in self.day_features.columns:
            self.day_valid = self.day_features[self.day_features['DAY_VALID'] == 1]
            self.day_invalid = self.day_features[self.day_features['DAY_VALID'] != 1]
        else:
            self.day_valid = self.day_features
            self.day_invalid = pd.DataFrame()

    def compute_low_quality_stats(self, output_filepath=None):
        """
        Calculates the percentage of time in various low-quality states and the percentage of that time that was imputed.
        The results are stored in a dataframe and added to self.day_stat_frames.
        If an output_filepath is provided, the stats are also saved to a simple Excel file.
        """
        stats = {}
        
        # Define the low-quality categories and their corresponding column prefixes
        categories = {
            'Gaps': 'gap',
            'Non-Wear': 'non_wear',
            'Jumps': 'jump',
            'Plummets': 'plummet',
            'Extreme Negative': 'extreme_negative'
        }
        
        # Check if necessary columns exist
        required_cols = ['begin_day', 'end_day']
        for prefix in categories.values():
            required_cols.append(f'{prefix}_duration')
            required_cols.append(f'imputed_{prefix}_duration')

        missing_cols = [col for col in required_cols if col not in self.day_features.columns]
            
        if missing_cols:
            print(f"Warning: Missing required columns for low quality stats, skipping: {', '.join(missing_cols)}")
            self.day_stat_frames.append(pd.DataFrame()) # Append empty frame
            return

        # Calculate total day duration using time difference between begin_day and end_day
        # Convert to datetime if not already
        self.day_features['begin_day'] = pd.to_datetime(self.day_features['begin_day'])
        self.day_features['end_day'] = pd.to_datetime(self.day_features['end_day'])
        
        # Calculate duration in hours for each day
        day_durations = (self.day_features['end_day'] - self.day_features['begin_day']).dt.total_seconds() / 3600
        total_day_duration = day_durations.sum()

        for name, prefix in categories.items():
            duration_col = f'{prefix}_duration'
            imputed_duration_col = f'imputed_{prefix}_duration'

            total_category_duration = self.day_features[duration_col].sum()
            total_imputed_duration = self.day_features[imputed_duration_col].sum()
            
            percent_of_total_time = (total_category_duration / total_day_duration) * 100 if total_day_duration > 0 else 0
            
            percent_imputed = (total_imputed_duration / total_category_duration) * 100 if total_category_duration > 0 else 0
            
            stats[name] = {
                '% of Total Day Time': percent_of_total_time,
                '% Imputed': percent_imputed
            }
            
        stats_df = pd.DataFrame.from_dict(stats, orient='index')
        self.day_stat_frames.append(stats_df)

        if output_filepath:
            # Ensure the directory exists
            output_dir = os.path.dirname(output_filepath)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            stats_df.to_excel(output_filepath)

    def add_curve_overlap_detection(self, curve_features_df=None):
        """
        Add curve overlap detection columns to day features.
        
        Args:
            curve_features_df: DataFrame containing curve features (optional)
        """
        print("\nAdding curve overlap detection to day features...")
        
        # Initialize curve overlap columns
        self.day_features['drinking_curve_overlap'] = 0
        self.day_features['valid_drinking_curve_overlap'] = 0
        self.day_features['total_curve_overlap_hours'] = 0.0
        
        if curve_features_df is None or curve_features_df.empty:
            print("No curve features provided - curve overlap columns initialized with default values")
            return
        
        # Ensure required columns exist in curve features
        required_curve_cols = ['subid', 'dataset_id', 'curve_id', 'begin_CURVE', 'end_CURVE', 'CURVE_VALID']
        missing_curve_cols = [col for col in required_curve_cols if col not in curve_features_df.columns]
        if missing_curve_cols:
            print(f"Warning: Missing required columns in curve features: {missing_curve_cols}")
            return
        
        # Convert curve timestamps to datetime
        curve_features_df['begin_CURVE'] = pd.to_datetime(curve_features_df['begin_CURVE'])
        curve_features_df['end_CURVE'] = pd.to_datetime(curve_features_df['end_CURVE'])
        
        # Convert day boundaries to datetime for comparison
        self.day_features['begin_day'] = pd.to_datetime(self.day_features['begin_day'])
        self.day_features['end_day'] = pd.to_datetime(self.day_features['end_day'])
        
        # Find maximum number of curves overlapping any single day to determine column count
        max_overlapping_curves = 0
        
        # Process each day to find overlapping curves
        for idx, day_row in self.day_features.iterrows():
            subid = day_row['SubID']
            dataset_id = day_row['Dataset_ID']
            day_start = day_row['begin_day']
            day_end = day_row['end_day']
            
            # Filter curves for this subject and dataset
            subject_curves = curve_features_df[
                (curve_features_df['subid'] == subid) & 
                (curve_features_df['dataset_id'] == dataset_id)
            ].copy()
            
            if subject_curves.empty:
                continue
            
            # Find curves that overlap with this day
            overlapping_curves = subject_curves[
                (subject_curves['begin_CURVE'] <= day_end) & 
                (subject_curves['end_CURVE'] >= day_start)
            ].sort_values('begin_CURVE')
            
            max_overlapping_curves = max(max_overlapping_curves, len(overlapping_curves))
        
        # Initialize dynamic curve columns based on maximum overlapping curves
        for n in range(1, max_overlapping_curves + 1):
            self.day_features[f'curve_{n}_id'] = None
            self.day_features[f'curve_{n}_valid'] = None
            self.day_features[f'curve_{n}_overlap_hours'] = None
            self.day_features[f'curve_{n}_extends_prior_day'] = None
            self.day_features[f'curve_{n}_extends_next_day'] = None
        
        # Process each day to populate curve overlap data
        for idx, day_row in self.day_features.iterrows():
            subid = day_row['SubID']
            dataset_id = day_row['Dataset_ID']
            day_start = day_row['begin_day']
            day_end = day_row['end_day']
            
            # Filter curves for this subject and dataset
            subject_curves = curve_features_df[
                (curve_features_df['subid'] == subid) & 
                (curve_features_df['dataset_id'] == dataset_id)
            ].copy()
            
            if subject_curves.empty:
                continue
            
            # Find curves that overlap with this day
            overlapping_curves = subject_curves[
                (subject_curves['begin_CURVE'] <= day_end) & 
                (subject_curves['end_CURVE'] >= day_start)
            ].sort_values('begin_CURVE')
            
            if not overlapping_curves.empty:
                # Update summary columns
                self.day_features.loc[idx, 'drinking_curve_overlap'] = 1
                
                # Check if any overlapping curves are valid
                if (overlapping_curves['CURVE_VALID'] == 1).any():
                    self.day_features.loc[idx, 'valid_drinking_curve_overlap'] = 1
                
                # Calculate total overlap hours
                total_overlap = 0
                for curve_idx, curve_row in overlapping_curves.iterrows():
                    # Calculate overlap duration
                    overlap_start = max(curve_row['begin_CURVE'], day_start)
                    overlap_end = min(curve_row['end_CURVE'], day_end)
                    overlap_hours = (overlap_end - overlap_start).total_seconds() / 3600
                    total_overlap += overlap_hours
                
                self.day_features.loc[idx, 'total_curve_overlap_hours'] = total_overlap
                
                # Populate individual curve columns
                for n, (curve_idx, curve_row) in enumerate(overlapping_curves.iterrows(), 1):
                    if n <= max_overlapping_curves:
                        # Calculate overlap duration for this curve
                        overlap_start = max(curve_row['begin_CURVE'], day_start)
                        overlap_end = min(curve_row['end_CURVE'], day_end)
                        overlap_hours = (overlap_end - overlap_start).total_seconds() / 3600
                        
                        # Determine extension flags
                        extends_prior = curve_row['begin_CURVE'] < day_start
                        extends_next = curve_row['end_CURVE'] > day_end
                        
                        # Populate curve columns
                        self.day_features.loc[idx, f'curve_{n}_id'] = curve_row['curve_id']
                        self.day_features.loc[idx, f'curve_{n}_valid'] = int(curve_row['CURVE_VALID'] == 1)
                        self.day_features.loc[idx, f'curve_{n}_overlap_hours'] = overlap_hours
                        self.day_features.loc[idx, f'curve_{n}_extends_prior_day'] = int(extends_prior)
                        self.day_features.loc[idx, f'curve_{n}_extends_next_day'] = int(extends_next)
        
        print(f"Curve overlap detection completed. Found curve overlaps on {self.day_features['drinking_curve_overlap'].sum()} days.")
        
        # Add curve overlap statistics to stats frames
        curve_stats = {
            'Days with curve overlap': self.day_features['drinking_curve_overlap'].sum(),
            'Days with valid curve overlap': self.day_features['valid_drinking_curve_overlap'].sum(),
            'Total curve overlap hours across all days': self.day_features['total_curve_overlap_hours'].sum(),
            'Average curve overlap hours per overlapping day': self.day_features[self.day_features['drinking_curve_overlap'] == 1]['total_curve_overlap_hours'].mean() if self.day_features['drinking_curve_overlap'].sum() > 0 else 0,
            'Maximum curves overlapping a single day': max_overlapping_curves
        }
        
        curve_stats_df = pd.DataFrame.from_dict(curve_stats, orient='index', columns=['Value'])
        self.day_stat_frames.append(curve_stats_df)
        
        print("Curve overlap statistics added to stats frames.")

    def export_workbook_days(self, file_name):
        """Export day features to an Excel workbook with plots."""
        print("\nExporting workbook...")
        print(f"File name: {file_name}")
        print(f"Day features columns: {self.day_features.columns.tolist()}")
        
        # Import report guide for variable key
        from App.SDM.Documenting.report_guide import report_guide
        
        with pd.ExcelWriter(file_name, engine='xlsxwriter', mode='w') as writer:
            # Add variable key
            variable_key = pd.DataFrame({
                'Variable': list(report_guide.day_feature_descriptions.keys()),
                'Description': list(report_guide.day_feature_descriptions.values())
            })
            variable_key.to_excel(writer, sheet_name='Variable Key', index=False)
            
            # Filter out unwanted columns from features export
            columns_to_exclude = ['quality_analyzer', 'device_removal_plot', 'signal_processing_plot']
            filtered_features = self.day_features.drop(columns=columns_to_exclude, errors='ignore')
            
            # Write the features sheet
            filtered_features.to_excel(writer, sheet_name='Features', index=False)
            
            # Write the stats sheets
            row_index = 0
            for i, frame in enumerate(self.day_stat_frames):
                frame.to_excel(writer, sheet_name='Stats', startrow=row_index)
                row_index += len(frame) + 2
            
            # Embed the plots (only if plot columns exist)
            if 'device_removal_plot' in self.day_features.columns and 'signal_processing_plot' in self.day_features.columns:
                print(self.day_features['device_removal_plot'])
                print(self.day_features['signal_processing_plot'])
                embed_graphs_into_workbook_tab(
                    writer.book,
                    [
                        self.day_features['device_removal_plot'].tolist(),
                        self.day_features['signal_processing_plot'].tolist()
                    ],
                    worksheet_name = 'Day Plots',
                    plot_header_text = '',
                    missing_plot_path_text = 'No Plot Available'
                )
            