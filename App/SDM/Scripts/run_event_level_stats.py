from App.SDM.Analysis.eventFeatures import eventFeatures
from SDM.Configuration.file_management import load, save_to_computer
import os
import pandas as pd

project_root = '/users/ndidier/SDM/skyn_data_manager'
data_input_folder = f'{project_root}/Inputs/Skyn_Data_PROCESSED/ARC/Burst1'
event_dfs = []

# for file in os.listdir(data_input_folder):
#   if 'processed' in file:
#     sdm_processor = load(file[:-4], data_input_folder)
#     event_dfs.append(sdm_processor.event_level_data)

# event_features = pd.concat(event_dfs)
# save_to_computer(event_features, 'event_features_df', f'{project_root}/Results/ARC/')

# event_features = load('event_features_df', f'{project_root}/Results/ARC/')

event_features_stat_model = eventFeatures(data_input_folder, 'ARC_10')
event_features_stat_model.run_all()
event_features_stat_model.export_sheet(f'{project_root}/Results/ARC_10/event_level_stats_10.xlsx')
event_features_stat_model.save(f'{project_root}/Results/ARC/', 10)