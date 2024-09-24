from SDM.Skyn_Processors.skyn_dataset import skynDataset
from datetime import date

# Path to the main directory
main_dir = '/Users/nathandidier/Desktop/Repositories/skyn_data_manager/Inputs/Skyn_Data/ACE'

cohort_name = 'ACE'

data_out = f'Users/nathandidier/Desktop/Repositories/skyn_data_manager/Results/{cohort_name}/{date.today().strftime("%m.%d.%Y")}/Processed_Datasets'
graphs_out = f'Users/nathandidier/Desktop/Repositories/skyn_data_manager/Results/{cohort_name}/{date.today().strftime("%m.%d.%Y")}/Plots'
analyses_out = f'Users/nathandidier/Desktop/Repositories/skyn_data_manager/Results/{cohort_name}/{date.today().strftime("%m.%d.%Y")}/Model_Performance'

sdm_processor = skynDataset(
  f'{main_dir}/121_001.csv',
  data_out,
  graphs_out,
  121,
  1,
  'e' + str(1),
  False,
  False,
  'CST',
  24
)

sdm_processor.process_as_multiple_episodes()