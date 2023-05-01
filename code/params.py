#Parameters that NEED MODIFICATION
cohort_name = 'nameYourCohort'
data_in = 'path/to/data'

#Parameters that MIGHT NEED MODIFICATION
metadata = 'resources/Cohort Metadata.xlsx'
subid_search_character = '#'
subid_search_length = 4
condition_search_character = '$'
condition_search_length = 3
sub_condition_search_character = '^'
sub_condition_search_length = 3
max_episode_duration = 18
skyn_download_timezone = -5

#If timestamps for cropping datasets are available, replace "None" with filepath to timestamps
#If timestamps are not available, keep "timestamps = None"
timestamps = None