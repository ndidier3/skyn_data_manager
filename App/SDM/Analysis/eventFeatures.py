from SDM.Analysis.statModel import statModel
from App.SDM.Analysis.featureFlagger import featureFlagger
from SDM.Configuration.file_management import load, save_to_computer
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

class eventFeatures():
  def __init__(self, processed_data_folder, cohort_name):
    self.processors = [load(file[:-4], processed_data_folder) for file in os.listdir(processed_data_folder) if 'processed' in file]
    self.subids_with_event_data = [processor.subid for processor in self.processors]
    self.event_features = pd.concat([processor.event_level_data for processor in self.processors], ignore_index=True)
    self.event_no_features = pd.concat([processor.events_with_no_skyn_data for processor in self.processors])
    self.allFeatureStats = statModel(self.event_features)
    self.noFeatureStats = statModel(self.event_no_features)
    self.stat_frames = []
    self.plot_folder = f'Results/{cohort_name}/FeaturePlots' if len(self.processors) else 'Results/'
    if not os.path.exists(self.plot_folder):
      os.mkdir(self.plot_folder)

    self.feature_names = [
      'ending_non_wear_perc_CURVE', 'consecutive_extreme_values_SEARCH', 'consecutive_extreme_values_CURVE',
      'device_turned_on_percent_CURVE', 'device_turned_on_duration_CURVE', 'device_worn_duration_CURVE', 
      'device_worn_percent_CURVE', 'device_worn_percent_of_device_on_CURVE',
      'negative_duration_CURVE', 'very_negative_duration_CURVE', 'very_negative_duration_SEARCH'
      'duration_CURVE', 'first_tac_CURVE', 'last_tac_CURVE',
      'mean_tac_CURVE', 'peak_CURVE', 'auc_total_CURVE', 'rise_duration_CURVE', 'fall_duration_CURVE', 'rise_rate_CURVE', 
      'fall_rate_CURVE', 'fall_complete_perc_CURVE', ''
    ]

  def add_flags(self):
    flagger = featureFlagger(self.event_features)
    flagger.run_all_flags_and_validations()
    self.event_features = flagger.ftrs
    self.allFeatureStats = statModel(self.event_features)
  
  def add_curve_status_column(self):
    self.event_features['CURVE_STATUS'] = np.where(
      self.event_features['SEARCH_VALID'] == 0, 'search_invalid',
      np.where(self.event_features['data_found_CURVE'], 'curve_found', 'no_curve')
    )
  
  def set_events_with_no_features(self):
    self.event_no_features['data_found_SEARCH'] = False
    self.event_no_features['data_found_CURVE'] = False
    self.event_no_features['SEARCH_VALID'] = 0
    self.event_no_features.rename(columns = {'event_number': 'event'}, inplace=True)
    event_features_no_data_found = self.event_features[~self.event_features['data_found_SEARCH']][
      ['subid',	'dataset_identifier',	'drink_total',	'day_id',	'drkyst_m',	'drkhrs',	'bac_r',	'event', 'data_found_SEARCH', 'data_found_CURVE', 'SEARCH_VALID']
    ]
    self.event_features = pd.concat([self.event_features, self.event_no_features], ignore_index=True)
    self.allFeatureStats = statModel(self.event_features)

    self.event_no_features = pd.concat([self.event_no_features, event_features_no_data_found])

  def set_sub_datasets(self):
    self.matched_events = self.event_features[self.event_features['data_found_SEARCH']==True]
    self.matchedFeatureStats = statModel(self.matched_events)

    self.curve_found_features = self.matched_events[self.matched_events['data_found_CURVE']==True]
    self.no_curve_found_features = self.matched_events[self.matched_events['data_found_CURVE']==False]

  def count_found_search_data(self):
    """ Saves counts of how many self-reported events had SEARCH DATA associated with it (Found or Not Found) """
    self.data_found_counts = {
      'Event with Skyn data': [len(self.matched_events)],
      'Events without Skyn data': [len(self.event_no_features)]
    }
    self.stat_frames.append(pd.DataFrame(self.data_found_counts))

  def count_unique_subids_of_found_search_data(self):
    """ Saves counts of how many unique subids (n) were associated with found vs. not found SEARCH DATA """
    self.subject_counts_by_data_found = {
      'Subjects with Matched Skyn data': [self.matched_events['subid'].nunique()],
      'Subjects with Un-matched events': [self.event_no_features['subid'].nunique()]
    }
    self.stat_frames.append(pd.DataFrame(self.subject_counts_by_data_found))
  
  def count_curve_feature_flags(self):
    self.allFeatureStats.filter_out('data_found_CURVE', False)
    for flag_col in [col for col in self.event_features.columns if 'FLAG' in col]:
      setattr(self, 'counts_' + flag_col, self.allFeatureStats.groupby_counts(flag_col))
      self.stat_frames.append(getattr(self, 'counts_' + flag_col))
    self.allFeatureStats.reset_data()
  
  def count_valid_features(self):
    self.allFeatureStats.filter_out('data_found_CURVE', False)
    for valid_col in [col for col in self.event_features.columns if 'VALID' in col]:
      setattr(self, 'counts_' + valid_col, self.allFeatureStats.groupby_counts(valid_col))
      self.stat_frames.append(getattr(self, 'counts_' + valid_col))
    self.allFeatureStats.reset_data()

  def count_valid_searches(self):
    self.valid_search_counts = self.allFeatureStats.groupby_counts('SEARCH_VALID')
    self.stat_frames.append(self.valid_search_counts)

  def compute_by_found_search(self, column, filter_valid_search = False, filter_invalid_search = False):
    """ 
    > Saves means, sd of continuous column across Found vs. Not Found SEARCH DATA 
    """
    stats = statModel(self.event_features)
    if filter_valid_search:
      stats.filter_out('SEARCH_VALID', 1)
    if filter_invalid_search:
      stats.filter_out('SEARCH_VALID', 0)
    result = stats.groupby_continuous_stats(
      'data_found_SEARCH', column
    )
    self.stat_frames.append(result)

  def count_found_curves(self):
    """
    > Saves counts of how many self-reported events had CURVE DATA associated with it (Found or Not Found) 
    > Includes only data_found_SEARCH == True
    """

    self.curve_found_counts = {
      'Matched Events': [len(self.matched_events)],
      'Curves Found': [len(self.curve_found_features)],
      'Curves Not Found': [len(self.no_curve_found_features)],
    }
    self.stat_frames.append(pd.DataFrame(self.curve_found_counts))
  
  def count_unique_subids_of_found_curves(self, subid_column = 'subid'):
    """ 
    > Saves counts of how many unique subids (n) were associated with found vs. not found CURVE DATA
    > Includes only data_found_SEARCH == True
    """
    self.subject_counts_by_curve_found = {
      'Subjects with Matched Events': [self.matched_events['subid'].nunique()],
      'Curves Found': [self.curve_found_features['subid'].nunique()],
      'Curves Not Found': [self.no_curve_found_features['subid'].nunique()],
    }
    self.stat_frames.append(pd.DataFrame(self.subject_counts_by_curve_found))

  def compute_by_curve_found(self, column):
    """ 
    > Saves means, sd of self-reported drinks across Found vs. Not Found CURVE DATA
    """
    stats = statModel(self.matched_events)
    self.drink_means_by_curve_found = stats.groupby_continuous_stats(
      'data_found_CURVE', column,
    )
    self.stat_frames.append(self.drink_means_by_curve_found)

  def count_rise_completion_bins(self):
    """
    > Saves counts of fall completion across bins 0-1 with 0.1 increment
    > Includes only data_found_SEARCH == True and data_found_CURVE == True 
    """
    stats = statModel(self.curve_found_features)
    # stats.filter_out('SEARCH_VALID', 0)
    self.rise_completion_counts = stats.groupby_counts_within_bins(
      'rise_complete_perc_CURVE',
      start_value = 0,
      increment = 0.1,
      end_value = 1,
      include_end_value_as_bin=True
    )
    self.stat_frames.append(self.rise_completion_counts)

  def count_fall_completion_bins(self):
    """
    > Saves counts of fall completion across bins 0-1 with 0.1 increment
    > Includes only data_found_SEARCH == True and data_found_CURVE == True 
    """
    # self.allFeatureStats.filter_out('SEARCH_VALID', 0)
    stats = statModel(self.curve_found_features)
    self.fall_completion_counts = stats.groupby_counts_within_bins(
      'fall_complete_perc_CURVE',
      start_value = 0,
      increment = 0.1,
      end_value = 1,
      include_end_value_as_bin=True
    )
    self.stat_frames.append(self.fall_completion_counts)
  
  def count_curve_duration_bins(self):
    """
    > Saves counts of fall completion across bins (0 through 24 hours)
    > Includes only data_found_SEARCH == True and data_found_CURVE == True 
    """
    # self.allFeatureStats.filter_out('SEARCH_VALID', 0)
    stats = statModel(self.curve_found_features)
    self.curve_duration_bin_counts = stats.groupby_counts_within_bins(
      'duration_CURVE',
      start_value = 0,
      increment = 1,
      end_value = 24,
      include_end_value_as_bin=True
    )
    self.stat_frames.append(self.curve_duration_bin_counts)

  def count_curve_start_non_wear_bins(self):
    """
    > Saves counts of curve starting non-wear proportions across bins [0, 0.2, 0.4, 0.6, 0.8, 1]
    > Includes only data_found_SEARCH == True and data_found_CURVE == True 
    """
    # self.allFeatureStats.filter_out('SEARCH_VALID', 0)
    stats = statModel(self.curve_found_features)
    self.curve_start_non_wear_counts = stats.groupby_counts_within_bins(
      'starting_non_wear_perc_CURVE',
      start_value = 0,
      increment = 0.2,
      end_value = 1,
      include_start_value_as_bin = True
    )
    self.stat_frames.append(self.curve_start_non_wear_counts)
  
  # def add_non_wear_curve_start_bin_column(self):
  #   # Bins: 0 is its own bin, followed by 0.2-0.4, 0.4-0.6, etc.
  #   bins = np.array([0, 0.0001, 0.2, 0.4, 0.6, 0.8, 1])  # 0 as its own separate bin
  #   labels = ['0'] + [f"{bins[i]}-{bins[i+1]}" for i in range(1, len(bins) - 1)]  # Label for 0 is just "0"

  #   # Apply binning only to non-null values
  #   non_null_data = self.event_features['starting_non_wear_perc_CURVE'].dropna()
  #   binned_data = pd.cut(
  #       non_null_data,
  #       bins=bins,
  #       labels=labels,
  #       right=False,
  #       include_lowest=True
  #   )

  #   self.event_features['starting_non_wear_perc_bin_CURVE'] = binned_data.reindex(self.event_features.index)
  #   self.allFeatureStats = statModel(event_features=self.event_features)

  # def compute_rise_rates_across_starting_non_wear_bins(self):
  #   self.add_non_wear_curve_start_bin_column()
  #   self.allFeatureStats.filter_out('SEARCH_VALID', 0)
  #   self.allFeatureStats.filter_out('data_found_SEARCH', False)
  #   self.allFeatureStats.filter_out('data_found_CURVE', False)
  #   self.rise_rates_across_ending_non_wear = self.allFeatureStats.groupby_continuous_stats(
  #     'starting_non_wear_perc_bin_CURVE',
  #     'rise_rate_CURVE'
  #   )
  #   self.stat_frames.append(self.rise_rates_across_ending_non_wear)
  #   self.allFeatureStats.reset_data()
  
  # def count_curve_end_non_wear_bins(self):
  #   """
  #   > Saves counts of curve ending non-wear proportions across bins [0, 0.2, 0.4, 0.6, 0.8, 1]
  #   > Includes only data_found_SEARCH == True and data_found_CURVE == True 
  #   """
  #   self.allFeatureStats.filter_out('SEARCH_VALID', 0)
  #   self.allFeatureStats.filter_out('data_found_SEARCH', False)
  #   self.allFeatureStats.filter_out('data_found_CURVE', False)
  #   self.curve_end_non_wear_counts = self.allFeatureStats.groupby_counts_within_bins(
  #     'ending_non_wear_perc_CURVE',
  #     start_value = 0,
  #     increment = 0.2,
  #     end_value = 1,
  #     include_start_value_as_bin = True
  #   )
  #   self.allFeatureStats.reset_data()
  #   self.stat_frames.append(self.curve_end_non_wear_counts)
  
  # def add_non_wear_curve_end_bin_column(self):
  #   # Bins: 0 is its own bin, followed by 0.2-0.4, 0.4-0.6, etc.
  #   bins = np.array([0, 0.0001, 0.2, 0.4, 0.6, 0.8, 1])  # 0 as its own separate bin
  #   labels = ['0'] + [f"{bins[i]}-{bins[i+1]}" for i in range(1, len(bins) - 1)]  # Label for 0 is just "0"

  #   # Apply binning only to non-null values
  #   non_null_data = self.event_features['ending_non_wear_perc_CURVE'].dropna()
  #   binned_data = pd.cut(
  #       non_null_data,
  #       bins=bins,
  #       labels=labels,
  #       right=False,
  #       include_lowest=True
  #   )

  #   self.event_features['ending_non_wear_perc_bin_CURVE'] = binned_data.reindex(self.event_features.index)
  #   self.allFeatureStats = statModel(event_features=self.event_features)

  # def compute_fall_rates_across_ending_non_wear_bins(self):
  #   self.add_non_wear_curve_end_bin_column()
  #   self.allFeatureStats.filter_out('SEARCH_VALID', 0)
  #   self.allFeatureStats.filter_out('data_found_SEARCH', False)
  #   self.allFeatureStats.filter_out('data_found_CURVE', False)
  #   self.fall_rates_across_ending_non_wear = self.allFeatureStats.groupby_continuous_stats(
  #     'ending_non_wear_perc_bin_CURVE',
  #     'fall_rate_CURVE'
  #   )
  #   self.stat_frames.append(self.fall_rates_across_ending_non_wear)
  #   self.allFeatureStats.reset_data()

  # def count_unique_subids_across_flags(self, subid_column = 'subid'):
  #   """ 
  #   > Saves unique SubID counts across FLAGS
  #   > Includes only data_found_SEARCH == True and data_found_CURVE == True
  #   """
  #   self.allFeatureStats.filter_out('SEARCH_VALID', 0)
  #   self.allFeatureStats.filter_out('data_found_SEARCH', False)
  #   self.allFeatureStats.filter_out('data_found_CURVE', False)
  #   for flag_col in [col for col in self.event_features.columns if 'FLAG' in col]:
  #     setattr(self, 'subject_counts_' + flag_col, self.allFeatureStats.unique_subids_per_category(
  #       flag_col, subid_column = subid_column
  #     ))
  #     self.stat_frames.append(getattr(self, 'subject_counts_' + flag_col))
  #   self.allFeatureStats.reset_data()
  
  def create_histogram(
      self, df, feature_column, 
      remove_invalid_search = False, 
      remove_valid_search = False,
      remove_invalid_features = False,
      remove_valid_features = False,
      filename = 'histogram'
    ):

    stats = statModel(df)
    if remove_invalid_search:
      stats.filter_out('SEARCH_VALID', 0)
    if remove_valid_search:
      stats.filter_out('SEARCH_VALID', 1)
    if remove_invalid_features:
      stats.filter_out(f'{feature_column}_VALID', 0)
    if remove_valid_features:
      stats.filter_out(f'{feature_column}_VALID', 1)

    df = stats.temp_data
    feature = df[feature_column]

    plt.hist(feature, edgecolor='black')
    plt.xlabel('Value')
    plt.ylabel('Frequency')
    plt.title(f'Distribution of {feature_column}: Curve Not Found')

    note = f"Count: {len(df)}\n"
    plt.text(0.95, 0.95, note, fontsize=10, color='blue', ha='right', va='top', transform=plt.gca().transAxes)
    plt.savefig(f'{self.plot_folder}/{filename}.png')
    plt.close()

  def create_histogram_by_group(
      self, df, feature_column, group_by_column,
      remove_invalid_search = False, 
      remove_valid_search = False,
      remove_invalid_features = False,
      remove_valid_features = False,
      ensure_zero_bin = False,
      filename = 'histogram'
    ):

    stats = statModel(df)
    if remove_invalid_search:
      stats.filter_out('SEARCH_VALID', 0)
    if remove_valid_search:
      stats.filter_out('SEARCH_VALID', 1)
    if remove_invalid_features:
      stats.filter_out(f'{feature_column}_VALID', 0)
    if remove_valid_features:
      stats.filter_out(f'{feature_column}_VALID', 1)
    df = stats.temp_data
    
    print(feature_column)
    print(group_by_column)

    groups = df[group_by_column].unique()
    df.sort_values(by=group_by_column, inplace=True)
    custom_colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']  # Blue, Orange, Green, Red, Purple, Brown

    if ensure_zero_bin:
        min_val = df[feature_column].min()
        max_val = df[feature_column].max()
        bins = np.concatenate(
            ([-0.5, 0.01], np.linspace(0.01, max_val, 9))  # Custom first bin and regular bins
        )
    else:
        bins = 10

    note = f"Total Count: {len(df)}\n"

    for i, group in enumerate(groups):
      print(group)
      group_data = df[df[group_by_column] == group][feature_column]
      # print(df[(df[group_by_column] == group) & (df[feature_column].isnull())]['subid'])
      print('grouped nulls', feature_column, group_data.isnull().sum())
      note += f"{group}: {len(group_data)}\n" 
      plt.hist(group_data, bins=bins, alpha=0.7, label=f'Group {group}', color=custom_colors[i % len(custom_colors)])

    plt.xlabel('Value')
    plt.ylabel('Frequency')
    plt.title(f'Distribution of {feature_column} x {group_by_column}')
    plt.text(0.5, 0.95, note, fontsize=10, color='blue', ha='right', va='top', transform=plt.gca().transAxes)
    plt.legend(title=group_by_column, loc='upper right', fontsize='small', title_fontsize='medium')
    plt.savefig(f'{self.plot_folder}/{filename}.png')
    plt.close()
  
  def create_histograms_of_self_report_by_curve_found(
      self, grouping_variable = 'CURVE_STATUS', 
      self_report_variables = ['drink_total', 'drkhrs', 'bac_r']
    ):
    
    for var in self_report_variables:
      self.create_histogram_by_group(
        self.matched_events, var, grouping_variable, ensure_zero_bin=False, filename = f'hist_{var}_by_{grouping_variable}'
      )
  
  def create_histograms_of_features_by_flags(self):
    df = self.curve_found_features
    features = [
        'duration_CURVE', 'auc_total_CURVE', 'peak_CURVE',
        'rise_rate_CURVE', 'rise_duration_CURVE', 'rise_auc_CURVE',
        'fall_rate_CURVE',  'fall_duration_CURVE', 'fall_auc_CURVE'
    ]
    for feature in features:
      grouping_variable = f'{feature}_STATUS'
      df[grouping_variable] = np.where(
        df['SEARCH_VALID'] == 0, 'search_invalid',
        np.where(df[f'{feature}_VALID'] == 0, 'feature_invalid', 'feature_valid')
      )
      self.create_histogram_by_group(
        df, feature, grouping_variable,
        ensure_zero_bin=False, filename=f'hist_{feature}_by_{grouping_variable}'
      )
  
  def create_histograms_search_quality_by_search_valid(self):
    df = self.matched_events
    features = ['very_negative_duration_SEARCH', 'device_worn_percent_SEARCH', 'device_worn_duration_SEARCH']
    grouping_variable = 'SEARCH_VALID'
    for feature in features:
      feature_nulls = df[feature].isnull().sum()
      self.create_histogram_by_group(
        df, feature, grouping_variable,
        ensure_zero_bin=False,
        filename=f'hist_{feature}_by_{grouping_variable}'
        # ensure_zero_bin = feature in ['device_worn_percent_SEARCH', 'device_worn_duration_SEARCH']
      )

  # def create_histogram_of_features(self):
  #   feature_columns = [
  #       'duration_CURVE', 'auc_total_CURVE', 'peak_CURVE',
  #       'rise_rate_CURVE', 'rise_duration_CURVE', 'rise_auc_CURVE',
  #       'fall_rate_CURVE',  'fall_duration_CURVE', 'fall_auc_CURVE'
  #   ]
  #   for feature_column in feature_columns:
  #     df = self.event_features[self.event_features[f'{feature_column}_VALID'] == 1]
  #     valid_count = len(df)
  #     invalid_count = len(self.event_features[f'{feature_column}_VALID'] == 0)
  #     try:
  #       plt.hist(df[feature_column], edgecolor='black')
  #       plt.xlabel('Value')
  #       plt.ylabel('Frequency')
  #       plt.title(f'Distribution of {feature_column}')

  #       note = f"Valid count: {valid_count}\nInvalid count: {invalid_count}"
  #       plt.text(0.95, 0.95, note, fontsize=10, color='blue', ha='right', va='top', transform=plt.gca().transAxes)
        
  #       plt.savefig(f'{self.plot_folder}/histogram_{feature_column}.png')
  #       plt.close()
  #     except:
  #       print(f'not made: {feature_column}')

  def run_all(self):
    
    self.add_flags()
    self.add_curve_status_column()
    self.set_events_with_no_features()
    self.set_sub_datasets()

    self.count_found_search_data()
    self.count_unique_subids_of_found_search_data()

    self.count_curve_feature_flags()
    self.count_valid_features()

    self.compute_by_found_search('drink_total')
    self.compute_by_found_search('drkhrs')
    self.compute_by_found_search('bac_r')

    self.compute_by_curve_found('drink_total')
    self.compute_by_curve_found('drkhrs')
    self.compute_by_curve_found('bac_r')
    
    self.count_found_curves()
    self.count_unique_subids_of_found_curves()

    self.create_histograms_search_quality_by_search_valid()
    self.create_histograms_of_self_report_by_curve_found()
    self.create_histograms_of_features_by_flags()

    # self.compute_drinks_by_found_curve()
    # self.count_rise_completion_bins()
    # self.count_fall_completion_bins()
    # self.count_curve_duration_bins()
    # self.count_curve_start_non_wear_bins()
    # self.count_curve_end_non_wear_bins()
    # self.compute_rise_rates_across_starting_non_wear_bins()
    # self.compute_fall_rates_across_ending_non_wear_bins()

    # self.create_histogram_of_features()
    # self.create_feature_histogram_no_curve_found('very_negative_duration_SEARCH')
    # self.create_feature_histogram_no_curve_found('device_worn_percent_SEARCH')
    # self.create_feature_histogram_no_curve_found('drink_total')
    # self.create_feature_histogram_no_curve_found('drkhrs')
    # self.create_feature_histogram_no_curve_found('bac_r')

    # self.create_feature_histogram_no_curve_found('very_negative_duration_SEARCH', filter_search_valid=True)
    # self.create_feature_histogram_no_curve_found('device_worn_percent_SEARCH', filter_search_valid=True)
    # self.create_feature_histogram_no_curve_found('drink_total', filter_search_valid=True)
    # self.create_feature_histogram_no_curve_found('drkhrs', filter_search_valid=True)
    # self.create_feature_histogram_no_curve_found('bac_r', filter_search_valid=True)
  
  def export_sheet(self, file_name):
    with pd.ExcelWriter(file_name, engine = 'openpyxl', mode = 'w') as writer:
      self.event_features.to_excel(writer, sheet_name='Features', index=False)
      self.event_no_features.to_excel(writer, sheet_name='No-Skyn-Data', index=False)
      row_index = 0
      for i, frame in enumerate(self.stat_frames):
        frame.to_excel(writer, sheet_name='STATS', startrow=row_index)
        row_index += len(frame) + 2
  
  def save(self, folder, CT=10):
    save_to_computer(self, f'featureAnalysis_CT{CT}', folder)
      

    



    # self.allFeatureStats.filter_out('data_found_SEARCH', False)

    # subid	dataset_identifier	event	day_id	drink_total	
    # curve_search_start_time	curve_search_end_time	data_found_SEARCH	
    # started_curve_count_SEARCH	complete_curve_count_SEARCH	
    # device_one_SEARCH	device_two_SEARCH	device_count_SEARCH	
    # device_turned_on_duration_SEARCH	device_worn_duration_SEARCH	
    # device_worn_percent_of_device_on_SEARCH	negative_duration_SEARCH
    # very_negative_duration_SEARCH	begin_SEARCH	end_SEARCH	
    # duration_SEARCH	first_tac_SEARCH	last_tac_SEARCH	mean_tac_SEARCH	
    # sd_tac_SEARCH	sem_tac_SEARCH	peak_SEARCH	auc_total_SEARCH	
    # data_found_CURVE	ending_non_wear_perc_CURVE	
    # consecutive_extreme_values_CURVE	
    # device_one_CURVE	device_two_CURVE	device_count_CURVE	
    # device_turned_on_duration_CURVE	device_worn_duration_CURVE	
    # device_worn_percent_of_device_on_CURVE	negative_duration_CURVE	
    # very_negative_duration_CURVE	begin_CURVE	end_CURVE	duration_CURVE
    # first_tac_CURVE	last_tac_CURVE	mean_tac_CURVE	sd_tac_CURVE	
    # sem_tac_CURVE	peak_CURVE	auc_total_CURVE	rise_duration_CURVE	
    # fall_duration_CURVE	relative_peak_CURVE	rise_rate_CURVE	
    # fall_rate_CURVE	fall_complete_perc_CURVE
