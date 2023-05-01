from skyn_processors.skyn_cohort_tester import skynCohortTester
from utils.Reporting.export import *
import tkinter
from tkinter import messagebox
import traceback

"""
COMMAND SUMMARY:
  -Process/clean a cohort of data, generate features for each dataset, and make predictions whether alcohol was consumed by using built-in predictive model
  -Dataset results will export to processed_data_and_plots folder
  -Cohort results will export to features_and_model_results folder
"""

#import params information needed for processing
from params import *

#Constant Parameters (do not modify unless certain)
data_out = f'processed_data_and_plots/data_{cohort_name}'
graphs_out = f'processed_data_and_plots/tac_curves_{cohort_name}'
analyses_out = 'features_and_model_results/'
original = load('04.19.2023', 'skyn_original_model')
built_in_models = original.models
export_report_from_previous_cohort = False
date_of_processing = 'dd.mm.yyyy'

#~~~~~~~~~~~~~~~~~~~ THE PROCEDURE ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

root = tkinter.Tk()
root.withdraw()
run_procedure = messagebox.askyesno("Skyn Data Manager", "Would you like to process Skyn datasets and make predictions?")

if run_procedure:
  try:
    if export_report_from_previous_cohort:
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



