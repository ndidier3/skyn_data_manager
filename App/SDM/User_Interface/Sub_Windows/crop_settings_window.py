from tkinter import *
from tkinter import filedialog, StringVar, IntVar
from tkinter.filedialog import askopenfile
from tkinter import messagebox
import pandas as pd
import os

class CropSettingsWindow(Toplevel):
  def __init__(self, parent):
    super().__init__(parent)
    self.title("Cropping Parameters")
    self.geometry("400x600")
    self.parent = parent
    self.main = parent.parent
        
    self.crop_window = None
    self.cropHeader = Label(self, text = 'Crop TAC Datasets')
    self.cropHeader.config(font=(None, 12, 'bold'))
    self.cropHeader.grid(row=0, column=0, padx=5, pady=(3,7))

    # set max episode duration
    self.max_dataset_duration = self.main.max_dataset_duration
    self.maxDatasetDurationVariable = IntVar()
    self.maxDatasetDurationVariable.set(self.max_dataset_duration) 
    self.maxDatasetDurationLabelText = 'What is the max number of hours to include in a dataset?'
    self.maxDatasetDurationLabel = Label(self, text = self.maxDatasetDurationLabelText)
    self.validate_max_dataset_duration = self.register(lambda P: len(P) <= 2)
    self.maxDatasetDurationEntry = Entry(self, text = self.maxDatasetDurationVariable, width = 6, validate="key", validatecommand=(self.validate_max_dataset_duration, "%P"))
    self.maxDatasetDurationLabel.grid(row=1, column=0, padx=5, pady=(5, 2))
    self.maxDatasetDurationEntry.grid(row=2, column=0, padx=5, pady=(2, 5))

    #Select timestamps dataset to indicate starting time of drinking episode

    self.cropBeginningCheckboxText = 'Check to crop datasets before designated timestamps.'
    self.cropBeginningVariable = IntVar()
    self.cropBeginningCheckbox = Checkbutton(self, text = self.cropBeginningCheckboxText, command = self.show_crop_fields, variable = self.cropBeginningVariable)
    self.cropBeginningCheckbox.grid(row=3, column=0, padx=5, pady=5)
    
    self.data_download_timezone = self.main.data_download_timezone
    self.timezoneVariable = IntVar()
    self.timezoneVariable.set(self.data_download_timezone)
    self.timezoneLabelText = "1. In which time zone was the data downloaded?\nIf participants downloaded their data, enter 999."
    self.timezoneLabel = Label(self, text = self.timezoneLabelText)
    self.timezoneEntry = Entry(self, text = self.timezoneVariable, width = 6)

    self.timestamps_filename = self.main.timestamps_filename
    self.timestamps_data = pd.DataFrame()
    self.timestampsLabelText = "2. Select Excel file that includes participants'\ntime zone and episode start times."
    self.timestampsLabel = Label(self, text = self.timestampsLabelText, width=50)
    self.timestampsButton = Button(self, width = 35, text='Select Excel file', command=self.select_timestamps_file)

    self.submitButton = Button(self, width = 15, text='Submit', fg='blue', command=self.submit)
    self.submitButton.grid(row=10, column=0, pady=(15, 7))

  def show_crop_fields(self):
    if self.cropBeginningVariable.get() == 1:
      self.timezoneLabel.grid(row = 4, column = 0, padx = 5, pady = 5)
      self.timezoneEntry.grid(row = 5, column = 0, padx = 5, pady = 5)
      self.timestampsLabel.grid(row=6, column=0, padx = 5, pady = 5)
      self.timestampsButton.grid(row=7, column=0, padx=5, pady=5)
    else:
      self.timezoneLabel.grid_forget()
      self.timezoneEntry.grid_forget()
      self.timestampsLabel.grid_forget()
      self.timestampsButton.grid_forget()
      self.timestamps_filename = None
  
  def select_timestamps_file(self):
    file = filedialog.askopenfile(mode='r', filetypes=[('Excel file with timestamps', '*.xlsx')])
    if file:
      excel_file = os.path.abspath(file.name)
      self.timestampsButton['text'] = f'2. Timestamps: {str(file.name.split("/")[-1])}'
      self.timestamps_filename = file.name
      self.timestamps_data = pd.read_excel(excel_file)
  
  def submit(self):
    if not self.timezoneEntry.get().lstrip('-').isdigit() and self.timezoneEntry.get() != 999:
      messagebox.showerror('SDM Error', 'Timezone must be an integer corresponding to a UTC timezone, unless participants downloaded their own Skyn data, in which case use 999.')
    elif not self.maxDatasetDurationEntry.get().isnumeric():
      messagebox.showerror('SDM Error', 'Max dataset duration must be an integer')
    else:
      self.main.update_crop_settings(int(self.maxDatasetDurationEntry.get()), int(self.timezoneEntry.get()), self.timestamps_filename)
      self.destroy()
    