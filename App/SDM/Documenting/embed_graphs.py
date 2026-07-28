import os
import xlsxwriter
import traceback

def embed_graphs_into_workbook_tab(
  workbook,
  lists_of_plot_paths=[[]],
  worksheet_name='plots',
  x_scale=65/140,
  y_scale=90/182,
  row_interval=20,
  column_interval=12,
  plot_header_text=[],
  missing_plot_path_text='no plot available'
):
  """ 
  Embeds graphs using xlsxwriter.
  workbook: writer.book of pd.ExcelWriter or xlsxwriter.Workbook(filename) 
  """
  worksheet = workbook.add_worksheet(worksheet_name)

  # Optional column headers above each plot column
  if plot_header_text:
    headers = plot_header_text if isinstance(plot_header_text, (list, tuple)) else [plot_header_text]
    for i, header in enumerate(headers):
      if i >= len(lists_of_plot_paths):
        break
      col_start = (i * column_interval) + 2
      worksheet.write(0, col_start, header)

  for i, plot_list in enumerate(lists_of_plot_paths):
    row_start = 2
    col_start = (i * column_interval) + 2
    col_name = xlsxwriter.utility.xl_col_to_name(col_start)

    for n, plot_path in enumerate(plot_list):
      image_start_cell = f"{col_name}{row_start + 1}"  # Excel is 1-indexed
      if plot_path and os.path.isfile(str(plot_path)):
        try:
          worksheet.insert_image(image_start_cell, str(plot_path), {
            'x_scale': x_scale,
            'y_scale': y_scale
          })
        except Exception as e:
          print(traceback.format_exc())
          worksheet.write(image_start_cell, f"Invalid: {plot_path}")
      else:
        worksheet.write(image_start_cell, missing_plot_path_text)
      row_start += row_interval
