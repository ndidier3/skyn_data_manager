import pandas as pd
import numpy as np
from utils.Configuration.configuration import *
from utils.Reporting.plotting import *
from utils.Signal_Processing.smooth_signal import *
from utils.Signal_Processing.remove_outliers import *
from utils.Crop.crop import *
from utils.Reporting.stats import *
from utils.Reporting.export import *

class skynOccasionProcessor:
  def __init__(self, path):
    self.path = path
    self.raw_dataset = None
    self.cleaned_dataset = None
    self.subid = get_subid_from_path(path)
    self.condition = get_condition_from_path(path)
    self.cohort = None
    self.study_title = None
    self.quality_assessment = pd.read_excel('C:/Users/ndidier/Desktop/skyn_data_manager/resources/Skyn Quality Assessment 10.20.2021.xlsx')
    self.timestamps = pd.read_excel('C:/Users/ndidier/Desktop/skyn_data_manager/resources/Skyn Drink Pic timestamps.xlsx')
    self.drinks_df = pd.read_excel('C:/Users/ndidier/Desktop/skyn_data_manager/resources/DrinkCount_MARS.xlsx')
    self.plot_folder = 'C:/Users/ndidier/Desktop/skyn_data_manager/processed/tac_curve_images'
    self.plot_paths = []
    self.export_folder = 'C:/Users/ndidier/Desktop/skyn_data_manager/processed/data/'
    self.stats = {'temp_cropped_count': 0, 'Cleaned': {}, 'Raw': {}}
    self.croppable = ((self.quality_assessment['Good?']=='Y') & (self.quality_assessment['SubID']==self.subid) & (self.quality_assessment['Condition']==self.condition)).any()
    self.data_cropped = False
    self.info_repository = {
      'raw': None,
      'interval': None,
      'cleaning': False,
      'signal_processing': None
    }

  def process_with_default_settings(self, make_plots=False):
    self.initialize_data()
    self.apply_basic_cleaning(15, major_threshold=0.70, minor_threshold=0.50)
    self.apply_smoothing([(50 * self.info_repository['interval']) + 1, (100 * self.info_repository['interval']) + 1], 3, ['TAC', 'TAC_cleaned', 'TAC_imputed'])
    if make_plots:
      self.plot_TAC_curves(additional_groupings={'cleaning_comparison': ['TAC', 'TAC_cleaned']})
      self.plot_cleaning_comparison()
    self.get_stats()
    self.temp_validity_check()

  def initialize_data(self):
    
    print(f'initializing {self.subid} {self.condition}')
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

    subid_folder = f'{self.plot_folder}/{self.subid}/'
    if not os.path.exists(subid_folder):
      os.mkdir(subid_folder)
    condition_folder = f'{self.plot_folder}/{self.subid}/{self.condition}'
    if not os.path.exists(condition_folder):
      os.mkdir(condition_folder)
    for version in ['Cleaned', 'Raw']:
      self.stats[version]['drink_total'] = get_drink_count(self.drinks_df, self.subid, self.condition)



    if 'Motion' in df_raw.columns.tolist():
      df_raw['Motion_Norm'] = normalize_column(df_raw['Motion'])
    if 'Temperature_C' in df_raw.columns.tolist():
      df_raw['Temperature_C_Norm'] = normalize_column(df_raw['Temperature_C'])
      
    if not multiple_device_ids(df_raw):
      self.raw_dataset = df_raw
      if self.croppable:
        self.crop_dataset()
        self.data_cropped = True
      self.info_repository['raw'] = df_raw['TAC'].tolist()
    else:
      print('Duplicate Device IDs detected')
      return False


  def apply_basic_cleaning(self, test_range, major_threshold, minor_threshold):
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
      
  def plot_column(self, variable_name):
    time_variable = self.time_variable
    if self.cleaned_dataset is not None:
      plot_path = plot_column(self.cleaned_dataset, self.plot_folder, self.subid, self.condition, variable_name, time_variable)
      self.plot_paths.append(plot_path)
    else:
      plot_path = plot_column(self.cleaned_dataset, self.plot_folder, self.subid, self.condition, variable_name, time_variable)
      self.plot_paths.append(plot_path)

  def plot_columns(self, variables, plot_name):
    time_variable = self.time_variable

    if self.cleaned_dataset is not None:
      plot_path = plot_overlaid_with_normalization(self.cleaned_dataset, self.plot_folder, self.subid, self.condition, variables, time_variable, plot_name)
      self.plot_paths.append(plot_path)
    else:
      plot_path = plot_overlaid_with_normalization(self.cleaned_dataset, self.plot_folder, self.subid, self.condition, variables, time_variable, plot_name)
      self.plot_paths.append(plot_path)

  def plot_cleaning_comparison(self):
    plot_cleaning_comparison(self, self.cleaned_dataset, self.raw_dataset, self.time_variable)

  def plot_TAC_curves(self, additional_groupings = {}):
    dataset_columns = self.cleaned_dataset.columns.tolist()

    for variable_name in [col for col in self.cleaned_dataset.columns.tolist() if 'TAC' in col]:
      plot_path = plot_TAC_curve(self.cleaned_dataset, self.plot_folder, self.subid, self.condition, variable_name, self.time_variable)
      self.plot_paths.append(plot_path)
    
    groupings = {
      'cleaned_smooth_comparison' : [col for col in dataset_columns if 'cleaned_smooth' in col],
      'greedy_smooth_comparison' : [col for col in dataset_columns if 'cleaned_greedy_smooth' in col],
    }
    groupings.update(additional_groupings)

    for group_name, variable_grouping in groupings.items():
      if len(variable_grouping) > 0:
        plot_path = plot_overlaid_TAC_curves(self.cleaned_dataset, self.plot_folder, self.subid, self.condition, variable_grouping, self.time_variable, group_name)
        self.plot_paths.append(plot_path)

  def crop_dataset(self, data_clean=False):
    if data_clean:
        self.cleaned_dataset = crop_using_timestamp(self.subid, self.condition, self.cleaned_dataset, self.quality_assessment, self.timestamps)
        self.cleaned_dataset, cropped_device_off_end = crop_device_off_end(self.cleaned_dataset)
        self.stats['cropped_device_off_end'] = cropped_device_off_end
        self.cleaned_dataset, cropped_device_off_start = crop_device_off_start(self.cleaned_dataset)
        self.stats['cropped_device_off_start'] = cropped_device_off_start
    else:
      self.raw_dataset = crop_using_timestamp(self.subid, self.condition, self.raw_dataset, self.quality_assessment, self.timestamps)
      self.raw_dataset, cropped_device_off_end = crop_device_off_end(self.raw_dataset)
      self.stats['cropped_device_off_end'] = cropped_device_off_end
      self.raw_dataset, cropped_device_off_start = crop_device_off_start(self.raw_dataset)
      self.stats['cropped_device_off_start'] = cropped_device_off_start

    self.time_variable = 'time_elapsed_hours_adjusted'
  
  def temp_validity_check(self):
    for version, df in {'Cleaned': self.cleaned_dataset, 'Raw': self.raw_dataset}.items():
      df['Below_28_C'] = df.apply(lambda row: 0 if row.Temperature_C > 28 else 1, axis=1)
      counts = df['Below_28_C'].value_counts()
      if 1 in counts.index.tolist():
        self.stats[version]['not_worn_percent'] = counts.loc[1] / (counts.loc[0] + counts.loc[1])
      else:
        self.stats[version]['not_worn_percent'] = 0

      self.stats[version]['not_worn_duration'] = self.stats[version]['not_worn_percent'] * self.stats[version]['duration']
      
      self.stats[version]['valid_duration'] = self.stats[version]['duration'] - self.stats[version]['not_worn_duration']
      self.stats[version]['valid_duration_percent'] = self.stats[version]['valid_duration'] / self.stats[version]['duration']
      self.stats[version]['valid_occasion'] = 1 if (self.stats[version]['valid_duration_percent'] > 0.9) and (self.stats[version]['valid_duration'] > 2) else 0

  def export_workbook(self):
    export_skyn_workbook(self.cleaned_dataset, self.subid, self.condition, self.export_folder, self.plot_paths)

  def get_stats(self):

    dfs = {
      'Cleaned': self.cleaned_dataset.copy(),
      'Raw': self.raw_dataset.copy()
    }

    #TAC Features
    for version, df in dfs.items():
      tac_variable = 'TAC_imputed_smooth_101' if version == 'Cleaned' else 'TAC'
      self.stats[version]['mean'], self.stats[version]['stdev'], self.stats[version]['sem'] = get_mean_stdev_sem(df, tac_variable)
      self.stats[version]['TAC_N'] = len(df)
      self.stats[version]['auc_total'], self.stats[version]['auc_per_hour'] = get_auc(df, tac_variable, self.time_variable)
      self.stats[version]['peak'] = get_peak(df, tac_variable)
      peak_index = get_peak_index(df, tac_variable)
      self.stats[version]['baseline_mean'], self.stats[version]['baseline_stdev'] = get_baseline_mean_stdev(df, tac_variable)
      self.stats[version]['rise_duration'], curve_begins_index = get_rise_duration(df, tac_variable, self.time_variable, peak_index)
      self.stats[version]['fall_duration'], curve_ends_index = get_fall_duration(df, tac_variable, self.time_variable, peak_index)
      self.stats[version]['rise_rate'] = get_rise_rate(self.stats[version]['rise_duration'], self.stats[version]['peak'])
      self.stats[version]['fall_rate'] = get_rise_rate(self.stats[version]['fall_duration'], self.stats[version]['peak'])
      self.stats[version]['duration'] = df[self.time_variable].max()
      self.stats[version]['curve_duration'] = get_curve_duration(self.stats[version]['rise_duration'], self.stats[version]['fall_duration'])
      self.stats[version]['curve_auc'] = get_curve_auc(df, tac_variable, curve_begins_index, curve_ends_index)
      self.stats[version]['curve_auc_per_hour'] = get_curve_auc_per_hour(self.stats[version]['curve_auc'], self.stats[version]['curve_duration'])

      #MOTION 
      self.stats[version]['no_motion'] = get_value_proportion(df, 0, 'Motion')
      self.stats[version]['mean_motion'], self.stats[version]['stdev_motion'], self.stats[version]['sem_motion'] = get_mean_stdev_sem(df, 'Motion')
      
      #TEMPERATURE
      self.stats[version]['mean_temp'], self.stats[version]['stdev_temp'], self.stats[version]['sem_temp'] = get_mean_stdev_sem(df, 'Temperature_C')

      #SIGNAL VARIABILITY
      self.stats[version]['average_tac_difference'], differences = get_average_tac_difference(df, 'TAC')
      self.stats[version]['get_tac_alteration_percent'] = get_tac_directional_alteration_percent(df, 'TAC')

      if version == 'Cleaned':
        #OUTLIERS AND CLEANING
        self.stats[version]['major_outlier_N'] = len(self.info_repository['signal_processing']['major_outliers'])
        self.stats[version]['minor_outlier_N'] = len(self.info_repository['signal_processing']['minor_outliers'])
        self.stats[version]['imputed_count'] = self.stats['Cleaned']['minor_outlier_N'] + self.stats[version]['major_outlier_N']

        #FITTINGNESS of smoothed curves
        self.stats[version]['r2_raw_vs_smoothraw'] = get_r2(df, 'TAC', 'TAC_smooth_101')
        self.stats[version]['r2_raw_vs_smoothimputed'] = get_r2(df, 'TAC', 'TAC_imputed_smooth_101')
        self.stats[version]['r2_imputed_vs_smoothimputed'] = get_r2(df, 'TAC_imputed', 'TAC_imputed_smooth_101')
    