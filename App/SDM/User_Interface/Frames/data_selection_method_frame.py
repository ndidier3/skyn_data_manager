from tkinter import *
from tkinter import StringVar

class DataSelectionMethodFrame(Frame):
  def __init__(self, parent, main_window):
    super().__init__(parent)
    self.grid()
    self.main_window = main_window
    self.data_selection_method = self.main_window.data_selection_method

    self.header = Label(self, text='Select data loading method:')
    self.header.grid(row=0, column=0, padx=5, pady=(3, 3), sticky='w')
    self.header.config(font=(None, 10, 'bold'))

    self.var = StringVar()
    self.var.set(None)

    custom_font = ('Arial', 9)
    self.loadFolderRadiobutton = Radiobutton(self, text = 'Load folder containing cohort of raw, unprocessed data (.xlsx or .csv). Configuration required.', command=self.update_data_selection_method, variable=self.var, value = 'Folder', font=custom_font)
    self.loadFolderRadiobutton.grid(row=1, column=0, padx=5, pady=1, sticky='w')

    self.loadSingleDatasetRadiobutton = Radiobutton(self, text = 'Load a single file of raw, unprocessed data (.xlsx or .csv). Configuration required.', command=self.update_data_selection_method, variable=self.var, value = 'Single', font=custom_font)
    self.loadSingleDatasetRadiobutton.grid(row=2, column=0, padx=5, pady=1, sticky='w')

    self.loadPreviousProcessorRadiobutton = Radiobutton(self, text = 'Load a previously saved SDM processor (.pickle). This means data is already processed.', command=self.update_data_selection_method, variable=self.var, value = 'Processor', font=custom_font)
    self.loadPreviousProcessorRadiobutton.grid(row=3, column=0, padx=5, pady=1, sticky='w')

    self.runTestRadiobutton = Radiobutton(self, text='Use example data (Folder = Raw/Test/) with default settings.', command=self.update_data_selection_method, variable=self.var, value='Test', font=custom_font)
    self.runTestRadiobutton.grid(row=4, column=0, padx=5, pady=1, sticky='w')
  
  def update_data_selection_method(self):
    self.data_selection_method = self.var.get()
    self.main_window.update_data_selection_method(self.data_selection_method)

    

