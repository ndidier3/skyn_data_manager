from skyn_processors.skyn_data_manager import skynDataManager
from utils.Reporting.export import *
import tkinter
from tkinter import messagebox
import traceback

#import params information needed for processing - MAKE SURE PARAMS.PY FILE IS UPDATED
from params import *

#Constant Parameters (do not modify unless certain)
data_out = f'processed_data_and_plots/data_{cohort_name}'
graphs_out = f'processed_data_and_plots/tac_curves_{cohort_name}'
analyses_out = 'features_and_model_results/'

#~~~~~~~~~~~~~~~~~~~ THE PROCEDURE ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

root = tkinter.Tk()
root.withdraw()
run_procedure = messagebox.askyesno("Skyn Data Manager", "Would you like to process/clean a cohort of Skyn data, generate features, build new model, and test model using cross validation?")

if run_procedure:
  try:
    if load_previous_processing:
      skyn_datasets = load(date_of_processing, cohort_name)
    else:
      #create skyn data manager
      skyn_datasets = skynDataManager(
        data_in,
        metadata_path=metadata,
        cohort_name = cohort_name,
        merge_variables = {},
        episode_start_timestamps_path=timestamps,
        data_out_folder=data_out,
        graphs_out_folder=graphs_out,
        analyses_out_folder=analyses_out,
        subid_search=subid_search_character,
        subid_range=subid_search_length, 
        condition_search=condition_search_character, 
        condition_range=condition_search_length,
        max_episode_duration=max_episode_duration
      )
      #signal processing on all datasets
      print('reached')
      skyn_datasets.load_bulk_skyn_occasions(make_plots=True, export_python_object=True)
      

    #train models and run cross validation
    skyn_datasets.run_analyses()

    #create excel workbook report
    skyn_datasets.create_report()

    root = tkinter.Tk()
    root.withdraw()
    messagebox.showinfo("Skyn Data Manager", "Signal Processing and Model Predictions: Complete.")
    
  except Exception:
    print(traceback.format_exc())
    root = tkinter.Tk()
    root.withdraw()
    messagebox.showerror('Skyn Data Manager Error', traceback.format_exc())
