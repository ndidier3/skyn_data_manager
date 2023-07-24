from skyn_processors.skyn_cohort_tester import skynOccasionProcessor
from utils.Reporting.export import *

#modify as needed
filepath = 'filepath'
data_out = 'folder to save processed data file'
graphs_out = 'folder to save graphs'
metadata_path = 'path to metadata'
episode_start_timestamps_path = None #optional: 'path to timestamps file'
subid_search_character = '#'
subid_search_length = 4
condition_search_character = '$'
condition_search_length = 3
sub_condition_search_character = '^'
sub_condition_search_length = 3
skyn_download_timezone = -5
max_episode_duration = 18

#do not modify
occasion = skynOccasionProcessor(
    filepath,
    data_out,
    graphs_out,
    subid_search_character, 
    subid_search_length,
    condition_search_character,
    condition_search_length,
    sub_condition_search_character,
    sub_condition_search_length,
    metadata_path,
    episode_start_timestamps_path,
    skyn_download_timezone,
    max_duration=max_episode_duration
)

occasion.process_with_default_settings(make_plots=True)
