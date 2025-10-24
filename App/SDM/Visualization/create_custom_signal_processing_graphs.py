#!/usr/bin/env python3
"""
Custom Curve Graph Generator
Creates curve graphs with larger fonts, better legends, and no subject IDs for publication/presentation purposes.
Takes a subject ID as a command line argument.
"""

import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib
matplotlib.use("Agg")

# Add the project root to the path to import modules
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, project_root)

from App.SDM.Configuration.file_management import load, create_individual_plot_folder, extract_subid, extract_dataset_identifier
from App.SDM.Visualization.plotting_utils import plot_event_lines


def plot_signal_processing_custom(df, plot_path, dataset_identifier, event_number, df_version, 
                                 curve_threshold, time_variable='datetime', title='Signal Processing', 
                                 event_timestamps={}, subtitle_text='', show_imputations=True, show_event_annotations=True):
    """
    Custom version of plot_signal_processing with larger fonts and no subject ID.
    """
    passed = df.loc[(df['imp_cand']==0)]
    gap = df.loc[df['gap'] == 1]
    non_wear = df.loc[(df['non_wear'] == 1)]
    jumps = df.loc[(df['jump_imp_cand'] == 1)]
    plummet = df.loc[(df['plummet_imp_cand'] == 1)]
    extreme_negative = df.loc[(df['extreme_negative_imp_cand'] == 1)]
    proximal_low_quality = df.loc[(df['proximal_low_quality_imp_cand'] == 1)]

    fig, ax = plt.subplots(figsize=(20, 10))  # Larger figure size
    
    # Smoothed Final TAC
    ax.plot(df[time_variable], df['TAC' if show_imputations else 'TAC_pre_imputation'], 
            label="TAC (Processed)", alpha=0.5, color="black", linewidth=3)
    
    # Passed (high quality values)
    ax.scatter(passed[time_variable], passed['TAC_pre_imputation'], label='Passed', 
               color='darkblue', marker='.', alpha=1.0, s=30)
    
    # Non Wear
    if not non_wear.empty:
        ax.scatter(non_wear[time_variable], non_wear['TAC_pre_imputation'], label='Non-Wear', 
                   color='lightpink', marker='x', alpha=0.7, s=30)
    
    # Extreme Negative
    if not extreme_negative.empty:
        ax.scatter(extreme_negative[time_variable], extreme_negative['TAC_pre_imputation'], 
                   label='Extreme Negative', color='lightsteelblue', marker='*', alpha=0.7, s=30)
    
    # Jumps
    if not jumps.empty:
        ax.scatter(jumps[time_variable], jumps['TAC_pre_imputation'], label='Jump', 
                   color='lightblue', marker='^', alpha=0.7, s=30)
    
    # Plummet
    if not plummet.empty:
        ax.scatter(plummet[time_variable], plummet['TAC_pre_imputation'], label='Plummet', 
                   color='thistle', marker='v', alpha=0.7, s=30)
    
    # Between low quality
    if not proximal_low_quality.empty:
        ax.scatter(proximal_low_quality[time_variable], proximal_low_quality['TAC_pre_imputation'],
                   label='Proximal Low Quality', color='gray', marker='s', alpha=0.7, s=30)
    
    # Imputed data
    if show_imputations:
        gap_imputed = df.loc[df['gap_imputed'] == 1]
        non_wear_imputed = df.loc[(df['non_wear_imputed'] == 1)]
        extreme_negative_imputed = df.loc[(df['extreme_negative_imputed'] == 1)]
        jump_imputed = df.loc[df['jump_imputed'] == 1]
        plummet_imputed = df.loc[df['plummet_imputed'] == 1]
        proximal_low_quality_imputed = df.loc[df['proximal_low_quality_imputed'] == 1]
        
        if not gap_imputed.empty:
            ax.scatter(gap_imputed[time_variable], gap_imputed['TAC_pre_savgol'], 
                       label='Imputed Gap', marker='o', alpha=1.0, facecolor='gray', 
                       edgecolors="black", s=30)
        if not non_wear_imputed.empty:
            ax.scatter(non_wear_imputed[time_variable], non_wear_imputed['TAC_pre_savgol'], 
                       label='Imputed Non-Wear', facecolor='lightpink', edgecolors="darkred", 
                       marker='o', alpha=1.0, s=30)
        if not extreme_negative_imputed.empty:
            ax.scatter(extreme_negative_imputed[time_variable], extreme_negative_imputed['TAC_pre_savgol'], 
                       label='Imputed Extreme Negative', facecolor='lightsteelblue', 
                       edgecolors="purple", marker='o', alpha=1.0, s=30)
        if not jump_imputed.empty:
            ax.scatter(jump_imputed[time_variable], jump_imputed['TAC_pre_savgol'], 
                       label='Imputed Jump', facecolor='lightblue', edgecolors="darkblue", 
                       marker='o', alpha=1.0, s=30)
        if not plummet_imputed.empty:
            ax.scatter(plummet_imputed[time_variable], plummet_imputed['TAC_pre_savgol'], 
                       label='Imputed Plummet', facecolor='thistle', edgecolors="purple", 
                       marker='o', alpha=1.0, s=30)
        if not proximal_low_quality_imputed.empty:
            ax.scatter(proximal_low_quality_imputed[time_variable], proximal_low_quality_imputed['TAC_pre_savgol'],
                       label='Imputed Proximal Low Quality', facecolor='gray', 
                       edgecolors="darkgreen", marker='o', alpha=1.0, s=30)
    
    # Plot threshold line
    ax.hlines(curve_threshold, xmin=df['datetime'].min(), xmax=df['datetime'].max(), 
              colors='black', linestyle='--', linewidth=2, label="Curve Threshold")

    # Plot event timestamps if available with custom line positioning
    if show_event_annotations and event_timestamps and all(value is not None for value in event_timestamps.values()):
        # Filter out drinking events before processing
        filtered_events = {k: v for k, v in event_timestamps.items() 
                          if 'drinkStart' not in k and 'drinkFinish' not in k}
        
        if filtered_events:
            # Custom event lines that end where text begins
            text_start = 0
            font_size = 19
            y_start = 0.6
            
            for i, (event, timestamp) in enumerate(filtered_events.items()):
                if pd.notna(timestamp) and timestamp != None:
                    from App.SDM.Configuration.configuration import get_closest_index_after_timestamp
                    idx = get_closest_index_after_timestamp(df, timestamp, 'datetime')
                    
                    # Calculate text position
                    text_y_pos = ax.get_ylim()[1] * y_start * (0.95 - text_start)
                    
                    # Draw line from 0 to where text begins
                    ax.vlines(df.loc[idx, 'datetime'], 0, text_y_pos, linestyles="dashed", linewidth=1.5)
                    
                    # Add text for curve start/end and other non-drinking events
                    display_text = event
                    ax.text(df.loc[idx, 'datetime'], text_y_pos, display_text, fontsize=font_size, fontstyle="italic")
                    
                    i += 1
                    if i > 0:
                        text_start += 0.07
                    elif i > 4:
                        text_start -= 0.07
                    elif i > 8:
                        text_start += 0.07
                    elif i > 12:
                        text_start -= 0.07
                    elif i > 16:
                        text_start += 0.07
                    elif i > 20:
                        text_start -= 0.07

    # Format the x-axis for time
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%I:%M %p'))

    # Larger fonts with bold styling
    ax.set_ylabel('TAC', fontsize=36, fontweight='bold')
    ax.set_title(title, fontsize=44, fontweight="bold", pad=40)
    ax.tick_params(axis='x', labelsize=20)
    ax.tick_params(axis='y', labelsize=30)
    
    # Improved legend layout - single column positioned in top right of graph area
    ax.legend(loc='upper right', bbox_to_anchor=(1.02, 1.15), ncol=1, 
              frameon=True, framealpha=0.95, edgecolor='black', facecolor='white', 
              fontsize=20, markerscale=1.5)

    # Custom subtitle without subject ID
    if subtitle_text:
        # Remove SubID information from subtitle using regex
        import re
        custom_subtitle = re.sub(r'SubID: \d+ --? ', '', subtitle_text)
        ax.text(0.5, 1.025, custom_subtitle, fontsize=18, style='italic',
                ha='center', va='center', transform=ax.transAxes)
    
    # Save the figure
    df_version = df_version if show_imputations else f'{df_version}_raw'
    path = f'{plot_path}{event_number}_TAC_processing_{df_version}_custom.png'
    plt.tight_layout()
    plt.savefig(path, bbox_inches='tight', dpi=300)
    plt.close('all')
    
    return path


