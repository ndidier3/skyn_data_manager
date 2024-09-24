from SDM.Skyn_Processors.skyn_dataset import skynDataset
from datetime import date
import pandas as pd

main_dir = '/Users/nathandidier/Desktop/Repositories/skyn_data_manager/Inputs/Skyn_Data/ACE'
cohort_name = 'ACE'

results_dir = f'Users/nathandidier/Desktop/Repositories/skyn_data_manager/Results/{cohort_name}/{date.today().strftime("%m.%d.%Y")}'
data_out = f'{results_dir}/Processed_Datasets'
graphs_out = f'{results_dir}/Plots'
analyses_out = f'{results_dir}/Model_Performance'

subids = [121, 127, 134, 141, 146, 147, 149, 150, 151, 153]

datasets = []
for subid in subids:
  sdm_processor = skynDataset(
    f'{main_dir}/{subid}_001.csv',
    data_out,
    graphs_out,
    subid,
    1,
    'e' + str(1),
    False,
    False,
    'CST',
    24
  )
  sdm_processor.process_as_multiple_episodes()
  datasets.append(sdm_processor.day_level_data)

combined_day_level_data = pd.concat(datasets, ignore_index=True)
combined_day_level_data.to_excel(f'{results_dir}/day_level_quality_metrics.xlsx')
