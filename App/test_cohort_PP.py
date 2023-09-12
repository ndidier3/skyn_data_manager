from SDM.Skyn_Processors.skyn_cohort_processor import skynCohortProcessor
from datetime import date
from SDM.Reporting.export import load_default_model
import os
model = load_default_model()
cohort_name = 'test_PP_cohort'
data_out = f'Results/{cohort_name}/{date.today().strftime("%m.%d.%Y")}/Processed_Datasets'
graphs_out = f'Results/{cohort_name}/{date.today().strftime("%m.%d.%Y")}/Plots'
analyses_out = f'Results/{cohort_name}/{date.today().strftime("%m.%d.%Y")}/Model_Performance'

if not os.path.exists('Results'):
  os.mkdir('Results')
if not os.path.exists(f'Results/{cohort_name}'):
  os.mkdir(f'Results/{cohort_name}')
if not os.path.exists(f'Results/{cohort_name}/{date.today().strftime("%m.%d.%Y")}'):
  os.mkdir(f'Results/{cohort_name}/{date.today().strftime("%m.%d.%Y")}')
if not os.path.exists(f'Results/{cohort_name}/{date.today().strftime("%m.%d.%Y")}/Model_Performance'):
  os.mkdir(f'Results/{cohort_name}/{date.today().strftime("%m.%d.%Y")}/Model_Performance')

path = os.path.abspath('Raw/TestData/')
file = path + '/' + os.listdir(path)[0]
print(file)
print(file[0 + len(path)+1: 3 + len(path)+2])
print(path)
sdm_processor = skynCohortProcessor(
  path + '/',
  metadata_path = 'Resources/Test/Cohort Metadata TEST.xlsx',
  cohort_name = 'test2',
  merge_variables = {},
  episode_start_timestamps_path=None,
  data_out_folder=data_out,
  graphs_out_folder=graphs_out,
  analyses_out_folder=analyses_out,
  subid_index_start=1 + len(path),
  subid_index_end=4 + len(path), 
  condition_index_start=6 + len(path), 
  condition_index_end=8 + len(path),
  episode_identifier_search_index_start=10 + len(path),
  episode_identifier_search_index_end=12 + len(path),
  max_dataset_duration=24,
  skyn_timestamps_timezone=-5
)

sdm_processor.process_cohort()
sdm_processor.make_predictions(model, prediction_type='binary')