def create_custom_signal_processing_graphs(data_path, show_event_annotations=True):
    """
    Main function to load subject data and create custom signal processing graphs.
    
    Args:
        data_path (str): Full path to the processed data file (.sdp.sdm)
        show_event_annotations (bool): Whether to show event start/end annotations
    """
    if not os.path.exists(data_path):
        print(f"Data file not found: {data_path}")
        return
    
    if not data_path.endswith('.sdp.sdm'):
        print(f"File must be a .sdp.sdm file: {data_path}")
        return
    
    # Extract subject ID and dataset identifier from filename using file_management functions
    filename = os.path.basename(data_path)
    subid = extract_subid(filename)
    dataset_identifier = extract_dataset_identifier(filename, validate=False)
    
    if not subid or not dataset_identifier:
        print(f"Could not extract valid subject ID or dataset identifier from filename: {filename}")
        print(f"Expected format: SUBID_DATASET_skyn_data_processed.sdp.sdm")
        return
    
    print(f"Loading processed data from: {data_path}")
    print(f"Subject ID: {subid}, Dataset: {dataset_identifier}")
    
    # Define paths
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    custom_graphs_folder = os.path.join(project_root, f'Custom_Signal_Processing_Graphs_{subid}_{dataset_identifier}')
    
    # Create custom graphs folder
    os.makedirs(custom_graphs_folder, exist_ok=True)
    
    try:
        print(f"Loading dataset {dataset_identifier}...")
        
        # Load the processed skynDataset
        dataset_name = f'{subid}_{dataset_identifier}_skyn_data_processed.sdp'
        skyn_dataset = load(dataset_name, os.path.dirname(data_path))
        
        # Create custom plot folder for this dataset
        custom_plot_folder = os.path.join(custom_graphs_folder, f'{subid}_{dataset_identifier}')
        os.makedirs(custom_plot_folder, exist_ok=True)
        custom_plot_folder = custom_plot_folder + '/'  # Ensure trailing slash
        
        print(f"Creating custom signal processing graphs for dataset {dataset_identifier}...")
        
        # Generate signal processing plots for each curve
        for i, curve in enumerate(skyn_dataset.curves):
            print(f"  Processing curve {i}...")
            
            # Create custom subtitle with date and drink count
            date = curve.curve.iloc[0]['datetime'].strftime('%B %d, %Y')
            
            # Extract drink count from event annotations
            drink_count = None
            for event_name in curve.curve_plot_annotations.keys():
                if 'drinkFinish' in event_name and 'drks' in event_name:
                    # Extract number from string like "drinkFinish_2_1_5.0drks"
                    try:
                        drink_count = event_name.split('_')[-1].replace('drks', '')
                        break
                    except:
                        pass
            
            if drink_count:
                custom_subtitle = f"{date} -- {drink_count} Drinks"
            else:
                custom_subtitle = date
            
            # Generate custom signal processing plot
            signal_processing_plot = plot_signal_processing_custom(
                curve.region, custom_plot_folder, dataset_identifier, curve.curve_id, 'CURVE',
                curve.curve_threshold, time_variable='datetime', title='Signal Processing',
                event_timestamps=curve.curve_plot_annotations,
                subtitle_text=custom_subtitle,
                show_imputations=curve.TAC_column != 'TAC_pre_imputation',
                show_event_annotations=show_event_annotations
            )
            
            print(f"    Generated: {os.path.basename(signal_processing_plot)}")
        
        print(f"Completed signal processing graphs for dataset {dataset_identifier}")
        
    except Exception as e:
        print(f"Error processing dataset {dataset_identifier}: {str(e)}")
        return
    
    print(f"\nCustom signal processing graphs completed! Check the folder: {custom_graphs_folder}")


if __name__ == "__main__":
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: python create_custom_signal_processing_graphs.py <data_path> [--no-events]")
        print("Example: python create_custom_signal_processing_graphs.py Inputs/Skyn_Data_PROCESSED/ARC/Burst1/1018_001_skyn_data_processed.sdp.sdm")
        print("Example: python create_custom_signal_processing_graphs.py Inputs/Skyn_Data_PROCESSED/ARC/Burst1/1018_001_skyn_data_processed.sdp.sdm --no-events")
        sys.exit(1)
    
    data_path = sys.argv[1]
    show_event_annotations = True
    
    if len(sys.argv) == 3 and sys.argv[2] == "--no-events":
        show_event_annotations = False
        print("Event annotations will be excluded from the graphs.")
    else:
        print("Event annotations will be included in the graphs.")
    
    create_custom_signal_processing_graphs(data_path, show_event_annotations)
