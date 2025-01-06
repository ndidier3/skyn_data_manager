# from SDM.Skyn_Processors.skyn_dataset import skynDataset
# from SDM.User_Interface.Utils.filename_tools import extract_dataset_identifier, extract_subid
# from SDM.Configuration.file_management import save_to_computer, create_save_directories
# from tkinter import messagebox
# import traceback
# from datetime import date
# import pandas as pd
# import os

# def process_many(project_root, data_input_folder, output_folder_name = 'cohort', single_file = None, use_popups = False):

#   processed_data_out = data_input_folder.replace('_RAW', '_PROCESSED')
#   results_dir = f'{project_root}/Results/{output_folder_name}/{date.today().strftime("%m.%d.%Y")}'
#   data_out = f'{results_dir}/Processed_Datasets'
#   graphs_out = f'{results_dir}/Plots'
#   analyses_out = f'{results_dir}/Model_Performance'

#   create_save_directories(project_root, processed_data_out, output_folder_name, data_out, graphs_out, analyses_out)

#   if single_file == None:
#     files = [os.path.join(data_input_folder, file) for file in os.listdir(data_input_folder)]
#   else:
#     files = [os.path.join(data_input_folder, single_file)]
  
#   processors = []
#   processed_datasets = [] #populated in loop below

#   for file in files:
#     print(file)
#     try:
#       subid = extract_subid(os.path.basename(file))
#       dataset_identifier = extract_dataset_identifier(os.path.basename(file))

#       print(subid)
#       print(dataset_identifier)

#       if dataset_identifier == '':
#         if use_popups:
#           messagebox.showerror('Error', 'Dataset ID is not found in filename.')
#         print('Dataset ID is not found in filename.')
#       else:
#         if not os.path.isfile(file):
#           if use_popups:
#             messagebox.showerror('Error', 'Invalid file.')
#           print('Invalid File')
#         else:
#           sdm_processor = skynDataset(
#             str(file),
#             processed_data_out,
#             data_out,
#             graphs_out,
#             subid,
#             dataset_identifier,
#             'e' + str(1),
#             False,
#             False,
#             'CST',
#             24
#           )
#           sdm_processor.process_skyn_data(day_start_hour=0)
#           processed_datasets.append(sdm_processor.day_level_data)
#           processors.append(sdm_processor)

#     except Exception:
#       if use_popups:
#         messagebox.showerror('SDM Error', f'Failed to load. See error: {traceback.format_exc()}')
#       print('SDM Error', f'Failed to load. See error: {traceback.format_exc()}')

#   save_to_computer(processors, 'processors', f'{project_root}/Results/{output_folder_name}')

#   if len(processed_datasets):
#     combined_day_level_data = pd.concat(processed_datasets, ignore_index=True)
#     combined_day_level_data.to_excel(f'{results_dir}/day_level_quality_metrics.xlsx', index=None)
