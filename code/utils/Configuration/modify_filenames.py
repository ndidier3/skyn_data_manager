import os
import pandas as pd

def modify_filenames(directory_path, insert_index, insert_character):

  directory = os.fsencode(directory_path)
  directory_absolute_path = os.path.abspath(directory_path) + '/'
  print(directory_absolute_path)
  for i, file in enumerate(os.listdir(directory)):
      filename = os.fsdecode(file)
      print('filename: ', file)
      if filename.endswith(".xlsx") or filename.endswith(".csv"): 
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

def modify_filenames_with_randomization(directory_path, randomization_filepath, strings_to_replace = [' A.', ' B.']):
  randomization = pd.read_excel(randomization_filepath)

  directory = os.fsencode(directory_path)
  directory_absolute_path = os.path.abspath(directory_path) + '/'
  for i, file in enumerate(os.listdir(directory)):
      filename = os.fsdecode(file)
      print('filename: ', filename)
      subid = filename[:4]
      rando_code = randomization.loc[randomization['subid'] == int(subid), 'rando_code'].tolist()[0]
      session_order = [' non.' if rando_code == 1 else ' alc.',
                       ' non.' if rando_code == 2 else ' alc.']

      if filename.endswith(".xlsx") or filename.endswith(".csv"):
        for i, s in enumerate(strings_to_replace):
          if s in filename:
            new_filename = filename.replace(s, session_order[i])
            print('new filename: ', new_filename)
            os.rename(directory_absolute_path + filename, directory_absolute_path + new_filename)

# modify_filenames('raw/C4_field/', 0, '#')
# modify_filenames('raw/C4_field/', 8, '')
# modify_filenames_with_randomization('raw/C4_lab', 'resources/C4 Measures/randomization_6.14.23.xlsx')
# replace_substring_in_filenames('raw/C4_lab', 'non', 'Non')
# replace_substring_in_filenames('raw/C4_lab', 'alc', 'Alc')
modify_filenames('raw/C4_lab/', 0, '#')
