#Parameters that NEED MODIFICATION
cohort_name = 'nameYourCohort'
data_in = 'path/to/data'
metadata = 'path/to/episode/metadata'

#Parameters that MIGHT NEED MODIFICATION
subid_search_character = '#'
subid_search_length = 4
condition_search_character = '$'
condition_search_length = 3
sub_condition_search_character = '^'
sub_condition_search_length = 3
max_episode_duration = 18

#If timestamps for cropping datasets are available, replace "None" with filepath to timestamps
#If timestamps are not available, keep "timestamps = None"
timestamps = None