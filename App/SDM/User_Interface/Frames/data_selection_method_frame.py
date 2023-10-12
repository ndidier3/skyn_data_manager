from tkinter import *
from tkinter import StringVar
from SDM.User_Interface.Sub_Windows.file_splitting_tool_window import FileSplittingToolWindow

class DataSelectionMethodFrame(Frame):
  def __init__(self, parent, main_window):
    super().__init__(parent)
    self.grid()
    self.main_window = main_window
    self.data_selection_method = self.main_window.data_selection_method

    self.openFileSplittingToolButton = Button(self, text = "Open File Splitting Tool", command=self.open_file_splitting_tool)
    self.openFileSplittingToolButton.grid(row=0, column=0, padx=5, pady=(5,10), sticky='w')

    self.header = Label(self, text='Select data loading method:', font=self.main_window.header_style)
    self.header.grid(row=1, column=0, padx=5, pady=(3, 3), sticky='w')

    self.var = StringVar()
    self.var.set(None)

    self.loadFolderRadiobutton = Radiobutton(self, text = 'Load folder containing cohort of raw, unprocessed data (.xlsx or .csv). Configuration required.', command=self.update_data_selection_method, variable=self.var, value = 'Folder', font=self.main_window.label_style)
    self.loadFolderRadiobutton.grid(row=2, column=0, padx=5, pady=1, sticky='w')

    self.loadSingleDatasetRadiobutton = Radiobutton(self, text = 'Load a single file of raw, unprocessed data (.xlsx or .csv). Configuration required.', command=self.update_data_selection_method, variable=self.var, value = 'Single', font=self.main_window.label_style)
    self.loadSingleDatasetRadiobutton.grid(row=3, column=0, padx=5, pady=1, sticky='w')

    self.loadPreviousProcessorRadiobutton = Radiobutton(self, text = 'Load a previously saved SDM processor (.pickle). This means data is already processed.', command=self.update_data_selection_method, variable=self.var, value = 'Processor', font=self.main_window.label_style)
    self.loadPreviousProcessorRadiobutton.grid(row=4, column=0, padx=5, pady=1, sticky='w')

    self.runTestRadiobutton = Radiobutton(self, text='Use example data (Folder = Raw/Test/) with default settings.', command=self.update_data_selection_method, variable=self.var, value='Test', font=self.main_window.label_style)
    self.runTestRadiobutton.grid(row=5, column=0, padx=5, pady=1, sticky='w')
  
  def update_data_selection_method(self):
    self.data_selection_method = self.var.get()
    self.main_window.update_data_selection_method(self.data_selection_method)

  def open_file_splitting_tool(self):
      sub_window = FileSplittingToolWindow(self, self.main_window)
      sub_window.grab_set()
      self.wait_window(sub_window)

    

