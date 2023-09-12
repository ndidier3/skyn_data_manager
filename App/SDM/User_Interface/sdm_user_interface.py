from SDM.Skyn_Processors.skyn_cohort_processor import skynCohortProcessor
from SDM.Skyn_Processors.skyn_dataset_processor import skynDatasetProcessor
from SDM.Reporting.export import *
from SDM.Configuration.configuration import get_drink_count
from SDM.User_Interface.Frames.optional_settings_frame import OptionalSettingsFrame
from SDM.User_Interface.Frames.data_selection_method_frame import DataSelectionMethodFrame
from SDM.User_Interface.Frames.program_selection_frame import ProgramSelectionFrame
from SDM.User_Interface.Sub_Windows.create_metadata_window import CreateMetadataWindow
from SDM.User_Interface.Sub_Windows.data_configuration_window import DataConfigurationWindow
from SDM.User_Interface.Utils.get_sdm_run_settings import get_sdm_run_settings
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

    self.params = {
      'show_merge_info': True
    }

    self.required_inputs_frame = Frame(self, highlightbackground="black", highlightthickness=3)
    self.required_inputs_frame.grid(row=0, column=0, padx=0, pady=0)

    self.mainHeader = Label(self.required_inputs_frame, text = 'Skyn Data Manager')
    self.mainHeader.config(font=(None, 12, 'bold'))
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
    self.cohortNameEntry.bind("<FocusOut>", self.showRunButton())

    #LOAD FILE DIRECTLY
    
    self.OptionsFrame = None

    self.files_to_merge = {}
    self.previous_processor = None
    self.models = {}
    self.timestamps_filename = None
    self.data_download_timezone = -5
    self.max_dataset_duration = 24
    self.subid_i_start = None
    self.subid_i_end = None
    self.condition_i_start = None
    self.condition_i_end = None
    self.episode_identifier_i_start = None
    self.episode_identifer_i_end = None

    self.defaults = {
      'files_to_merge': {},
      'previous_processor': None,
      'models': {},
      'timestamps_filename': None,
      'data_download_timezone': -5,
      'max_dataset_duration': 24,
      'subid_i_start': None,
      'subid_i_end': None,
      'condition_i_start': None,
      'condition_i_end': None,
      'episode_identifier_i_start': None,
      'episode_identifer_i_end': None,
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
    self.program_selection_frame = ProgramSelectionFrame(self.required_inputs_frame, self)
    self.program_selection_frame.grid(row=2, column=1, padx=5, pady=(0, 15), sticky='w')
    self.x_separator_mid.grid(row=3, column=1, columnspan=2, sticky='ew')
    self.refresh_user_interface()

  def update_program(self, selection):
    self.program = selection
    self.refresh_user_interface()
  
  def refresh_user_interface(self):
    if self.data_selection_method != 'Test':
      self.data_loading_frame.grid(row=4, column=1, padx=5, pady=0)
      self.selectDataLabel.grid(row=2, column=0, padx=(0, 50), pady=(2,0))
      self.selectDataButton.grid(row=3, column=0, padx=(0, 50), pady=(0,7))
    else:
      self.data_loading_frame.grid_forget()
      self.selectDataLabel.grid_forget()
      self.selectDataButton.grid_forget()
      if self.OptionsFrame:
        self.unload_optional_settings()

    if self.data_selection_method != 'Test' and self.data_selection_method != 'Processor':
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

    if self.selected_data == '':
      if self.data_selection_method == 'Single':
        self.selectDataButton['text'] = 'Select Dataset (.xlsx or .csv)'
        self.selectDataButton.config(width = 27)
      elif self.data_selection_method == 'Processor':
        self.selectDataButton['text'] = 'Select Processor (.pickle)'
        self.selectDataButton.grid(row=2, column=0, padx=30, pady=30)
        self.selectDataButton.config(width = 22)
      else:
        self.selectDataButton['text'] = 'Select Cohort (Folder of .xlsx and/or .csv files)'
        self.selectDataButton.config(width = 35)

    if self.program:
      if self.OptionsFrame:
        self.unload_optional_settings()
      self.show_optional_settings()
      if 'T' in self.program:
        self.models = {}
    else:
      if self.OptionsFrame:
        self.unload_optional_settings()

    self.showRunButton()

  def showRunButton(self):
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
    if list(self.defaults.values()) != [self.files_to_merge, self.previous_processor, self.models, self.timestamps_filename, self.data_download_timezone, self.max_dataset_duration, self.subid_i_start, self.subid_i_end, self.condition_i_start, self.condition_i_end, self.episode_identifier_i_start, self.episode_identifer_i_end]:
      messagebox.showinfo('SDM: Update', 'Settings Reset to Defaults.')
      self.reset_settings()

  def reset_settings(self):
    self.files_to_merge = {}
    self.previous_processor = None
    self.models = {}
    self.timestamps_filename = None
    self.data_download_timezone = -5
    self.max_dataset_duration = 24
    self.subid_i_start = None
    self.subid_i_end = None
    self.condition_i_start = None
    self.condition_i_end = None
    self.episode_identifier_i_start = None
    self.episode_identifer_i_end = None
  
  def select_skyn_data(self):
    if self.data_selection_method == 'Single':
      skyn_dataset_file = filedialog.askopenfile(mode='r', filetypes=[('Skyn dataset','*.xlsx *.csv *.CSV')])
      if skyn_dataset_file:
        skyn_dataset_filename = os.path.abspath(skyn_dataset_file.name)
        self.selected_data = skyn_dataset_filename
        file_to_parse_metadata=skyn_dataset_filename.split("\\")[-1]
        data_configuration_window = DataConfigurationWindow(self, file_to_parse_metadata)
        data_configuration_window.grab_set()
        self.wait_window(data_configuration_window)
        self.selectDataLabel['text'] = f'Dataset selected: {file_to_parse_metadata}'

    elif self.data_selection_method == 'Processor':
      processor_file = filedialog.askopenfile(mode='r', filetypes=[('Previous Processor', '*.pickle')])
      if processor_file:
        try:
          pickle_in = open(processor_file.name, "rb") 
          skyn_processor = pickle.load(pickle_in)
          pickle_in.close()
          self.selected_data = skyn_processor
          self.selectDataLabel['text'] = f'Skyn processor: {str(processor_file.name.split("/")[-1])}'
        except:
          self.selectDataLabel['text'] = f'Failed to load: {str(processor_file.name.split("/")[-1])}'
    else:
      cohort_data_folder = filedialog.askdirectory()
      if cohort_data_folder:
        self.selected_data = cohort_data_folder + '/'
        file_to_parse_metadata = [f for f in os.listdir(cohort_data_folder) if os.path.isfile(os.path.join(cohort_data_folder, f))][0]
        print(file_to_parse_metadata)
        data_configuration_window = DataConfigurationWindow(self, file_to_parse_metadata)
        data_configuration_window.grab_set()
        self.wait_window(data_configuration_window)
        self.selectDataLabel['text'] = f'Cohort Data:  {cohort_data_folder.split("/")[-1]}'

    self.showRunButton()
      
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
    
    self.showRunButton()

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
      file = self.selected_data.split("\\")[-1]
      return {
        'SubID': [file[int(self.subid_i_start):int(self.subid_i_end)+1]],
        'Condition': [file[int(self.condition_i_start): int(self.condition_i_end)+1]],
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
                                :int(self.episode_identifer_i_end) + 1] 
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
      self.selected_data = os.path.abspath('Raw/TestData/')
      self.subid_i_start = 0
      self.subid_i_end = 3
      self.condition_i_start = 5
      self.condition_i_end = 8
      self.episode_identifier_i_start = 10
      self.episode_identifer_i_end = 13
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
        path_length_to_folder = len("/".join(self.selected_data.split("\\")[:-1]) + '/')
        print(self.selected_data.split("\\")[:-1])
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

