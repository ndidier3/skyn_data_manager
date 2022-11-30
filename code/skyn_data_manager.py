from skyn_occasion_processor import skynOccasionProcessor
import glob
import pandas as pd
from utils.Configuration.configuration import *
from utils.Reporting.plotting import *
from utils.Reporting.export import *
from utils.Machine_Learning.model_testing import *
from utils.Machine_Learning.pca import *
from utils.Machine_Learning.cv_with_rf import cv_with_rf
from utils.Machine_Learning.cv_with_lr import cv_with_lr
import xlsxwriter

class skynDataManager:
  def __init__(self, folder_path):
    self.data_folder = folder_path
    self.occasion_paths = glob.glob(f'{folder_path}*')
    self.cohort = 'Skyn Cohort'
    self.subids = []
    self.doses = {}
    self.occasions = []
    self.quality_assessment = pd.read_excel('C:/Users/ndidier/Desktop/skyn_data_manager/resources/Skyn Quality Assessment 10.20.2021.xlsx')
    self.timestamps = pd.read_excel('C:/Users/ndidier/Desktop/skyn_data_manager/resources/Skyn Drink Pic timestamps.xlsx')
    self.export_folder = 'C:/Users/ndidier/Desktop/skyn_data_manager/features'
    #self.croppable_subids = [subid for subid in self.timestamps['SubID'].tolist() if subid in self.quality_assessment[self.quality_assessment['Good?']=='Y']['SubID'].tolist()]
    self.merged_raw = None
    self.merged_clean = None
    self.feature_visuals_path = None
    self.stats = {
      'Cleaned': pd.DataFrame(),
      'Raw': pd.DataFrame(),
      'Model_Summary': pd.DataFrame(index=['Features', 'Split Method', 'TP', 'TN', 'FP', 'FN', 'Correct', 'AUC_ROC', 'Accuracy',  'AUC_ROC_Accuracy', 'Accuracy_Sklearn']),
      'Model_Results': {},
      'PCA': pd.DataFrame()}
    self.models = {
      'Cleaned': {},
      'Raw': {}
    }
    self.cv_results = {
      'Cleaned': {},
      'Raw': {}
    }

  def load_bulk_skyn_occasions(self, make_plots=True, force_refresh=False):
    for path in self.occasion_paths:
      print(path)
      
      occasion = skynOccasionProcessor(path)
      for version in ['Raw', 'Cleaned']:
        occasion.stats[version]['drink_total'] = get_drink_count(occasion.drinks_df, occasion.subid, occasion.condition)
      if (path not in [occasion.path for occasion in self.occasions]) or (force_refresh):

        occasion.process_with_default_settings(make_plots=True)
        occasion.plot_column('Motion')
        occasion.plot_column('Temperature_C')
        occasion.plot_columns(['TAC', 'Motion', 'Temperature_C'], plot_name='Temp - Motion - TAC')  
        occasion.plot_columns(['TAC', 'Temperature_C'], plot_name='Temp - TAC')
        occasion.plot_columns(['TAC', 'Motion'], plot_name='Motion - TAC')
        occasion.plot_cleaning_comparison()
        self.occasions.append(occasion)
        occasion.export_workbook()
    # try:
    self.export_stats()
    self.export_feature_plots(versions=['Cleaned', 'Raw'])
    for version in ['Cleaned', 'Raw']:
      # self.create_random_forest(version)
      # self.create_logistic_regression(version)
      # for model_name in self.models[version].keys():
      for model_name in ['random_forest', 'logistic_regression']:
        self.cross_validation(version, model_name)
    self.export_stats()
    self.principal_component_analysis('Cleaned')
    self.principal_component_analysis('Raw')
    self.create_report_by_occasion()
    # except Exception as error:
    #   print(error)
    #   print('exporting not complete')

  def export_stats(self, force_refresh=False):
    print('reached export')
    data = {
      'Cleaned': {
        'subid': [],
        'condition': []
        #features will be added here...
      },
      'Raw': {
        'subid': [],
        'condition': []
        #features will be added here...
      }
    }
    for version in ['Raw', 'Cleaned']:
      for occasion in self.occasions:
        data[version]['subid'].append(occasion.subid)
        data[version]['condition'].append(occasion.condition)
        for key, value in occasion.stats[version].items():
          refresh = (key not in self.stats[version].columns.tolist()) or (force_refresh)
          if refresh:
            if key not in data[version].keys():
              data[version][key] = [value]
            else:
              data[version][key].append(value)
      if len(self.stats[version]) > 0:
        self.stats[version] = self.stats[version].merge(pd.DataFrame(data[version]))
      else:
        self.stats[version] = pd.DataFrame(data[version])
      self.stats[version].to_excel(f'{self.export_folder}/{version}_stats.xlsx')

  def export_feature_plots(self, versions=['Cleaned', 'Raw']):
    for version in versions:
      plot_folder = plot_box_whisker(self.stats[version], ['mean', 'curve_auc', 'rise_duration', 'fall_duration', 'peak', 'average_tac_difference'], 'condition', self.export_folder, version)
      self.feature_visuals_path = plot_folder

  def principal_component_analysis(self, version):
    selected_features=['mean', 'auc_total', 'peak', 'curve_auc', 'rise_duration', 'fall_duration', 'average_tac_difference']
    explained_variances = PCA_with_features(self.stats[version], selected_features, version)
    self.stats['PCA'][f'PCA with {version} Data'] = explained_variances

  def cross_validation(self, version, model_name):
    if model_name not in self.cv_results[version].keys():
      self.cv_results[version][model_name] = {}
    if model_name == 'random_forest':
      cv_stats, cv_results, incorrect, correct, predictors, splits = cv_with_rf(self.stats[version])
    if model_name == 'logistic_regression':
      cv_stats, cv_results, incorrect, correct, predictors, splits = cv_with_lr(self.stats[version])
      print(f'{model_name}: {cv_stats}')
    self.cv_results[version][model_name]['cv_stats'] = cv_stats
    self.cv_results[version][model_name]['cv_results'] = cv_results
    self.cv_results[version][model_name]['incorrect'] = incorrect
    self.cv_results[version][model_name]['correct'] = correct
    self.cv_results[version][model_name]['K'] = splits
    self.stats['Model_Summary'][f'CV with {model_name} - {version} Data'] = [', '.join(predictors), f'Group K-Fold (K={splits})', cv_stats['TP'], cv_stats['TN'], cv_stats['FP'], cv_stats['FN'], cv_stats['correct'],  cv_stats['auc_roc'], cv_stats['accuracy'],  cv_stats['auc_roc_sklearn'], cv_stats['accuracy_sklearn']]
    self.stats['Model_Results'][f'{model_name} - {version}'] = pd.DataFrame(cv_results)
    for occasion in self.occasions:
      if len(incorrect[(incorrect['subid']==occasion.subid) & (incorrect['condition'] == occasion.condition)]):
        occasion.stats[version]['cv'] = 'incorrect'
      elif len(correct[(correct['subid']==occasion.subid) & (correct['condition'] == occasion.condition)]):
        occasion.stats[version]['cv'] = 'correct'
      else:
        occasion.stats[version]['cv'] = 'excluded'
  
  # def create_random_forest(self, version):
  #   selected_features=['curve_auc', 'rise_rate', 'fall_duration', 'peak']
  #   test_size=0.25
  #   model, roc_auc, accuracy = ML_with_rf(self.stats[version], version, self.feature_visuals_path, test_size=test_size, selected_features=selected_features)
  #   self.stats['Models'][f'Random Forest - {version} Data'] = [', '.join(selected_features),f'Holdout Method (Test Size = {test_size})', roc_auc, accuracy]
  #   self.models[version]['random_forest'] = model
  
  # def create_logistic_regression(self, version):
  #   selected_features=['curve_auc', 'rise_rate', 'fall_duration', 'peak']
  #   test_size=0.25
  #   model, roc_auc, accuracy = ML_with_lr(self.stats[version], test_size, selected_features)
  #   self.stats['Models'][f'Logistic Regression - {version} Data'] = [', '.join(selected_features), f'Holdout Method (Test Size = {test_size})', roc_auc, accuracy]

  #   self.models[version]['logistic_regression'] = model
  def create_temp_histogram(self):
    temperatures = []
    for occasion in self.occasions:
      data = occasion.raw_dataset['Temperature_C'].tolist()
      temperatures.extend(data)
    temperatures_below_28 = [temp for temp in temperatures if temp < 28]
    print(len(temperatures_below_28) / len(temperatures))

    import matplotlib.pyplot as plt
    plt.hist(temperatures, bins = [20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40])
    plt.ylabel("Counts (1000's)")
    plt.xlabel('Temperature (Celsius)')
    plt.title('Temperature Distribution')
    plt.xticks([20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40])
    plt.yticks(ticks = [2000, 4000, 6000, 8000, 10000, 12000, 14000, 16000, 18000], labels=[2, 4, 6, 8, 10, 12, 14, 16, 18])
    plt.savefig(f'{self.export_folder}/temperature_histogram.png')

  def create_report_by_occasion(self):
    writer = pd.ExcelWriter(f'{self.export_folder}/skyn_report_MARS.xlsx', engine='xlsxwriter')
    for version in ['Cleaned', 'Raw']:
      self.stats[version].to_excel(writer, index=False, sheet_name=f'Features {version}')
      for model_name in ['random_forest', 'logistic_regression']:
        self.stats['Model_Results'][f'{model_name} - {version}'].to_excel(writer, index=False, sheet_name=f'{model_name} - {version}')

    # self.stats['Models'].to_excel(writer, sheet_name='Model Summaries')

    #variable_key.to_excel(writer, sheet_name='Variable Key', index=False)
    counter = 0

    for occasion in self.occasions:
      for version in ['Cleaned', 'Raw']:
        row = (counter * 24) + 2
        col = 14
        stats = occasion.stats[version]
        metadata = occasion.info_repository
        sheet_name = f'Report by Occasion {version}'
        basic_info = pd.Series(name='Basic Info', data=[occasion.subid, occasion.condition, stats['drink_total']], index=['SubID', 'Condition', 'Drink Total'])
        basic_info.to_excel(writer, sheet_name = sheet_name, startrow = row, startcol=1)

        general_stats = pd.Series(name='TAC Dataset: General Stats',
        data=[stats['mean'], stats['stdev'], stats['sem'], stats['TAC_N'], stats['baseline_mean'], stats['baseline_stdev'], stats['average_tac_difference'], stats['get_tac_alteration_percent'], stats['not_worn_percent'], stats['valid_duration'], stats['valid_duration_percent'], stats['valid_occasion'], stats['cv']],
        index=['TAC Mean', 'TAC SD', 'TAC SEM', 'TAC Count', 'Baseline Mean', 'Baseline SD', 'Avg TAC Difference', 'TAC Alteration %', 'Not Worn %', 'Valid Duration', 'Valid %', 'Valid Occasion', 'CV Result'])
        general_stats.to_excel(writer, sheet_name = sheet_name, startrow = row, startcol=4)

        curve_features = pd.Series(name='Curve Features',
        data=[stats['peak'], stats['auc_total'], stats['auc_per_hour'], stats['curve_duration'], stats['rise_duration'], stats['fall_duration'], stats['rise_rate'], stats['fall_rate']], 
        index=['Peak', 'AUC Total', 'AUC / Hr', 'Curve Duration', 'Rise Duration', 'Fall Duration', 'Rise Rate', 'Fall Rate'])
        curve_features.to_excel(writer, sheet_name = sheet_name, startrow = row, startcol=7)

        if version == 'Raw':
          cleaning_stats = pd.DataFrame({'No Cleaning Stats' : ['This is Raw Data']})
        else:
          cleaning_stats = pd.Series(name='Cleaning Stats', data=[stats['TAC_N'], stats['major_outlier_N'], metadata['signal_processing']['major_threshold'], stats['minor_outlier_N'], metadata['signal_processing']['minor_threshold'], stats['imputed_count'], ], index=['TAC Count', 'Major Outlier Count', 'Major Threshold', 'Minor Outlier Count', 'Major Outlier Count', 'Imputed Count'])
        cleaning_stats.to_excel(writer, sheet_name = sheet_name, startrow = row, startcol=col * 1 + 6)

        motion_stats = pd.Series(name='Motion', data=[stats['mean_motion'], stats['stdev_motion'], stats['sem_motion'], stats['no_motion']], index=['Mean', 'SD', 'SEM', 'No Motion %'])
        motion_stats.to_excel(writer, sheet_name = sheet_name, startrow = row, startcol=col * 2 + 6)

        temp_stats = pd.Series(name='Temperature (C)', data=[stats['mean_temp'], stats['stdev_temp'], stats['sem_temp']], index=['Mean', 'SD', 'SEM'])
        temp_stats.to_excel(writer, sheet_name = sheet_name, startrow = row, startcol=col * 3 + 6)

        if version == 'Cleaned':
          raw_rawSm_r2 = pd.Series(name='R^2 - Raw vs. Raw Smooth', data=[stats['r2_raw_vs_smoothraw']])
          raw_rawSm_r2.to_excel(writer, sheet_name = sheet_name, startrow = row, startcol=col * 4 + 6)

          raw_impSm_r2 = pd.Series(name='R^2 - Raw vs. Imputed Smooth', data=[stats['r2_raw_vs_smoothimputed']])
          raw_impSm_r2.to_excel(writer, sheet_name = sheet_name, startrow = row, startcol=col * 5 + 6)

          imp_impSm_r2 = pd.Series(name='R^2 - Imputed vs. Imputed Smooth', data=[stats['r2_imputed_vs_smoothimputed']])
          imp_impSm_r2.to_excel(writer, sheet_name = sheet_name, startrow = row, startcol=col * 6 + 6)

      counter += 1
    
    counter = 0
    workbook = writer.book
    worksheet = workbook.get_worksheet_by_name('Report by Occasion Cleaned')
    for occasion in self.occasions:
      col_start = 10
      col_interval = 14
      row = (counter * 24) + 2
 
      plot_folder = f'{occasion.plot_folder}/{occasion.subid}/{occasion.condition}'
      x = xlsxwriter.utility.xl_col_to_name(col_start + (col_interval * 0))
      image_start_cell = x + str(row)
      worksheet.insert_image(image_start_cell, f'{plot_folder}/TAC_imputed_smooth_101 - {occasion.subid} - {occasion.condition}.png')

      x = xlsxwriter.utility.xl_col_to_name(col_start + (col_interval * 1))
      image_start_cell = x + str(row)
      worksheet.insert_image(image_start_cell, f'{plot_folder}/cleaning/cleaning - {occasion.subid} - {occasion.condition}.png')

      x = xlsxwriter.utility.xl_col_to_name(col_start + (col_interval * 2))
      image_start_cell = x + str(row)
      worksheet.insert_image(image_start_cell, f'{plot_folder}/overlaid/Motion - TAC - {occasion.subid} - {occasion.condition}.png')

      x = xlsxwriter.utility.xl_col_to_name(col_start + (col_interval * 3))
      image_start_cell = x + str(row)
      worksheet.insert_image(image_start_cell, f'{plot_folder}/overlaid/Temp - TAC - {occasion.subid} - {occasion.condition}.png')


      counter += 1
    writer.save()

