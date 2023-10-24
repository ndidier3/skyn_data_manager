import pandas as pd
import pickle
from datetime import date
import xlsxwriter

def export_skyn_workbook(cleaned_dataset, subid, condition, dataset_identifier, predictions, save_path, simple_plot_paths, complex_plot_paths):
  variable_key = pd.DataFrame({'Variable/Descriptor':
      ['datetime / device timestamp', 'Time', 'time_elapsed_hours', 'potential_artifact', 'TAC', 'Cleaned', 'Greedy', 'Smooth_XYZ', 'TAC_change', 'Motion', 'Temperature C', 'device_id', 'FOR MORE INFORMATION:'],
  'Explanation':
      ['Timestamp originally produced by biosensor.',
      'Timestamp converted to AM/PM time format.',
      'The amount of time passed since initial biosensor reading.',
      'A Binary variable that indicates whether the data point was detected as an outlier by the greedy algorithm. A 1 indicates that the data point may be an artifact of device error.',
      'Data produced by Skyn biosensor. Units are: ug/L(air)',
      'Data cleaned by the standard cleaning method. Abbreviation: C.',
      'Data cleaned by the greedy cleaning method. Abbreviation: CG.',
      'Data smoothed with Savitzky-Golay filter at a window of size XYZ.',
      'The amount of TAC change from the current time point to the previous time point.',
      'A measurement of device motion. Produced by the Skyn.',
      'A measurement of temperature in Celsius. Produced by the Skyn',
      'Device ID',
      'See Word document saved here: Z:\Groups\King\ MARS 2\ 06) Data Management\ 3) Skyn']})
    
  writer = pd.ExcelWriter(f'{save_path}/skyn_{subid}_{condition}{dataset_identifier}.xlsx', engine='xlsxwriter')

  cleaned_dataset.to_excel(writer, sheet_name='Data', index=False)
  variable_key.to_excel(writer, sheet_name='Variable Key', index=False)

  if len(predictions) > 0:
    predictions.to_excel(writer, sheet_name='Predictions', index=False)

  workbook = writer.book
  worksheet = workbook.add_worksheet('Signal Processing Visuals')
  worksheet.set_default_row(20)
  row_index = 1
  for plot_path in complex_plot_paths:
    image_start_cell = 'B' + str(row_index)
    worksheet.insert_image(image_start_cell, (plot_path))
    row_index += 30

  workbook = writer.book
  worksheet = workbook.add_worksheet('Motion & Temp Graphs')
  row_index = 1
  for plot_path in simple_plot_paths:
    image_start_cell = 'B' + str(row_index)
    worksheet.insert_image(image_start_cell, (plot_path))
    row_index += 20

  writer.close()

def save(object, filename, folder):
  out = open(f'{folder}/{filename}.pickle', "wb")
  pickle.dump(object, out)
  out.close()
  print('SAVE SUCCESSFUL')

def load(name, folder):
  pickle_in = open(f'{folder}/{name}.pickle', "rb") 
  object = pickle.load(pickle_in)
  pickle_in.close()
  return object

def load_default_model():
  pickle_in = open('App/SDM/Default_Model/MARSRF_model.pickle', "rb")
  object = pickle.load(pickle_in)
  pickle_in.close()
  return {'RF_default': object}

def export_variable_key(writer, new_model_development = True):
  variable_key = pd.read_excel('Resources/FeatureKey.xlsx', index_col='Variable Name')
  if new_model_development:
    variable_key.drop('prediction', inplace=True)
    variable_key.rename(index = {'correct': 'cv_<model-type>'}, inplace=True)
  else:
    variable_key = variable_key[:40]
  variable_key.to_excel(writer, sheet_name='KEY')

def get_model_summary_sheet_name(model_name, data_version):
  model_name_new = model_name.split('_')[0][0].upper() + model_name.split('_')[0][1:] + ' ' + model_name.split('_')[1][0].upper() + model_name.split('_')[1][1:]
  return f'{model_name_new} - {data_version}'

def reorder_tabs(analyses_out_folder, cohort_name):
  workbook = xlsxwriter.Workbook(f'{analyses_out_folder}/skyn_report_{cohort_name}.xlsx')

  sheetlist = workbook.worksheets._name
  sheetlist.insert(1, sheetlist.pop(len(sheetlist) - 1))

  workbook.worksheets_objs.sort(key=lambda x: sheetlist.index(x.name))
  workbook.close()

def merge_using_subid(sdm_results, merge_variables):
  print(merge_variables)
  for file, info in merge_variables.items():
    df = info['df']
    print(info['subid_column'])
    print(info['variables'])
    data_to_add = df[[info['subid_column']] + info['variables']]
    sdm_results = sdm_results.merge(data_to_add, on=info['subid_column'], how='left')
  return sdm_results