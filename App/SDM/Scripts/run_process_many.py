from App.SDM.Run.process_many import process_many

# MAC
# project_root = '/Users/nathandidier/Desktop/Repositories/skyn_data_manager'
# Linux
project_root = '/users/ndidier/SDM/skyn_data_manager' 
# Windows
# project_root = ''


data_input_folder = f'{project_root}/Inputs/Skyn_Data/ARC/Burst1'
output_folder_name = 'ARC'


# how to set output folder name? Separate by date?

process_many(project_root, data_input_folder = data_input_folder, output_folder_name = output_folder_name)



  #153 left out
  # subids = [101, 102, 106, 112, 113, 114, 115, 117, 118, 120, 121, 122, 123, 127, 130, 
  #           132, 133, 134, 138, 139, 140, 141, 143, 146, 147, 149, 150, 151, 153, 155, 
  #           157, 159, 160, 161, 162, 165, 167, 171, 172, 174, 180, 181, 183, 185, 186, 
  #           189, 190, 194, 198, 199, 202, 204, 206, 207, 208, 209, 210, 211, 212, 213, 
  #           214, 215, 216, 218, 219, 220, 221, 222, 223, 227, 233, 236, 237, 238, 241, 
  #           243, 246, 247, 250, 251, 253, 255, 256, 258, 259, 260, 267, 270, 271, 272, 
  #           273, 274, 276, 277, 280, 281, 282, 286, 291, 292, 295, 296]