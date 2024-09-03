from tkinter import *
from tkinter import filedialog, StringVar, IntVar
from tkinter.filedialog import askopenfile
from tkinter import messagebox
import pandas as pd
import os
import traceback
from SDM.Configuration.configuration import update_column_names
from SDM.Configuration.modify_filenames import generate_random_id
from SDM.Configuration.split_skyn_dataset import *

class FileSplittingToolWindow(Toplevel):
  def __init__(self, parent, main_window):
    super().__init__(parent)

    self.geometry("350x200")
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

    self.subidAssignmentMethods = {
      'Single individual -- Manually assign SubID': 1,
      'Single individual -- Generate random SubID': 2,
      'Multiple individuals -- Split by unique emails and manually assign SubIDs': 3,
      'Multiple individuals -- Split by unique emails and generate random SubIDs': 4
    }
    self.subidAssignmentMethodLabel = Label(self.frame, text="How would you like to assign SubIDs?")
    self.subidAssignmentMethodVar = StringVar()
    self.subidAssignmentMethodVar.set(list(self.subidAssignmentMethods.keys())[1])  # Set default value

    self.subidAssignmentMethodDropmenu = OptionMenu(self.frame, self.subidAssignmentMethodVar, *self.subidAssignmentMethods.keys(), command=self.toggle_subid_assignment_method)

    self.validate_numeric = self.register(lambda P: (P.isdigit() and len(P) <= 6) or len(P) == 0)
    self.subidLabel = Label(self.frame, text = 'Enter SubID', font=self.main_window.label_style)
    self.subidEntry = Entry(self.frame, width = 15, validate='key', validatecommand=(self.validate_numeric, "%P"))

    self.assign_subid_by_email_table = LabelFrame(self)

    self.executeFileSplittingButton = Button(self, text = 'Split Files', command = self.split_file)

  def open_file(self):
    file = filedialog.askopenfile(mode='r', filetypes=[('Skyn Dataset','*.xlsx'), ('Skyn Dataset','*.csv')])
    self.geometry("900x600")
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

  def show_remaining_prompts(self, val):
    self.show_subid_assignment_options(val)
    self.show_file_split_button(val)
  
  def show_subid_assignment_options(self, val):
    if val:
      self.subidAssignmentMethodLabel.grid(row=11, column = 0, pady=(5,2), padx=(0,5), sticky='w')
      self.subidAssignmentMethodDropmenu.grid(row=11, column=1, pady=(5,2), padx=(5,0), sticky='e')
    else:
      self.subidAssignmentMethodLabel.grid_forget()
      self.subidAssignmentMethodDropmenu.grid_forget()

  def show_file_split_button(self, val):
    if val:
      self.executeFileSplittingButton.grid(row=20, column=0, padx=10, pady=10)
    else:
      self.executeFileSplittingButton.grid_forget()

  def toggle_subid_assignment_method(self, val):
    self.subidAssignmentMethodVar.set(val)
    key = self.subidAssignmentMethods[val]
    if key == 1 or key == 3:
      if key == 1:
        self.subidLabel.grid(row=12, column = 0, pady=(5,2), padx=(30,5), sticky='w')
        self.subidEntry.grid(row=12, column=1, pady=(5,2), padx=(5,0), sticky='e')
        self.assign_subid_by_email_table.grid_forget()
      else:
        self.subidLabel.grid_forget()
        self.subidEntry.grid_forget()

      if key == 3:
        self.show_assign_subid_by_email_table()
        self.subidLabel.grid_forget()
        self.subidEntry.grid_forget()
      else:
        self.assign_subid_by_email_table.grid_forget()
    else:
      self.subidLabel.grid_forget()
      self.subidEntry.grid_forget()
      self.assign_subid_by_email_table.grid_forget()

  def show_assign_subid_by_email_table(self):
    self.assign_subid_by_email_table.grid(row=15, column=0, pady=(20, 2), padx=(0, 5), sticky='w', columnspan=2)
    Label(self.assign_subid_by_email_table, text="Email", font=self.main_window.label_style).grid(row=0, column=0, sticky="w", padx=3, pady=3)
    Label(self.assign_subid_by_email_table, text="SubID", font=self.main_window.label_style).grid(row=0, column=1, sticky="w", padx=3, pady=3)

    emails = self.data_to_split['email'].unique()
    self.subid_entries_per_email = {}

    for i, email in enumerate(emails):
      Label(self.assign_subid_by_email_table, text=email, font=self.main_window.label_style).grid(row=i+1, column=0, sticky="w", padx=3, pady=1)
      entry = Entry(self.assign_subid_by_email_table, width=10, validate='key', validatecommand=(self.validate_numeric, "%P"))
      entry.grid(row=i+1, column=1, sticky="w", padx=3, pady=1)
      self.subid_entries_per_email[email] = entry

  def split_file(self):
    key = self.subidAssignmentMethods[self.subidAssignmentMethodVar.get()]
    if key == 1 or key == 2:
      try:
        datasets = split_skyn_dataset(self.data_to_split, self.split_time.get())
        subid = self.subidEntry.get() if (self.subidEntry.get() and key == 2) else None
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
    if key == 3 or key == 4:
      try:
        if key == 3:
          for email, entry in self.subid_entries_per_email.items():
              subid = entry.get()
              if not subid or not subid.isdigit() or len(subid) > 6:
                  messagebox.showerror('SDM Error', f'Please ensure all SubIDs are filled in correctly with up to 6 digits for each email.')
                  return None
                    
        datasets_by_email = split_skyn_dataset_by_email(self.data_to_split, self.split_time.get())
        subids = []
        emails = []
        dataset_identifiers = []
        start_timestamps = []
        end_timestamps = []

        output_folder = self.export_folder + f'DayLevel_{os.path.splitext(os.path.basename(self.filepath))[0]}'
        if not os.path.exists(output_folder):
            os.mkdir(output_folder)

        i = 1
        for email, datasets in datasets_by_email.items():
            for timeframe, dataset in datasets.items():
                subid = self.subid_entries_per_email[email].get() if key == 3 else generate_random_id()
                subids.append(subid)
                emails.append(email)
                dataset_identifier = f"{i:03d}"  # Pad the identifier to 3 digits
                dataset_identifiers.append(dataset_identifier)
                start_timestamps.append(min(dataset['datetime']))
                end_timestamps.append(max(dataset['datetime']))
                filename = f"{output_folder}/{subid}_{dataset_identifier}.xlsx"
                dataset.to_excel(filename, index=False, sheet_name="data")
                i += 1

        split_details = pd.DataFrame({
            'Email': emails,
            'SubID': subids,
            'Dataset_Identifiers': dataset_identifiers,
            'Start_Timestamp': start_timestamps,
            'End_Timestamp': end_timestamps
        })
        split_details.to_excel(self.export_folder + f'Split_Details_{os.path.splitext(os.path.basename(self.filepath))[0]}.xlsx', index=False)

        messagebox.showinfo('SDM Update', f'Split files are saved here: {output_folder}/')

      except:
        print(traceback.format_exc())
        messagebox.showerror('SDM Error', f'Failed to split files. Error likely due to format of timestamps:\n{traceback.format_exc()}')
    
