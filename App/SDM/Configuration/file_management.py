import pandas as pd
import pickle
from datetime import date
import xlsxwriter
import os
import re
import numpy as np
from collections import Counter

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
  # Temporarily patch the import system to handle old import paths in pickled models
  import sys
  from types import ModuleType
  
  # Create a mock module for the old import path
  old_module = ModuleType('App.SDM.Machine_Learning.Machine_Learning')
  sys.modules['App.SDM.Machine_Learning.Machine_Learning'] = old_module
  
  # Import the actual modules and make them available through the old path
  try:
    from App.SDM.Machine_Learning import model_optimization, cv_folds, get_feature_importances, metrics
    old_module.model_optimization = model_optimization
    old_module.cv_folds = cv_folds
    old_module.get_feature_importances = get_feature_importances
    old_module.metrics = metrics
  except ImportError:
    pass  # If imports fail, continue anyway
  
  try:
    pickle_in = open(f'App/SDM/Trained_Models/{name}.sdma', "rb")
    model = pickle.load(pickle_in)
    pickle_in.close()
    return model
  finally:
    # Clean up the temporary module
    if 'App.SDM.Machine_Learning.Machine_Learning' in sys.modules:
      del sys.modules['App.SDM.Machine_Learning.Machine_Learning']

def save_to_computer(object, filename, folder, extension='sdm'):

  out = open(f'{folder}/{filename}.{extension}', "wb")
  pickle.dump(object, out)
  out.close()


def load(name, folder):
  try:
    extension = 'sdm'
    pickle_in = open(f'{folder}/{name}.{extension}', "rb")
  except FileNotFoundError:
    try:
      extension = 'pickle'
      pickle_in = open(f'{folder}/{name}.{extension}', "rb")
    except FileNotFoundError:
      raise FileNotFoundError(f"Could not find file '{name}' with extensions 'sdm' or 'pickle' in folder '{folder}'. "
                             f"Please check that the file exists and is not a hidden file (starting with '.').")
  object = pickle.load(pickle_in)
  pickle_in.close()
  return object

def load_default_model(name='Alc_vs_Non', type='RF'):
  # Temporarily patch the import system to handle old import paths in pickled models
  import sys
  from types import ModuleType
  
  # Create a mock module for the old import path
  old_module = ModuleType('App.SDM.Machine_Learning.Machine_Learning')
  sys.modules['App.SDM.Machine_Learning.Machine_Learning'] = old_module
  
  # Import the actual modules and make them available through the old path
  try:
    from App.SDM.Machine_Learning import model_optimization, cv_folds, get_feature_importances, metrics
    old_module.model_optimization = model_optimization
    old_module.cv_folds = cv_folds
    old_module.get_feature_importances = get_feature_importances
    old_module.metrics = metrics
  except ImportError:
    pass  # If imports fail, continue anyway
  
  try:
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
  finally:
    # Clean up the temporary module
    if 'App.SDM.Machine_Learning.Machine_Learning' in sys.modules:
      del sys.modules['App.SDM.Machine_Learning.Machine_Learning']



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
  if not os.path.exists(f'{project_root}/Results/{output_folder_name}/{date.today().strftime("%m.%d.%Y")}'):
    os.mkdir(f'{project_root}/Results/{output_folder_name}/{date.today().strftime("%m.%d.%Y")}')
  if not os.path.exists(data_out):
    os.mkdir(data_out)
  if not os.path.exists(graphs_out):
    os.mkdir(graphs_out)
  if not os.path.exists(analyses_out):
    os.mkdir(analyses_out)
  if not os.path.exists(f'{project_root}/Results/Error_Logs'):
    os.mkdir(f'{project_root}/Results/Error_Logs')

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

def extract_subid(input_string, validate=True):
    pattern = re.compile(r'^(\d{3,6})')
    match = pattern.findall(input_string)
      
    if match:
      if validate:
        return match[0] if is_subid_valid(match[0]) else ''
      else:
        return match[0]
    else:
      return ''

def is_subid_valid(subid):
  return (2 < len(str(subid))) and (7 > len(str(subid))) and (subid.isnumeric())

def is_dataset_id_valid(episode_id, used_ids, assess_new=False):
  try:
    if assess_new and (used_ids != None):
      id_already_used = (episode_id in used_ids) or (int(episode_id) in used_ids)
      return (len(episode_id) == 3) and all([char.isdigit() for char in episode_id]) and (int(episode_id) != 0) and not id_already_used
    elif used_ids != None: #to assess existing filename with dataset id
      id_repeated = used_ids.count(episode_id) + used_ids.count(int(episode_id)) > 1
      return (len(episode_id) == 3) and all([char.isdigit() for char in episode_id]) and (int(episode_id) != 0) and not id_repeated
    else:
      return (len(episode_id) == 3) and all([char.isdigit() for char in episode_id]) and (int(episode_id) != 0)
  except:
    return False

def extract_dataset_identifier(filename, used_ids=None, validate = True, assess_new=False):
  if validate:
    try:
        dataset_identifier = filename.split(".")[0].split("_")[1]
        
        return dataset_identifier if is_dataset_id_valid(dataset_identifier, used_ids, assess_new=assess_new) else ''
    except:
      return ''
  else:
    try:
        dataset_identifier = str(filename.split(".")[0].split("_")[1])[:3]
        
        return dataset_identifier
    except:
      return ''
  
def matches_filename_convention(filename, used_ids, assess_new=False):
  subid = extract_subid(filename)
  dataset_id = extract_dataset_identifier(filename)
  return (is_subid_valid(subid)) and (is_dataset_id_valid(dataset_id, used_ids, assess_new))

def extract_additional_filename_text(filename):
  try:
    return str(filename.split(".")[0].split("_")[2])[:3]
  except:
    return ''
  
def stringify_dataset_id(dataset_identifier):
  return "".join(['0' for i in range(0, 3 - len(str(dataset_identifier)))]) + str(dataset_identifier) #gaurantees 3 characters
