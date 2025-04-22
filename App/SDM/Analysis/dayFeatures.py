from App.SDM.Analysis.statModel import statModel
from App.SDM.Configuration.file_management import load, save_to_computer
from App.SDM.Documenting.embed_graphs import embed_graphs_into_workbook_tab
import os
import pandas as pd

class dayFeatures():
    def __init__(self, processed_data_folder):
        print(f"Looking for files in: {processed_data_folder}")
        files = [f for f in os.listdir(processed_data_folder) if 'processed' in f]
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
            
        # Try to concatenate with more information
        day_level_dfs = []
        for i, processor in enumerate(self.processors):
            df = processor.day_level_data
            if isinstance(df, pd.DataFrame) and not df.empty:
                day_level_dfs.append(df)
            else:
                print(f"\nSkipping processor {i} - DataFrame is empty or not a DataFrame")
                
        if not day_level_dfs:
            print("\nWARNING: No valid DataFrames found to concatenate!")
            self.day_features = pd.DataFrame()  # Create empty DataFrame
        else:
            self.day_features = pd.concat(day_level_dfs, ignore_index=True)
            
        print("\nFinal day_features:")
        print("Shape:", self.day_features.shape)
        print("Columns:", self.day_features.columns.tolist())
        
        if self.day_features.empty:
            print("\nWARNING: day_features is empty! Cannot proceed with column operations.")
            return
            
        self.day_features[['SubID', 'DayNo']] = self.day_features[['SubID', 'DayNo']].astype(int)
        self.day_features.drop_duplicates(subset=['SubID', 'DayNo'], inplace=True)
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
        with pd.ExcelWriter(file_name, engine='xlsxwriter', mode='w') as writer:
            self.day_features.to_excel(writer, sheet_name='Features', index=False)
            
            row_index = 0
            for i, frame in enumerate(self.day_stat_frames):
                frame.to_excel(writer, sheet_name='Stats', startrow=row_index)
                row_index += len(frame) + 2

            # Embed plots if they exist
            if 'device_removal_plot' in self.day_features.columns and 'signal_processing_plot' in self.day_features.columns:
                embed_graphs_into_workbook_tab(
                    writer.book,
                    [
                        self.day_features['device_removal_plot'].tolist(),
                        self.day_features['signal_processing_plot'].tolist()
                    ],
                    worksheet_name='Day Plots',
                    plot_header_text='',
                    missing_plot_path_text='No Plot Available'
                ) 