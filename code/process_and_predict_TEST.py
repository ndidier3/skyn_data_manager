from skyn_processors.skyn_cohort_tester import skynCohortTester
from utils.Reporting.export import *
import tkinter
from tkinter import messagebox
import traceback

#THIS SCRIPT IS DESIGNED AS A TEST
#SUMMARY: 
  # Clean a cohort of test data, 
  # generate features for each dataset,
  # make predictions whether alcohol was consumed by using built-in model
  # generate individual processed datasets
  # generate summary file with graphs and prediction results

#Parameters that NEED MODIFICATION
cohort_name = 'TestData'
data_in = 'raw/TestData/'
metadata = 'resources/Test/Cohort Metadata TEST.xlsx'

#Parameters that MIGHT NEED MODIFICATION
subid_search_character = '#'
subid_search_length = 4
condition_search_character = '$'
condition_search_length = 3
sub_condition_search_character = '^'
sub_condition_search_length = 3
max_episode_duration = 18
skyn_download_timezone = -5

#If timestamps for cropping datasets are available, replace "None" with filepath to timestamps
#If timestamps are not available, keep "timestamps = None"

timestamps = None

#Constant Parameters (do not modify unless certain)
data_out = f'processed_data_and_plots/data_{cohort_name}'
graphs_out = f'processed_data_and_plots/tac_curves_{cohort_name}'
analyses_out = 'features_and_model_results/'
original = load('07.17.2023', 'Original Model') #UPDATE
built_in_models = original.models
load_previous_processing = False

#~~~~~~~~~~~~~~~~~~~ THE PROCEDURE ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

root = tkinter.Tk()
root.withdraw()
run_procedure = messagebox.askyesno("Skyn Data Manager", "Would you like to process Skyn datasets and make predictions?")

if run_procedure:
  try:
    if load_previous_processing:
      skyn_dataset = load('04.20.2023', cohort_name) #UPDATE
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
    messagebox.showinfo("Skyn Data Manager", "Signal Processing and Model Predictions: Complete.")

  except Exception:
    print(traceback.format_exc())
    root = tkinter.Tk()
    root.withdraw()
    messagebox.showerror('Skyn Data Manager Error', traceback.format_exc())


