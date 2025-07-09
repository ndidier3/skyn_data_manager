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
            
        # Print details about each processor
        for i, processor in enumerate(self.processors):
            print(f"\nProcessor {i}:")
            print(f"  Type: {type(processor)}")
            print(f"  Has day_level_data: {hasattr(processor, 'day_level_data')}")
            print(f"  day_level_data type: {type(processor.day_level_data)}")
            print(f"  day_level_data shape: {processor.day_level_data.shape if isinstance(processor.day_level_data, pd.DataFrame) else 'Not a DataFrame'}")
            print(f"  day_level_data columns: {processor.day_level_data.columns.tolist() if isinstance(processor.day_level_data, pd.DataFrame) else 'Not a DataFrame'}")
            
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

    def configure_columns_for_compliance_check(self):
        self.day_features['FLAG_square_wave'] = None
        self.day_features['FLAG_extreme_negative'] = (self.day_features['extreme_negative_duration'] > 2).astype(int)
        self.day_features['FLAG_extreme_high_temp'] = (self.day_features['temp_max'] > 50).astype(int)
        self.day_features['FLAG_extreme_low_temp'] = (self.day_features['temp_min'] < 0).astype(int)
                                                                        
        """Reorder the compliance flag columns to be the 4th column onwards."""
        flag_columns = [col for col in self.day_features.columns if col.startswith('FLAG_')]
        other_columns = [col for col in self.day_features.columns if not col.startswith('FLAG_')]
        new_order = other_columns[:3] + flag_columns + other_columns[3:]
        self.day_features = self.day_features[new_order]

    def export_workbook_days(self, file_name):
        """Export day features to an Excel workbook with plots."""
        print("\nExporting workbook...")
        print(f"File name: {file_name}")
        print(f"Day features columns: {self.day_features.columns.tolist()}")
        
        with pd.ExcelWriter(file_name, engine='xlsxwriter', mode='w') as writer:
            # Write the features sheet
            self.day_features.to_excel(writer, sheet_name='Features', index=False)
            
            # Write the stats sheets
            row_index = 0
            for i, frame in enumerate(self.day_stat_frames):
                frame.to_excel(writer, sheet_name='Stats', startrow=row_index)
                row_index += len(frame) + 2
            
            print(self.day_features['device_removal_plot'])
            print(self.day_features['signal_processing_plot'])
            # Embed the plots
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
            