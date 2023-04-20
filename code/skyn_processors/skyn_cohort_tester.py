from skyn_processors.skyn_occasion_processor import skynOccasionProcessor
from utils.Reporting.export import *
import glob
import pandas as pd
import xlsxwriter
import numpy as np

class skynCohortTester:
  def __init__(self, models, folder_path, cohort_name, data_out_folder, graphs_out_folder, analyses_out_folder, subid_search, subid_range, condition_search, condition_range, sub_condition_search = None, sub_condition_range = None, metadata_path = None, episode_start_timestamps_path = None, max_episode_duration = 18):
    self.models = models
    self.data_folder = folder_path
    self.cohort_name = cohort_name
    self.data_out_folder = data_out_folder
    self.graphs_out_folder = graphs_out_folder
    self.analyses_out_folder = analyses_out_folder
    self.subid_search = subid_search
    self.subid_range = subid_range
    self.condition_search = condition_search
    self.condition_range = condition_range
    self.sub_condition_search = sub_condition_search
    self.sub_condition_range = sub_condition_range
    self.metadata_path = metadata_path
    self.timestamps_path = episode_start_timestamps_path
    self.occasion_paths = glob.glob(f'{folder_path}*')
    self.occasions = []
    self.max_episode_duration = max_episode_duration
    self.predictions = {}
    self.stats = {
      'Cleaned': pd.DataFrame(),
      'Raw': pd.DataFrame(),
      'Model_Summary': pd.DataFrame(index=['Split Method', 'TP', 'TN', 'FP', 'FN', 'Sensitivity', 'Specificity', 'Correct', 'AUC_ROC', 'Accuracy', 'Accuracy_Sklearn']),
      'Model_Results': {},
      'PCA': pd.DataFrame()
    }

  def process_and_make_predictions(self, export_python_object=True):
    for path in self.occasion_paths:
      print(path)
      occasion = skynOccasionProcessor(path, self.data_out_folder, self.graphs_out_folder, self.subid_search, self.subid_range, self.condition_search, self.condition_range, self.sub_condition_search, self.sub_condition_range, metadata_path=self.metadata_path, episode_start_timestamps_path=self.timestamps_path)
      occasion.max_duration = self.max_episode_duration
      occasion.process_with_default_settings(make_plots=True)
      occasion.plot_column('Motion')
      occasion.plot_column('Temperature_C')
      occasion.plot_tac_and_temp()
      occasion.plot_temp_cleaning()
      occasion.plot_cleaning_comparison()
      self.occasions.append(occasion)
      occasion.export_workbook()
    self.load_stats()
    self.stats['Cleaned'].to_excel(f'{self.data_out_folder}/Cleaned_test_stats.xlsx')
    for version in ['Cleaned', 'Raw']:
      predictors = ['curve_auc', 'rise_rate', 'fall_duration', 'peak', 'fall_rate', 'rise_duration', 'TAC_N', 'average_tac_difference', 'tac_alteration_percent']
      model = self.models[version]['random_forest']
      if version == 'Cleaned':
        predictors = predictors + ['major_outlier_N', 'minor_outlier_N']
      X_test = self.stats[version][predictors]
      self.predictions[version] = model.predict(X_test)
      predictions = self.predictions[version]
      self.stats[version]['prediction'] = ['Alc' if x==1 else 'Non' for x in predictions]
      self.stats[version]['correct'] = np.where(self.stats[version]['prediction'] == self.stats[version]['condition'], 'correct', 'incorrect')
    if export_python_object:
      save(self, self.cohort_name, './processed_data_and_plots/data_manager_exports')
  
  def load_stats(self, force_refresh=False):
    print('reached export')
    data = {
      'Cleaned': {
        'subid': [],
        'condition': [],
        'sub_condition': []
        #features will be added here...
      },
      'Raw': {
        'subid': [],
        'condition': [],
        'sub_condition': []
        #features will be added here...
      }
    }
    for version in ['Raw', 'Cleaned']:
      for occasion in self.occasions:
        data[version]['subid'].append(occasion.subid)
        data[version]['condition'].append(occasion.condition)
        data[version]['sub_condition'].append(occasion.sub_condition)
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

  def create_report(self):
    writer = pd.ExcelWriter(f'{self.analyses_out_folder}/skyn_report_{self.cohort_name}.xlsx', engine='xlsxwriter')

    for version in ['Cleaned', 'Raw']:
      to_export = self.stats[version]
      cols = to_export.columns.tolist()
      cols.insert(3, cols.pop(len(cols)-1))
      cols.insert(3, cols.pop(len(cols)-1))
      to_export = to_export[cols]
      to_export.to_excel(writer, index=False, sheet_name=f'Features - {version}')

    export_variable_key(writer, new_model_development=False)

    counter = 0
    for occasion in self.occasions:
      row = (counter * 20) + 2
      col = 15
      stats = occasion.stats['Cleaned']
      signal_processing_info = occasion.info_repository['signal_processing']
      sheet_name = 'Report by Drinking Episode'

      results = self.stats['Cleaned']
      prediction_clean = results.loc[(results['subid'] == occasion.subid) & (results['condition'] == occasion.condition) & (results['sub_condition'] == occasion.sub_condition), 'prediction'].tolist()[0]
      correct_clean = results.loc[(results['subid'] == occasion.subid) & (results['condition'] == occasion.condition) & (results['sub_condition'] == occasion.sub_condition), 'correct'].tolist()[0]
      
      results = self.stats['Raw']
      prediction_raw = results.loc[(results['subid'] == occasion.subid) & (results['condition'] == occasion.condition) & (results['sub_condition'] == occasion.sub_condition), 'prediction'].tolist()[0]
      correct_raw = results.loc[(results['subid'] == occasion.subid) & (results['condition'] == occasion.condition) & (results['sub_condition'] == occasion.sub_condition), 'correct'].tolist()[0]

      basic_info = pd.Series(
        name='Basic Info', 
        data=[occasion.subid, occasion.condition, occasion.sub_condition, stats['drink_total'], 'Yes' if occasion.croppable else 'No', prediction_clean, correct_clean, prediction_raw, prediction_clean], 
        index=['SubID', 'Condition', 'Sub_Condition', 'Drink Total', 'Data Cropped?', 'Prediction (clean)', 'Correct (clean)', 'Prediction (raw)', 'Correct (raw)'])
      basic_info.to_excel(writer, sheet_name = sheet_name, startrow = row, startcol=1)

      general_stats = pd.Series(
        name='TAC Dataset: General Stats',
        data=[stats['mean'], stats['stdev'], stats['sem'], stats['TAC_N'], stats['baseline_mean'], stats['baseline_stdev'], stats['average_tac_difference'], stats['tac_alteration_percent'], stats['not_worn_percent'], stats['valid_duration'], stats['valid_duration_percent'], stats['valid_occasion']],
        index=['TAC Mean', 'TAC SD', 'TAC SEM', 'TAC Count', 'Baseline Mean', 'Baseline SD', 'Avg TAC Difference', 'TAC Alteration %', 'Not Worn %', 'Valid Duration', 'Valid %', 'Valid Occasion'])
      general_stats.to_excel(writer, sheet_name = sheet_name, startrow = row, startcol=4)

      curve_features = pd.Series(
        name='Curve Features',
        data=[stats['peak'], stats['auc_total'], stats['auc_per_hour'], stats['curve_duration'], stats['rise_duration'], stats['fall_duration'], stats['rise_rate'], stats['fall_rate']], 
        index=['Peak', 'AUC Total', 'AUC / Hr', 'Curve Duration', 'Rise Duration', 'Fall Duration', 'Rise Rate', 'Fall Rate'])
      curve_features.to_excel(writer, sheet_name = sheet_name, startrow = row, startcol=7)


      cleaning_stats = pd.Series(
        name='Cleaning Stats', 
        data=[stats['TAC_N'], stats['major_outlier_N'], signal_processing_info['major_threshold'], stats['minor_outlier_N'], signal_processing_info['minor_threshold'], stats['imputed_count'], ], index=['TAC Count', 'Major Outlier Count', 'Major Threshold', 'Minor Outlier Count', 'Minor Threshold', 'Imputed Count'])
      cleaning_stats.to_excel(writer, sheet_name = sheet_name, startrow = row, startcol=col * 2 + 5)

      counter += 1
    
    counter = 0
    workbook = writer.book
    worksheet = workbook.get_worksheet_by_name('Report by Drinking Episode')
    crop_plot_placement_adjustment = 1 if any([occasion.croppable for occasion in self.occasions]) else 0
    for occasion in self.occasions:
      col_start = 10
      col_interval = 13
      row = (counter * 20) + 2

      x_scale = 65/140
      y_scale = 90/182

      plot_folder = f'{occasion.plot_folder}/{occasion.subid}/{occasion.condition}'

      x = xlsxwriter.utility.xl_col_to_name(col_start + (col_interval * 0))
      image_start_cell = x + str(row)
      worksheet.insert_image(image_start_cell, 
                             f'{plot_folder}/{occasion.subid}_{occasion.condition}{occasion.sub_condition}_smoothed_curve.png', 
                             {'x_scale': x_scale,
                              'y_scale': y_scale})
      
      if occasion.croppable:
        x = xlsxwriter.utility.xl_col_to_name(col_start + (col_interval * 1))
        image_start_cell = x + str(row)
        worksheet.insert_image(image_start_cell, f'{plot_folder}/{occasion.subid}_{occasion.condition}{occasion.sub_condition}_cropping.png', 
                              {'x_scale': x_scale,
                                'y_scale': y_scale})
        
      x = xlsxwriter.utility.xl_col_to_name(col_start + (col_interval * (1 + crop_plot_placement_adjustment) + 2))
      image_start_cell = x + str(row)
      worksheet.insert_image(image_start_cell, f'{plot_folder}/cleaning/cleaning - {occasion.subid} - {occasion.condition}{occasion.sub_condition}.png', 
                            {'x_scale': x_scale,
                              'y_scale': y_scale})
      
      x = xlsxwriter.utility.xl_col_to_name(col_start + (col_interval * (2 + crop_plot_placement_adjustment) + 2))
      image_start_cell = x + str(row)
      worksheet.insert_image(image_start_cell, f'{plot_folder}/{occasion.subid}_{occasion.condition}{occasion.sub_condition}_temp_cleaning.png', 
                             {'x_scale': x_scale,
                              'y_scale': y_scale})

      counter += 1
    writer.save()
      