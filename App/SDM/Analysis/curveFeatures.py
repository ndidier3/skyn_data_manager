from App.SDM.Analysis.statModel import statModel
from App.SDM.Skyn_Processors.ema_region import emaRegion
from App.SDM.Configuration.file_management import load, save_to_computer
from App.SDM.Documenting.embed_graphs import embed_graphs_into_workbook_tab
import os
import pandas as pd

class curveFeatures():
  def __init__(self, processed_data_folder):
    self.processors = [load(file[:-4], processed_data_folder) for file in os.listdir(processed_data_folder) if 'processed' in file]
    self.processors = [processor for processor in self.processors if hasattr(processor, 'curve_features')]
    self.curve_features = pd.concat([processor.curve_features for processor in self.processors], ignore_index=True)
    self.curve_features[['subid', 'curve_id']] = self.curve_features[['subid', 'curve_id']].astype(int)
    self.curve_features.drop_duplicates(subset=['subid', 'curve_id'], inplace=True)
    self.curve_stat_frames = []

    self.default_tac_features = [
      'duration_CURVE', 'auc_total_CURVE', 'auc_relative_CURVE', 
      'peak_CURVE', 'relative_peak_CURVE',
      'rise_rate_CURVE', 'rise_duration_CURVE',
      'fall_rate_CURVE',  'fall_duration_CURVE'
    ]

    self.person_level_feature_types = {
        # Continuous TAC features
        'duration_CURVE': 'numeric',
        'auc_total_CURVE': 'numeric',
        'auc_relative_CURVE': 'numeric',
        'peak_CURVE': 'numeric',
        'relative_peak_CURVE': 'numeric',
        'rise_rate_CURVE': 'numeric',
        'rise_duration_CURVE': 'numeric',
        'fall_rate_CURVE': 'numeric',
        'fall_duration_CURVE': 'numeric',
        
        # Quality features from periphery
        'total_duration_PERIPHERY': 'numeric',
        'device_turned_on_duration_PERIPHERY': 'numeric',
        'device_turned_on_percent_PERIPHERY': 'numeric',
        'device_worn_duration_PERIPHERY': 'numeric',
        'device_worn_percent_PERIPHERY': 'numeric',
        'imputed_duration_PERIPHERY': 'numeric',
        'imputed_percent_PERIPHERY': 'numeric',
        'low_quality_duration_PERIPHERY': 'numeric',
        'low_quality_percent_PERIPHERY': 'numeric',
        'unimputed_low_quality_duration_PERIPHERY': 'numeric',
        'unimputed_low_quality_percent_PERIPHERY': 'numeric',
        
        # Quality features from curve
        'total_duration_CURVE': 'numeric',
        'device_turned_on_duration_CURVE': 'numeric',
        'device_turned_on_percent_CURVE': 'numeric',
        'device_worn_duration_CURVE': 'numeric',
        'device_worn_percent_CURVE': 'numeric',
        'consecutive_non_wear_duration_CURVE': 'numeric',
        'consecutive_non_wear_percent_CURVE': 'numeric',
        'flatline_max_CURVE': 'numeric',
        'flatlined_percent_CURVE': 'numeric',
        'jump_duration_CURVE': 'numeric',
        'jump_percent_CURVE': 'numeric',
        'plummet_duration_CURVE': 'numeric',
        'plummet_percent_CURVE': 'numeric',
        'imputed_duration_CURVE': 'numeric',
        'imputed_percent_CURVE': 'numeric',
        'low_quality_duration_CURVE': 'numeric',
        'low_quality_percent_CURVE': 'numeric',
        'unimputed_low_quality_duration_CURVE': 'numeric',
        'unimputed_low_quality_percent_CURVE': 'numeric',
        
        # Categorical features
        'CURVE_VALID': 'categorical',
        'device_count_REGION': 'categorical'
    }

    self.curve_valid = self.curve_features[self.curve_features['CURVE_VALID'] == 1]
    self.curve_invalid = self.curve_features[self.curve_features['CURVE_VALID'] != 1]

  def compile_imputation_info(self):
    """Compile imputation information from all processors"""
    imputation_dfs = []
    for processor in self.processors:
      if hasattr(processor, 'imputation_info'):
        df = processor.imputation_info.copy()
        df['subid'] = processor.subid
        df['dataset_identifier'] = processor.dataset_identifier
        imputation_dfs.append(df)
    return pd.concat(imputation_dfs, ignore_index=True) if imputation_dfs else pd.DataFrame()

  def compute_tac_feature_stats(self):
    valid = statModel(self.curve_valid)
    invalid = statModel(self.curve_invalid)
    valid_feature_stats = valid.continuous_stats_for_columns(self.default_tac_features)
    invalid_feature_stats = invalid.continuous_stats_for_columns(self.default_tac_features)
    self.curve_stat_frames.append(valid_feature_stats)
    self.curve_stat_frames.append(invalid_feature_stats)

  def count_curve_flags(self):
    stats = statModel(self.curve_features)
    for flag_col in [col for col in self.curve_features.columns if 'FLAG' in col]:
      setattr(self, 'counts_' + flag_col, stats.groupby_counts(flag_col))
      self.curve_stat_frames.append(getattr(self, 'counts_' + flag_col))

  def compute_person_level_stats(self):
    """
    Compute person-level statistics for both continuous and categorical curve features.
    Adds the results to curve_stat_frames.
    """
    # Create a copy of the feature types dictionary
    feature_types = self.person_level_feature_types.copy()
    
    # Add any flag columns as categorical
    for col in self.curve_features.columns:
        if 'FLAG' in col:
            feature_types[col] = 'categorical'
    
    # Compute person-level stats
    stats = statModel(self.curve_features)
    person_stats = stats.get_subid_level_stats(feature_types)
    
    self.person_level_stats = person_stats

  def run_stats(self):
    self.compute_tac_feature_stats()
    self.count_curve_flags()
    self.compute_person_level_stats()

  def export_workbook_curves(self, file_name):
    with pd.ExcelWriter(file_name, engine = 'xlsxwriter', mode = 'w') as writer:
      # Add the new Imputation Info tab
      
      self.curve_features.to_excel(writer, sheet_name='Features', index=False)
      self.person_level_stats.to_excel(writer, sheet_name='Person Level Stats', index=True)
      self.compile_imputation_info().to_excel(writer, sheet_name='Imputations', index=False)
      
      row_index = 0
      for i, frame in enumerate(self.curve_stat_frames):
        frame.to_excel(writer, sheet_name='Stats', startrow=row_index)
        row_index += len(frame) + 2
    
      embed_graphs_into_workbook_tab(
        writer.book,
        [
          self.curve_invalid['device_removal_plot'].tolist(),
          self.curve_invalid['signal_processing_plot'].tolist(),
          self.curve_invalid['signal_processing_plot_wide'].tolist()
        ],
         worksheet_name = 'Invalid Curves',
         plot_header_text = '', # this will be revised to work as a list (search valid)
         missing_plot_path_text = 'No Plot Available'
      )

      embed_graphs_into_workbook_tab(
        writer.book,
        [
          self.curve_valid['device_removal_plot'].tolist(),
          self.curve_valid['signal_processing_plot'].tolist(),
          self.curve_valid['signal_processing_plot_wide'].tolist()
        ],
         worksheet_name = 'Valid Curves',
         plot_header_text = '', # this will be revised to work as a list (search valid)
         missing_plot_path_text = 'No Plot Available'
      )
