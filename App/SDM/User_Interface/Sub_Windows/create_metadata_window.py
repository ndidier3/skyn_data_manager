from SDM.User_Interface.Utils.filename_tools import *
from SDM.User_Interface.Sub_Windows.rename_files_window import RenameFilesWindow
from tkinter import *
from tkinter import filedialog, StringVar, IntVar, Toplevel
from tkinter.filedialog import askopenfile
from tkinter import messagebox
from datetime import date
import traceback
import pandas as pd
import os

class CreateMetadataWindow(Toplevel):
  def __init__(self, main_window):
    super().__init__(main_window)
    self.main_window = main_window
    self.geometry("400x300")

    #FRAME
    self.metadata_frame = Frame(self, width=600, height=800, highlightbackground="black", highlightthickness=2)
    self.metadata_frame.grid(row=0, column=1, padx=7, pady=7)

    #Contained within frame...
    #Select Cohort Folder
    self.selectCohortFolder = Button(self.metadata_frame, text="Select Folder with Skyn Data", width=24, command=self.load_cohort_folder)
    self.selectCohortFolder.grid(row=0, column=1, pady=5, padx=5)

    #Select Cohort Name
    self.cohortNameLabelText = 'Cohort Name'
    self.cohortNameLabel = Label(self.metadata_frame, text = self.cohortNameLabelText)
    self.validate_cohort_name_length = self.metadata_frame.register(lambda P: len(P) <= 10)
    self.cohortNameEntry = Entry(self.metadata_frame, width = 20, validate="key", validatecommand=(self.validate_cohort_name_length, "%P")) 
    self.cohortNameLabel.grid(row=1, column=1, padx=5, pady=(10,2))
    self.cohortNameEntry.grid(row=2, column=1, padx=5, pady=(2,10))

    #To load after cohort folder and cohort name are selected...
    #InstructionalText
    self.instructions = 'Confirm that SubIDs, Conditions, and Dataset IDs have been properly read for each episode listed below.\nNext, select each episode that you want to exclude from analyses. \nTo create metadata file, click the button below.'
    self.instructionsLabel = Label(self.metadata_frame, text = self.instructions, anchor='w', justify='left')

    #A row for each file
    self.excludeSubidsListbox = Listbox(self.metadata_frame, selectmode=MULTIPLE, height=18, width=60)

    #when filesnmaed directory with skyn data are
    self.filenames_verified = False

    #When files are verified, show button to create metadata template
    self.createMetadataButton = Button(self.metadata_frame, text = 'Create metadata template (.xlsx)', width = 25, command=self.createMetadata, fg = 'blue')

  def verify_directory(self, directory):
    self.filenames_verified = directory_analysis_ready(directory)

    if self.filenames_verified:
      self.geometry("580x490")
      self.folder_metadata = create_metadata_from_cohort_folder(directory)
    else:
      renameFiles = RenameFilesWindow(self, directory, self.filenames)
      renameFiles.grab_set()
    
  def load_cohort_folder(self):
    cohort_data_folder = filedialog.askdirectory()
    self.lift()
    if cohort_data_folder:
      self.filenames = os.listdir(cohort_data_folder)
      self.verify_directory(cohort_data_folder + '/')
    
    print('verified?', self.filenames_verified)
    if self.filenames_verified:
      self.filenames = os.listdir(cohort_data_folder)
      subids = [extract_subid(filename) for filename in self.filenames]
      dataset_ids = [extract_dataset_identifier(filename) for filename in self.filenames]
      print(self.filenames)
      print(len(subids), 'subid list length')
      print(len(dataset_ids), 'id list length')
      print(dataset_ids)

      self.episode_labels = Variable(value = [f'Subject: {subids[i]} | ID: {dataset_ids[i]}' for i in range(0, len(subids))])
      self.instructionsLabel.grid(row=3, column=1, padx=5, pady=5)
      self.excludeSubidsListbox.configure(listvariable=self.episode_labels)
      self.excludeSubidsListbox.grid(row=4, column=1, padx=5, pady=5)
      self.createMetadataButton.grid(row=5, column=1, padx=5, pady=7)


  def createMetadata(self):
    try:
      self.selected_text_list = [i for i in self.excludeSubidsListbox.curselection()]
      self.folder_metadata['Use_Data'] = [self.folder_metadata['Use_Data'][i] if i not in self.selected_text_list else 'N' for i in range(0, len(self.folder_metadata['Use_Data']))]
      meta_df = pd.DataFrame(self.folder_metadata)
      meta_df.to_excel(f'Inputs/Metadata/{self.cohortNameEntry.get()}_Metadata.xlsx', index=False)
      messagebox.showinfo('Success', f'File created: Inputs/Metadata/{self.cohortNameEntry.get()}_Metadata.xlsx')
      self.destroy()
    except Exception:
      print(traceback.format_exc())
      messagebox.showerror('\Error creating metadata file', traceback.format_exc())
  
  # def create_metadata_from_file(self):
  #   file = os.path.split(self.selected_data)[-1]
  #   return {
  #     'SubID': [extract_subid(file)],
  #     'Dataset_Identifier': [extract_dataset_identifier(file, validate=False, assess_new=False)],
  #     'Use_Data': ["Y"],
  #     'TotalDrks': [""],
  #     'Notes': [""]
  #   }    


