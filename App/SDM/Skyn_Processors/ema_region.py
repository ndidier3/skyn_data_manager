import pandas as pd
from App.SDM.Feature_Engineering.tac_features import *
from App.SDM.Feature_Engineering.quality_features import *
from App.SDM.Visualization.tac import *
from App.SDM.Visualization.device_non_wear import plot_device_removal

class emaRegion():
  def __init__(self, df: pd.DataFrame, subid, dataset_identifier, ema_id, self_report_start_time, event_labels, extend_before_hours = 2, extend_after_hours = 4):
    self.df = df

    self.subid = subid
    self.dataset_identifier = dataset_identifier
    self.ema_id = ema_id
    self.self_report_start_time = self_report_start_time
    self.event_labels = event_labels

    self.plot_annotations = {}

    if len(self.df) > 0:
      self_report_region_start = self.self_report_start_time - pd.Timedelta(hours=extend_before_hours) 
      self_report_region_end = self.self_report_start_time + pd.Timedelta(hours=extend_after_hours)
      self.self_report_region = self.df[(self.df['datetime'] >= self_report_region_start) & (self.df['datetime'] <= self_report_region_end)]
      self.self_report_region.reset_index(inplace=True, drop=True)
    else:
      self.self_report_region = pd.DataFrame()
    
    if len(self.self_report_region) > 0:
      region_event_labels = self.event_labels[
        (self.event_labels['timestamp'] >= self.self_report_region.iloc[0]['datetime']) & 
        (self.event_labels['timestamp'] <= self.self_report_region.iloc[-1]['datetime'])
      ]
      for i, row in region_event_labels.iterrows():
        self.plot_annotations[row['label']] = row['timestamp']

      self.self_report_region_quality_features = {
        'subid': self.subid,
        'dataset_identifier': self.dataset_identifier,
        'ema_id': self.ema_id,
        'self_report_start_time': self.self_report_start_time,  
        'total_duration_EMA_REGION': len(self.self_report_region) / 60,
        'TAC_max_EMA_REGION': self.self_report_region['TAC'].max(),
        'TAC_avg_EMA_REGION': self.self_report_region['TAC'].mean(),
        'device_turned_on_duration_EMA_REGION': (self.self_report_region['device_turned_on'].sum()) / 60,
        'device_turned_on_percent_EMA_REGION': (self.self_report_region['device_turned_on'].sum()) / len(self.self_report_region),
        'device_worn_duration_EMA_REGION': (self.self_report_region['device_worn_model'].sum()) / 60,
        'device_worn_percent_EMA_REGION': (self.self_report_region['device_worn_model'].sum()) / len(self.self_report_region),
        'imputed_duration_EMA_REGION': self.self_report_region['imputed'].sum() / 60,
        'imputed_percent_EMA_REGION': self.self_report_region['imputed'].sum() / len(self.self_report_region),
        'low_quality_duration_EMA_REGION': get_low_quality_duration(self.self_report_region),
        'low_quality_percent_EMA_REGION': get_low_quality_percent(self.self_report_region),
        'unimputed_low_quality_duration_EMA_REGION': get_unimputed_low_quality_duration(self.self_report_region),
        'unimputed_low_quality_percent_EMA_REGION': get_unimputed_low_quality_percent(self.self_report_region),
        'negative_duration_EMA_REGION': (self.self_report_region['TAC'] <= 0).sum() / 60,
        'sub_negative_10_duration_EMA_REGION': (self.self_report_region['TAC'] <= -10).sum() / 60,
        'sub_negative_10_percent_EMA_REGION': (self.self_report_region['TAC'] <= -10).sum() / len(self.self_report_region),
        'consecutive_sub_negative_10_duration_EMA_REGION': (count_longest_consecutive_below(self.self_report_region, X=-10) / 60),
        'sub_negative_20_duration_EMA_REGION': (self.self_report_region['TAC'] <= -20).sum() / 60,
        'sub_negative_20_percent_EMA_REGION': (self.self_report_region['TAC'] <= -20).sum() / len(self.self_report_region),
        'consecutive_sub_negative_20_duration_EMA_REGION': (count_longest_consecutive_below(self.self_report_region, X=-20) / 60),
        'sub_negative_40_duration_EMA_REGION': (self.self_report_region['TAC'] <= -40).sum() / 60,
        'sub_negative_40_percent_EMA_REGION': (self.self_report_region['TAC'] <= -40).sum() / len(self.self_report_region),
        'consecutive_sub_negative_40_duration_EMA_REGION': (count_longest_consecutive_below(self.self_report_region, X=-40) / 60),
        'device_removal_plot_EMA_REGION': None,
        'signal_processing_plot_EMA_REGION': None
      }
    else:
      default_info = {
        'subid': self.subid,
        'dataset_identifier': self.dataset_identifier,
        'ema_id': self.ema_id,
        'self_report_start_time': self.self_report_start_time, 
      }
      keys = [
        "total_duration", 'TAC_max', 'TAC_avg', "device_turned_on_duration", "device_turned_on_percent",
        "device_worn_duration", "device_worn_percent", "imputed_duration",
        "imputed_percent", "low_quality_duration", "low_quality_percent",
        "unimputed_low_quality_duration", "unimputed_low_quality_percent",
        "negative_duration", "sub_negative_10_duration", "sub_negative_10_percent",
        "consecutive_sub_negative_10_duration", "sub_negative_20_duration",
        "sub_negative_20_percent", "consecutive_sub_negative_20_duration",
        "sub_negative_40_duration", "sub_negative_40_percent",
        "consecutive_sub_negative_40_duration", "device_removal_plot",
        "signal_processing_plot"
      ]
      self.self_report_region_quality_features = {f"{key}_EMA_REGION": None for key in keys}
      self.self_report_region_quality_features = {**default_info, **self.self_report_region_quality_features}

  def make_device_removal_plot(self, plot_folder):
    if len(self.self_report_region) > 0:
      date = self.self_report_region.iloc[0]['datetime'].strftime('%B %d, %Y')
      subtitle_text = f'SubID: {self.subid} -- Date: {date} -- EMA: {self.ema_id}'
      self.device_removal_plot_path = plot_device_removal(
        self.self_report_region, plot_folder, self.subid, self.ema_id, self.dataset_identifier, 
        'Temperature_C', 'datetime', motion_variable='Motion', add_color=True, 
        method = 'Model Predictions', prediction_column = 'device_worn_model', df_version = 'EMA_REGION',
        event_timestamps = self.plot_annotations,
        subtitle_text = subtitle_text
      )
      self.self_report_region_quality_features['device_removal_plot_EMA_REGION'] = self.device_removal_plot_path

  def make_signal_processing_plot(self, plot_folder, curve_threshold, drink_total):
    if len(self.self_report_region) > 0:
      date = self.self_report_region.iloc[0]['datetime'].strftime('%B %d, %Y')
      subtitle_text = f'SubID: {self.subid} -- Date: {date} -- EMA: {self.ema_id} -- Drinks: {drink_total}'
      self.signal_processing_plot_path = plot_signal_processing(
        self.self_report_region, plot_folder, self.subid, self.ema_id, self.dataset_identifier, 'EMA_REGION',
        curve_threshold, time_variable='datetime', title = f'Signal Processing',
        event_timestamps = self.plot_annotations,
        subtitle_text = subtitle_text
      )
      self.self_report_region_quality_features['signal_processing_plot_EMA_REGION'] = self.signal_processing_plot_path
