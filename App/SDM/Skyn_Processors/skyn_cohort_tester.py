from ..Reporting.export import *
import pandas as pd
import xlsxwriter
import numpy as np
import os

class skynCohortTester:
  def __init__(self, cohort_processor, models = {}):
    self.models = models
    self.data_folder = cohort_processor.data_folder
    self.cohort_name = cohort_processor.cohort_name
    self.data_out_folder = cohort_processor.data_out_folder
    self.graphs_out_folder = cohort_processor.graphs_out_folder
    self.analyses_out_folder = cohort_processor.analyses_out_folder
    self.merge_variables = cohort_processor.merge_variables
    self.occasions = cohort_processor.occasions
    self.stats = cohort_processor.stats
    self.predictions = {}

  def make_binary_predictions(self, predictors = ['curve_auc', 'rise_rate', 'fall_duration', 'peak', 'fall_rate', 'rise_duration', 'TAC_N', 'average_tac_difference', 'tac_alteration_percent', 'major_outlier_N', 'minor_outlier_N']):
    for version in ['Cleaned', 'Raw']:
      features = self.stats[version]
      if 'major_outlier_N' not in features.columns.tolist():
        features['major_outlier_N'] = [0 for i in range(0, len(features))]
      if 'minor_outlier_N' not in features.columns.tolist():
        features['minor_outlier_N'] = [0 for i in range(0, len(features))]
      for model_name, model in self.models.items():
        self.predictions[model_name + '_' + version] = model.predict(features[predictors])
        predictions = self.predictions[model_name + '_' + version]
        self.stats[version][model_name + '_prediction'] = ['Alc' if x==1 else 'Non' for x in predictions]
        self.stats[version][model_name + '_correct'] = np.where(
          self.stats[version]['condition'] == 'Unk', 
            'unknown',
          np.where(self.stats[version][model_name + '_prediction'] == self.stats[version]['condition'], 
            'correct', 'incorrect'))
        
    python_object_folder = self.analyses_out_folder + '/Python_Objects'
    if not os.path.exists(python_object_folder):
      os.mkdir(python_object_folder)
    

  def create_feature_and_predictions_report(self):
    writer = pd.ExcelWriter(f'{self.analyses_out_folder}/SDM_predictions_{self.cohort_name}.xlsx', engine='xlsxwriter')

    for version in ['Cleaned', 'Raw']:
      to_export = self.stats[version]
      cols = to_export.columns.tolist()
      for model in self.models:
        cols.insert(3, cols.pop(len(cols)-1))
        cols.insert(3, cols.pop(len(cols)-1))
      to_export = to_export[cols]
      to_export = merge_using_subid(to_export, self.merge_variables)
      to_export.to_excel(writer, index=False, sheet_name=f'Features - {version}')

    export_variable_key(writer, new_model_development=False)

    counter = 0
    
    for occasion in self.occasions:
      row = (counter * 20) + 2
      col = 15
      stats = occasion.stats['Cleaned']
      signal_processing_info = occasion.info_repository['signal_processing']
      sheet_name = 'Report by Drinking Episode'


      occasion_data=[occasion.subid, occasion.condition, occasion.dataset_identifier, stats['drink_total'], 'Yes' if occasion.croppable else 'No']
      index_labels = ['SubID', 'Condition', 'Dataset_Identifier', 'Drink Total', 'Data Cropped?']
      for model_name, model in self.models.items():
        results = self.stats['Cleaned']
        prediction_clean = results.loc[(results['subid'] == occasion.subid) & (results['condition'] == occasion.condition) & (results['dataset_identifier'] == occasion.dataset_identifier), model_name + '_prediction'].tolist()[0]
        correct_clean = results.loc[(results['subid'] == occasion.subid) & (results['condition'] == occasion.condition) & (results['dataset_identifier'] == occasion.dataset_identifier), model_name + '_correct'].tolist()[0]

        results = self.stats['Raw']
        prediction_raw = results.loc[(results['subid'] == occasion.subid) & (results['condition'] == occasion.condition) & (results['dataset_identifier'] == occasion.dataset_identifier), model_name + '_prediction'].tolist()[0]
        correct_raw = results.loc[(results['subid'] == occasion.subid) & (results['condition'] == occasion.condition) & (results['dataset_identifier'] == occasion.dataset_identifier), model_name + '_correct'].tolist()[0]

        occasion_data.extend([prediction_clean, correct_clean])
        index_labels.extend([model_name + ' prediction (cleaned)', model_name + ' correct (cleaned)'])
        occasion_data.extend([prediction_raw, correct_raw])
        index_labels.extend([model_name + ' prediction (raw)', model_name + ' correct (raw)'])

      basic_info = pd.Series(
        name='Occasion Info / Model Predictions', 
        data=occasion_data, 
        index=index_labels
        )
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

      cleaning_results = pd.Series(
        name='Cleaning Results', 
        data=[stats['TAC_N'], stats['major_outlier_N'], signal_processing_info['major_threshold'], stats['minor_outlier_N'], signal_processing_info['minor_threshold'], stats['imputed_count'], ], index=['TAC Count', 'Major Outlier Count', 'Major Threshold', 'Minor Outlier Count', 'Minor Threshold', 'Imputed Count'])
      cleaning_results.to_excel(writer, sheet_name = sheet_name, startrow = row, startcol=col * 2 + 5)

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
                             f'{plot_folder}/{occasion.subid}_{occasion.condition}{occasion.dataset_identifier}_smoothed_curve.png', 
                             {'x_scale': x_scale,
                              'y_scale': y_scale})
      
      if occasion.croppable:
        x = xlsxwriter.utility.xl_col_to_name(col_start + (col_interval * 1))
        image_start_cell = x + str(row)
        worksheet.insert_image(image_start_cell, f'{plot_folder}/{occasion.subid}_{occasion.condition}{occasion.dataset_identifier}_cropping.png', 
                              {'x_scale': x_scale,
                                'y_scale': y_scale})
        
      x = xlsxwriter.utility.xl_col_to_name(col_start + (col_interval * (1 + crop_plot_placement_adjustment) + 2))
      image_start_cell = x + str(row)
      worksheet.insert_image(image_start_cell, f'{plot_folder}/cleaning/cleaning - {occasion.subid} - {occasion.condition}{occasion.dataset_identifier}.png', 
                            {'x_scale': x_scale,
                              'y_scale': y_scale})
      
      x = xlsxwriter.utility.xl_col_to_name(col_start + (col_interval * (2 + crop_plot_placement_adjustment) + 2))
      image_start_cell = x + str(row)
      worksheet.insert_image(image_start_cell, f'{plot_folder}/{occasion.subid}_{occasion.condition}{occasion.dataset_identifier}_temp_cleaning.png', 
                             {'x_scale': x_scale,
                              'y_scale': y_scale})

      counter += 1
    writer.save()
      