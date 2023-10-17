import os

def matches_convention(filename, dataset_identifier_required = False):
  filename = filename.split(".")[0]
  dataset_info = filename.split(" ")
  
  if len(dataset_info) != 2 and len(dataset_info) != 3:
    return False
  if len(dataset_info) == 2 and dataset_identifier_required:
    return False
  else:
    for i, info in enumerate(dataset_info):
      #verify subid
      if i == 0:
        if ((2 >= len(str(info)) > 6) and not info.isnumeric()):
          return False
      #verify condition
      if i == 1:
        if info not in ['Alc', 'Non', 'Unk']:
          return False
      #verify Dataset ID (if applicable)
      if i == 2:
        if (len(info) != 3 or any([not char.isdigit() for char in info])):
          return False
    return True

def identify_dataset_identifier(filename, used_epi_ids = []):

  if len(filename.split(".")[0].split(" ")) != 3:
    return None
  
  try:
    dataset_identifier = str(filename.split(".")[0].split(" ")[2])
    test_numeric = int(filename.split(".")[0].split(" ")[2])
    dataset_identifier = dataset_identifier[:3]
    return dataset_identifier
  except:
    dataset_identifier_number = 1
    while dataset_identifier_number in [int(i) for i in used_epi_ids]:
      dataset_identifier_number += 1
    dataset_identifier = "".join(['0' for i in range(0, 3 - len(str(dataset_identifier_number)))]) + str(dataset_identifier_number) #gaurantees 3 characters
    return dataset_identifier
  
def identify_condition(filename):
  if 'alc' in filename.lower():
    return 'Alc'
  if 'non' in filename.lower():
    return 'Non'
  if 'unk' in filename.lower():
    return 'Unk'
  return ''

def identify_subid(filename):
  if len(filename.split(" ")) > 0:
    subid = filename.split(" ")[0]
    if ((2 < len(str(subid)) <= 6) and subid.isnumeric()):
      return subid
  return ''

def directory_analysis_ready(directory):
  filenames = [file for file in os.listdir(directory) if file.endswith((".xlsx", ".csv"))]
  filenames_valid = all([matches_convention(file) for file in filenames])
  subids_consistent = all([len(identify_subid(filename)) == len(identify_subid(filenames[0])) for filename in filenames])
  conditions_consistent = all([identify_condition(filename) in ['Alc', 'Non', 'Unk'] for filename in filenames])
  dataset_identifiers_consistent = all([len(identify_dataset_identifier(filename)) == len(identify_dataset_identifier(filenames[0])) if identify_dataset_identifier(filenames[0]) and identify_dataset_identifier(filename) else identify_dataset_identifier(filename) for filename in filenames])
  dataset_identifiers_required = all([identify_dataset_identifier(filename) != None for filename in filenames])

  print(filenames)
  print(filenames_valid, filenames)
  print(subids_consistent, 'subids')
  print(conditions_consistent, 'conditions')
  print(dataset_identifiers_consistent, 'epi consistent')
  print([len(identify_dataset_identifier(filename)) == len(identify_dataset_identifier(filenames[0])) if identify_dataset_identifier(filenames[0]) and identify_dataset_identifier(filename) else identify_dataset_identifier(filename) for filename in filenames])
  print(dataset_identifiers_required, 'epi required')
  print([identify_dataset_identifier(filename) != None for filename in filenames])

  if dataset_identifiers_required:
    return filenames_valid and subids_consistent and conditions_consistent and dataset_identifiers_consistent
  else:
    return filenames_valid and subids_consistent and conditions_consistent

def get_default_parsing_indices(subid, dataset_identifiers_required):
  subid_length = len(subid)
  return [0, subid_length - 1, subid_length + 1, subid_length + 3, (subid_length + 5) if dataset_identifiers_required else None, (subid_length + 7) if dataset_identifiers_required else None]

def models_ready(processor):
  return len(list(processor.models.values())) > 0 if hasattr(processor, 'models') else False 

def data_ready(processor):
  print('has occasions attr', hasattr(processor, 'occasions'))
  return len(processor.occasions) > 0 if hasattr(processor, 'occasions') else False