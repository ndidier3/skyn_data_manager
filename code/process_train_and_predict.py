from skyn_processors.skyn_data_manager import skynDataManager
from utils.Reporting.export import *
import tkinter
from tkinter import messagebox
import traceback

#import params information needed for processing
from params import *

#Constant Parameters (do not modify unless certain)
data_out = f'processed_data_and_plots/data_{cohort_name}'
graphs_out = f'processed_data_and_plots/tac_curves_{cohort_name}'
analyses_out = 'features_and_model_results/'
original = load('04.19.2023', 'skyn_original_model')
built_in_models = original.models
repeat_signal_processing = False
date_of_processing = 'dd.mm.yyyy'

#~~~~~~~~~~~~~~~~~~~ THE PROCEDURE ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

root = tkinter.Tk()
root.withdraw()
run_procedure = messagebox.askyesno("Skyn Data Manager", "Would you like to process/clean a cohort of Skyn data, generate features, build new model, and test model using cross validation?")

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
        subid_search=subid_search_character,
        subid_range=subid_search_length, 
        condition_search=condition_search_character, 
        condition_range=condition_search_length,
        sub_condition_search=sub_condition_search_character,
        sub_condition_range=sub_condition_search_length,
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
