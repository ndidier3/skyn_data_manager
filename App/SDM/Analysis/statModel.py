import pandas as pd

class statModel:
  def __init__(self, event_features):
    self.event_features = event_features

    self.temp_data = self.event_features.copy()

  def reset_data(self):
    self.temp_data = self.event_features.copy()

  def filter_out(self, column, value):
    self.temp_data = self.temp_data[self.temp_data[column] != value]
  
  def groupby_counts(self, column):
    group_stats = self.temp_data.groupby(column).size().to_frame(name='Count')
    group_stats['%'] = (group_stats['Count'] / group_stats['Count'].sum()) * 100
    group_stats.columns.name = column
    return group_stats

  def groupby_counts_above_below(self, continuous_column, cutoff):
    """Counts values below vs. above (or equal to) cutoff."""
    # Create a new column to classify values as above or below the cutoff
    self.temp_data['above_or_below'] = self.temp_data[continuous_column].apply(
        lambda x: f'below {cutoff}' if x < cutoff else f'at or above {cutoff}'
    )
    group_stats = self.temp_data.groupby('above_or_below').size().to_frame(name='Count')
    group_stats.columns.name = f'{continuous_column} < {cutoff}'

    return group_stats

  def groupby_counts_within_bins(self, column, start_value=0, end_value=1, increment=0.2, 
                                include_start_value_as_bin=False, include_end_value_as_bin=False):
    
    bins = [round(start_value + (i * increment), 2) for i in range(int((end_value - start_value) / increment) + 1)]

    if include_start_value_as_bin:
      bins.insert(1, start_value + 0.0001)  
      
    if include_end_value_as_bin:
      bins.insert(-1, end_value - 0.0001)

    bins = sorted(set(bins))

    # Generate the bin labels
    bin_labels = [f'{bins[i-1]} - {bins[i]}' for i in range(1, len(bins))]

    # Define the 'right' parameter depending on whether we want to include the end value in the last bin
    right = include_end_value_as_bin

    # Create the binned column
    self.temp_data['binned'] = pd.cut(self.temp_data[column], bins=bins, labels=bin_labels, right=right, include_lowest=include_start_value_as_bin)
    
    # Group by the binned column and return the count
    result = self.temp_data.groupby('binned').size().reset_index(name='Count')

    # Rename the 'binned' column to be the column name as the header/label
    result.rename(columns={'binned': f'{column}_binned'}, inplace=True)

    return result

  def groupby_continuous_stats(self, categorical_column, continuous_column):
    result = self.temp_data.groupby(categorical_column)[continuous_column].agg(['mean', 'std', 'sem'])
    result.columns.name = categorical_column
    return result
  
  def unique_subids_per_category(self, column, subid_column='subid'):
    unique_counts = self.temp_data.groupby(column)[subid_column].nunique().to_frame(name=f'N_subjects_by_{column}')
    unique_counts.columns.name = column
    return unique_counts