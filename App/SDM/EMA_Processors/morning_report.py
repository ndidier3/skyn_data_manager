import pandas as pd
import traceback
from SDM.Visualization.device_non_wear import create_histogram_self_reported_non_wear

def time_difference_in_minutes(t1, t2):
  delta1 = pd.Timestamp.combine(pd.Timestamp(0).date(), t1) - pd.Timestamp(0)
  delta2 = pd.Timestamp.combine(pd.Timestamp(0).date(), t2) - pd.Timestamp(0)
  return abs((delta1 - delta2).total_seconds() / 60)

def within_X_minutes(row, ref_column, target_columns, threshold=30):
  ref_time = row[ref_column]
  if pd.notna(ref_time):  # Check if ref_time is not NaT
    ref_time = ref_time.time()
    for col in target_columns:
      target_time = row[col]
      if pd.notna(target_time):  # Check if target_time is not NaT
        target_time = target_time.time()
        if time_difference_in_minutes(ref_time, target_time) <= threshold:
          return 1
    
  return 0 

class MorningReport:
  def __init__(self, path):
    
    self.morning_data = pd.read_excel(path)
    self.morning_data_key = pd.read_excel(path, sheet_name='KEY')
    self.day_ids = sorted(self.morning_data['EMADAYN'].unique().tolist())
    self.device_non_wear_columns = ['braceoff1', 'braceon1', 'braceoff2_1', 'braceon2_1', 'braceoff2_2', 'braceon2_2', 'braceoff3_1', 'braceon3_1', 'braceoff3_2', 'braceon3_2', 'braceoff3_3', 'braceon3_3']
    self.includes_bracelet_off = all([col in self.morning_data.columns for col in self.device_non_wear_columns])
    self.day_level_metrics = pd.DataFrame(index=self.day_ids)
    if self.includes_bracelet_off:
      self.calculate_non_wear()
      self.calculate_non_wear_duration_by_day()
      self.calculate_non_wear_count_by_day()
      self.run_quality_checks()    
      
  def calculate_non_wear(self):
    self.morning_data[self.device_non_wear_columns] = self.morning_data[self.device_non_wear_columns].apply(pd.to_datetime, format='%H:%M', errors='coerce')
    self.device_off_duration_columns = []
    for idx in range(0, len(self.device_non_wear_columns), 2):
      new_col_name = self.device_non_wear_columns[idx] + '_duration_hrs'
      self.device_off_duration_columns.append(new_col_name)
      self.morning_data[new_col_name] = self.morning_data[self.device_non_wear_columns[idx+1]] - self.morning_data[self.device_non_wear_columns[idx]]
      self.morning_data[new_col_name] = self.morning_data[new_col_name].dt.total_seconds() / 60 / 60
      #if duration is negative, this indicates that the 'deviceon' time has a smaller military time value than 'deviceoff' time - adding 24 hours resolves this
      self.morning_data[new_col_name] = self.morning_data[new_col_name].apply(lambda x: x + 24 if x < 0 else x)
      self.morning_data[new_col_name] = self.morning_data[new_col_name].apply(lambda x: 24 if x > 24 else x)
    self.morning_data['device_non_wear_duration_hrs'] = self.morning_data[self.device_off_duration_columns].sum(axis=1)

  def calculate_non_wear_duration_by_day(self):
    self.non_wear_duration_by_day = []
    for day in self.day_ids:
      day_data = self.morning_data[self.morning_data['EMADAYN']==day]
      self.non_wear_duration_by_day.append(day_data['device_non_wear_duration_hrs'].mean())
    self.day_level_metrics['non_wear_duration'] = self.non_wear_duration_by_day

  def calculate_non_wear_count_by_day(self):
    self.non_wear_count_by_day = []
    for day in self.day_ids:
      day_data = self.morning_data[self.morning_data['EMADAYN']==day]
      average_non_wear_count = (len(day_data[day_data['bracenumoff']=='Once']) + (len(day_data[day_data['bracenumoff']=='Twice']) * 2) + (len(day_data[day_data['bracenumoff']=='3 times or more']) * 3)) / len(day_data)
      self.non_wear_count_by_day.append(average_non_wear_count)
    self.day_level_metrics['non_wear_count'] = self.non_wear_count_by_day

  def run_quality_checks(self):
    device_off_columns = [col for col in self.device_non_wear_columns if 'off' in col]
    self.morning_data['flag_device_off_time_within_30_min_of_survey'] = self.morning_data.apply(lambda row: within_X_minutes(row, 'SURVEYTIME', device_off_columns), axis=1)
    self.morning_data['flag_non_wear_less_10_min'] = self.morning_data['device_non_wear_duration_hrs'].apply(lambda x: 1 if (x < (10/60)) and (x > 0) else 0)
    self.morning_data['flag_non_wear_over_half_day'] = self.morning_data['device_non_wear_duration_hrs'].apply(lambda x: 1 if x > 12 else 0)
    
    self.count_device_off_time_within_30_min_of_survey_by_day = []
    self.count_non_wear_less_10_min_by_day = []
    self.count_non_wear_over_half_day_by_day = []
    for day in self.day_ids:
      day_data = self.morning_data[self.morning_data['EMADAYN']==day]
      self.count_device_off_time_within_30_min_of_survey_by_day.append(
        day_data['flag_device_off_time_within_30_min_of_survey'].sum()
        )
      self.count_non_wear_less_10_min_by_day.append(day_data['flag_non_wear_less_10_min'].sum())
      self.count_non_wear_over_half_day_by_day.append(day_data['flag_non_wear_over_half_day'].sum())
    self.day_level_metrics['count_device_off_time_within_30_min_of_survey'] = self.count_device_off_time_within_30_min_of_survey_by_day
    self.day_level_metrics['count_non_wear_less_10_min'] = self.count_non_wear_less_10_min_by_day
    self.day_level_metrics['count_non_wear_over_half_day'] = self.count_non_wear_over_half_day_by_day

  def export_processed_data(self, out):
    with pd.ExcelWriter(out) as writer:
      self.morning_data.to_excel(writer, index=False, sheet_name='Data')
      self.day_level_metrics.to_excel(writer, sheet_name = 'Day-Level')
      self.morning_data_key.to_excel(writer, index=False, sheet_name='KEY')
  
  def plot_non_wear_duration_by_day(self, out):
    try:
      create_histogram_self_reported_non_wear(self.day_ids, self.non_wear_duration_by_day, out, version='Duration')
    except Exception:
      if len(self.non_wear_duration_by_day) == 0:
        print('Non-wear data not found.')
      print(traceback.format_exc())

  def plot_non_wear_count_by_day(self, out):
    try:
      create_histogram_self_reported_non_wear(self.day_ids, self.non_wear_count_by_day, out, version='Count')
    except Exception:
      if len(self.non_wear_count_by_day) == 0:
        print('Non-wear data not found.')
      print(traceback.format_exc())
