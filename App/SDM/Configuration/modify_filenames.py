import os
import pandas as pd
import string
import random

def modify_filenames(directory_path, insert_index, insert_character):

  directory = os.fsencode(directory_path)
  directory_absolute_path = os.path.abspath(directory_path) + '/'
  print(directory_absolute_path)
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

def generate_random_id(length=4):
  characters = string.ascii_letters + string.digits  # Letters and digits
  random_id = ''.join(random.choice(characters) for _ in range(length))
  return random_id

# modify_filenames('raw/C4_field/', 0, '#')
# modify_filenames('raw/C4_field/', 8, '')
# modify_filenames_with_randomization('raw/C4_lab', 'resources/C4 Measures/randomization_8.4.23.xlsx', [0, 1], 4)
# replace_substring_in_filenames('raw/C4_lab', 'non', 'Non')
# replace_substring_in_filenames('raw/C4_lab', 'alc', 'Alc')
# modify_filenames('raw/C4_lab/', 0, '#')

# directory = os.fsencode('raw/C4_lab')
# directory_absolute_path = os.path.abspath('raw/C4_lab') + '/'
# print(directory_absolute_path)
# for i, file in enumerate(os.listdir(directory)):
#     filename = os.fsdecode(file)
#     print('filename: ', file)
#     if (filename.endswith(".xlsx") or filename.endswith(".csv")) and (filename[0:2] == '##'):
#         new_filename = filename[:1] + filename[2:]
#         print('new filename', new_filename)
#         os.rename(directory_absolute_path + filename, directory_absolute_path + new_filename)