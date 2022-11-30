import pandas as pd
import pickle

def export_skyn_workbook(cleaned_dataset, subid, condition, excel_path, plot_paths):
  variable_key = pd.DataFrame({'Variable/Descriptor':
      ['datetime / device timestamp', 'Time', 'time_elapsed_hours', 'potential_artifact', 'TAC', 'Cleaned', 'Greedy', 'Smooth_XYZ', 'TAC_change', 'Motion', 'Temperature C', 'device_id', 'FOR MORE INFORMATION:'],
  'Explanation':
      ['Timestamp originally produced by biosensor.',
      'Timestamp converted to AM/PM time format.',
      'The amount of time passed since initial biosensor reading.',
      'A Binary variable that indicates whether the data point was detected as an outlier by the greedy algorithm. A 1 indicates that the data point may be an artifact of device error.',
      'Data produced by Skyn biosensor. Units are: ug/L(air)',
      'Data cleaned by the standard cleaning method. Abbreviation: C.',
      'Data cleaned by the greedy cleaning method. Abbreviation: CG.',
      'Data smoothed with Savitzky-Golay filter at a window of size XYZ.',
      'The amount of TAC change from the current time point to the previous time point.',
      'A measurement of device motion. Produced by the Skyn.',
      'A measurement of temperature in Celsius. Produced by the Skyn',
      'Device ID',
      'See Word document saved here: Z:\Groups\King\ MARS 2\ 06) Data Management\ 3) Skyn']})
    
  writer = pd.ExcelWriter(f'{excel_path}/skyn_{subid}_{condition}.xlsx', engine='xlsxwriter')

  cleaned_dataset.to_excel(writer, sheet_name='Data', index=False)
  variable_key.to_excel(writer, sheet_name='Variable Key', index=False)

  workbook = writer.book
  worksheet = workbook.add_worksheet('Graphs')

  row_index = 1
  counter = 0
  column_indices = ['A', 'K', 'U']
  for plot_path in plot_paths:
    if ((counter+3)%3) == 0:
      if counter != 0:
        row_index += 24
    column_index = column_indices[(counter+3)%3]
    image_start_cell = column_index + str(row_index)
    worksheet.insert_image(image_start_cell, (plot_path))
    counter += 1
  writer.save()

def save(object, folder, filename):
  out = open(f'{folder}/{filename}.pickle', "wb")
  pickle.dump(object, out)
  out.close()
  print('SAVE SUCCESSFUL')

def load(folder, filename):
  pickle_in = open(f'{folder}/{filename}.pickle', "rb") 
  object = pickle.load(pickle_in)
  pickle_in.close()
  return object
