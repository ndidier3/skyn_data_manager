from SDM.Skyn_Processors.skyn_dataset import skynDataset
from datetime import date

# Path to the main directory
main_dir = '/Users/nathandidier/Desktop/Repositories/skyn_data_manager/Inputs/Skyn_Data_RAW/ACE'

cohort_name = 'ACE'

data_out = f'Users/nathandidier/Desktop/Repositories/skyn_data_manager/Results/{cohort_name}/{date.today().strftime("%m.%d.%Y")}/Processed_Datasets'
graphs_out = f'Users/nathandidier/Desktop/Repositories/skyn_data_manager/Results/{cohort_name}/{date.today().strftime("%m.%d.%Y")}/Plots'
analyses_out = f'Users/nathandidier/Desktop/Repositories/skyn_data_manager/Results/{cohort_name}/{date.today().strftime("%m.%d.%Y")}/Model_Performance'
processed_data_out = '/Users/nathandidier/Desktop/Repositories/skyn_data_manager/Inputs/Skyn_Data_PROCESSED/'

sdm_processor = skynDataset(
  f'{main_dir}/121_001.csv',
  processed_data_out,
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

sdm_processor.process_skyn_data()