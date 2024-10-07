import os
import pandas as pd
import string
import random
from SDM.User_Interface.Utils.filename_tools import extract_subid, stringify_dataset_id

def standardize_filename(filename, dataset_id, text='', ext=''):
  """ rewrites filename with standard format of <subid>_<dataset-ID>_<optional-text>.<ext>
  uses original extension if not specified"""
  subid = extract_subid(filename)
  dataset_id = stringify_dataset_id(dataset_id)
  if ext == '':
    _, ext = os.path.splitext(filename)

  if len(text):
    return f'{subid}_{dataset_id}_{text}{ext}'
  else:
    return f'{subid}_{dataset_id}{ext}'
  
def standardize_filenames_within_folder(folder_path, dataset_id = 1, text=''):

  filenames = os.listdir(folder_path)
  
  for filename in filenames:
    _, ext = os.path.splitext(filename)
    if ext == '.xlsx' or ext == '.csv':
      new_filename = standardize_filename(filename, dataset_id, text=text)
      old_filepath = os.path.join(folder_path, filename)
      new_filepath = os.path.join(folder_path, new_filename)
      print(old_filepath)
      print(new_filepath)
      os.rename(old_filepath, new_filepath)

def modify_filenames(directory_path, insert_index, insert_character):

  directory = os.fsencode(directory_path)
  directory_absolute_path = os.path.abspath(directory_path) + '/'
  for i, file in enumerate(os.listdir(directory)):
      filename = os.fsdecode(file)
      print('filename: ', file)
      if (filename.endswith(".xlsx") or filename.endswith(".csv")) and (filename[insert_index] != '#'): 
          new_filename = filename[:insert_index] + insert_character + filename[insert_index:]
          print('new filename', new_filename)
          os.rename(directory_absolute_path + filename, directory_absolute_path + new_filename)

def replace_substring_in_filenames(directory_path, substring_find, substring_replace):

  directory = os.fsencode(directory_path)
  directory_absolute_path = os.path.abspath(directory_path) + '/'
  print(directory_absolute_path)
  for i, file in enumerate(os.listdir(directory)):
      filename = os.fsdecode(file)
      print('filename: ', file)
      if filename.endswith(".xlsx") or filename.endswith(".csv"): 
          if substring_find in filename:
            new_filename = filename.replace(substring_find, substring_replace)
            print('new filename: ', filename)
            os.rename(directory_absolute_path + filename, directory_absolute_path + new_filename)

def modify_filenames_with_randomization(directory_path, randomization_filepath, starting_indices_subid, subid_length, strings_to_replace = [' A.', ' B.']):
  randomization = pd.read_excel(randomization_filepath)

  directory = os.fsencode(directory_path)
  directory_absolute_path = os.path.abspath(directory_path) + '/'
  for i, file in enumerate(os.listdir(directory)):
      filename = os.fsdecode(file)
      print('filename: ', filename)
      
      for index in starting_indices_subid:
         if filename[index: index + subid_length].isnumeric():
            subid = int(filename[index: index + subid_length])
            break

      print(subid)
      print(randomization.loc[randomization['subid'] == subid, 'rando_code'])
      rando_code = randomization.loc[randomization['subid'] == subid, 'rando_code'].tolist()[0]
      session_order = [' non.' if rando_code == 1 else ' alc.',
                       ' non.' if rando_code == 2 else ' alc.']

      if filename.endswith(".xlsx") or filename.endswith(".csv"):
        for i, s in enumerate(strings_to_replace):
          if s in filename:
            new_filename = filename.replace(s, session_order[i])
            print('new filename: ', new_filename)
            os.rename(directory_absolute_path + filename, directory_absolute_path + new_filename)

def generate_random_id(length=6):
    first_digit = random.choice(string.digits[1:])  # Choose from '1' to '9'
    remaining_digits = ''.join(random.choice(string.digits) for _ in range(length - 1))
    random_id = first_digit + remaining_digits
    
    return random_id
