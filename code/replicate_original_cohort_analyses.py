from skyn_processors.skyn_data_manager import skynDataManager
from utils.Reporting.export import *
import tkinter
from tkinter import messagebox
import traceback

#SUMMARY: Replicate signal processing and model testing described in Didier et al., under review. 

#setup parameters (do not change)
data_in = 'raw/MARS/'
data_out = 'processed_data_and_plots/data/'
graphs_out = 'processed_data_and_plots/tac_curves'
analyses_out = 'features_and_model_results/'
metadata = 'resources/MARS_original_testing/Skyn MARS Quality Assessment.xlsx'
timestamps = 'resources/MARS_original_testing/Timestamps MARS.xlsx'
max_episode_duration = 18
subid_search = '#'
subid_range = 4
condition_search = '.'
condition_range = -3
cohort_name = 'MARS'

#Do you want to re-run signal cleaning for each dataset? This takes 15+ minutes.
repeat_signal_processing = False #If False, model training and testing with still be conducted

#~~~~~~~~~~~~~~~~~~~ THE PROCEDURE ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

root = tkinter.Tk()
root.withdraw()
run_procedure = messagebox.askyesno("Skyn Data Manager", "Would you like to replicate the results of the original Skyn cohort? Note: The cohort name is MARS.")

if run_procedure:
  try:
    if repeat_signal_processing:
      #create skyn data manager
      skyn_dataset = skynDataManager(
        data_in,
        cohort_name, 
        data_out,
        graphs_out,
        analyses_out,
        subid_search=subid_search,
        subid_range=subid_range, 
        condition_search=condition_search, 
        condition_range=condition_range,
        metadata_path=metadata,
        episode_start_timestamps_path=timestamps,
        max_episode_duration=max_episode_duration
      )
      #signal processing on all datasets
      skyn_dataset.load_bulk_skyn_occasions(make_plots=True, export_python_object=True)

    else:
      skyn_dataset = load('04.20.2023', cohort_name)

    #train models and run cross validation
    skyn_dataset.run_analyses()

    #create excel workbook report
    skyn_dataset.create_report()

    root = tkinter.Tk()
    root.withdraw()
    messagebox.showinfo("Skyn Data Manager", "Signal Processing and Model Predictions: Complete.")
    
  except Exception:
    print(traceback.format_exc())
    root = tkinter.Tk()
    root.withdraw()
    messagebox.showerror('Skyn Data Manager Error', traceback.format_exc())

