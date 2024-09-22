import sys
from SDM.Skyn_Processors.skyn_cohort import skynCohort
from datetime import date
import os

cohort_name = 'Test'

SDM_path = os.path.expanduser('~/SDM/skyn_data_manager')

data_out = f'{SDM_path}/Results/{cohort_name}/{date.today().strftime("%m.%d.%Y")}/Processed_Datasets'
graphs_out = f'{SDM_path}/Results/{cohort_name}/{date.today().strftime("%m.%d.%Y")}/Plots'
analyses_out = f'{SDM_path}/Results/{cohort_name}/{date.today().strftime("%m.%d.%Y")}/Model_Performance'


sdm_processor = skynCohort(
  os.path.abspath(f'{SDM_path}/Inputs/Skyn_Data/TestData/') + '/',
  metadata_path = f'{SDM_path}/Inputs/Metadata/Cohort Metadata TEST.xlsx',
  cohort_name = 'Test',
  merge_variables = {},
  disable_crop_start = False,
  disable_crop_end = False,
  data_out_folder = data_out,
  graphs_out_folder = graphs_out,
  analyses_out_folder = analyses_out,
  max_dataset_duration = 24,
  skyn_upload_timezone = 'CST',
)

sdm_processor.process_cohort(False)