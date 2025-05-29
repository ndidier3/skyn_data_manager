"""
Skyn Data Manager (SDM) - Main Orchestrator

This module contains the main SDM class that orchestrates the entire data processing and analysis pipeline.
It manages the workflow of processing raw Skyn data, performing analyses, and generating reports.
"""

from App.SDM.Skyn_Processors.skyn_dataset import skynDataset
from App.SDM.Analysis.curveFeatures import curveFeatures
from App.SDM.Analysis.curveFeaturesWithEvents import curveFeaturesWithEvents
from App.SDM.Configuration.file_management import (
    extract_dataset_identifier, 
    extract_subid,
    save_to_computer, 
    create_save_directories, 
    load, 
    create_individual_plot_folder
)
from App.SDM.Documenting.embed_graphs import embed_graphs_into_workbook_tab
import traceback
from datetime import date, datetime
import pandas as pd
import os

class SDM:
    """
    Skyn Data Manager (SDM) - Main orchestrator class for processing and analyzing Skyn data.
    
    This class manages the entire workflow of:
    1. Processing raw Skyn data files
    2. Performing various analyses (curve features, day-level analysis, etc.)
    3. Generating reports and visualizations
    4. Tracking processing status and errors
    
    The class maintains state about the processing workflow, including:
    - Processing status for each step
    - Error logs
    - Processing settings
    - Results and outputs
    """
    
    def __init__(self, project_root, data_input_folder, output_folder_name='cohort'):
        """
        Initialize the SDM workflow.
        
        Args:
            project_root (str): Root directory of the project
            data_input_folder (str): Path to input data folder
            output_folder_name (str): Name for output folder
        """
        self.project_root = project_root
        self.data_input_folder = data_input_folder
        self.output_folder_name = output_folder_name
        
        # Set up directory structure
        self.processed_data_out = data_input_folder.replace('_RAW', '_PROCESSED')
        self.results_dir = f'{project_root}/Results/{output_folder_name}/{date.today().strftime("%m.%d.%Y")}'
        self.data_out = f'{self.results_dir}/Datasets'
        self.graphs_out = f'{self.results_dir}/Plots'
        self.analyses_out = f'{self.results_dir}/Model_Performance'
        
        # Create directories
        create_save_directories(
            project_root, 
            self.processed_data_out, 
            output_folder_name, 
            self.data_out, 
            self.graphs_out, 
            self.analyses_out
        )
        
        # Initialize storage for results
        self.processors = []
        self.day_datasets = []
        self.curve_features = []
        self.event_datasets = []
        self.event_curve_matches = []
        self.no_skyn_data_found = []

        # Initialize settings storage
        self.gaps_and_non_wear_attrs = {}
        self.smooth_and_impute_attrs = {}
        self.curve_attrs = {}
        self.day_attrs = {}
        self.event_attrs = {}

        # Initialize status tracking with nested dictionaries
        self.status = {}  # Will store status for each subject-dataset pair
        
        # Initialize error storage with nested dictionaries
        self.errors = {}  # Will store errors for each subject-dataset pair

    def _get_subject_dataset_key(self, subid, dataset_identifier):
        """Helper method to create a consistent key for subject-dataset pairs."""
        return f"{subid}_{dataset_identifier}"

    def _initialize_subject_dataset_status(self, subid, dataset_identifier):
        """Initialize status and error tracking for a new subject-dataset pair."""
        key = self._get_subject_dataset_key(subid, dataset_identifier)
        if key not in self.status:
            self.status[key] = {
                'gaps_and_non_wear': 'not_attempted',
                'smooth_and_impute': 'not_attempted',
                'identify_curves': 'not_attempted',
                'analyze_days': 'not_attempted',
                'match_events': 'not_attempted',
                'analyze_curves': 'not_attempted',
                'export_results': 'not_attempted'
            }
            self.errors[key] = {
                'gaps_and_non_wear': [],
                'smooth_and_impute': [],
                'identify_curves': [],
                'analyze_days': [],
                'match_events': [],
                'analyze_curves': [],
                'export_results': []
            }

    def process_data(self, 
                    use_prior_save=True,
                    smooth_and_impute=False,
                    adjust_for_gaps_and_non_wear=False,
                    analyze_days=False,
                    identify_curves=False,
                    match_events_to_curves=False,
                    gaps_and_non_wear_attrs={},
                    smooth_and_impute_attrs={},
                    curve_attrs={},
                    day_attrs={'day_start_hour': 0, 'make_graphs': True},
                    event_attrs={}):
        """
        Process raw data files through the SDM pipeline.
        
        Args:
            use_prior_save (bool): Whether to use previously saved processed data
            smooth_and_impute (bool): Whether to smooth and impute data
            adjust_for_gaps_and_non_wear (bool): Whether to adjust for gaps and non-wear
            analyze_days (bool): Whether to perform day-level analysis
            identify_curves (bool): Whether to identify curves
            match_events_to_curves (bool): Whether to match events to curves
            gaps_and_non_wear_attrs (dict): Attributes for gap and non-wear processing
            smooth_and_impute_attrs (dict): Attributes for smoothing and imputation
            curve_attrs (dict): Attributes for curve identification
            day_attrs (dict): Attributes for day-level analysis
            event_attrs (dict): Attributes for event matching
        """
        # Store settings
        self.gaps_and_non_wear_attrs = gaps_and_non_wear_attrs
        self.smooth_and_impute_attrs = smooth_and_impute_attrs
        self.curve_attrs = curve_attrs
        self.day_attrs = day_attrs
        self.event_attrs = event_attrs

        files = [os.path.join(self.data_input_folder, file) for file in os.listdir(self.data_input_folder)]
        
        for file in files:
            try:
                subid = extract_subid(os.path.basename(file))
                print(f"\nProcessing file for subject {subid}")
                dataset_identifier = extract_dataset_identifier(os.path.basename(file))
                print(f"Dataset identifier: {dataset_identifier}")
                
                if dataset_identifier == '':
                    print(f"Warning: Empty dataset identifier for file: {file}")
                    continue
                
                if not os.path.isfile(file):
                    print(f"Error: Invalid file path: {file}")
                    continue
                    
                sdm_processor = None
                prior_processor_loaded = False
                
                if use_prior_save:
                    try:
                        print(f"Attempting to load prior save for {subid}_{dataset_identifier}")
                        sdm_processor = load(f'{subid}_{dataset_identifier}_skyn_data_processed.sdp', self.processed_data_out)
                        sdm_processor.data_out_folder = self.data_out
                        sdm_processor.plot_folder = create_individual_plot_folder(self.graphs_out, subid)
                        prior_processor_loaded = True
                        print(f"Successfully loaded prior save for {subid}_{dataset_identifier}")
                    except Exception as e:
                        error_msg = f"Failed to load prior save for {subid}_{dataset_identifier}: {str(e)}"
                        print(error_msg)
                        self.errors['gaps_and_non_wear'].append(error_msg)
                        continue

                if not prior_processor_loaded:
                    print(f"Creating new processor for {subid}_{dataset_identifier}")
                    sdm_processor = skynDataset(str(file), self.processed_data_out, self.data_out, self.graphs_out, subid, dataset_identifier, 'e' + str(1))
                
                if adjust_for_gaps_and_non_wear:
                    try:
                        print(f"Adjusting for gaps and non-wear for {subid}_{dataset_identifier}")
                        sdm_processor.adjust_for_gaps_and_non_wear(**self.gaps_and_non_wear_attrs)
                        self.status['gaps_and_non_wear'] = 'success'
                    except Exception as e:
                        error_msg = f"Error adjusting gaps and non-wear for {subid}_{dataset_identifier}: {str(e)}"
                        print(error_msg)
                        self.errors['gaps_and_non_wear'].append(error_msg)
                        self.status['gaps_and_non_wear'] = 'failed'
                    
                if smooth_and_impute:
                    try:
                        print(f"Smoothing and imputing for {subid}_{dataset_identifier}")
                        sdm_processor.smooth_and_impute(**self.smooth_and_impute_attrs)
                        self.status['smooth_and_impute'] = 'success'
                    except Exception as e:
                        error_msg = f"Error smoothing and imputing for {subid}_{dataset_identifier}: {str(e)}"
                        print(error_msg)
                        self.errors['smooth_and_impute'].append(error_msg)
                        self.status['smooth_and_impute'] = 'failed'
                    
                if identify_curves:
                    try:
                        print(f"Identifying curves for {subid}_{dataset_identifier}")
                        sdm_processor.identify_curves(curve_attrs=self.curve_attrs)
                        if not match_events_to_curves:
                            print(f"Making curve graphs for {subid}_{dataset_identifier}")
                            sdm_processor.make_curve_graphs()
                            self.curve_features.append(sdm_processor.curve_features)
                        self.status['identify_curves'] = 'success'
                    except Exception as e:
                        error_msg = f"Error identifying curves for {subid}_{dataset_identifier}: {str(e)}"
                        print(error_msg)
                        self.errors['identify_curves'].append(error_msg)
                        self.status['identify_curves'] = 'failed'
                        
                if analyze_days:
                    try:
                        print(f"Running day analysis for {subid}_{dataset_identifier}")
                        sdm_processor.run_day_level_analysis(**self.day_attrs)
                        if not sdm_processor.day_level_data.empty:
                            print(f"Found day data with shape: {sdm_processor.day_level_data.shape}")
                            self.day_datasets.append(sdm_processor.day_level_data)
                            self.status['analyze_days'] = 'success'
                        else:
                            error_msg = f"WARNING: No day data found for {subid}_{dataset_identifier}"
                            print(error_msg)
                            self.errors['analyze_days'].append(error_msg)
                            self.status['analyze_days'] = 'failed'
                    except Exception as e:
                        error_msg = f"Error running day analysis for {subid}_{dataset_identifier}: {str(e)}"
                        print(error_msg)
                        self.errors['analyze_days'].append(error_msg)
                        self.status['analyze_days'] = 'failed'
                        
                if match_events_to_curves:
                    try:
                        print(f"Configuring event data for {subid}_{dataset_identifier}")
                        sdm_processor.configure_event_data(**self.event_attrs)
                        print(f"Making curve graphs for {subid}_{dataset_identifier}")
                        sdm_processor.make_curve_graphs()
                        print(f"Setting EMA regions for {subid}_{dataset_identifier}")
                        sdm_processor.set_ema_regions()
                        self.curve_features.append(sdm_processor.curve_features)
                        self.event_datasets.append(sdm_processor.events)
                        self.status['match_events'] = 'success'
                    except Exception as e:
                        error_msg = f"Error matching events for {subid}_{dataset_identifier}: {str(e)}"
                        print(error_msg)
                        self.errors['match_events'].append(error_msg)
                        self.status['match_events'] = 'failed'
                
                self.processors.append(sdm_processor)
                    
            except Exception as e:
                error_msg = f"\nError processing file {file}:\nError type: {type(e).__name__}\nError message: {str(e)}\nFull traceback:\n{traceback.format_exc()}"
                print(error_msg)
                self.errors['gaps_and_non_wear'].append(error_msg)
                print("\n")

    def analyze_curves(self, include_events=False, event_attrs=None, day_attrs=None):
        """
        Run curve features analysis on processed data.
        
        Args:
            include_events (bool): Whether to include event analysis
            event_attrs (dict): Attributes for event analysis
            day_attrs (dict): Attributes for day-level analysis
        """
        try:
            # Update event and day attrs if provided
            if event_attrs:
                self.event_attrs.update(event_attrs)
            if day_attrs:
                self.day_attrs.update(day_attrs)

            if include_events:
                analyzer = curveFeaturesWithEvents(
                    self.processed_data_out,
                    smooth_and_impute_attrs=self.smooth_and_impute_attrs,
                    curve_attrs=self.curve_attrs,
                    event_attrs=self.event_attrs,
                    day_attrs=self.day_attrs
                )
                analyzer.run_event_stats()
                analyzer.export_workbook_events_and_curves(
                    f'{self.analyses_out}/curve_features_with_events.xlsx',
                    smooth_and_impute_attrs=self.smooth_and_impute_attrs,
                    curve_attrs=self.curve_attrs,
                    event_attrs=self.event_attrs,
                    day_attrs=self.day_attrs
                )
            else:
                analyzer = curveFeatures(
                    self.processed_data_out,
                    smooth_and_impute_attrs=self.smooth_and_impute_attrs,
                    curve_attrs=self.curve_attrs
                )
                analyzer.run_stats()
                analyzer.export_workbook_curves(
                    f'{self.analyses_out}/curve_features.xlsx',
                    include_plots=True,
                    export_imputations=True
                )
            self.status['analyze_curves'] = 'success'
        except Exception as e:
            error_msg = f"Error analyzing curves: {str(e)}"
            print(error_msg)
            self.errors['analyze_curves'].append(error_msg)
            self.status['analyze_curves'] = 'failed'

    def export_results(self):
        """Export all processed results to appropriate files."""
        try:
            if len(self.day_datasets):
                print(f'Combining {len(self.day_datasets)} day datasets')
                combined_day_level_data = pd.concat(self.day_datasets, ignore_index=True)
                print(f'Combined day data shape: {combined_day_level_data.shape}')
                combined_day_level_data.to_excel(f'{self.results_dir}/day_level_results.xlsx', index=None)
            else:
                print('WARNING: No day datasets to combine')

            if len(self.curve_features):
                print(f'Combining {len(self.curve_features)} curve feature datasets')
                with pd.ExcelWriter(f'{self.results_dir}/curve_level_results.xlsx', engine='xlsxwriter', mode='w') as writer:
                    combined_curve_features = pd.concat(self.curve_features, ignore_index=True)
                    combined_curve_features.to_excel(writer, index=None, sheet_name="Features")
                    print(f'Combined curve features shape: {combined_curve_features.shape}')
            
            if len(self.event_curve_matches):
                print(f'Combining {len(self.event_curve_matches)} event curve match datasets')
                with pd.ExcelWriter(f'{self.results_dir}/curve_level_results.xlsx', engine='xlsxwriter', mode='w') as writer:
                    combined_curve_features = pd.concat(self.curve_features, ignore_index=True)
                    combined_curve_features.to_excel(writer, index=None, sheet_name="Features")
                    print(f'Combined event curve matches shape: {combined_curve_features.shape}')
                    
            with pd.ExcelWriter(f'{self.results_dir}/event_level_results.xlsx', engine='xlsxwriter') as writer:
                if len(self.event_datasets):
                    print(f'Combining {len(self.event_datasets)} event datasets')
                    combined_event_level_datasets = pd.concat(self.event_datasets, ignore_index=True)
                    combined_event_level_datasets.to_excel(writer, index=None, sheet_name='event-data')
                    print(f'Combined event data shape: {combined_event_level_datasets.shape}')
                if len(self.no_skyn_data_found):
                    print(f'Combining {len(self.no_skyn_data_found)} no-skyn-data datasets')
                    combined_no_skyn_data_events = pd.concat(self.no_skyn_data_found, ignore_index=True)
                    combined_no_skyn_data_events.to_excel(writer, index=None, sheet_name='no-skyn-data')
                    print(f'Combined no-skyn-data shape: {combined_no_skyn_data_events.shape}')
            self.status['export_results'] = 'success'
        except Exception as e:
            error_msg = f"Error exporting results: {str(e)}"
            print(error_msg)
            self.errors['export_results'].append(error_msg)
            self.status['export_results'] = 'failed'

    def get_status_report(self):
        """
        Get a comprehensive status report of the workflow.
        
        Returns:
            dict: Dictionary containing status and error information for each subject-dataset pair
        """
        summary = {
            'total_subject_datasets': len(self.status),
            'successful_steps': 0,
            'failed_steps': 0,
            'not_attempted_steps': 0,
            'total_errors': 0
        }
        
        for key, status_dict in self.status.items():
            for status in status_dict.values():
                if status == 'success':
                    summary['successful_steps'] += 1
                elif status == 'failed':
                    summary['failed_steps'] += 1
                else:
                    summary['not_attempted_steps'] += 1
            
            for errors in self.errors[key].values():
                summary['total_errors'] += len(errors)
        
        return {
            'status': self.status,
            'errors': self.errors,
            'summary': summary
        }

    def get_settings(self):
        """
        Get a dictionary of all current settings.
        
        Returns:
            dict: Dictionary containing all workflow settings
        """
        return {
            'gaps_and_non_wear_attrs': self.gaps_and_non_wear_attrs,
            'smooth_and_impute_attrs': self.smooth_and_impute_attrs,
            'curve_attrs': self.curve_attrs,
            'day_attrs': self.day_attrs,
            'event_attrs': self.event_attrs
        }

    def load_settings(self, settings_dict):
        """
        Load settings from a dictionary.
        
        Args:
            settings_dict (dict): Dictionary containing settings to load
        """
        if 'gaps_and_non_wear_attrs' in settings_dict:
            self.gaps_and_non_wear_attrs = settings_dict['gaps_and_non_wear_attrs']
        if 'smooth_and_impute_attrs' in settings_dict:
            self.smooth_and_impute_attrs = settings_dict['smooth_and_impute_attrs']
        if 'curve_attrs' in settings_dict:
            self.curve_attrs = settings_dict['curve_attrs']
        if 'day_attrs' in settings_dict:
            self.day_attrs = settings_dict['day_attrs']
        if 'event_attrs' in settings_dict:
            self.event_attrs = settings_dict['event_attrs']

    def process_single_subject(self,
                             subid,
                             event_data=pd.DataFrame(),
                             event_subid_column='ID',
                             use_prior_save=True,
                             smooth_and_impute=False,
                             adjust_for_gaps_and_non_wear=False,
                             analyze_days=False,
                             identify_curves=False,
                             match_events_to_curves=False,
                             gaps_and_non_wear_attrs={},
                             smooth_and_impute_attrs={},
                             curve_attrs={},
                             day_attrs={'day_start_hour': 0, 'make_graphs': True},
                             event_attrs={}):
        """
        Process and analyze data for a single subject.
        """
        # Store settings
        self.gaps_and_non_wear_attrs = gaps_and_non_wear_attrs
        self.smooth_and_impute_attrs = smooth_and_impute_attrs
        self.curve_attrs = curve_attrs
        self.day_attrs = day_attrs
        self.event_attrs = event_attrs

        # Find the file for the specified subject
        files = [os.path.join(self.data_input_folder, file) for file in os.listdir(self.data_input_folder)]
        subject_files = [f for f in files if str(subid) in os.path.basename(f)]
        
        if not subject_files:
            error_msg = f"No files found for subject {subid}"
            print(error_msg)
            return
            
        file = subject_files[0]  # Take the first matching file
        
        try:
            print(f"\nProcessing file for subject {subid}")
            dataset_identifier = extract_dataset_identifier(os.path.basename(file))
            print(f"Dataset identifier: {dataset_identifier}")
            
            if dataset_identifier == '':
                error_msg = f"Warning: Empty dataset identifier for file: {file}"
                print(error_msg)
                return
            
            if not os.path.isfile(file):
                error_msg = f"Error: Invalid file path: {file}"
                print(error_msg)
                return

            # Initialize status tracking for this subject-dataset pair
            self._initialize_subject_dataset_status(subid, dataset_identifier)
            key = self._get_subject_dataset_key(subid, dataset_identifier)
                
            sdm_processor = None
            prior_processor_loaded = False
            
            if use_prior_save:
                try:
                    print(f"Attempting to load prior save for {subid}_{dataset_identifier}")
                    sdm_processor = load(f'{subid}_{dataset_identifier}_skyn_data_processed.sdp', self.processed_data_out)
                    sdm_processor.data_out_folder = self.data_out
                    sdm_processor.plot_folder = create_individual_plot_folder(self.graphs_out, subid)
                    prior_processor_loaded = True
                    print(f"Successfully loaded prior save for {subid}_{dataset_identifier}")
                except Exception as e:
                    error_msg = f"Failed to load prior save for {subid}_{dataset_identifier}: {str(e)}"
                    print(error_msg)
                    self.errors[key]['gaps_and_non_wear'].append(error_msg)
                    return

            if not prior_processor_loaded:
                print(f"Creating new processor for {subid}_{dataset_identifier}")
                sdm_processor = skynDataset(str(file), self.processed_data_out, self.data_out, self.graphs_out, subid, dataset_identifier, 'e' + str(1))
            
            # Start with gaps and non-wear processing
            if adjust_for_gaps_and_non_wear:
                try:
                    print(f"Adjusting for gaps and non-wear for {subid}_{dataset_identifier}")
                    sdm_processor.adjust_for_gaps_and_non_wear(**self.gaps_and_non_wear_attrs)
                    self.status[key]['gaps_and_non_wear'] = 'success'
                    # Save initial state after gaps and non-wear processing
                    sdm_processor.save_self(valid=True)
                except Exception as e:
                    error_msg = f"Error adjusting gaps and non-wear for {subid}_{dataset_identifier}: {str(e)}"
                    print(error_msg)
                    self.errors[key]['gaps_and_non_wear'].append(error_msg)
                    self.status[key]['gaps_and_non_wear'] = 'failed'
                    return  # Stop processing if gaps and non-wear fails
            
            # Continue with other processing steps only if gaps and non-wear succeeded
            if self.status[key]['gaps_and_non_wear'] == 'success':
                if smooth_and_impute:
                    try:
                        print(f"Smoothing and imputing for {subid}_{dataset_identifier}")
                        sdm_processor.smooth_and_impute(**self.smooth_and_impute_attrs)
                        self.status[key]['smooth_and_impute'] = 'success'
                    except Exception as e:
                        error_msg = f"Error smoothing and imputing for {subid}_{dataset_identifier}: {str(e)}"
                        print(error_msg)
                        self.errors[key]['smooth_and_impute'].append(error_msg)
                        self.status[key]['smooth_and_impute'] = 'failed'
                
                if identify_curves:
                    try:
                        print(f"Identifying curves for {subid}_{dataset_identifier}")
                        sdm_processor.identify_curves(curve_attrs=self.curve_attrs)
                        if not match_events_to_curves:
                            print(f"Making curve graphs for {subid}_{dataset_identifier}")
                            sdm_processor.make_curve_graphs()
                            sdm_processor.curve_features.to_excel(f'{self.results_dir}/curve_features_{subid}.xlsx', index=None)
                            self.curve_features.append(sdm_processor.curve_features)
                        self.status[key]['identify_curves'] = 'success'
                    except Exception as e:
                        error_msg = f"Error identifying curves for {subid}_{dataset_identifier}: {str(e)}"
                        print(error_msg)
                        self.errors[key]['identify_curves'].append(error_msg)
                        self.status[key]['identify_curves'] = 'failed'
                    
                if analyze_days:
                    try:
                        print(f"Running day analysis for {subid}_{dataset_identifier}")
                        sdm_processor.run_day_level_analysis(**self.day_attrs)
                        if not sdm_processor.day_level_data.empty:
                            print(f"Found day data with shape: {sdm_processor.day_level_data.shape}")
                            sdm_processor.day_level_data.to_excel(f'{self.results_dir}/day_level_results_{subid}.xlsx', index=None)
                            self.day_datasets.append(sdm_processor.day_level_data)
                            self.status[key]['analyze_days'] = 'success'
                        else:
                            error_msg = f"WARNING: No day data found for {subid}_{dataset_identifier}"
                            print(error_msg)
                            self.errors[key]['analyze_days'].append(error_msg)
                            self.status[key]['analyze_days'] = 'failed'
                    except Exception as e:
                        error_msg = f"Error running day analysis for {subid}_{dataset_identifier}: {str(e)}"
                        print(error_msg)
                        self.errors[key]['analyze_days'].append(error_msg)
                        self.status[key]['analyze_days'] = 'failed'
                    
                if match_events_to_curves:
                    try:
                        print(f"Configuring event data for {subid}_{dataset_identifier}")
                        sdm_processor.configure_event_data(**self.event_attrs)
                        print(f"Making curve graphs for {subid}_{dataset_identifier}")
                        sdm_processor.make_curve_graphs()
                        print(f"Setting EMA regions for {subid}_{dataset_identifier}")
                        sdm_processor.set_ema_regions()
                        sdm_processor.curve_features.to_excel(f'{self.results_dir}/curve_features_{subid}.xlsx', index=None)
                        self.curve_features.append(sdm_processor.curve_features)
                        self.event_datasets.append(sdm_processor.events)
                        self.status[key]['match_events'] = 'success'
                    except Exception as e:
                        error_msg = f"Error matching events for {subid}_{dataset_identifier}: {str(e)}"
                        print(error_msg)
                        self.errors[key]['match_events'].append(error_msg)
                        self.status[key]['match_events'] = 'failed'
            
            self.processors.append(sdm_processor)
            
            # Save final state after all processing
            self.save_self(valid=self.status[key]['gaps_and_non_wear'] == 'success')
                
        except Exception as e:
            error_msg = f"\nError processing file {file}:\nError type: {type(e).__name__}\nError message: {str(e)}\nFull traceback:\n{traceback.format_exc()}"
            print(error_msg)
            if 'key' in locals():
                self.errors[key]['gaps_and_non_wear'].append(error_msg)
            print("\n")
            # Save SDM state even if there was an error
            self.save_self(valid=False)

    def save_self(self, valid=True):
        """
        Save the current state of the SDM instance to a file.
        
        Args:
            valid (bool): Whether the current state is valid. If False, saves as invalid state.
        """
        try:
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f'sdm_state_{"valid" if valid else "invalid"}_{timestamp}.sdm'
            
            # Save to the results directory
            save_path = os.path.join(self.results_dir, filename)
            save_to_computer(self, filename, self.results_dir)
            
            print(f"SDM state saved to: {save_path}")
            
        except Exception as e:
            error_msg = f"Error saving SDM state: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            # Log error to the error logs folder
            error_log_path = os.path.join(self.results_dir, 'Error_Logs')
            os.makedirs(error_log_path, exist_ok=True)
            error_file = os.path.join(error_log_path, f'sdm_save_error_{timestamp}.txt')
            with open(error_file, 'w') as f:
                f.write(error_msg)

    @classmethod
    def load_prior_sdm(cls, filepath):
        """
        Load a previously saved SDM state.
        
        Args:
            filepath (str): Path to the saved SDM state file
            
        Returns:
            SDM: The loaded SDM instance, or None if loading failed
        """
        try:
            # Load and return the saved state directly
            loaded_sdm = load(filepath, os.path.dirname(filepath))
            print(f"Successfully loaded SDM state from: {filepath}")
            return loaded_sdm
            
        except Exception as e:
            error_msg = f"Error loading SDM state: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            # Log error to the error logs folder
            error_log_path = os.path.join(os.path.dirname(filepath), 'Error_Logs')
            os.makedirs(error_log_path, exist_ok=True)
            error_file = os.path.join(error_log_path, f'sdm_load_error_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.txt')
            with open(error_file, 'w') as f:
                f.write(error_msg)
            return None 