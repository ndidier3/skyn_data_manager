from tkinter import *
from tkinter import filedialog, StringVar, IntVar
from tkinter.filedialog import askopenfile
from tkinter import messagebox
import pandas as pd
import os

class DataConfigurationWindow(Toplevel):
  def __init__(self, parent, file_to_parse_metadata):
    super().__init__(parent)

    self.geometry("500x600")
    self.title('Configure Data')

    self.parent = parent
    self.file_to_parse_metadata = file_to_parse_metadata

    self.configurationLabel = Label(self, text = 'Data Loading Configuration')
    self.configurationLabel.config(font=(None, 11, 'bold'))

    #display filename
    self.cohort_filename_example = ''
    self.filenameExampleLabelText = f'First file in cohort data folder:\n {self.cohort_filename_example}'
    self.filenameExampleLabel = Label(self, text = self.filenameExampleLabelText)
    self.filenameExampleLabel.config(font=(None, 9, 'italic'))
    
    print(self.file_to_parse_metadata, 'within window')
    self.filename_indices_UI = [f'{c} (index = {i})' for i, c in enumerate(self.file_to_parse_metadata)]

    #Subject ID search
    self.subidSearchCharacterLabelText = 'Select the first character of Subject ID:'
    self.subidSearchCharacterLabel = Label(self, text = self.subidSearchCharacterLabelText)
    self.subid_index_start = StringVar(self)
    self.subid_index_start.set(None)
    self.subidSearchCharacterOptionMenu = OptionMenu(self, self.subid_index_start, *self.filename_indices_UI)

    self.subidSearchEndLabelText = 'Select the last character of Subject ID:'
    self.subidSearchEndLabel = Label(self, text = self.subidSearchEndLabelText)
    self.subid_index_end = StringVar(self)
    self.subid_index_end.set(None)
    self.subidSearchEndOptionMenu = OptionMenu(self, self.subid_index_end, *self.filename_indices_UI)

    #Condition search
    self.conditionSearchCharacterLabelText = 'Select the first character of Condition:'
    self.conditionSearchCharacterLabel = Label(self, text = self.conditionSearchCharacterLabelText)
    self.condition_index_start = StringVar(self)
    self.condition_index_start.set(None)
    self.conditionSearchCharacterOptionMenu = OptionMenu(self, self.condition_index_start, *self.filename_indices_UI)
    
    self.conditionSearchEndLabelText = 'Select the last character of Condition:'
    self.conditionSearchEndLabel = Label(self, text = self.conditionSearchEndLabelText)
    self.condition_index_end = StringVar(self)
    self.condition_index_end.set(None)
    self.conditionSearchEndOptionMenu = OptionMenu(self, self.condition_index_end, *self.filename_indices_UI)

    #Sub Condition search

    self.episodeIdentifierRequired= IntVar()
    self.episodeIdentifierCheckbox = Checkbutton(self, text='Check if Episode Identifiers are in filenames.\n Only necessary for distinguishing multiple datasets \n of the same SubID and Condition.', variable=self.episodeIdentifierRequired, command=self.show_episode_identifier_fields)

    self.episodeIdentifierSearchCharacterLabelText = 'Select the first character of Episode Identifier:'
    self.episodeIdentifierSearchCharacterLabel = Label(self, text = self.episodeIdentifierSearchCharacterLabelText)
    self.episode_identifier_index_start = StringVar(self)
    self.episode_identifier_index_start.set(None)
    self.episodeIdentifierSearchCharacterOptionMenu = OptionMenu(self, self.episode_identifier_index_start, *self.filename_indices_UI)
    
    self.episodeIdentifierSearchEndLabelText = 'Select the last character of Episode Identifier:'
    self.episodeIdentifierSearchEndLabel = Label(self, text = self.episodeIdentifierSearchEndLabelText)
    self.episode_identifier_index_end = StringVar(self)
    self.episode_identifier_index_end.set(None)
    self.episodeIdentifierSearchEndOptionMenu = OptionMenu(self, self.episode_identifier_index_end, *self.filename_indices_UI)
    
    self.filenameExampleLabel['text'] = f'First file in folder: {self.file_to_parse_metadata.split("/")[0]}'
    self.configurationLabel.grid(row=5, column=1, padx=5, pady=3)
    self.filenameExampleLabel.grid(row=6, column=1, padx=5, pady=1)
    self.subidSearchCharacterLabel.grid(row=7, column=1, padx=5, pady=(1, 0))
    self.subidSearchCharacterOptionMenu.grid(row=8, column=1, padx=5, pady=(0, 1))
    self.subidSearchEndLabel.grid(row=9, column=1, padx=(1, 0))
    self.subidSearchEndOptionMenu.grid(row=10, column=1, padx=5, pady=(0, 1))
    self.conditionSearchCharacterLabel.grid(row=11, column=1, padx=5, pady=(1, 0))
    self.conditionSearchCharacterOptionMenu.grid(row=12, column=1, padx=5, pady=(0, 1))
    self.conditionSearchEndLabel.grid(row=13, column=1, padx=5, pady=(1, 0))
    self.conditionSearchEndOptionMenu.grid(row=14, column=1, padx=5, pady=(0, 1))
    self.episodeIdentifierCheckbox.grid(row=15, column=1, padx=5, pady=(3,2))

    self.nextButton = Button(self, text = 'Next', command=self.next) 
    self.nextButton.grid(row=20, column=1, padx=5, pady=5, sticky='se')   
    
  def show_episode_identifier_fields(self):
    if self.episodeIdentifierRequired.get() == 1:
      self.episodeIdentifierSearchCharacterLabel.grid(row=16, column=1, padx=5, pady=(1, 0))
      self.episodeIdentifierSearchCharacterOptionMenu.grid(row=17, column=1, padx=5, pady=(0, 1))
      self.episodeIdentifierSearchEndLabel.grid(row=18, column=1, padx=5, pady=(1, 0))
      self.episodeIdentifierSearchEndOptionMenu.grid(row=19, column=1, padx=5, pady=(0, 1))
    else:
      self.episodeIdentifierSearchCharacterLabel.grid_forget()
      self.episodeIdentifierSearchCharacterOptionMenu.grid_forget()
      self.episodeIdentifierSearchEndLabel.grid_forget()
      self.episodeIdentifierSearchEndOptionMenu.grid_forget()    

  def next(self):
    self.parsing_indices = [
      self.filename_indices_UI.index(self.subid_index_start.get()) if self.subid_index_start.get() in self.filename_indices_UI else None,
      self.filename_indices_UI.index(self.subid_index_end.get()) if self.subid_index_end.get() in self.filename_indices_UI else None,
      self.filename_indices_UI.index(self.condition_index_start.get()) if self.condition_index_start.get() in self.filename_indices_UI else None,
      self.filename_indices_UI.index(self.condition_index_end.get()) if self.condition_index_end.get() in self.filename_indices_UI else None,
      self.filename_indices_UI.index(self.episode_identifier_index_start.get()) if self.episode_identifier_index_start.get() in self.filename_indices_UI else None,
      self.filename_indices_UI.index(self.episode_identifier_index_end.get()) if self.episode_identifier_index_end.get() in self.filename_indices_UI else None
    ]
    print('parsing indices', self.parsing_indices)

    if any(item is None for item in self.parsing_indices[:4]):
      messagebox.showerror('SDM Error', 'Please select indices for SubID and Condition.')
    else:
      self.configurationLabel.grid_forget()
      self.filenameExampleLabel.grid_forget()
      self.subidSearchCharacterLabel.grid_forget()
      self.subidSearchCharacterOptionMenu.grid_forget()
      self.subidSearchEndLabel.grid_forget()
      self.subidSearchEndOptionMenu.grid_forget()
      self.conditionSearchCharacterLabel.grid_forget()
      self.conditionSearchCharacterOptionMenu.grid_forget()
      self.conditionSearchEndLabel.grid_forget()
      self.conditionSearchEndOptionMenu.grid_forget()
      self.episodeIdentifierCheckbox.grid_forget()
      self.episodeIdentifierSearchCharacterLabel.grid_forget()
      self.episodeIdentifierSearchCharacterOptionMenu.grid_forget()
      self.episodeIdentifierSearchEndLabel.grid_forget()
      self.episodeIdentifierSearchEndOptionMenu.grid_forget()
      self.nextButton.grid_forget()
      self.parent.update_filename_parsing(self.parsing_indices)
      data = self.parent.prepare_filename_data()
      self.episode_labels = Variable(
        value = [f'Subject: {data["SubID"][i]} | Condition: {data["Condition"][i]} | ID: {data["Episode_Identifier"][i] if data["Episode_Identifier"][i] else "NA"}' for i in range(0, len(data['SubID']))])
      
      self.fileDataListbox = Listbox(self, selectmode="none", height=18, width=60, listvariable=self.episode_labels)
      self.fileDataListbox.grid(row=22, column=1, padx=5, pady=5)

      self.verifyLabel = Label(self, text = 'Are filenames parsed correctly?')
      self.verifyLabel.grid(row=23, column=1, padx=5, pady=(7, 2))

      self.yes_no_frame = Frame(self)
      self.yes_no_frame.grid(row=24, column=1)

      self.yesButton = Button(self.yes_no_frame, text = 'Yes', width = 10, command = self.submit)
      self.yesButton.grid(column=0, row=0, padx=(0, 10), pady=5)
      self.noButton = Button(self.yes_no_frame, text = 'No', width = 10, command = self.back)
      self.noButton.grid(column=1, row=0, padx=(10, 0), pady=5)

  def submit(self):
    self.destroy()

  
  
  def back(self):
    self.configurationLabel.grid(row=5, column=1, padx=5, pady=3)
    self.filenameExampleLabel.grid(row=6, column=1, padx=5, pady=1)
    self.subidSearchCharacterLabel.grid(row=7, column=1, padx=5, pady=(1, 0))
    self.subidSearchCharacterOptionMenu.grid(row=8, column=1, padx=5, pady=(0, 1))
    self.subidSearchEndLabel.grid(row=9, column=1, padx=(1, 0))
    self.subidSearchEndOptionMenu.grid(row=10, column=1, padx=5, pady=(0, 1))
    self.conditionSearchCharacterLabel.grid(row=11, column=1, padx=5, pady=(1, 0))
    self.conditionSearchCharacterOptionMenu.grid(row=12, column=1, padx=5, pady=(0, 1))
    self.conditionSearchEndLabel.grid(row=13, column=1, padx=5, pady=(1, 0))
    self.conditionSearchEndOptionMenu.grid(row=14, column=1, padx=5, pady=(0, 1))
    self.episodeIdentifierCheckbox.grid(row=15, column=1, padx=5, pady=(3,2))
    self.nextButton.grid(row=20, column=1, padx=5, pady=5, sticky='se')

    self.fileDataListbox.grid_forget()
    self.verifyLabel.grid_forget()
    self.yes_no_frame.grid_forget()

    self.parsing_indices = [None for i in range(0, len(self.parsing_indices))]