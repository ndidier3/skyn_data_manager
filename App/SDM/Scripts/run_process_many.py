from App.SDM.Run.process_many import process_many
import pandas as pd

# MAC
# project_root = '/Users/nathandidier/Desktop/Repositories/skyn_data_manager'
# Linux
project_root = '/users/ndidier/SDM/skyn_data_manager' 
# Windows
# project_root = ''

# """ACE """
# data_input_folder = f'{project_root}/Inputs/Skyn_Data_RAW/ACE'
# output_folder_name = 'ACE'

# """ ACE META """
# event_path = f'{project_root}/Inputs/Metadata/ACE_RG_paper_subset_alcsam.csv'
# event_data = pd.read_csv(event_path)
# event_data = event_data.dropna(subset=['drinkstart_timestamp'])
# event_data = event_data.drop_duplicates(subset=['ID', 'sub_episode_id']).reset_index(drop=True)
# extra_columns = ['sex', 'age', 'weekend', 'skynversion', 'sub_episode_id', 'eventuse', 'usetype_initial', 'drinkstart_timestamp', 'n_sam_days', 'totdrinks_fin', 'totdrinks_fin_mr']

""" ARC TEST """
# data_input_folder = f'{project_root}/Inputs/Skyn_Data_RAW/ARC/EventTest'
# output_folder_name = 'ARC_test'

""" ARC """
data_input_folder = f'{project_root}/Inputs/Skyn_Data_RAW/ARC/Burst1'
output_folder_name = 'ARC_10'

""" ARC META """
event_path = f'{project_root}/Inputs/Metadata/ARC_flagged.xlsx'
event_data = pd.read_excel(event_path)
event_data = event_data[event_data['final966']=='Selected'].reset_index(drop=True)
extra_columns = ['drkyst_m', 'drkhrs', 'bac_r']

# process_many(project_root, data_input_folder, output_folder_name, event_data=event_data, use_prior_save=False, process_raw_data=True, analyze_day_level=True, extra_columns = extra_columns)
process_many(project_root, data_input_folder, output_folder_name, event_data=event_data, use_prior_save=True, process_raw_data=False, analyze_day_level=False, extra_columns = extra_columns)

#no event processing requested
# process_many(project_root, data_input_folder, output_folder_name, use_prior_save=False, process_raw_data=True, analyze_day_level=False, extra_columns = extra_columns)

""" MARS """
# data_input_folder = f'{project_root}/Inputs/Skyn_Data_RAW/MARS/'
# output_folder_name = 'MARS'

# process_many(project_root, data_input_folder, output_folder_name, use_prior_save=False, process_raw_data=True, analyze_day_level=True)

"""
event_timestamps = {
    "bracelet_on": datetime.strptime("Dec 6 2024 1:24 PM", "%b %d %Y %I:%M %p"),
    "prime_drink": datetime.strptime("Dec 6 2024 2:08 PM", "%b %d %Y %I:%M %p"),
    "block_1": datetime.strptime("Dec 6 2024 2:51 PM", "%b %d %Y %I:%M %p"),
    "block_2": datetime.strptime("Dec 6 2024 3:52 PM", "%b %d %Y %I:%M %p"),
    "bracelet_off": datetime.strptime("Dec 6 2024 7:01 PM", "%b %d %Y %I:%M %p")
  }

"""