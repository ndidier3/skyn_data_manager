from App.SDM.Analysis.statModel import statModel
from App.SDM.Configuration.file_management import load, save_to_computer
from App.SDM.Documenting.embed_graphs import embed_graphs_into_workbook_tab
from App.SDM.Configuration.file_management import extract_subid
import os
import pandas as pd
from openpyxl import Workbook
from openpyxl.drawing.image import Image

class dayFeatures():
    def __init__(self, processed_data_folder, subid=None):
        print(f"Looking for files in: {processed_data_folder}")
        files = [f for f in os.listdir(processed_data_folder) if 'processed' in f]
        
        # Filter files by subid if specified
        if subid is not None:
            files = [file for file in files if extract_subid(file) == str(subid)]
            if not files:
                raise ValueError(f"No processed files found for subid {subid}")
            print(f"Filtered to files for subid {subid}: {files}")
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

        # Define default day-level features to analyze based on day_level_dataframe
        self.default_day_features = [
            'device_one',
            'device_two',
            'device_count',
            'total_duration',
            'device_turned_on_duration',
            'device_turned_on_percent',
            'device_worn_duration',
            'device_worn_percent',
            'imputed_duration',
            'imputed_percent',
            'low_quality_duration',
            'low_quality_percent',
            'unimputed_low_quality_duration',
            'unimputed_low_quality_percent',
            'negative_duration',
            'sub_negative_10_duration',
            'sub_negative_10_percent',
            'consecutive_sub_negative_10_duration',
            'sub_negative_20_duration',
            'sub_negative_20_percent',
            'consecutive_sub_negative_20_duration',
            'sub_negative_40_duration',
            'sub_negative_40_percent',
            'consecutive_sub_negative_40_duration',
            'started_curve_count',
            'complete_curve_count',
            'consecutive_non_wear_duration',
            'consecutive_non_wear_percent',
            'flatline_max',
            'flatlined_percent',
            'jump_duration',
            'jump_percent',
            'plummet_duration',
            'plummet_percent',
            'begin_day',
            'end_day',
            'date'
        ]

        # Split data into valid and invalid days if there's a validity column
        if 'DAY_VALID' in self.day_features.columns:
            self.day_valid = self.day_features[self.day_features['DAY_VALID'] == 1]
            self.day_invalid = self.day_features[self.day_features['DAY_VALID'] != 1]
        else:
            self.day_valid = self.day_features
            self.day_invalid = pd.DataFrame()

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
            