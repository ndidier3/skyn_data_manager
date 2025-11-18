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
        files = [f for f in os.listdir(processed_data_folder) 
                 if 'processed' in f and not f.startswith('.')]
        
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
        
        # Drop rows with missing SubID, Dataset_ID, or day_no before converting to int
        rows_before = len(self.day_features)
        self.day_features.dropna(subset=['SubID', 'Dataset_ID', 'day_no'], inplace=True)
        self.day_features[['SubID', 'day_no']] = self.day_features[['SubID', 'day_no']].astype(int)
        # Primary key: SubID + Dataset_ID + day_no
        self.day_features.drop_duplicates(subset=['SubID', 'Dataset_ID', 'day_no'], inplace=True)
        print(f"Day features: {len(self.day_features)} rows ({rows_before - len(self.day_features)} dropped)")
        self.day_stat_frames = []

        # Split data into valid and invalid days if there's a validity column
        if 'DAY_VALID' in self.day_features.columns:
            self.day_valid = self.day_features[self.day_features['DAY_VALID'] == 1]
            self.day_invalid = self.day_features[self.day_features['DAY_VALID'] != 1]
        else:
            self.day_valid = self.day_features
            self.day_invalid = pd.DataFrame()
    
    def filter_days_by_date_range(self, metadata_csv_path, first_date_column='Day 1', last_date_column='Day 14'):
        """
        Filter day-level data to only include days within the date range specified in a metadata CSV.
        
        This method reads a CSV file with ID, BURST, and date columns. It uses ID as SubID and 
        BURST as Dataset_ID to filter days. Only days with timestamps between first_date_column 
        and last_date_column (inclusive) are retained.
        
        Args:
            metadata_csv_path (str): Path to the metadata CSV file
            first_date_column (str): Column name for the start date (default: 'Day 1')
            last_date_column (str): Column name for the end date (default: 'Day 14')
        
        Returns:
            None (modifies self.day_features in place)
        """
        print(f"\nFiltering days by metadata date range...")
        print(f"  Metadata file: {metadata_csv_path}")
        print(f"  Date range: {first_date_column} to {last_date_column}")
        
        metadata = pd.read_csv(metadata_csv_path)
        
        # Strip whitespace from column names
        metadata.columns = metadata.columns.str.strip()

        # Check if required columns exist in metadata
        required_meta_cols = ['ID', 'BURST', first_date_column, last_date_column]
        missing_meta_cols = [col for col in required_meta_cols if col not in metadata.columns]
        if missing_meta_cols:
            print(f"Warning: Missing required columns in metadata: {missing_meta_cols}")
            return
        
        # Forward-fill the ID column if there are null IDs (ID is only on the first row for each subject)
        if metadata['ID'].isna().any():
            print("  Detected null IDs in metadata - applying forward-fill...")
            metadata['ID'] = metadata['ID'].ffill()
        
        # Remove rows where ID or BURST is still missing
        metadata = metadata.dropna(subset=['ID', 'BURST'])
        
        # Convert date columns to datetime
        metadata[first_date_column] = pd.to_datetime(metadata[first_date_column], errors='coerce')
        metadata[last_date_column] = pd.to_datetime(metadata[last_date_column], errors='coerce')
        
        # Remove rows with invalid dates
        metadata = metadata.dropna(subset=[first_date_column, last_date_column])
        
        # Convert begin_day and end_day to datetime if not already
        self.day_features['begin_day'] = pd.to_datetime(self.day_features['begin_day'])
        self.day_features['end_day'] = pd.to_datetime(self.day_features['end_day'])
        
        # Reset index to ensure sequential integer indices
        self.day_features = self.day_features.reset_index(drop=True)
        
        # Create a list to track which rows to keep
        rows_to_keep = []
        rows_before = len(self.day_features)
        
        # Debug counters
        total_processed = 0
        matches_found = 0
        date_overlap_passed = 0
        
        # Process each day in day_features
        for idx, day_row in self.day_features.iterrows():
            total_processed += 1
            subid = str(day_row['SubID'])
            dataset_id = str(day_row['Dataset_ID'])
            day_start = day_row['begin_day']
            day_end = day_row['end_day']
            
            # Find matching metadata row
            # Convert Dataset_ID and BURST to int for comparison (Dataset_ID='001' should match BURST=1)
            try:
                dataset_id_int = int(dataset_id)
            except ValueError:
                # If Dataset_ID can't be converted to int, skip this row
                continue
            
            # Convert SubID to int for robust matching (handles leading zeros)
            try:
                subid_int = int(subid)
            except ValueError:
                # If SubID can't be converted to int, skip this row
                continue
            
            # Match on integer values to avoid string comparison issues
            metadata_row = metadata[
                (metadata['ID'].astype(int) == subid_int) &
                (metadata['BURST'].astype(int) == dataset_id_int)
            ]
            
            if metadata_row.empty:
                # No matching metadata found - exclude this day
                continue
            
            matches_found += 1
            
            # Get the date range for this SubID-Dataset_ID combination
            start_date = metadata_row[first_date_column].iloc[0]
            end_date = metadata_row[last_date_column].iloc[0]
            
            # The metadata dates represent the START of each included day
            # CSV "Day 1" = 8/8/24 means include days starting on or after 8/8/24
            # CSV "Day 14" = 8/21/24 means include days starting on or before 8/21/24
            # So day_no=2 (begin_day=8/8) through day_no=15 (begin_day=8/21) will be kept
            if day_start >= start_date and day_start <= end_date:
                date_overlap_passed += 1
                rows_to_keep.append(idx)
        
        # Debug output
        print(f"  DEBUG - Total rows processed: {total_processed}")
        print(f"  DEBUG - Metadata matches found: {matches_found}")
        print(f"  DEBUG - Passed date overlap check: {date_overlap_passed}")
        print(f"  DEBUG - Items in rows_to_keep before dedup: {len(rows_to_keep)}")
        
        # Filter dataframe to only keep matching rows
        # Ensure unique indices (in case of duplicates)
        duplicates_count = len(rows_to_keep) - len(set(rows_to_keep))
        rows_to_keep = list(set(rows_to_keep))
        print(f"  DEBUG - Duplicate indices removed: {duplicates_count}")
        print(f"  DEBUG - Unique indices to keep: {len(rows_to_keep)}")
        
        if len(rows_to_keep) > 0:
            self.day_features = self.day_features.loc[rows_to_keep]
            self.day_features = self.day_features.reset_index(drop=True)
        else:
            # No rows to keep - empty the dataframe
            self.day_features = self.day_features.iloc[0:0]
        
        rows_after = len(self.day_features)
        rows_excluded = rows_before - rows_after
        
        print(f"  Days before filtering: {rows_before}")
        print(f"  Days after filtering: {rows_after}")
        print(f"  Days excluded: {rows_excluded}")
        
        # Update valid/invalid day splits if they exist
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
        self.day_features['predicted_drinking_curve_overlap'] = 0
        self.day_features['predicted_drinking_day_by_curve_start'] = 0
        self.day_features['total_curve_overlap_hours'] = 0.0
        self.day_features['predicted_drinking_overlap_hours'] = 0.0
        
        if curve_features_df is None or curve_features_df.empty:
            print("No curve features provided - curve overlap columns initialized with default values")
            return
        
        # Ensure required columns exist in curve features
        required_curve_cols = ['subid', 'dataset_id', 'curve_id', 'begin_CURVE', 'end_CURVE', 'DRINKING_PRED', 'high_quality_duration_CURVE']
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
        
        # Reset index to ensure unique indices for proper assignment
        self.day_features = self.day_features.reset_index(drop=True)
        
        # Find maximum number of curves overlapping any single day to determine column count
        max_overlapping_curves = 0
        
        # Process each day to find overlapping curves
        for idx, day_row in self.day_features.iterrows():
            subid = day_row['SubID']
            dataset_id = day_row['Dataset_ID']
            day_start = day_row['begin_day']
            day_end = day_row['end_day']
            
            # Filter curves for this subject and dataset
            # Convert to same data types to ensure proper matching
            subject_curves = curve_features_df[
                (curve_features_df['subid'].astype(str) == str(subid)) & 
                (curve_features_df['dataset_id'].astype(str) == str(dataset_id))
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
            self.day_features[f'curve_{n}_id'] = pd.Series([None] * len(self.day_features), index=self.day_features.index)
            self.day_features[f'curve_{n}_predicted_drinking'] = pd.Series([None] * len(self.day_features), index=self.day_features.index)
            self.day_features[f'curve_{n}_overlap_hours'] = pd.Series([None] * len(self.day_features), index=self.day_features.index)
            self.day_features[f'curve_{n}_high_quality_duration'] = pd.Series([None] * len(self.day_features), index=self.day_features.index)
            self.day_features[f'curve_{n}_extends_prior_day'] = pd.Series([None] * len(self.day_features), index=self.day_features.index)
            self.day_features[f'curve_{n}_extends_next_day'] = pd.Series([None] * len(self.day_features), index=self.day_features.index)
        
        # Process each day to populate curve overlap data
        for idx, day_row in self.day_features.iterrows():
            subid = day_row['SubID']
            dataset_id = day_row['Dataset_ID']
            day_start = day_row['begin_day']
            day_end = day_row['end_day']
            
            # Filter curves for this subject and dataset
            # Convert to same data types to ensure proper matching
            subject_curves = curve_features_df[
                (curve_features_df['subid'].astype(str) == str(subid)) & 
                (curve_features_df['dataset_id'].astype(str) == str(dataset_id))
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
                self.day_features.loc[day_row.name, 'drinking_curve_overlap'] = 1
                
                # Check if any overlapping curves are predicted drinking
                predicted_drinking_curves = overlapping_curves[overlapping_curves['DRINKING_PRED'] == 1]
                if not predicted_drinking_curves.empty:
                    self.day_features.loc[day_row.name, 'predicted_drinking_curve_overlap'] = 1
                
                # Check if any predicted drinking curves START within this day
                curves_starting_in_day = predicted_drinking_curves[
                    (predicted_drinking_curves['begin_CURVE'] >= day_start) & 
                    (predicted_drinking_curves['begin_CURVE'] < day_end)
                ]
                if not curves_starting_in_day.empty:
                    self.day_features.loc[day_row.name, 'predicted_drinking_day_by_curve_start'] = 1
                
                # Calculate total overlap hours
                total_overlap = 0
                predicted_drinking_overlap = 0
                for curve_idx, curve_row in overlapping_curves.iterrows():
                    # Calculate overlap duration
                    overlap_start = max(curve_row['begin_CURVE'], day_start)
                    overlap_end = min(curve_row['end_CURVE'], day_end)
                    overlap_hours = (overlap_end - overlap_start).total_seconds() / 3600
                    total_overlap += overlap_hours
                    
                    # Add to predicted drinking overlap only if curve is predicted drinking
                    if curve_row['DRINKING_PRED'] == 1:
                        predicted_drinking_overlap += overlap_hours
                
                self.day_features.loc[day_row.name, 'total_curve_overlap_hours'] = total_overlap
                self.day_features.loc[day_row.name, 'predicted_drinking_overlap_hours'] = predicted_drinking_overlap
                
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
                        self.day_features.loc[day_row.name, f'curve_{n}_id'] = curve_row['curve_id']
                        self.day_features.loc[day_row.name, f'curve_{n}_predicted_drinking'] = int(curve_row['DRINKING_PRED'] == 1)
                        self.day_features.loc[day_row.name, f'curve_{n}_overlap_hours'] = overlap_hours
                        self.day_features.loc[day_row.name, f'curve_{n}_high_quality_duration'] = curve_row.get('high_quality_duration_CURVE', 0)
                        self.day_features.loc[day_row.name, f'curve_{n}_extends_prior_day'] = int(extends_prior)
                        self.day_features.loc[day_row.name, f'curve_{n}_extends_next_day'] = int(extends_next)

        print(f"Curve overlap detection completed. Found curve overlaps on {self.day_features['drinking_curve_overlap'].sum()} days.")
        
        # Add curve overlap statistics to stats frames
        curve_stats = {
            'Days with curve overlap': self.day_features['drinking_curve_overlap'].sum(),
            'Days with predicted drinking curve overlap': self.day_features['predicted_drinking_curve_overlap'].sum(),
            'Days with predicted drinking curve starting in day': self.day_features['predicted_drinking_day_by_curve_start'].sum(),
            'Total curve overlap hours across all days': self.day_features['total_curve_overlap_hours'].sum(),
            'Total predicted drinking overlap hours across all days': self.day_features['predicted_drinking_overlap_hours'].sum(),
            'Average curve overlap hours per overlapping day': self.day_features[self.day_features['drinking_curve_overlap'] == 1]['total_curve_overlap_hours'].mean() if self.day_features['drinking_curve_overlap'].sum() > 0 else 0,
            'Average predicted drinking overlap hours per overlapping day': self.day_features[self.day_features['predicted_drinking_curve_overlap'] == 1]['predicted_drinking_overlap_hours'].mean() if self.day_features['predicted_drinking_curve_overlap'].sum() > 0 else 0,
            'Maximum curves overlapping a single day': max_overlapping_curves
        }
        
        curve_stats_df = pd.DataFrame.from_dict(curve_stats, orient='index', columns=['Value'])
        self.day_stat_frames.append(curve_stats_df)
        
        print("Curve overlap statistics added to stats frames.")

    def export_workbook_days(self, file_name, split_plots_by=None, include_nonwear_plots=True, include_signal_processing_plots=True):
        """
        Export day features to an Excel workbook with plots.
        
        Args:
            file_name (str): Path to output Excel file
            split_plots_by (str, optional): How to split visualization tabs:
                - None (default): All plots in one 'Day Plots' tab
                - 'drinking': Split by predicted_drinking_curve_overlap (any overlap with predicted drinking curve)
                - 'drinking_by_start': Split by predicted_drinking_day_by_curve_start (drinking curve starts in day)
            include_nonwear_plots (bool, optional): Whether to include non-wear detection plots (device_removal_plot). Default: True
            include_signal_processing_plots (bool, optional): Whether to include signal processing plots. Default: True
        """
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
            
            # Embed the plots (only if plot columns exist and are requested)
            # Determine which plots to include
            plot_columns_to_include = []
            if include_nonwear_plots and 'device_removal_plot' in self.day_features.columns:
                plot_columns_to_include.append('device_removal_plot')
            if include_signal_processing_plots and 'signal_processing_plot' in self.day_features.columns:
                plot_columns_to_include.append('signal_processing_plot')
            
            # Only embed plots if at least one type is requested
            if plot_columns_to_include:
                for col in plot_columns_to_include:
                    print(self.day_features[col])
                
                if split_plots_by == 'drinking' and 'predicted_drinking_curve_overlap' in self.day_features.columns:
                    # Split by drinking days (overlap-based)
                    drinking_days = self.day_features[self.day_features['predicted_drinking_curve_overlap'] == 1]
                    non_drinking_days = self.day_features[self.day_features['predicted_drinking_curve_overlap'] == 0]
                    
                    if not non_drinking_days.empty:
                        embed_graphs_into_workbook_tab(
                            writer.book,
                            [non_drinking_days[col].tolist() for col in plot_columns_to_include],
                            worksheet_name = 'Non-Drinking Days',
                            plot_header_text = '',
                            missing_plot_path_text = 'No Plot Available'
                        )
                    
                    if not drinking_days.empty:
                        embed_graphs_into_workbook_tab(
                            writer.book,
                            [drinking_days[col].tolist() for col in plot_columns_to_include],
                            worksheet_name = 'Drinking Days',
                            plot_header_text = '',
                            missing_plot_path_text = 'No Plot Available'
                        )
                
                elif split_plots_by == 'drinking_by_start' and 'predicted_drinking_day_by_curve_start' in self.day_features.columns:
                    # Split by drinking days (curve start-based)
                    drinking_days = self.day_features[self.day_features['predicted_drinking_day_by_curve_start'] == 1]
                    non_drinking_days = self.day_features[self.day_features['predicted_drinking_day_by_curve_start'] == 0]
                    
                    if not non_drinking_days.empty:
                        embed_graphs_into_workbook_tab(
                            writer.book,
                            [non_drinking_days[col].tolist() for col in plot_columns_to_include],
                            worksheet_name = 'Non-Drinking Days (by start)',
                            plot_header_text = '',
                            missing_plot_path_text = 'No Plot Available'
                        )
                    
                    if not drinking_days.empty:
                        embed_graphs_into_workbook_tab(
                            writer.book,
                            [drinking_days[col].tolist() for col in plot_columns_to_include],
                            worksheet_name = 'Drinking Days (by start)',
                            plot_header_text = '',
                            missing_plot_path_text = 'No Plot Available'
                        )
                
                else:
                    # Default: all plots in one tab
                    embed_graphs_into_workbook_tab(
                        writer.book,
                        [self.day_features[col].tolist() for col in plot_columns_to_include],
                        worksheet_name = 'Day Plots',
                        plot_header_text = '',
                        missing_plot_path_text = 'No Plot Available'
                    )
            