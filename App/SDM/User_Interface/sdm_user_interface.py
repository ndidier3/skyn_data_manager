from SDM.Skyn_Processors.skyn_cohort_processor import skynCohortProcessor
from SDM.Skyn_Processors.skyn_dataset_processor import skynDatasetProcessor
from SDM.Reporting.export import *
from SDM.Configuration.configuration import get_drink_count
from SDM.User_Interface.Frames.optional_settings_frame import OptionalSettingsFrame
from SDM.User_Interface.Frames.data_selection_method_frame import DataSelectionMethodFrame
from SDM.User_Interface.Frames.program_selection_frame import ProgramSelectionFrame
from SDM.User_Interface.Sub_Windows.create_metadata_window import CreateMetadataWindow
from SDM.User_Interface.Sub_Windows.filenames_confirmation_window import FilenamesConfirmationWindow
from SDM.User_Interface.Sub_Windows.rename_files_window import RenameFilesWindow
from SDM.User_Interface.Utils.filename_tools import *
from SDM.User_Interface.Utils.get_sdm_run_settings import get_sdm_run_settings
from SDM.User_Interface.Utils.get_font_size import get_font_size
from tkinter import *
from tkinter import filedialog, ttk
from tkinter import messagebox
from datetime import date, datetime
import pickle
import os
from pathlib import Path
import traceback
import pandas as pd

