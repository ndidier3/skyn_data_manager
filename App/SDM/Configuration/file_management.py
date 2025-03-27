import pandas as pd
import pickle
from datetime import date
import xlsxwriter
import os

def export_to_computer(object, filepath):
  out = open(filepath, "wb")
  pickle.dump(object, out)
  out.close()
  print('successful export: ', filepath)
  
def import_from_computer(filename):
  pickle_in = open(filename, "rb") 
  object = pickle.load(pickle_in)
  pickle_in.close()
  return object

def import_model(name='RF_non_wear_CSDP'):
  pickle_in = open(f'App/SDM/Trained_Models/{name}.sdma', "rb")
  model = pickle.load(pickle_in)
  pickle_in.close()
  return model

def save_to_computer(object, filename, folder, extension='sdm'):

  out = open(f'{folder}/{filename}.{extension}', "wb")
  pickle.dump(object, out)
  out.close()
  print(f'SAVE SUCCESSFUL: {folder}/{filename}.{extension}')


def load(name, folder):
  try:
    extension = 'sdm'
    pickle_in = open(f'{folder}/{name}.{extension}', "rb")
  except:
    extension = 'pickle'
    pickle_in = open(f'{folder}/{name}.{extension}', "rb") 
  object = pickle.load(pickle_in)
  pickle_in.close()
  return object

def load_default_model(name='Alc_vs_Non', type='RF'):
  for extension in ['sdmtm', 'pickle']:
    try:
      if name == 'Alc_vs_Non':
        pickle_in = open(f'App/SDM/Trained_Models/MARS2C4{type}_Alc_vs_Non.{extension}', "rb")
      if name == 'AUD':
        pickle_in = open(f'App/SDM/Trained_Models/MARS2C4{type}_AUD.{extension}', "rb")
      if name == 'Binge':
        pickle_in = open(f'App/SDM/Trained_Models/MARS2C4{type}_Binge.{extension}', "rb")
      if name=='worn_vs_removed':
        pickle_in = open(f'App/SDM/Trained_Models/worn_vs_removed_{type}.{extension}', "rb")
        # type='LinReg'
      if name == 'fall_duration':
        pickle_in = open(f'App/SDM/Trained_Models/fall_duration_CLN_LinearReg.{extension}', "rb")
      if name == 'fall_rate':
        pickle_in = open(f'App/SDM/Trained_Models/fall_rate_CLN_LinearReg.{extension}', "rb")
      if name == 'rise_duration':
        pickle_in = open(f'App/SDM/Trained_Models/rise_duration_CLN_LinearReg.{extension}', "rb")
      if name == 'rise_rate':
        pickle_in = open(f'App/SDM/Trained_Models/rise_rate_CLN_LinearReg.{extension}', "rb")
    except:
      pass

  object = pickle.load(pickle_in)
  pickle_in.close()

  return object



def get_model_summary_sheet_name(model_name, data_version):
  model_name_new = model_name.split('_')[0][0].upper() + model_name.split('_')[0][1:] + ' ' + model_name.split('_')[1][0].upper() + model_name.split('_')[1][1:]
  return f'{model_name_new} - {data_version}'

def reorder_tabs(analyses_out_folder, cohort_name):
  workbook = xlsxwriter.Workbook(f'{analyses_out_folder}/skyn_report_{cohort_name}.xlsx')

  sheetlist = workbook.worksheets._name
  sheetlist.insert(1, sheetlist.pop(len(sheetlist) - 1))
  #does this bring a tab from back to front?
  workbook.worksheets_objs.sort(key=lambda x: sheetlist.index(x.name))
  workbook.close()

def merge_using_subid(sdm_results, merge_variables):
  for file, info in merge_variables.items():
    df = info['df']
    data_to_add = df[[info['subid_column']] + info['variables']]
    sdm_results = sdm_results.merge(data_to_add, on=info['subid_column'], how='left')
  return sdm_results

def create_save_directories(project_root, processed_data_out, output_folder_name, data_out, graphs_out, analyses_out):
  if not os.path.exists(processed_data_out):
    os.makedirs(processed_data_out, exist_ok=True)
  if not os.path.exists(f'{project_root}/Results/{output_folder_name}'):
    os.mkdir(f'{project_root}/Results/{output_folder_name}')
    print('results path exists: ', os.path.exists(f'{project_root}/Results/{output_folder_name}'))
  if not os.path.exists(f'{project_root}/Results/{output_folder_name}/{date.today().strftime("%m.%d.%Y")}'):
    os.mkdir(f'{project_root}/Results/{output_folder_name}/{date.today().strftime("%m.%d.%Y")}')
  if not os.path.exists(data_out):
    os.mkdir(data_out)
  if not os.path.exists(graphs_out):
    os.mkdir(graphs_out)
  if not os.path.exists(analyses_out):
    os.mkdir(analyses_out)

def create_individual_plot_folder(graphs_out, subid):
  # Create subid plot folder within the plot folder
  subid_plot_folder = f'{graphs_out}/{subid}/'
  if not os.path.exists(subid_plot_folder):
      os.makedirs(subid_plot_folder, exist_ok=True)
  
  return subid_plot_folder

def create_feature_plot_folder(cohort_name):
  path = f'Results/{cohort_name}/FeaturePlots/'
  if not os.path.exists(path):
    os.mkdir(path)
  return path