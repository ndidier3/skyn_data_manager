from tkinter import *
from tkinter import filedialog, StringVar, IntVar
from tkinter.filedialog import askopenfile
from tkinter import messagebox
import pandas as pd
import os
import traceback
from SDM.Configuration.configuration import update_column_names
from SDM.Configuration.modify_filenames import generate_random_id
from SDM.Configuration.split_skyn_dataset import split_skyn_dataset

class FileSplittingToolWindow(Toplevel):
  def __init__(self, parent, main_window):
    super().__init__(parent)

    self.geometry("350x100")
    self.title('Skyn Dataset Splitter')

    self.parent = parent
    self.main_window = main_window

    self.header = Label(self, text = "Complete the following prompts to split a \nSkyn dataset into multiple datasets", font = self.main_window.header_style)
    self.header.grid(row=0, column=0, padx=(8, 2), pady=5)

    self.frame = Frame(self)
    self.frame.grid(row=1, column=0)

    self.data_to_split = pd.DataFrame()
    self.selectFileButton = Button(self.frame, text = "Select File to Split", command = self.open_file)
    self.selectedFileLabel = Label(self.frame, text = "", font=self.main_window.label_style)
    self.selectedFileLabel.grid(row=1, column=0, pady=(5,2), padx=(0,5), sticky='w')
    self.selectFileButton.grid(row=1, column=1, pady=(5,2), padx=(5,0), sticky='e')

    self.split_time_options = [str(i+1) + ':00' for i in range(0, 24)]
    self.split_time = StringVar()
    self.split_time.set(None)
    self.splitTimeStartLabel = Label(self.frame, text = 'Select the hour of the day where splitting should occur.', font=self.main_window.label_style)
    self.splitTimeOptionMenu = OptionMenu(self.frame, self.split_time, *self.split_time_options, command=self.show_interval_options)

    self.interval_options = ['Day-Level']
    self.interval = StringVar()
    self.interval.set(None)
    self.intervalLabel = Label(self.frame, text = f'Select frequency at which the data should be split at {self.split_time.get()}', font=self.main_window.label_style)
    self.intervalOptionMenu = OptionMenu(self.frame, self.interval, *self.interval_options, command = self.show_remaining_prompts)

    self.exclude_intervals = IntVar()
    self.excludeIntervalsCheckbuttonLabel = Label(self.frame, text = 'Check the box to exclude data at certain times of the day.', font=self.main_window.label_style)
    self.excludeIntervalsCheckbutton = Checkbutton(self.frame, text ='', variable=self.exclude_intervals, command=self.show_exclude_interval_options)

    self.exclude_start_options = [str(i+1) + ':00' for i in range(0, 24)]
    self.exclude_start = StringVar()
    self.exclude_start.set(None)
    self.excludeStartLabel = Label(self.frame, text = 'Select time to begin excluding data.', font=self.main_window.label_style)
    self.excludeStartOptionMenu = OptionMenu(self.frame, self.exclude_start, *self.exclude_start_options, command = lambda x: self.exclude_start.set(x))

    self.exclude_end_options = [str(i+1) + ':00' for i in range(0, 24)]
    self.exclude_end = StringVar()
    self.exclude_end.set(None)
    self.excludeEndLabel = Label(self.frame, text = 'Select time to finish excluding data.', font=self.main_window.label_style)
    self.excludeEndOptionMenu = OptionMenu(self.frame, self.exclude_end, *self.exclude_end_options, command = lambda x: self.exclude_end.set(x))

    self.one_subject = IntVar()
    self.oneSubidLabel = Label(self.frame, text = 'Check the box if all data corresponds to a single person.', font=self.main_window.label_style)
    self.oneSubidCheckbutton = Checkbutton(self.frame, variable = self.one_subject, command = self.show_subid)

    validate_numeric = self.register(lambda P: (P.isdigit() and len(P) <= 6) or len(P) == 0)
    self.subidLabel = Label(self.frame, text = 'Enter SubID', font=self.main_window.label_style)
    self.subidEntry = Entry(self.frame, width = 15, validate='key', validatecommand=(validate_numeric, "%P"))

    self.executeFileSplittingButton = Button(self, text = 'Split Files', command = self.split_file)

  def open_file(self):
    file = filedialog.askopenfile(mode='r', filetypes=[('Skyn Dataset','*.xlsx'), ('Skyn Dataset','*.csv')])
    self.geometry("500x500")
    self.grab_set()
    self.lift()
    if file:
      filepath = os.path.abspath(file.name)
      self.filepath = filepath
      self.export_folder = os.path.dirname(filepath) + '/'
      if filepath[-3:] == 'csv':
        self.data_to_split = pd.read_csv(filepath)
      else:
        self.data_to_split = pd.read_excel(filepath)

      self.data_to_split = update_column_names(self.data_to_split)
      self.data_to_split.sort_values(by="datetime", inplace=True)
      self.selectedFileLabel['text'] = f'Selected File: {file.name.split("/")[-1]}'
      self.selectedFileLabel.config(fg='green')
      self.splitTimeStartLabel.grid(row=3, column=0, pady=(5,2), padx=(0,5), sticky='w')
      self.splitTimeOptionMenu.grid(row=3, column=1, pady=(5,2), padx=(5,0), sticky='e')

  def show_interval_options(self, val):
    self.split_time.set(val)
    if val:
      self.intervalLabel['text'] = f'Select frequency at which the data should be split at {self.split_time.get()}'
      self.intervalLabel.grid(row=4, column=0, pady=(5,2), padx=(0,5), sticky='w')
      self.intervalOptionMenu.grid(row=4, column=1, pady=(5,2), padx=(5,0), stick='e')
    else:
      self.intervalLabel.grid_forget()
      self.intervalOptionMenu.grid_forget()
      self.excludeStartLabel.grid_forget()
      self.excludeStartOptionMenu.grid_forget()
      self.excludeEndLabel.grid_forget()
      self.excludeEndOptionMenu.grid_forget()

  def show_remaining_prompts(self, val):
    self.interval.set(val)
    self.show_subid_id_checkbox(val)
    self.show_exclude_intervals_checkbox(val)
    self.show_file_split_button(val)
  
  def show_subid_id_checkbox(self, val):
    if val:
      self.oneSubidLabel.grid(row = 10, column = 0, pady=(5,2), padx=(0, 5), sticky='e')
      self.oneSubidCheckbutton.grid(row = 10, column = 1, pady=(5,2), padx=(5,0), sticky='e')
    else:
      self.oneSubidLabel.grid_forget()
      self.oneSubidCheckbutton.grid_forget()

  def show_exclude_intervals_checkbox(self, val):
    if val:
      self.excludeIntervalsCheckbuttonLabel.grid(row = 5, column = 0, pady=(5,2), padx=(0, 5), sticky='w')
      self.excludeIntervalsCheckbutton.grid(row = 5, column = 1, pady=(5,2), padx=(5,0), sticky = 'e')
    else:
      self.excludeIntervalsCheckbuttonLabel.grid_forget()
      self.excludeIntervalsCheckbutton.grid_forget()

  def show_exclude_interval_options(self):
    if self.exclude_intervals.get() == 1:
      self.excludeStartLabel.grid(row=7, column=0, pady=(5, 2), padx=(30,5), sticky='w')
      self.excludeStartOptionMenu.grid(row=7, column=1, pady=(2, 5), padx=(5,20), sticky='e')
      self.excludeEndLabel.grid(row=8, column=0, pady=(5, 2), padx=(30,5), sticky='w')
      self.excludeEndOptionMenu.grid(row=8, column=1, pady=(2, 5), padx=(5,20), sticky='e')
    else:
      self.excludeStartLabel.grid_forget()
      self.excludeStartOptionMenu.grid_forget()
      self.excludeEndLabel.grid_forget()
      self.excludeEndOptionMenu.grid_forget()
      # self.

  def show_subid(self):
    if self.one_subject.get() == 1:
      self.subidLabel.grid(row=11, column = 0, pady=(5,2), padx=(30,5), sticky='w')
      self.subidEntry.grid(row=11, column=1, pady=(5,2), padx=(5,0), sticky='e')
    else:
      self.subidLabel.grid_forget()
      self.subidEntry.grid_forget()

  def show_file_split_button(self, val):
    if val:
      self.executeFileSplittingButton.grid(row=15, column=0, padx=10, pady=10)
    else:
      self.executeFileSplittingButton.grid_forget()

  def get_data_duration(self):
    return self.data_to_split['datetime'].max() - self.data_to_split['datetime'].min()
  
  def split_file(self):
    try:
      datasets = split_skyn_dataset(self.data_to_split, self.split_time.get(), self.interval.get(), self.exclude_start.get(),self.exclude_end.get())
      subid = self.subidEntry.get() if self.subidEntry.get() else None
      subids = []
      dataset_identifiers = []
      start_timestamps = []
      end_timestamps = []

      if not os.path.exists(self.export_folder + f'DayLevel_{os.path.splitext(os.path.basename(self.filepath))[0]}'):
        os.mkdir(self.export_folder + f'DayLevel_{os.path.splitext(os.path.basename(self.filepath))[0]}')

      i = 1
      for timeframe, dataset in datasets.items():
        subid = subid if subid else generate_random_id()
        subids.append(subid)
        dataset_identifier = "".join(['0' for _ in range(0, 3 - len(str(i)))] + [str(d) for d in str(i)])
        dataset_identifiers.append(dataset_identifier)
        start_timestamps.append(min(dataset['datetime']))
        end_timestamps.append(max(dataset['datetime']))
        filename = self.export_folder + f'DayLevel_{os.path.splitext(os.path.basename(self.filepath))[0]}/{subid}_{dataset_identifier}.xlsx'
        dataset.to_excel(filename, index=False, sheet_name="data")
        i += 1
      
      split_details = pd.DataFrame({'SubID': subids,
                    'Dataset_Identifiers': dataset_identifiers,
                    'Start_Timestamp': start_timestamps,
                    'End_Timestamp': end_timestamps})
      split_details.to_excel(self.export_folder + f'Split_Details_{os.path.splitext(os.path.basename(self.filepath))[0]}.xlsx', index=False)

      messagebox.showinfo('SDM Update', f'Split files are saved here: {self.export_folder}DayLevel_{os.path.splitext(os.path.basename(self.filepath))[0]}/')
      
    except Exception:
      print(traceback.format_exc())
      messagebox.showerror('SDM Error', f'Failed to split files. Error likely due to format of timestamps:\n{traceback.format_exc()}')


    
