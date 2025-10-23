from App.SDM.Skyn_Processors.skyn_dataset import skynDataset
from App.SDM.Configuration.file_management import extract_dataset_identifier, extract_subid
from App.SDM.Configuration.file_management import save_to_computer, create_save_directories, load, create_individual_plot_folder
from App.SDM.Documenting.embed_graphs import embed_graphs_into_workbook_tab
import traceback
from datetime import date
import pandas as pd
import os

def process_and_analyze_single_subject(
    project_root,
    data_input_folder,
    subid,
    output_folder_name='single_subject',
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
    event_attrs={}
):
    """
    Process and analyze data for a single subject.
    
    Args:
        project_root (str): Root directory of the project
        data_input_folder (str): Directory containing the input data files
        subid (str): Subject ID to process
        output_folder_name (str): Name of the output folder
        event_data (pd.DataFrame): DataFrame containing event data
        event_subid_column (str): Column name containing subject IDs in event_data
        use_prior_save (bool): Whether to use previously saved processed data
        smooth_and_impute (bool): Whether to smooth and impute data
        adjust_for_gaps_and_non_wear (bool): Whether to adjust for gaps and non-wear
        analyze_days (bool): Whether to perform day-level analysis
        identify_curves (bool): Whether to identify curves
        match_events_to_curves (bool): Whether to match events to curves
        gaps_and_non_wear_attrs (dict): Attributes for gaps and non-wear adjustment
        smooth_and_impute_attrs (dict): Attributes for smoothing and imputation
        curve_attrs (dict): Attributes for curve identification
        day_attrs (dict): Attributes for day-level analysis
        event_attrs (dict): Attributes for event-level analysis
    """
    
    """ CREATE SAVE DIRECTORIES """
    processed_data_out = data_input_folder.replace('_RAW', '_PROCESSED')
    results_dir = f'{project_root}/Results/{output_folder_name}/{date.today().strftime("%m.%d.%Y")}'
    data_out = f'{results_dir}/Datasets'
    graphs_out = f'{results_dir}/Plots'
    analyses_out = f'{results_dir}/Model_Performance'
    create_save_directories(project_root, processed_data_out, output_folder_name, data_out, graphs_out, analyses_out)

    """ Find the file for the specified subject """
    files = [os.path.join(data_input_folder, file) for file in os.listdir(data_input_folder)]
    subject_files = [f for f in files if str(subid) in os.path.basename(f)]
    
    if not subject_files:
        print(f"No files found for subject {subid}")
        return
        
    file = subject_files[0]  # Take the first matching file
    
    try:
        print(f"\nProcessing file for subject {subid}")
        dataset_identifier = extract_dataset_identifier(os.path.basename(file))
        print(f"Dataset identifier: {dataset_identifier}")
        
        if dataset_identifier == '':
            print(f"Warning: Empty dataset identifier for file: {file}")
            return
        
        if not os.path.isfile(file):
            print(f"Error: Invalid file path: {file}")
            return
            
        sdm_processor = None
        prior_processor_loaded = False
        
        if use_prior_save:
            try:
                print(f"Attempting to load prior save for {subid}_{dataset_identifier}")
                sdm_processor = load(f'{subid}_{dataset_identifier}_skyn_data_processed.sdp', processed_data_out)
                sdm_processor.data_out_folder = data_out
                sdm_processor.plot_folder = create_individual_plot_folder(graphs_out, subid)
                prior_processor_loaded = True
                print(f"Successfully loaded prior save for {subid}_{dataset_identifier}")
            except Exception as e:
                print(f"Failed to load prior save for {subid}_{dataset_identifier}: {str(e)}")
                return

        if not prior_processor_loaded:
            print(f"Creating new processor for {subid}_{dataset_identifier}")
            sdm_processor = skynDataset(str(file), processed_data_out, data_out, graphs_out, subid, dataset_identifier, 'e' + str(1))
        
        if adjust_for_gaps_and_non_wear:
            print(f"Adjusting for gaps and non-wear for {subid}_{dataset_identifier}")
            sdm_processor.adjust_for_gaps_and_non_wear(**gaps_and_non_wear_attrs)
            
        if smooth_and_impute:
            print(f"Smoothing and imputing for {subid}_{dataset_identifier}")
            sdm_processor.smooth_and_impute(**smooth_and_impute_attrs)
            
        if identify_curves:
            print(f"Identifying curves for {subid}_{dataset_identifier}")
            sdm_processor.identify_curves(curve_attrs=curve_attrs)
            if not match_events_to_curves:
                print(f"Making curve graphs for {subid}_{dataset_identifier}")
                sdm_processor.make_curve_graphs()
                sdm_processor.curve_features.to_excel(f'{results_dir}/curve_features_{subid}.xlsx', index=None)
                
        if analyze_days:
            print(f"Running day analysis for {subid}_{dataset_identifier}")
            sdm_processor.run_day_level_analysis(**day_attrs)
            if not sdm_processor.day_level_data.empty:
                print(f"Found day data with shape: {sdm_processor.day_level_data.shape}")
                sdm_processor.day_level_data.to_excel(f'{results_dir}/day_level_results_{subid}.xlsx', index=None)
            else:
                print(f"WARNING: No day data found for {subid}_{dataset_identifier}")
                
        if match_events_to_curves:
            print(f"Configuring event data for {subid}_{dataset_identifier}")
            sdm_processor.configure_event_data(**event_attrs)
            print(f"Making curve graphs for {subid}_{dataset_identifier}")
            sdm_processor.make_curve_graphs()
            print(f"Setting EMA regions for {subid}_{dataset_identifier}")
            sdm_processor.set_ema_regions()
            sdm_processor.curve_features.to_excel(f'{results_dir}/curve_features_{subid}.xlsx', index=None)
                
    except Exception as e:
        print(f"\nError processing file {file}:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print("Full traceback:")
        print(traceback.format_exc())
        print("\n") 