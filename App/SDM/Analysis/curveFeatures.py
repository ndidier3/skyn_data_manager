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

    self.curve_valid = self.curve_features[self.curve_features['CURVE_VALID'] == 1]
    self.curve_invalid = self.curve_features[self.curve_features['CURVE_VALID'] != 1]

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

  #CURVE QUALITY

  def run_stats(self):
    self.compute_tac_feature_stats()
    self.count_curve_flags()

  def export_workbook_curves(self, file_name):
    with pd.ExcelWriter(file_name, engine = 'xlsxwriter', mode = 'w') as writer:
      self.curve_features.to_excel(writer, sheet_name='Features', index=False)
      
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
