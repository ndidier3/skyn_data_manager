#Parameters that NEED MODIFICATION
cohort_name = 'cohort name'
data_in = 'folder that holds all cohort data'

#Parameters that MIGHT NEED MODIFICATION
metadata = 'filepath to corresponding metadata'
filenames_and_variables = {
    # SEE DOWN BELOW FOR EXAMPLE
  }
subid_search_character = '#'
subid_search_length = 4
condition_search_character = '.'
condition_search_length = -3
sub_condition_search_character = None
sub_condition_search_length = None
max_episode_duration = 18
skyn_download_timezone = -5

#If timestamps for cropping datasets are available, replace "None" with filepath to timestamps
#If timestamps are not available, use "timestamps = None"
timestamps = None

load_previous_processing = False
#if true for above, then provide date of previous processing below
date_of_processing = 'dd.mm.yyyy' 


# #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# #EXAMPLE OF PARAMS

# #Parameters that NEED MODIFICATION
# cohort_name = 'C4_lab'
# data_in = 'raw/C4_lab/'

# #Parameters that MIGHT NEED MODIFICATION
# metadata = 'resources/C4Lab Metadata.xlsx'
# filenames_and_variables = {
#     'resources/C4 Measures/demographics.xlsx': ['subid', 'group', 'sex', 'race', 'education'],
#     'resources/C4 Measures/randomization_8.4.23.xlsx': ['subid', 'rando_code']}
# subid_search_character = '#'
# subid_search_length = 4
# condition_search_character = '.'
# condition_search_length = -3
# sub_condition_search_character = None
# sub_condition_search_length = None
# max_episode_duration = 8
# skyn_download_timezone = -5

# #If timestamps for cropping datasets are available, replace "None" with filepath to timestamps
# #If timestamps are not available, keep "timestamps = None"
# timestamps = None

# load_previous_processing = True
# date_of_processing = '08.04.2023'




