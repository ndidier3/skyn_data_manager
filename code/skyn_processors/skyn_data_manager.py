from skyn_processors.skyn_occasion_processor import skynOccasionProcessor
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
  def __init__(self, folder_path, cohort_name, data_out_folder, graphs_out_folder, analyses_out_folder, subid_search, subid_range, condition_search, condition_range, sub_condition_search = None, sub_condition_range = None, metadata_path = None, episode_start_timestamps_path = None, max_episode_duration = 18):
    self.data_folder = folder_path
    self.cohort_name = cohort_name
    self.data_out_folder = data_out_folder
    self.graphs_out_folder = graphs_out_folder
    self.analyses_out_folder = analyses_out_folder
    self.model_figures_folder = self.analyses_out_folder + 'figures/'
    self.subid_search = subid_search
    self.subid_range = subid_range
    self.condition_search = condition_search
    self.condition_range = condition_range
    self.sub_condition_search = sub_condition_search
    self.sub_condition_range = sub_condition_range
    self.occasion_paths = glob.glob(f'{folder_path}*')
    self.cohort = 'Skyn Cohort'
    self.subids = []
    self.doses = {}
    self.occasions = []
    self.max_episode_duration = max_episode_duration
    self.metadata_path = metadata_path
    self.timestamps_path = episode_start_timestamps_path
    self.merged_raw = None
    self.merged_clean = None
    self.stats = {
      'Cleaned': pd.DataFrame(),
      'Raw': pd.DataFrame(),
      'Model_Summary': pd.DataFrame(index=['Split Method', 'TP', 'TN', 'FP', 'FN', 'Sensitivity', 'Specificity', 'Correct', 'AUC_ROC', 'Accuracy', 'Accuracy_Sklearn']),
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

  def load_bulk_skyn_occasions(self, make_plots=True, force_refresh=False, export_python_object=False):
    for path in self.occasion_paths:
      print(path)
      
      occasion = skynOccasionProcessor(path, self.data_out_folder, self.graphs_out_folder, self.subid_search, self.subid_range, self.condition_search, self.condition_range, self.sub_condition_search, self.sub_condition_range, self.metadata_path, self.timestamps_path)
      occasion.max_duration = self.max_episode_duration
      for dataset_version in ['Raw', 'Cleaned']:
        print(occasion.condition_range)
        print(occasion.condition_search)
        print(occasion.condition)
        occasion.stats[dataset_version]['drink_total'] = get_drink_count(occasion.metadata, occasion.subid, occasion.condition, occasion.sub_condition)
      if (path not in [occasion.path for occasion in self.occasions]) or (force_refresh):

        occasion.process_with_default_settings(make_plots=True)
        occasion.plot_column('Motion')
        occasion.plot_column('Temperature_C')
        occasion.plot_tac_and_temp()
        occasion.plot_temp_cleaning()
        occasion.plot_cleaning_comparison()
        self.occasions.append(occasion)
        occasion.export_workbook()
    if export_python_object:
      save(self, self.cohort_name, './processed_data_and_plots/data_manager_exports')
    
  def run_analyses(self, force_refresh=False):
    if not os.path.exists(self.model_figures_folder):
      os.mkdir(self.model_figures_folder)
    self.export_stats(force_refresh=force_refresh)
    self.export_feature_plots(dataset_versions=['Cleaned', 'Raw'])
    for dataset_version in ['Cleaned', 'Raw']:
      for model_name in ['random_forest', 'logistic_regression']:
        self.cross_validation(dataset_version, model_name)
    self.export_stats()
    self.principal_component_analysis('Cleaned')
    self.principal_component_analysis('Raw')
    """
    THIS REPORT BUILDING NEEDS TO OCCUR EALIRER
    """
    
    # except Exception as error:
    #   print(error)
    #   print('exporting not complete')

  def export_stats(self, force_refresh=False):
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
    for dataset_version in ['Raw', 'Cleaned']:
      for occasion in self.occasions:
        print(occasion.subid)
        print(occasion.stats[dataset_version])
        data[dataset_version]['subid'].append(occasion.subid)
        data[dataset_version]['condition'].append(occasion.condition)
        data[dataset_version]['sub_condition'].append(occasion.sub_condition)
        for key, value in occasion.stats[dataset_version].items():
          refresh = (key not in self.stats[dataset_version].columns.tolist()) or (force_refresh)
          if refresh:
            if key not in data[dataset_version].keys():
              data[dataset_version][key] = []
              data[dataset_version][key].append(value)
            else:
              data[dataset_version][key].append(value)
      print(data[dataset_version])
      for key, value in data[dataset_version].items():
        print(key)
        print(len(value))
      if len(self.stats[dataset_version]) > 0:
        self.stats[dataset_version] = self.stats[dataset_version].merge(pd.DataFrame(data[dataset_version]))
      else:
        self.stats[dataset_version] = pd.DataFrame(data[dataset_version])

  def export_feature_plots(self, dataset_versions=['Cleaned', 'Raw']):
    for dataset_version in dataset_versions:
      plot_folder = plot_box_whisker(self.stats[dataset_version], ['mean', 'curve_auc', 'rise_duration', 'fall_duration', 'peak', 'average_tac_difference'], 'condition', self.model_figures_folder, dataset_version, self.cohort_name)

  def principal_component_analysis(self, dataset_version):
    selected_features=['mean', 'auc_total', 'peak', 'curve_auc', 'rise_duration', 'fall_duration', 'average_tac_difference']
    explained_variances = PCA_with_features(self.stats[dataset_version], selected_features, dataset_version)
    self.stats['PCA'][f'PCA with {dataset_version} Data'] = explained_variances

  def cross_validation(self, dataset_version, model_name):
    if model_name not in self.cv_results[dataset_version].keys():
      self.cv_results[dataset_version][model_name] = {}
    if model_name == 'random_forest':
      cv_stats, cv_results, incorrect, correct, predictors, splits, model = cv_with_rf(self.stats[dataset_version])
    if model_name == 'logistic_regression':
      cv_stats, cv_results, incorrect, correct, predictors, splits, model = cv_with_lr(self.stats[dataset_version])
    self.cv_results[dataset_version][model_name]['cv_stats'] = cv_stats
    self.cv_results[dataset_version][model_name]['cv_results'] = cv_results
    self.cv_results[dataset_version][model_name]['incorrect'] = incorrect
    self.cv_results[dataset_version][model_name]['correct'] = correct
    self.cv_results[dataset_version][model_name]['K'] = splits
    self.stats['Model_Summary'][f'{model_name}_{dataset_version}'] = [f'Group K-Fold (K={splits})', cv_stats['TP'], cv_stats['TN'], cv_stats['FP'], cv_stats['FN'],  (cv_stats['TP'] / (cv_stats['TP'] + cv_stats['FN'])), (cv_stats['TN'] / (cv_stats['TN'] + cv_stats['FP'])),  cv_stats['correct'],  cv_stats['auc_roc'], cv_stats['accuracy'], cv_stats['accuracy_sklearn']]
    self.stats['Model_Results'][f'{model_name} - {dataset_version}'] = pd.DataFrame(cv_results)
    for occasion in self.occasions:
      condition = {'Alc': 1, 'Non': 0}[occasion.condition]
      if len(incorrect[(incorrect['subid']==occasion.subid) & (incorrect['condition'] == condition)]):
        occasion.stats[dataset_version][f'cv_{model_name}'] = 'incorrect'
      elif len(correct[(correct['subid']==occasion.subid) & (correct['condition'] == condition)]):
        occasion.stats[dataset_version][f'cv_{model_name}'] = 'correct'
      else:
        occasion.stats[dataset_version][f'cv_{model_name}'] = 'excluded'
    self.models[dataset_version][model_name] = model
    if model_name == 'random_forest':
      plot_rf_feature_importances(model, predictors, dataset_version, self.cohort_name, self.model_figures_folder)
      plot_rf_tree(model, predictors, dataset_version, self.cohort_name, self.model_figures_folder)

  def create_report(self):
    writer = pd.ExcelWriter(f'{self.analyses_out_folder}/skyn_report_{self.cohort_name}.xlsx', engine='xlsxwriter')

    export_variable_key(writer)
    
    counter = 0
    for occasion in self.occasions:
      row = (counter * 20) + 2
      col = 15
      stats = occasion.stats['Cleaned']
      signal_processing_info = occasion.info_repository['signal_processing']
      sheet_name = 'Report by Drinking Episode'

      basic_info = pd.Series(name='Basic Info', data=[occasion.subid, occasion.condition, occasion.sub_condition, stats['drink_total'], 'Yes' if occasion.croppable else 'No'], index=['SubID', 'Condition', 'Sub_Condition', 'Drink Total', 'Data Cropped?'])
      basic_info.to_excel(writer, sheet_name = sheet_name, startrow = row, startcol=1)

      general_stats = pd.Series(name='TAC Dataset: General Stats',
      data=[stats['mean'], stats['stdev'], stats['sem'], stats['TAC_N'], stats['baseline_mean'], stats['baseline_stdev'], stats['average_tac_difference'], stats['tac_alteration_percent'], stats['not_worn_percent'], stats['valid_duration'], stats['valid_duration_percent'], stats['valid_occasion'], stats['cv_random_forest'], stats['cv_logistic_regression']],
      index=['TAC Mean', 'TAC SD', 'TAC SEM', 'TAC Count', 'Baseline Mean', 'Baseline SD', 'Avg TAC Difference', 'TAC Alteration %', 'Not Worn %', 'Valid Duration', 'Valid %', 'Valid Occasion', 'CV Result - RF', 'CV Result - LR'])
      general_stats.to_excel(writer, sheet_name = sheet_name, startrow = row, startcol=4)

      curve_features = pd.Series(name='Curve Features',
      data=[stats['peak'], stats['auc_total'], stats['auc_per_hour'], stats['curve_duration'], stats['rise_duration'], stats['fall_duration'], stats['rise_rate'], stats['fall_rate']], 
      index=['Peak', 'AUC Total', 'AUC / Hr', 'Curve Duration', 'Rise Duration', 'Fall Duration', 'Rise Rate', 'Fall Rate'])
      curve_features.to_excel(writer, sheet_name = sheet_name, startrow = row, startcol=7)


      cleaning_stats = pd.Series(name='Cleaning Stats', data=[stats['TAC_N'], stats['major_outlier_N'], signal_processing_info['major_threshold'], stats['minor_outlier_N'], signal_processing_info['minor_threshold'], stats['imputed_count'], ], index=['TAC Count', 'Major Outlier Count', 'Major Threshold', 'Minor Outlier Count', 'Minor Threshold', 'Imputed Count'])
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
    
    self.stats['Model_Summary'].to_excel(writer, sheet_name='Model Summaries')

    for dataset_version in ['Cleaned', 'Raw']:
        to_export = self.stats[dataset_version]
        cols = to_export.columns.tolist()
        cols.insert(3, cols.pop(len(cols)-1))
        cols.insert(3, cols.pop(len(cols)-1))
        cols.insert(3, cols.pop(len(cols)-1))
        to_export = to_export[cols]
        to_export.to_excel(writer, index=False, sheet_name=f'Features - {dataset_version}')
        for model_name in ['random_forest', 'logistic_regression']:
          self.stats['Model_Results'][f'{model_name} - {dataset_version}'].to_excel(writer, index=False, sheet_name=get_model_summary_sheet_name(model_name, dataset_version))

    writer.save()