class SkynDataManagerApp(Tk):
  def __init__(self):
    super().__init__()
    self.geometry("1400x800")
    self.title("SDM")

    style = ttk.Style()
    style.configure("BW-Label", foreground="black", background="white", fontsize=14)
    style.configure("Header", foreground="black", background="white", fontsize=14)


    self.required_inputs_frame = Frame(self, highlightbackground="black", highlightthickness=3)
    self.required_inputs_frame.grid(row=0, column=0, padx=0, pady=0)
    
    self.header_style = (None, get_font_size('header'), 'bold')
    self.label_style = (None, get_font_size('label'))

    self.mainHeader = Label(self.required_inputs_frame, text = 'Skyn Data Manager', font=self.header_style)
    self.mainHeader.grid(row=0, column=1, padx=5, pady=8)

    self.data_selection_method = None
    self.data_selection_method_frame = DataSelectionMethodFrame(self.required_inputs_frame, self)
    self.data_selection_method_frame.grid(row=1, column=1, padx=5, pady=5, sticky='w')

    self.program = None
    self.program_selection_frame = ProgramSelectionFrame(self.required_inputs_frame, self)

    self.data_loading_frame = Frame(self.required_inputs_frame)

    self.x_separator_mid = ttk.Separator(self.required_inputs_frame, orient='horizontal')
    self.y_separator = ttk.Separator(self.data_loading_frame, orient='vertical')

    #Select data folder
    self.selected_data = ''
    self.selectDataLabelText = 'Select data:'
    self.selectDataLabel = Label(self.data_loading_frame, text = self.selectDataLabelText)
    self.selectDataButton = Button(self.data_loading_frame, width = 27, text='Select Data', command=self.select_skyn_data)

    #Configure data button
    self.configureData = Button(self.data_loading_frame, width = 27, text = 'Configure Data')

    #cohort name
    self.cohortNameLabelText = 'Cohort Name:'
    self.cohortNameLabel = Label(self.data_loading_frame, text = self.cohortNameLabelText)
    self.validate_cohort_name_length = self.register(lambda P: len(P) <= 10)
    self.cohortNameEntry = Entry(self.data_loading_frame, width = 20, validate="key", validatecommand=(self.validate_cohort_name_length, "%P"))    

    #select metadata
    self.metadata = None
    self.metadataLabelText = 'Select metadata:'
    self.metaselectDataLabel = Label(self.data_loading_frame, text = self.metadataLabelText)
    self.metadataFolderButton = Button(self.data_loading_frame, width = 20, text='Select metadata (.xlsx)', command=self.open_metadata)
    
    #create metadata
    self.createMetaselectDataLabelText = 'No metadata file created?'
    self.createMetaselectDataLabel = Label(self.data_loading_frame, text = self.createMetaselectDataLabelText)
    self.createMetadataButton = Button(self.data_loading_frame, text='Create metadata (.xlsx)', command=self.open_metadata_creator)

    self.runProgramButton = Button(self, text='RUN PROGRAM', fg='blue', command=self.run)
    self.cohortNameEntry.bind("<FocusOut>", self.show_run_button())

    #LOAD FILE DIRECTLY
    
    self.OptionsFrame = None

    self.models = {}
    self.files_to_merge = {}
    self.data_download_timezone = -5
    self.timestamps_filename = None
    self.max_dataset_duration = 24

    self.previous_processor = None
    self.subid_i_start = None
    self.subid_i_end = None
    self.condition_i_start = None
    self.condition_i_end = None
    self.episode_identifier_i_start = None
    self.episode_identifer_i_end = None
    self.episode_identifiers_required = False

    self.defaults_options = {
      'models': {},
      'files_to_merge': {},
      'data_download_timezone': -5,
      'timestamps_filename': None,
      'max_dataset_duration': 24,
    }

    self.update_idletasks()
    mainloop()
  
  def update_data_selection_method(self, selection):
    #possible selections are Processor, Folder, Single, or Test
    self.program = None
    if self.OptionsFrame:
        self.unload_optional_settings()
    self.data_selection_method = selection
    self.program_selection_frame.grid_forget()
    if self.data_selection_method != 'Processor':
      self.program_selection_frame = ProgramSelectionFrame(self.required_inputs_frame, self)
      self.program_selection_frame.grid(row=2, column=1, padx=5, pady=(0, 15), sticky='w')
      self.x_separator_mid.grid(row=3, column=1, columnspan=2, sticky='ew')
    self.unload_data()
    self.refresh_user_interface()

  def update_program(self, selection):
    self.program = selection
    self.refresh_user_interface()
  
  def refresh_user_interface(self):  
    if self.data_selection_method in ['Single', 'Folder', 'Processor']:
      self.data_loading_frame.grid_forget()
      self.selectDataLabel.grid_forget()
      self.selectDataButton.grid_forget()
      self.data_loading_frame.grid(row=4, column=1, padx=5, pady=0)
      self.selectDataLabel.grid(row=2, column=0, padx=(0, 50), pady=(2,0))
      self.selectDataButton.grid(row=3, column=0, padx=(0, 50), pady=(0,7))
    else: #Test
      self.data_loading_frame.grid_forget()
      self.selectDataLabel.grid_forget()
      self.selectDataButton.grid_forget()
      if self.OptionsFrame:
        self.OptionsFrame.grid_forget()
      
    if self.data_selection_method == 'Single' or self.data_selection_method == 'Folder':
      self.cohortNameLabel.grid(row=0, column=0, padx=(0, 50), pady=(2, 0))
      self.cohortNameEntry.grid(row=1, column=0, padx=(0, 50), pady=(0, 5))
      self.metaselectDataLabel.grid(row=0, column=2, padx=(50, 0), pady=(2, 0))
      self.metadataFolderButton.grid(row=1, column=2, padx=(50, 0), pady=(0, 5))
      self.createMetaselectDataLabel.grid(row=2, column=2, padx=(50, 0), pady=(2, 0))
      self.createMetadataButton.grid(row=3, column=2, padx=(50, 0), pady=(0, 7))
      self.y_separator.grid(row=0, column=1, rowspan=6, sticky='ns')
    else:
      self.metaselectDataLabel.grid_forget()
      self.metadataFolderButton.grid_forget()
      self.cohortNameLabel.grid_forget()
      self.cohortNameEntry.grid_forget()
      self.createMetaselectDataLabel.grid_forget()
      self.createMetadataButton.grid_forget()
      self.y_separator.grid_forget()

    if self.data_selection_method == 'Single':
      self.selectDataButton['text'] = 'Select Dataset (.xlsx or .csv)'
      self.selectDataButton.config(width = 27)
    elif self.data_selection_method == 'Processor':
      self.selectDataButton['text'] = 'Select Processor (.pickle)'
      self.selectDataButton.grid(row=3, column=0, padx=5, pady=5)
      self.selectDataButton.config(width = 22)
    else:
      self.selectDataButton['text'] = 'Select Cohort (Folder of .xlsx and/or .csv files)'
      self.selectDataButton.config(width = 35)

    if self.program:
      if self.OptionsFrame:
        self.unload_optional_settings()
      if self.data_selection_method != 'Test':
        self.show_optional_settings()
      if 'T' in self.program:
        self.models = {}
    else:
      if self.OptionsFrame:
        self.unload_optional_settings()

    self.show_run_button()

  def show_run_button(self):
    if self.program and self.data_selection_method:
      if self.data_selection_method == 'Test':
        self.runProgramButton.grid(row=35, column=0, pady=(30, 15), padx=(100, 0), sticky='w')
      elif self.data_selection_method == 'Folder' or self.data_selection_method == 'Single':
        print(self.selected_data, self.metadata, self.cohortNameEntry.get(), self.subid_i_start, self.subid_i_end, self.condition_i_start, self.condition_i_end)
        if (self.selected_data and self.metadata and self.cohortNameEntry.get() and type(self.subid_i_start) == int and type(self.subid_i_end) == int and type(self.condition_i_start) == int and type(self.condition_i_end) == int):
          self.runProgramButton.grid(row=35, column=0, pady=(30, 15), padx=(100, 0), sticky='w')
        else:
          self.runProgramButton.grid_forget()
      elif self.data_selection_method == 'Processor':
        if self.previous_processor:
          self.runProgramButton.grid(row=35, column=0, pady=(30, 15), padx=(100, 0), sticky='w')
        else:
          self.runProgramButton.grid_forget()
      else:
        self.runProgramButton.grid_forget()
    else:
      self.runProgramButton.grid_forget()

  def show_optional_settings(self):
    self.OptionsFrame = OptionalSettingsFrame(self)
    self.OptionsFrame.grid(row=0, column=1, padx=10, pady=0, sticky='n')

  def unload_optional_settings(self):
    self.OptionsFrame.grid_forget()
    if list(self.defaults_options.values()) != [self.models, self.files_to_merge, self.data_download_timezone, self.timestamps_filename,  self.max_dataset_duration]:
      self.reset_optional_settings()

  def reset_optional_settings(self):
    self.files_to_merge = {}
    self.models = {}
    self.timestamps_filename = None
    self.data_download_timezone = -5
    self.max_dataset_duration = 24

  def unload_data(self):
    self.selectDataLabel['text'] = 'Select Data'
    self.selectDataLabel.config(fg = 'black')
    self.selectDataButton['text'] = self.selectDataLabelText
    self.selected_data = ''
    self.previous_processor = None
  
  def select_skyn_data(self):
    if self.data_selection_method == 'Single':
      skyn_dataset_file = filedialog.askopenfile(mode='r', filetypes=[('Skyn dataset','*.xlsx *.csv *.CSV')])
      if skyn_dataset_file:
        skyn_dataset_filename = os.path.abspath(skyn_dataset_file.name)
        self.selected_data = skyn_dataset_filename
        print('this gets split', skyn_dataset_filename)
        filename=os.path.split(skyn_dataset_filename)[-1]
        self.selectDataLabel['text'] = f'Dataset selected: {filename}'
        skyn_dataset_file.close()
        self.verify_filename(filename, os.path.dirname(self.selected_data))

    elif self.data_selection_method == 'Processor':
      processor_file = filedialog.askopenfile(mode='r', filetypes=[('Previous Processor', '*.pickle')])
      if processor_file:
        try:
          pickle_in = open(processor_file.name, "rb") 
          skyn_processor = pickle.load(pickle_in)
          pickle_in.close()
          model_avail = models_ready(skyn_processor)
          data_avail = data_ready(skyn_processor)
          data_avail = all([occasion.condition in ['Alc', 'Non'] for occasion in skyn_processor.occasions])

          if not model_avail and not data_avail:
            self.previous_processor = None
            self.selected_data = ''
            messagebox.showerror('SDM Error', 'This file does not have data processed, or data is not processsed with known labels (Alc or Non).')
            self.select_skyn_data()
          elif data_avail:
            if not model_avail:
              messagebox.showinfo('SDM', 'No models detected within file. You will not be able to make predictions using already-trained model. However, you can build a new model using this file.')
            self.previous_processor = skyn_processor
            self.selected_data = processor_file.name
            self.selectDataLabel['text'] = f'Skyn processor: {str(processor_file.name.split("/")[-1])}'
            self.selectDataLabel.config(fg = 'green')
            if self.program_selection_frame.grid_info():
              self.program_selection_frame.update_processor_programs(model_avail)
            else:
              self.program_selection_frame = ProgramSelectionFrame(self.required_inputs_frame, self)
              self.program_selection_frame.grid(row=2, column=1, padx=5, pady=(0, 15), sticky='w')
              self.x_separator_mid.grid(row=3, column=1, columnspan=2, sticky='ew')
            
        except Exception:
          print(traceback.format_exc())
          messagebox.showerror('SDM Error', traceback.format_exc())
          self.selectDataLabel['text'] = f'Failed to load: {str(processor_file.name.split("/")[-1])}'
          self.selectDataLabel.config(fg = 'red')
    else:
      cohort_data_folder = filedialog.askdirectory()
      if cohort_data_folder:
        self.verify_directory(cohort_data_folder + '/')
        
    self.show_run_button()

  def verify_directory(self, directory):
    print(directory)
    self.filenames = [file for file in os.listdir(directory)]
    self.episode_identifiers_required = all([identify_episode_identifier(filename) != None for filename in self.filenames])
    self.user_confirmation = False
    if directory_analysis_ready(directory):
      self.parsing_indices = get_default_parsing_indices(identify_subid(self.filenames[0]), self.episode_identifiers_required)
      self.selected_data = directory
      self.update_filename_parsing(self.parsing_indices)
      confirmation_window = FilenamesConfirmationWindow(self, self.parsing_indices)
      confirmation_window.grab_set()
      self.wait_window(confirmation_window)
      self.user_confirmation = confirmation_window.confirmed
    if directory_analysis_ready(directory) and self.user_confirmation:
      self.update_filename_parsing(self.parsing_indices)
      self.selectDataLabel['text'] = f'Cohort Data:  {self.selected_data.split("/")[-1]}'
      self.selectDataLabel.config(fg='green')
    else:
      self.selectDataLabel.config(fg='black')
      renameFiles = RenameFilesWindow(self, directory, self.filenames)
      renameFiles.grab_set()
      self.wait_window(renameFiles)
      self.select_skyn_data()

  def verify_filename(self, filename, directory):
    self.filenames = [file for file in os.listdir(directory)]
    subid = identify_subid(filename)
    condition = identify_condition(filename)
    episode_identifier = identify_episode_identifier(filename)
    self.episode_identifiers_required = episode_identifier != None

    filename_valid = identify_subid(filename) and identify_condition(filename)
    self.user_confirmation = False
    if filename_valid:
      self.user_confirmation = messagebox.askyesno('SDM', f'Is data set info correct?\nSubID = {subid}\nCondition = {condition}\nEpisode Identifier = {episode_identifier}')
      print('confirmed?', self.user_confirmation)
    if filename_valid and self.user_confirmation:
      self.parsing_indices = get_default_parsing_indices(identify_subid(filename), self.episode_identifiers_required)
      self.update_filename_parsing(self.parsing_indices)
      self.selectDataLabel.config(fg='green')
    else:
      renameFiles = RenameFilesWindow(self, directory, self.filenames)
      renameFiles.grab_set()
      self.wait_window(renameFiles)
      self.select_skyn_data()

  def update_filename_parsing(self, indices):
    self.subid_i_start = indices[0]
    self.subid_i_end = indices[1]
    self.condition_i_start = indices[2] 
    self.condition_i_end = indices[3]
    self.episode_identifier_i_start = indices[4]
    self.episode_identifer_i_end = indices[5]

  def update_models(self, model_name, model):
    self.models[model_name] = model

  def reset_models(self):
    self.models = {}
  
  def update_files_to_merge(self, files_to_merge):
    self.files_to_merge = files_to_merge

  def update_crop_settings(self, max_dataset_duration, timezone, timestamps_filename):
    self.max_dataset_duration = max_dataset_duration
    self.data_download_timezone = timezone
    self.timestamps_filename = timestamps_filename

  def open_metadata(self):
    file = filedialog.askopenfile(mode='r', filetypes=[('Metadata Excel file','*.xlsx')])
    if file:
      metadata_file = os.path.abspath(file.name)
      metadata = pd.read_excel(metadata_file)
      necessary_columns = ['SubID', 'Condition', 'Episode_Identifier','Use_Data', 'TotalDrks']
      if all(col in metadata.columns for col in necessary_columns):
        self.metaselectDataLabel['text'] = f'Selected metadata: {str(file.name.split("/")[-1])}'
        self.metadata = metadata_file
      else:
        messagebox.showerror('SDM Error', f'Metadata file must have columns: {", ".join(necessary_columns)}. \nFor example, see file: Resources/Test/Cohort Metadata TEST.xlsx')
    
    self.show_run_button()

  def open_metadata_creator(self):
    if self.cohortNameEntry.get() == '':
      messagebox.showerror("Error", 'Missing Cohort Name') 
    elif self.selected_data == '': 
      messagebox.showerror("Error", 'Ensure you have selected cohort folder, selected SubID and Condition indices, and provided a Cohort Name.') 
    elif None in [
      self.subid_i_start, 
      self.subid_i_end]:
      messagebox.showerror("Error", 'Missing SubID index selections.')
    elif None in [
      self.condition_i_start, 
      self.condition_i_end]:
      messagebox.showerror("Error", 'Missing Condition index selections') 
    else:
      data = self.prepare_filename_data()
      CreateMetadataWindow(data, self.cohortNameEntry.get(), self)    

  def prepare_filename_data(self):
    if self.data_selection_method == 'Single':
      file = os.path.split(self.selected_data)[-1]
      return {
        'SubID': [file[int(self.subid_i_start):int(self.subid_i_end) + 1]],
        'Condition': [file[int(self.condition_i_start): int(self.condition_i_end) + 1]],
        'Episode_Identifier': [file[int(self.episode_identifier_i_start): int(self.episode_identifer_i_end)+1]] if all([self.episode_identifier_i_start, self.episode_identifer_i_end]) else [""],
        'Use_Data': ["Y"],
        'TotalDrks': [""],
        'Notes': [""]
      }
    else:
      if None in [self.episode_identifier_i_start, self.episode_identifer_i_end]:
        episode_identifiers = ["" for i in range(0, len(
                                [file 
                                  for file in os.listdir(self.selected_data) 
                                  if (file[-3:]== 'csv') or (file[-4:] == 'xlsx')
                                ]))
                              ]
      else:
        episode_identifiers = [file[
                                int(self.episode_identifier_i_start)
                                :int(self.episode_identifer_i_end)+1] 
                              for file in os.listdir(self.selected_data) 
                              if (file[-3:] == 'csv') or (file[-4:] == 'xlsx')]
      return {
        'SubID': [file[
                    int(self.subid_i_start)
                    :int(self.subid_i_end)+1] 
                  for file in os.listdir(self.selected_data) 
                  if (file[-3:] == 'csv') or (file[-4:] == 'xlsx')],
        'Condition': [file[
                        int(self.condition_i_start)
                        :int(self.condition_i_end)+1] 
                      for file in os.listdir(self.selected_data)
                      if (file[-3:] == 'csv') or (file[-4:] == 'xlsx')],
        'Episode_Identifier': episode_identifiers,
        'Use_Data': ["Y" for i in range(0, len(
                      [file 
                        for file in os.listdir(self.selected_data) 
                        if (file[-3:]== 'csv') or (file[-4:] == 'xlsx')
                      ]))
                    ],
        'TotalDrks': ["" for i in range(0, len(
                      [file 
                        for file in os.listdir(self.selected_data) 
                        if (file[-3:]== 'csv') or (file[-4:] == 'xlsx')
                      ]))
                    ],
        'Notes': ["" for i in range(0, len(
                  [file 
                    for file in os.listdir(self.selected_data) 
                      if (file[-3:]== 'csv') or (file[-4:] == 'xlsx')
                    ]))
                  ]
      }     

  def run(self):
    
    program = self.program
    data_format = self.data_selection_method 

    self.models = self.models if len(list((self.models.keys())))>0 else load_default_model()

    if data_format == 'Test':
      cohort_name = 'Test'
      self.selected_data = os.path.abspath('Raw/TestData/') + '/'
      self.filenames = [file for file in os.listdir(self.selected_data)]
      self.parsing_indices = get_default_parsing_indices(identify_subid(self.filenames[0]), True)
      self.subid_i_start = self.parsing_indices[0]
      self.subid_i_end = self.parsing_indices[1]
      self.condition_i_start = self.parsing_indices[2]
      self.condition_i_end = self.parsing_indices[3]
      self.episode_identifier_i_start = self.parsing_indices[4]
      self.episode_identifer_i_end = self.parsing_indices[5]
      self.metadata = 'Resources/Test/Cohort Metadata TEST.xlsx'
    elif data_format == 'Processor':
      cohort_name = self.previous_processor.cohort_name
    else:
      cohort_name = self.cohortNameEntry.get()
    
    try:
      if not os.path.exists('Results'):
        os.mkdir('Results')
      if not os.path.exists(f'Results/{cohort_name}'):
        os.mkdir(f'Results/{cohort_name}')
      if not os.path.exists(f'Results/{cohort_name}/{date.today().strftime("%m.%d.%Y")}'):
        os.mkdir(f'Results/{cohort_name}/{date.today().strftime("%m.%d.%Y")}')
      if not os.path.exists(f'Results/{cohort_name}/{date.today().strftime("%m.%d.%Y")}/Model_Performance'):
        os.mkdir(f'Results/{cohort_name}/{date.today().strftime("%m.%d.%Y")}/Model_Performance')
    except Exception:
          print(traceback.format_exc())
          messagebox.showerror('Error', traceback.format_exc())

    data_out = f'Results/{cohort_name}/{date.today().strftime("%m.%d.%Y")}/Processed_Datasets'
    graphs_out = f'Results/{cohort_name}/{date.today().strftime("%m.%d.%Y")}/Plots'
    analyses_out = f'Results/{cohort_name}/{date.today().strftime("%m.%d.%Y")}/Model_Performance'

    print(self.files_to_merge)

    try:
      if data_format == 'Folder' or data_format == 'Test':
        sdm_processor = skynCohortProcessor(
          self.selected_data,
          metadata_path = self.metadata,
          cohort_name = cohort_name,
          merge_variables = self.files_to_merge,
          episode_start_timestamps_path=self.timestamps_filename,
          data_out_folder=data_out,
          graphs_out_folder=graphs_out,
          analyses_out_folder=analyses_out,
          subid_index_start=int(self.subid_i_start) + len(self.selected_data),
          subid_index_end=int(self.subid_i_end) + len(self.selected_data), 
          condition_index_start=int(self.condition_i_start) + len(self.selected_data), 
          condition_index_end=int(self.condition_i_end) + len(self.selected_data),
          episode_identifier_search_index_start=int(self.episode_identifier_i_start) + len(self.selected_data) if self.episode_identifier_i_start else None,
          episode_identifier_search_index_end=int(self.episode_identifer_i_end) + len(self.selected_data) if self.episode_identifer_i_end else None,
          max_dataset_duration=int(self.max_dataset_duration),
          skyn_timestamps_timezone=int(self.data_download_timezone)
        )
        if program == 'P':
          run_procedure = messagebox.askyesno("Skyn Data Manager", f'Would you like to process Skyn datasets and calculate features for cohort "{cohort_name}"?')
          if run_procedure:
            sdm_processor.process_cohort()
            writer = pd.ExcelWriter(f'Results/{cohort_name}/{date.today().strftime("%m.%d.%Y")}/features.xlsx')
            sdm_processor.stats['Cleaned'].to_excel(writer, sheet_name = 'Cleaned', index=False)
            sdm_processor.stats['Raw'].to_excel(writer, sheet_name = 'Raw', index=False)
        elif program == 'PP':
          run_procedure = messagebox.askyesno("Skyn Data Manager", f'Would you like to process Skyn datasets, calculate features and make predictions on cohort "{cohort_name}" using model(s): {", ".join([model_name for model_name in self.models.keys()])}?')
          if run_procedure:
            sdm_processor.process_cohort()
            sdm_processor.make_predictions(self.models, prediction_type='binary')
        elif program == 'PTP':
          run_procedure = messagebox.askyesno("Skyn Data Manager", f'Using data from cohort "{cohort_name}", would you like to process Skyn datasets, calculate features, train new models and test with cross validation?')
          if run_procedure:
            sdm_processor.process_cohort()
            sdm_processor.model_dev_and_test()
            sdm_processor.create_feature_model_and_predictions_report()
        else:
          run_procedure = False
          messagebox.showerror('Error', 'Invalid program selection.')
  
      if data_format == 'Processor':
        sdm_processor = self.previous_processor
        if program == 'PP':
          run_procedure = messagebox.askyesno("Skyn Data Manager", f'Would you like to make predictions on cohort "{cohort_name}" using model(s): {", ".join([model_name for model_name in self.models.keys()])}?')
          if run_procedure:
            sdm_processor.make_predictions(self.models, prediction_type='binary')
        elif program == 'PTP':
          run_procedure = messagebox.askyesno("Skyn Data Manager", f'Using data from cohort "{cohort_name}", would you like to train new models and test with cross validation?')
          if run_procedure:
            sdm_processor.model_dev_and_test()
            sdm_processor.create_feature_model_and_predictions_report()
        else:
          run_procedure = False
          messagebox.showerror('Error', 'Invalid program selection.')
      if data_format == 'Single':
        path_length_to_folder = len("/".join(os.path.split(self.selected_data)[:-1]) + '/')
        occasion = skynDatasetProcessor(
          self.selected_data,
          data_out,
          graphs_out,
          int(self.subid_i_start) + path_length_to_folder,
          int(self.subid_i_end) + path_length_to_folder, 
          int(self.condition_i_start) + path_length_to_folder, 
          int(self.condition_i_end) + path_length_to_folder,
          int(self.episode_identifier_i_start) + path_length_to_folder if self.episode_identifier_i_start else None,
          int(self.episode_identifer_i_end) + path_length_to_folder if self.episode_identifer_i_end else None,
          self.metadata,
          self.timestamps_filename,
          self.data_download_timezone,
          self.max_dataset_duration
        )
        if program == 'P':
          run_procedure = messagebox.askyesno("Skyn Data Manager", f'Would you like to make process single dataset? \nSelected data: {self.selected_data}')
          if run_procedure:
            metadata = pd.read_excel(self.metadata)
            occasion.max_duration = self.max_dataset_duration
            for dataset_version in ['Raw', 'Cleaned']:
              try:
                occasion.stats[dataset_version]['drink_total'] = get_drink_count(occasion.metadata, occasion.subid, occasion.condition, occasion.episode_identifier)
              except:
                pass
            occasion.process_with_default_settings(make_plots=True)
            occasion.plot_column('Motion')
            occasion.plot_column('Temperature_C')
            occasion.plot_tac_and_temp()
            occasion.plot_temp_cleaning()
            occasion.plot_cleaning_comparison()
            occasion.export_workbook()
        elif program == 'PP':
          run_procedure = messagebox.askyesno("Skyn Data Manager", f'Would you like to make process single dataset and make predictions using model(s): {", ".join([model_name for model_name in self.models.keys()])} ? \nSelected data: {self.selected_data}')
          if run_procedure:
            metadata = pd.read_excel(self.metadata)
            occasion.max_duration = self.max_dataset_duration
            for dataset_version in ['Raw', 'Cleaned']:
              try:
                occasion.stats[dataset_version]['drink_total'] = get_drink_count(occasion.metadata, occasion.subid, occasion.condition, occasion.episode_identifier)
              except:
                pass
            occasion.process_with_default_settings(make_plots=True)
            occasion.plot_column('Motion')
            occasion.plot_column('Temperature_C')
            occasion.plot_tac_and_temp()
            occasion.plot_temp_cleaning()
            occasion.plot_cleaning_comparison()
            occasion.make_prediction(self.models) # The only difference between P and PP
            occasion.export_workbook()

      SDM_run_settings = get_sdm_run_settings(self, self.data_selection_method, program, data_out, graphs_out, analyses_out, cohort_name)
      SDM_run_settings.to_excel(f'Results/{cohort_name}/{date.today().strftime("%m.%d.%Y")}/program_settings_{datetime.now().strftime("%H-%M-%S")}.xlsx',
                                sheet_name='Program Settings')
      messagebox.showinfo("Skyn Data Manager", f'Program complete. Program settings saved here: Results/{cohort_name}/{date.today().strftime("%m.%d.%Y")}/.')

    except Exception:
      print(traceback.format_exc())
      messagebox.showerror('Error', traceback.format_exc())

