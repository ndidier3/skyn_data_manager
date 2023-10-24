from .skyn_cohort_tester import skynCohortTester
from .skyn_dataset_processor import skynDatasetProcessor
from ..Configuration.configuration import *
from ..Reporting.plotting import *
from ..Reporting.export import *
from ..Reporting.export import merge_using_subid
from ..Machine_Learning.model_optimization import *
from ..Machine_Learning.pca import *
from ..Stats.stats import *
from ..Machine_Learning.RF_model_dev import RF_CV_alc_vs_non, RF_CV_worn_vs_removed
from ..Machine_Learning.LR_model_dev import LR_CV_alc_vs_non, LR_CV_worn_vs_removed
import glob
import pandas as pd
import xlsxwriter

class skynCohortProcessor:
  def __init__(self,
      #data in: tac data, metadata, redcap data, etc.
      folder_path, #path to datasets to be analyzed
      metadata_path = None, #path to find metadata
      cohort_name = None, #give a name to this collection  of datasets
      merge_variables = {}, 
      episode_start_timestamps_path = None, 

      #export settings
      data_out_folder = None, #folder to save processed data
      graphs_out_folder = None, #folder to save graphs
      analyses_out_folder = None, #folder to save features and model results

      #configuring how to identify a file's subid, condition and - if needed - a dataset_identifier
      subid_index_start = '#', #character (string) to indicate where subid begins
      subid_index_end = 4, 
      condition_index_start = '.', #character (string) to indicate where condition begins within a filename
      condition_index_end = -3, 
      dataset_identifier_search_index_start = None, #character (numeric string, e.g., 001, 002, 003) to distinguish between subids with repeated conditions
      dataset_identifier_search_index_end = None,  
      
      #signal processing customization
      max_dataset_duration = 18, 
      skyn_timestamps_timezone = -5,
      
      #model development customization
      predictors = ['curve_auc', 'rise_rate', 'fall_duration', 'peak', 'fall_rate', 'rise_duration', 'TAC_N', 'average_tac_difference', 'tac_alteration_percent', 'major_outlier_N', 'minor_outlier_N']
      ):
    
    #data in: tac data, metadata, redcap data, etc.
    self.data_folder = folder_path
    self.cohort_name = cohort_name
    self.metadata_path = metadata_path
    self.merge_variables = merge_variables
    self.timestamps_path = episode_start_timestamps_path
    self.occasion_paths = glob.glob(f'{folder_path}*')
    self.subids = []
    self.occasions = []

    #export settings
    self.data_out_folder = data_out_folder
    self.graphs_out_folder = graphs_out_folder
    self.analyses_out_folder = analyses_out_folder
    self.model_figures_folder = self.analyses_out_folder + '/Figures'
    self.python_object_folder = self.analyses_out_folder + '/Python_Objects'

    #configuring how to identify a file's subid, condition and - if needed - a dataset_identifier
    self.subid_index_start = subid_index_start
    self.subid_index_end = subid_index_end
    self.condition_index_start = condition_index_start
    self.condition_index_end = condition_index_end
    self.dataset_identifier_search_index_start = dataset_identifier_search_index_start
    self.dataset_identifier_search_index_end = dataset_identifier_search_index_end

    #signal processing customization
    self.max_dataset_duration = max_dataset_duration
    self.skyn_timestamps_timezone = skyn_timestamps_timezone

    #results
    self.predictors = predictors
    self.master_dataset = pd.DataFrame()
    self.stats = {
      'Cleaned': pd.DataFrame(),
      'Raw': pd.DataFrame(),
      'Model_Summary_Alc_vs_Non': pd.DataFrame(index=['Split Method', 'TP', 'TN', 'FP', 'FN', 'Sensitivity', 'Specificity', 'Correct', 'AUC_ROC', 'Accuracy', 'Accuracy_Sklearn']),
      'Model_Results_Alc_vs_Non': {},
      'PCA': pd.DataFrame(),
      'Model_Summary_Worn_vs_Removed': pd.DataFrame(index=['Split Method', 'TP', 'TN', 'FP', 'FN', 'Sensitivity', 'Specificity', 'Correct', 'AUC_ROC', 'Accuracy', 'Accuracy_Sklearn']),
      'Model_Results_Worn_vs_Removed': {}}
    
    self.cv_results_alc_vs_non = {
      'Cleaned': {},
      'Raw': {}
    }
    self.models = {}
    self.cv_results_worn_vs_removed = {
    }
    self.device_removal_models = {
      'random_forest': None,
      'logistic_regression': None
    }

  def process_cohort(self, make_plots=True, force_refresh=False, export_python_object=False):
    for i, path in enumerate(self.occasion_paths):
      print(path)
      occasion = skynDatasetProcessor(path, self.data_out_folder, self.graphs_out_folder, self.subid_index_start, self.subid_index_end, self.condition_index_start, self.condition_index_end, self.dataset_identifier_search_index_start, self.dataset_identifier_search_index_end, self.metadata_path, self.timestamps_path, self.skyn_timestamps_timezone)
      metadata = pd.read_excel(self.metadata_path)
      occasion.max_duration = self.max_dataset_duration
      if ((metadata['Use_Data']=='Y') & (metadata['SubID']==occasion.subid) & (metadata['Condition']==occasion.condition)).any():
        for dataset_version in ['Raw', 'Cleaned']:
          occasion.stats[dataset_version]['drink_total'] = get_drink_count(occasion.metadata, occasion.subid, occasion.condition, occasion.dataset_identifier)
        if (path not in [occasion.path for occasion in self.occasions]) or (force_refresh):
          occasion.process_with_default_settings(make_plots=True)
          occasion.plot_column('Motion')
          occasion.plot_column('Temperature_C')
          occasion.plot_tac_and_temp()
          occasion.plot_temp_cleaning()
          occasion.plot_cleaning_comparison()
          self.occasions.append(occasion)
          occasion.export_workbook()
        occasion.cleaned_dataset['dataset_id'] = str(occasion.subid) + occasion.condition + occasion.dataset_identifier if occasion.dataset_identifier else str(occasion.subid) + occasion.condition
      if len(self.master_dataset) == 0:
        self.master_dataset = occasion.cleaned_dataset
      else:
        self.master_dataset = self.master_dataset.append(occasion.cleaned_dataset)
    self.load_stats()
    
    if not os.path.exists(self.python_object_folder):
      os.mkdir(self.python_object_folder)
    if export_python_object:
      save(self, self.cohort_name + '_features_only', self.python_object_folder)
  
  def make_predictions(self, models, prediction_type='binary', save_processor=True):
    if prediction_type == 'binary':
      tester = skynCohortTester(self, models)
      tester.make_binary_predictions(predictors=self.predictors)
      tester.create_feature_and_predictions_report()
      if save_processor:
        save(self, self.cohort_name + '_predictions', self.python_object_folder)
    
  def model_dev_and_test(self, force_refresh=False, save_processor=True, save_models=True):
    if not os.path.exists(self.model_figures_folder):
      os.mkdir(self.model_figures_folder)
    self.load_stats(force_refresh=force_refresh)
    self.export_feature_plots(dataset_versions=['Cleaned', 'Raw'])
    for dataset_version in ['Cleaned', 'Raw']:
      for model_name in ['random_forest', 'logistic_regression']:
        self.cross_validation_alc_vs_non(dataset_version, model_name)
    self.load_stats(force_refresh=force_refresh)
    self.principal_component_analysis('Cleaned')
    self.principal_component_analysis('Raw')
    if save_processor:
      save(self, self.cohort_name + '_models_and_predictions', self.python_object_folder)
    if save_models:
      save(self.models['random_forest_cleaned'], self.cohort_name + 'RF_model_cleaned', self.python_object_folder)
      save(self.models['logistic_regression_cleaned'], self.cohort_name + 'LR_model_cleaned', self.python_object_folder)
      save(self.models['random_forest_raw'], self.cohort_name + 'RF_model_raw', self.python_object_folder)
      save(self.models['logistic_regression_raw'], self.cohort_name + 'LR_model_raw', self.python_object_folder)
  
  def load_stats(self, force_refresh=True):
    data = {
      'Cleaned': {
        'subid': [],
        'condition': [],
        'dataset_identifier': []
        #features will be added here...
      },
      'Raw': {
        'subid': [],
        'condition': [],
        'dataset_identifier': []
        #features will be added here...
      }
    }
    for dataset_version in ['Raw', 'Cleaned']:
      for occasion in self.occasions:
        data[dataset_version]['subid'].append(occasion.subid)
        data[dataset_version]['condition'].append(occasion.condition)
        data[dataset_version]['dataset_identifier'].append(occasion.dataset_identifier)
        for key, value in occasion.stats[dataset_version].items():
          refresh = (key not in self.stats[dataset_version].columns.tolist()) or (force_refresh)
          if refresh:
            if key not in data[dataset_version].keys():
              data[dataset_version][key] = []
              data[dataset_version][key].append(value)
            else:
              data[dataset_version][key].append(value)
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

  def cross_validation_alc_vs_non(self, dataset_version, model_name):
    self.cv_results_alc_vs_non[dataset_version][model_name] = {}
    if model_name == 'random_forest':
      cv_stats, cv_results, incorrect, correct, predictors, splits, model = RF_CV_alc_vs_non(self.stats[dataset_version])
    if model_name == 'logistic_regression':
      cv_stats, cv_results, incorrect, correct, predictors, splits, model = LR_CV_alc_vs_non(self.stats[dataset_version])

    self.cv_results_alc_vs_non[dataset_version][model_name]['cv_stats'] = cv_stats
    self.cv_results_alc_vs_non[dataset_version][model_name]['cv_results'] = cv_results
    self.cv_results_alc_vs_non[dataset_version][model_name]['incorrect'] = incorrect
    self.cv_results_alc_vs_non[dataset_version][model_name]['correct'] = correct
    self.cv_results_alc_vs_non[dataset_version][model_name]['K'] = splits
    self.stats['Model_Summary_Alc_vs_Non'][f'{model_name}_{dataset_version}'] = [f'Group K-Fold (K={splits})', cv_stats['TP'], cv_stats['TN'], cv_stats['FP'], cv_stats['FN'],  (cv_stats['TP'] / (cv_stats['TP'] + cv_stats['FN'])), (cv_stats['TN'] / (cv_stats['TN'] + cv_stats['FP'])),  cv_stats['correct'],  cv_stats['auc_roc'], cv_stats['accuracy'], cv_stats['accuracy_sklearn']]
    self.stats['Model_Results_Alc_vs_Non'][f'{model_name} - {dataset_version}'] = pd.DataFrame(cv_results)
    for occasion in self.occasions:
      condition = {'Alc': 1, 'Non': 0}[occasion.condition]
      if len(incorrect[(incorrect['subid']==occasion.subid) & (incorrect['condition'] == condition)]):
        occasion.stats[dataset_version][f'cv_{model_name}'] = 'incorrect'
      elif len(correct[(correct['subid']==occasion.subid) & (correct['condition'] == condition)]):
        occasion.stats[dataset_version][f'cv_{model_name}'] = 'correct'
      else:
        occasion.stats[dataset_version][f'cv_{model_name}'] = 'excluded'
    self.models[f'{model_name.lower()}_{dataset_version.lower()}'] = model
    if model_name == 'random_forest':
      feature_importance = plot_rf_feature_importances(model, predictors, dataset_version, self.cohort_name, self.model_figures_folder)
      feature_importance.to_excel(f'{self.analyses_out_folder}/feature_importance_{self.cohort_name}_{dataset_version}.xlsx')
      plot_rf_tree(model, predictors, dataset_version, self.cohort_name, self.model_figures_folder)

  def cross_validation_worn_vs_removed(self, model_name):
    self.cv_results_alc_vs_non[model_name] = {}
    if model_name == 'random_forest':
      cv_stats, cv_results, incorrect, correct, predictors, splits, model = RF_CV_worn_vs_removed(self.master_dataset)
    if model_name == 'logistic_regression':
      cv_stats, cv_results, incorrect, correct, predictors, splits, model = LR_CV_worn_vs_removed(self.master_dataset)
    
    self.cv_results_alc_vs_non[model_name]['cv_stats'] = cv_stats
    self.cv_results_alc_vs_non[model_name]['cv_results'] = cv_results
    self.cv_results_alc_vs_non[model_name]['incorrect'] = incorrect
    self.cv_results_alc_vs_non[model_name]['correct'] = correct
    self.cv_results_alc_vs_non[model_name]['K'] = splits
    self.stats['Model_Summary_Worn_vs_Removed'][model_name] = [f'Group K-Fold (K={splits})', cv_stats['TP'], cv_stats['TN'], cv_stats['FP'], cv_stats['FN'],  (cv_stats['TP'] / (cv_stats['TP'] + cv_stats['FN'])), (cv_stats['TN'] / (cv_stats['TN'] + cv_stats['FP'])),  cv_stats['correct'],  cv_stats['auc_roc'], cv_stats['accuracy'], cv_stats['accuracy_sklearn']]
    self.stats['Model_Results_Worn_vs_Removed'][f'{model_name}'] = pd.DataFrame(cv_results)
    
    self.device_removal_models[model_name] = model
    if model_name == 'random_forest':
      feature_importance = plot_rf_feature_importances(model, predictors, 'Cleaned', self.cohort_name, self.model_figures_folder)
      feature_importance.to_excel(f'{self.analyses_out_folder}/feature_importance_{self.cohort_name}.xlsx')
      plot_rf_tree(model, predictors, self.cohort_name, self.model_figures_folder)

  def create_feature_model_and_predictions_report(self):
    writer = pd.ExcelWriter(f'{self.analyses_out_folder}/SDM_model_report_{self.cohort_name}.xlsx', engine='xlsxwriter')

    export_variable_key(writer)
    
    counter = 0
    for occasion in self.occasions:
      row = (counter * 20) + 2
      col = 15
      stats = occasion.stats['Cleaned']
      signal_processing_info = occasion.info_repository['signal_processing']
      sheet_name = 'Report by Drinking Episode'

      basic_info = pd.Series(name='Basic Info', data=[occasion.subid, occasion.condition, occasion.dataset_identifier, stats['drink_total'], 'Yes' if occasion.croppable else 'No'], index=['SubID', 'Condition', 'Dataset_Identifier', 'Drink Total', 'Data Cropped?'])
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
    
    self.stats['Model_Summary_Alc_vs_Non'].to_excel(writer, sheet_name='Model Summaries')

    for dataset_version in ['Cleaned', 'Raw']:
        to_export = self.stats[dataset_version]
        #reordering columns
        cols = to_export.columns.tolist()
        cols.insert(3, cols.pop(len(cols)-1))
        cols.insert(3, cols.pop(len(cols)-1))
        cols.insert(3, cols.pop(len(cols)-1))
        to_export = to_export[cols]

        to_export = merge_using_subid(to_export, self.merge_variables)
        to_export.to_excel(writer, index=False, sheet_name=f'Features - {dataset_version}')
        for model_name in ['random_forest', 'logistic_regression']:
          self.stats['Model_Results_Alc_vs_Non'][f'{model_name} - {dataset_version}'].to_excel(writer, index=False, sheet_name=get_model_summary_sheet_name(model_name, dataset_version))

    writer.close()
  
  def iterative_near_real_time_testing(self):
  
    features = pd.DataFrame(columns=['subid', 'condition', 'curve_duration', 'peak', 'rise_rate', 'fall_rate', 'rise_duration', 'fall_duration', 'avg_tac_diff'])
    for i in range(5, 120, 5):
      features['curve_duration'].append()
      for occasion in self.occasions:

        baseline_mean, baseline_sd = get_baseline_mean_stdev(occasion.cleaned_dataset, 'TAC_imputed_smooth_101')
        peak_index = get_peak_index(occasion.dataset, 'TAC_imputed_smooth_101')
        rise_duration, curve_beginning = get_rise_duration(occasion.cleaned_dataset, 'TAC_imputed_smooth_101', occasion.time_variable, peak_index)
        data = occasion.cleaned_dataset.iloc[curve_beginning: curve_beginning + i]
        #find beginning of curve index
        
        #crop dataset from here to i
        #calculate rise rate, peak, fall rate, rise duration, fall duration, duration, average tac change
