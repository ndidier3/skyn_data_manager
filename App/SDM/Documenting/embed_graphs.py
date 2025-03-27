import xlsxwriter

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

  for i, plot_list in enumerate(lists_of_plot_paths):
    row_start = 2
    col_start = (i * column_interval) + 2
    col_name = xlsxwriter.utility.xl_col_to_name(col_start)

    for n, plot_path in enumerate(plot_list):
      if plot_path:
        try:
          image_start_cell = f"{col_name}{row_start + 1}"  # Excel is 1-indexed
          worksheet.insert_image(image_start_cell, plot_path, {
            'x_scale': x_scale,
            'y_scale': y_scale
          })
        except Exception as e:
          error_cell = f"{col_name}{row_start + 1}"
          worksheet.write(error_cell, f"Invalid: {plot_path}")  # Insert text instead
      row_start += row_interval
