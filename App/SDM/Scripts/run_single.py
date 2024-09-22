from SDM.Skyn_Processors.skyn_dataset import skynDataset
import os
from datetime import date

SDM_path = os.path.expanduser('~/SDM/skyn_data_manager')
cohort_name = 'Test'
data_out = f'Results/{cohort_name}/{date.today().strftime("%m.%d.%Y")}/Processed_Datasets'
graphs_out = f'Results/{cohort_name}/{date.today().strftime("%m.%d.%Y")}/Plots'
analyses_out = f'Results/{cohort_name}/{date.today().strftime("%m.%d.%Y")}/Model_Performance'


sdm_processor = skynDataset(
  'Inputs/Skyn_Data/Test_ND/5001 001 Alc.xlsx',
  data_out,
  graphs_out,
  5001,
  1,
  'e' + str(1),
  False,
  False,
  'CST',
  24
)

sdm_processor.process_as_multiple_episodes()