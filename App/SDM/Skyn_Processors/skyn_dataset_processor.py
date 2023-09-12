from ..Configuration.configuration import *
from ..Crop.crop import *
from ..Signal_Processing.smooth_signal import *
from ..Signal_Processing.remove_outliers import *
from ..Reporting.plotting import *
from ..Stats.stats import *
from ..Reporting.export import *
import pandas as pd
import numpy as np
import traceback

class skynDatasetProcessor:
  def __init__(self, path, data_out_folder, graphs_out_folder, subid_index_start, subid_index_end, condition_index_start, condition_index_end, episode_identifier_index_start = None, episode_identifier_index_end = None, metadata_path = None, episode_start_timestamps_path = None, skyn_download_timezone = -5, max_duration = 18):
    self.path = path
    self.subid_index_start = subid_index_start
    self.subid_index_end = subid_index_end
    self.condition_index_start = condition_index_start
    self.condition_index_end = condition_index_end
    self.episode_identifier_index_start = episode_identifier_index_start
    self.episode_identifier_index_end = episode_identifier_index_end
    print(path[condition_index_start:condition_index_end+1], 'condition')
    print(path[subid_index_start:subid_index_end+1], 'subid')
    self.subid = int(path[subid_index_start:subid_index_end+1])
    self.condition = path[condition_index_start:condition_index_end+1]
    self.episode_identifier = '' if (self.episode_identifier_index_start == None) or (self.episode_identifier_index_end == None) else path[self.episode_identifier_index_start:self.episode_identifier_index_end+1]
    print(self.episode_identifier, 'episode identifier')
    self.raw_dataset = None
    self.cleaned_dataset = None
    self.cohort = None
    self.study_title = None
    self.metadata = pd.read_excel(metadata_path) if metadata_path != None else pd.DataFrame(columns=['SubID', 'Condition', 'episode_identifier','Use_Data'])
    self.timestamps = pd.read_excel(episode_start_timestamps_path) if episode_start_timestamps_path != None else pd.DataFrame(columns = ['SubID', 'Start Date', 'Start Time', 'Time Zone'])
    self.skyn_download_timezone = skyn_download_timezone
    self.data_out_folder = data_out_folder
    self.plot_folder = graphs_out_folder
    self.simple_plot_paths = []
    self.complex_plot_paths = []
    self.plot_paths = self.simple_plot_paths + self.complex_plot_paths
    self.condition_plot_folder = None
    self.stats = {'temp_cropped_count': 0, 'Cleaned': {}, 'Raw': {}}
    self.croppable = is_data_croppable(self.subid, self.condition, self.episode_identifier, self.metadata) if len(self.timestamps) != 0 else False
    self.max_duration = max_duration
    self.data_cropped = False
    self.info_repository = {
      'raw': None,
      'interval': None,
      'cleaning': False,
      'signal_processing': None,
      'baseline_corrected': False
    }
    self.predictions = pd.DataFrame()

  def initialize_data(self):
    print(f'initializing {self.subid} {self.condition} {self.episode_identifier}')
    if self.path[-3:] == 'csv':
      df_raw = pd.read_csv(self.path, index_col=False)
    else:
      df_raw = pd.read_excel(self.path, index_col=False)
    df_raw = update_column_names(df_raw)
    df_raw = rename_TAC_column(df_raw)
    df_raw, new_day_index_list, interval = get_time_elapsed(df_raw)
    self.time_variable = 'time_elapsed_hours'
    self.info_repository['interval'] = interval

    df_raw = remove_junk_columns(df_raw)

    # df_raw['TAC'] = baseline_correct_tac(df_raw['TAC'])
    # self.info_repository['baseline_corrected'] = True
    
    if not os.path.exists(self.data_out_folder):
      os.mkdir(self.data_out_folder)
    if not os.path.exists(self.plot_folder):
      os.mkdir(self.plot_folder)
    subid_plot_folder = f'{self.plot_folder}/{self.subid}/'
    if not os.path.exists(subid_plot_folder):
      os.mkdir(subid_plot_folder)
    condition_plot_folder = f'{self.plot_folder}/{self.subid}/{self.condition}'
    if not os.path.exists(condition_plot_folder):
      os.mkdir(condition_plot_folder)
    self.condition_plot_folder = condition_plot_folder

    for dataset_version in ['Cleaned', 'Raw']:
      self.stats[dataset_version]['drink_total'] = get_drink_count(self.metadata, self.subid, self.condition, self.episode_identifier)

    if 'Motion' in df_raw.columns.tolist():
      df_raw['Motion_Norm'] = normalize_column(df_raw['Motion'])
    if 'Temperature_C' in df_raw.columns.tolist():
      df_raw['Temperature_C_Norm'] = normalize_column(df_raw['Temperature_C'])
      
    if not multiple_device_ids(df_raw):
      self.raw_dataset = df_raw
      self.crop_dataset_based_on_temperature()
      if self.croppable:
        self.crop_dataset_with_timestamps()
        self.data_cropped = True
      elif self.max_duration:
        self.crop_dataset_with_max_duration()
        self.data_cropped = True
      self.info_repository['raw'] = df_raw['TAC'].tolist()
    else:
      print(f'Multiple Device IDs detected within single dataset {self.subid} {self.condition}{self.episode_identifier}')
      return False
    
  def process_with_default_settings(self, make_plots=False):
    self.initialize_data()
    self.apply_basic_cleaning(15)
    self.apply_smoothing([51, 101], 3, ['TAC', 'TAC_cleaned', 'TAC_imputed'])
    if make_plots:
      self.plot_tac_and_temp()
      self.plot_temp_cleaning()
      self.plot_cleaning_comparison()
    self.get_stats()
    self.temp_validity_check()

  def apply_basic_cleaning(self, test_range, major_threshold=0.75, minor_threshold=0.50):
    df = self.raw_dataset.copy()
    imputed_TAC, cleaned_TAC, major_outliers, minor_outliers = find_and_replace_outliers(df, test_range, self.time_variable, major_threshold, minor_threshold)

    if self.cleaned_dataset is not None:
      self.cleaned_dataset['TAC_imputed'] = imputed_TAC
      self.cleaned_dataset['TAC_cleaned'] = cleaned_TAC
      self.cleaned_dataset['major_outlier'] = [(1 if i in major_outliers else 0) for i in range(0, len(self.cleaned_dataset))]
      self.cleaned_dataset['minor_outlier'] = [(1 if i in minor_outliers else 0) for i in range(0, len(self.cleaned_dataset))]
    else:
      dataset = self.raw_dataset.copy()
      dataset['TAC_imputed'] = imputed_TAC
      dataset['TAC_cleaned'] = cleaned_TAC
      dataset['major_outlier'] = [(1 if i in major_outliers else 0) for i in range(0, len(dataset))]
      dataset['minor_outlier'] = [(1 if i in minor_outliers else 0) for i in range(0, len(dataset))]
      self.cleaned_dataset = dataset

    self.cleaned_dataset = remove_junk_columns(self.cleaned_dataset)
    self.info_repository['signal_processing'] = {
      'TAC_imputed': imputed_TAC,
      'TAC_data' : cleaned_TAC,
      'cleaning_method' : 'Cleaned (basic)',
      'test_range': test_range,
      'deleted_count': cleaned_TAC.count(np.nan),
      'major_threshold': major_threshold,
      'minor_threshold': minor_threshold,
      'major_outliers': major_outliers,
      'minor_outliers': minor_outliers
    }

  def apply_smoothing(self, window_lengths, polyorder, variables):
    smoothed_tac_variables = smooth_signals(self.cleaned_dataset, window_lengths, polyorder, variables, self.time_variable)
    for variable in variables:
      for window_length in window_lengths:
        smoothed_tac = smoothed_tac_variables[f'{variable}_{window_length}']
        smoothed_variable_name = f'{variable}_smooth_{window_length}'
        self.cleaned_dataset[smoothed_variable_name] = smoothed_tac
        self.info_repository['signal_processing']['TAC_smoothed'] = smoothed_tac
   
  def crop_dataset_based_on_temperature(self, data_clean=False):
    if data_clean:
        self.cleaned_dataset, cropped_device_off_end = crop_device_off_end(self.cleaned_dataset)
        self.stats['cropped_device_off_end'] = cropped_device_off_end
        self.cleaned_dataset, cropped_device_off_start = crop_device_off_start(self.cleaned_dataset)
        self.stats['cropped_device_off_start'] = cropped_device_off_start
    else:
      self.raw_dataset, cropped_device_off_end = crop_device_off_end(self.raw_dataset)
      self.stats['cropped_device_off_end'] = cropped_device_off_end
      self.raw_dataset, cropped_device_off_start = crop_device_off_start(self.raw_dataset)
      self.stats['cropped_device_off_start'] = cropped_device_off_start

  def crop_dataset_with_timestamps(self, data_clean=False):
    if data_clean:
        self.cleaned_dataset, cropped_plot_path = crop_using_timestamp(self.subid, self.condition, self.episode_identifier, self.cleaned_dataset, self.metadata, self.timestamps, self.condition_plot_folder, self.max_duration, self.skyn_download_timezone)
    else:
      self.raw_dataset, cropped_plot_path = crop_using_timestamp(self.subid, self.condition, self.episode_identifier, self.raw_dataset, self.metadata, self.timestamps, self.condition_plot_folder, self.max_duration, self.skyn_download_timezone)

    self.complex_plot_paths.append(cropped_plot_path)
    self.time_variable = 'time_elapsed_hours_adjusted'

  def crop_dataset_with_max_duration(self):
    self.raw_dataset['datetime'] = pd.to_datetime(self.raw_dataset['datetime'])
    min_timestamp = self.raw_dataset['datetime'].min()
    max_timestamp = min_timestamp + pd.DateOffset(hours=self.max_duration)
    self.raw_dataset = self.raw_dataset[(self.raw_dataset['datetime'] >= min_timestamp) & (self.raw_dataset['datetime'] <= max_timestamp)]

  
  def temp_validity_check(self):
    for dataset_version, df in {'Cleaned': self.cleaned_dataset, 'Raw': self.raw_dataset}.items():
      df.loc[:, 'Below_28_C'] = df.apply(lambda row: 0 if row.Temperature_C > 28 else 1, axis=1)
      counts = df['Below_28_C'].value_counts()
      if 1 in counts.index.tolist():
        self.stats[dataset_version]['not_worn_percent'] = counts.loc[1] / (counts.loc[0] + counts.loc[1])
      else:
        self.stats[dataset_version]['not_worn_percent'] = 0

      self.stats[dataset_version]['not_worn_duration'] = self.stats[dataset_version]['not_worn_percent'] * self.stats[dataset_version]['duration']
      
      self.stats[dataset_version]['valid_duration'] = self.stats[dataset_version]['duration'] - self.stats[dataset_version]['not_worn_duration']
      self.stats[dataset_version]['valid_duration_percent'] = self.stats[dataset_version]['valid_duration'] / self.stats[dataset_version]['duration']
      self.stats[dataset_version]['valid_occasion'] = 1 if (self.stats[dataset_version]['valid_duration_percent'] > 0.5) and (self.stats[dataset_version]['valid_duration'] > 2) else 0

  def export_workbook(self):
    export_skyn_workbook(self.cleaned_dataset, self.subid, self.condition, self.episode_identifier, self.predictions, self.data_out_folder, self.simple_plot_paths, self.complex_plot_paths)

  def get_stats(self):

    dfs = {
      'Cleaned': self.cleaned_dataset.copy(),
      'Raw': self.raw_dataset.copy()
    }

    #TAC Features
    for dataset_version, df in dfs.items():
      tac_variable = 'TAC_imputed_smooth_101' if dataset_version == 'Cleaned' else 'TAC'
      self.stats[dataset_version]['mean'], self.stats[dataset_version]['stdev'], self.stats[dataset_version]['sem'] = get_mean_stdev_sem(df, tac_variable)
      self.stats[dataset_version]['TAC_N'] = len(df)
      self.stats[dataset_version]['auc_total'], self.stats[dataset_version]['auc_per_hour'] = get_auc(df, tac_variable, self.time_variable)
      self.stats[dataset_version]['peak'] = get_peak(df, tac_variable)
      peak_index = get_peak_index(df, tac_variable)
      self.stats[dataset_version]['baseline_mean'], self.stats[dataset_version]['baseline_stdev'] = get_baseline_mean_stdev(df, tac_variable)
      self.stats[dataset_version]['rise_duration'], curve_begins_index = get_rise_duration(df, tac_variable, self.time_variable, peak_index)
      
      self.stats[dataset_version]['fall_duration'], curve_ends_index = get_fall_duration(df, tac_variable, self.time_variable, peak_index)
      self.stats[dataset_version]['rise_rate'] = get_rise_rate(self.stats[dataset_version]['rise_duration'], self.stats[dataset_version]['peak'])
      self.stats[dataset_version]['fall_rate'] = get_fall_rate(self.stats[dataset_version]['fall_duration'], self.stats[dataset_version]['peak'])
      self.stats[dataset_version]['duration'] = df[self.time_variable].max()
      self.stats[dataset_version]['curve_duration'] = get_curve_duration(self.stats[dataset_version]['rise_duration'], self.stats[dataset_version]['fall_duration'])
      self.stats[dataset_version]['curve_auc'] = get_curve_auc(df, tac_variable, curve_begins_index, curve_ends_index)
      self.stats[dataset_version]['curve_auc_per_hour'] = get_curve_auc_per_hour(self.stats[dataset_version]['curve_auc'], self.stats[dataset_version]['curve_duration'])

      #MOTION 
      self.stats[dataset_version]['no_motion'] = get_value_proportion(df, 0, 'Motion')
      self.stats[dataset_version]['mean_motion'], self.stats[dataset_version]['stdev_motion'], self.stats[dataset_version]['sem_motion'] = get_mean_stdev_sem(df, 'Motion')
      
      #TEMPERATURE
      self.stats[dataset_version]['mean_temp'], self.stats[dataset_version]['stdev_temp'], self.stats[dataset_version]['sem_temp'] = get_mean_stdev_sem(df, 'Temperature_C')

      #SIGNAL VARIABILITY
      self.stats[dataset_version]['average_tac_difference'], differences = get_average_tac_difference(df, 'TAC')
      self.stats[dataset_version]['tac_alteration_percent'] = get_tac_directional_alteration_percent(df, 'TAC')

      if dataset_version == 'Cleaned':
        #OUTLIERS AND CLEANING
        self.stats[dataset_version]['major_outlier_N'] = len(self.info_repository['signal_processing']['major_outliers'])
        self.stats[dataset_version]['minor_outlier_N'] = len(self.info_repository['signal_processing']['minor_outliers'])
        self.stats[dataset_version]['imputed_count'] = self.stats['Cleaned']['minor_outlier_N'] + self.stats[dataset_version]['major_outlier_N']
        
        plot_path = plot_smoothed_curve(df, self.plot_folder, self.subid, self.condition, self.episode_identifier, self.time_variable, self.stats[dataset_version]['peak'], self.stats[dataset_version]['baseline_mean'] + self.stats[dataset_version]['baseline_stdev'], curve_begins_index, curve_ends_index)
        self.complex_plot_paths.append(plot_path)

  # MAKE PLOTS     
  def plot_column(self, variable_name):
    plot_path = plot_column(self.cleaned_dataset, self.plot_folder, self.subid, self.condition, self.episode_identifier, variable_name, self.time_variable)
    self.simple_plot_paths.append(plot_path)
    
  def plot_normalized_columns(self, variables, plot_name):
    plot_path = plot_overlaid_with_normalization(self.cleaned_dataset, self.plot_folder, self.subid, self.condition, self.episode_identifier, variables, self.time_variable, plot_name)
    self.simple_plot_paths.append(plot_path)
  
  def plot_temp_cleaning(self):
    plot_path = plot_temp_cleaning(self.cleaned_dataset, self.plot_folder, self.subid, self.condition, self.episode_identifier, 'Temperature_C', self.time_variable)
    self.complex_plot_paths.append(plot_path)

  def plot_tac_and_temp(self):
    plot_path = plot_tac_and_temp(self.cleaned_dataset, self.plot_folder, self.subid, self.condition, self.episode_identifier, 'TAC', 'Temperature_C', self.time_variable)
    self.complex_plot_paths.append(plot_path)

  def plot_cleaning_comparison(self):
    plot_path = plot_cleaning_comparison(self, self.cleaned_dataset, self.raw_dataset, self.time_variable)
    self.complex_plot_paths.append(plot_path)

  def plot_TAC_curves(self, additional_groupings = {}):
    dataset_columns = self.cleaned_dataset.columns.tolist()
    for variable_name in [col for col in self.cleaned_dataset.columns.tolist() if 'TAC' in col]:
      plot_path = plot_TAC_curve(self.cleaned_dataset, 
      self.plot_folder, self.subid, self.condition, self.episode_identifier, variable_name, self.time_variable)
      self.complex_plot_paths.append(plot_path)
    
    groupings = {
      'cleaned_smooth_comparison' : [col for col in dataset_columns if 'cleaned_smooth' in col]
    }
    groupings.update(additional_groupings)

    for group_name, variable_grouping in groupings.items():
      if len(variable_grouping) > 0:
        plot_path = plot_overlaid_TAC_curves(self.cleaned_dataset, self.plot_folder, self.subid, self.condition,self.episode_identifier, variable_grouping, self.time_variable, group_name)
        self.plot_paths.append(plot_path)

  def make_prediction(self, models, predictors = ['curve_auc', 'rise_rate', 'fall_duration', 'peak', 'fall_rate', 'rise_duration', 'TAC_N', 'average_tac_difference', 'tac_alteration_percent', 'major_outlier_N', 'minor_outlier_N']):
    predictions = {}
    for version in ['Cleaned', 'Raw']:
      if version == 'Raw':
        self.stats[version]['major_outlier_N'] = 0
        self.stats[version]['minor_outlier_N'] = 0
      data = np.array([self.stats[version][feature] for feature in predictors]).reshape(1, -1)
      for model_name, model in models.items():
        try:
          prediction = model.predict(data)
          predictions[model_name + '_' + version] = 'Alc' if prediction==1 else 'Non'
          predictions[model_name + '_' + version + '_correct'] = 'correct' if predictions[model_name + '_' + version] == self.condition else 'incorrect'
        except Exception:
          print(traceback.format_exc())
          return traceback.format_exc()
        #   pass
        # #will only attempt if first try fails. removing the last two data points may work if the model was trained using Raw data that does not include outlier_Ns
        # try:
        #   prediction = model.predict(data[:-2])
        #   predictions[model_name + '_' + version] = 'Alc' if prediction==1 else 'Non'
        #   predictions[model_name + '_' + version + '_correct'] = 'correct' if predictions[model_name + '_' + version] == self.condition else 'incorrect'
    print(predictions) 
    self.predictions = pd.DataFrame([predictions])


  