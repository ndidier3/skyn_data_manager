from skyn_processors.skyn_cohort_tester import skynCohortTester
from utils.Reporting.export import *
import tkinter
from tkinter import messagebox
import traceback

"""
COMMAND SUMMARY:
  1. Process/clean a cohort of data
  2. Generate features for each dataset
  3. Make predictions whether alcohol was consumed by using built-in predictive model
  4. Dataset results will export to processed_data_and_plots folder
  5. Cohort results will export to features_and_model_results folder
"""

#import params information needed for processing - Make sure params.py file is updated
from params import *

#Constant Parameters (do not modify unless certain)
data_out = f'processed_data_and_plots/data_{cohort_name}'
graphs_out = f'processed_data_and_plots/tac_curves_{cohort_name}'
analyses_out = 'features_and_model_results/'
original = load('07.17.2023', 'Original Model')
built_in_models = original.models

#~~~~~~~~~~~~~~~~~~~ THE PROCEDURE ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

root = tkinter.Tk()
root.withdraw()
run_procedure = messagebox.askyesno("Skyn Data Manager", "Would you like to process Skyn datasets and make predictions?")

if run_procedure:
  try:
    if load_previous_processing:
      skyn_dataset = load(date_of_processing, cohort_name)
      skyn_dataset.create_report()
    else:
      skyn_dataset = skynCohortTester(
        built_in_models,
        data_in,
        cohort_name,
        data_out,
        graphs_out,
        analyses_out,
        subid_search_character,
        subid_search_length,
        condition_search_character,
        condition_search_length,
        sub_condition_search_character,
        sub_condition_search_length,
        metadata_path = metadata,
        merge_variables=filenames_and_variables,
        episode_start_timestamps_path=timestamps,
        max_episode_duration=max_episode_duration,
        skyn_download_timezone=skyn_download_timezone
      )

      skyn_dataset.process_and_make_predictions(export_python_object=True)
      skyn_dataset.create_report()

    root = tkinter.Tk()
    root.withdraw()
    messagebox.showinfo("showinfo", "Signal Processing and Model Predictions: Complete.")

  except Exception:
    print(traceback.format_exc())
    root = tkinter.Tk()
    root.withdraw()
    messagebox.showerror('Error', traceback.format_exc())



