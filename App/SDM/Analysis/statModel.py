import pandas as pd
import scipy.stats as stats
import numpy as np

def compare_correlation_strengths(r1, n1, r2, n2):
    """
    Compare the strength of two independent correlation coefficients using Fisher's z-transformation.
    Returns the p-value for the difference.
    """
    # Fisher's z-transformation cannot be computed for r = 1 or r = -1, handle this case
    if abs(r1) == 1 or abs(r2) == 1:
        return 0.0 # Or handle as a special case, a perfect correlation is likely significant
        
    if n1 <= 3 or n2 <= 3:
        return np.nan
    
    # Fisher's z-transformation
    z1 = np.arctanh(r1)
    z2 = np.arctanh(r2)
    
    # Standard error of the difference
    se_diff = np.sqrt(1 / (n1 - 3) + 1 / (n2 - 3))
    
    # Z-statistic for the difference
    z_stat = (z1 - z2) / se_diff
    
    # Two-tailed p-value
    p_value = stats.norm.sf(abs(z_stat)) * 2
    
    return p_value

class statModel:
  def __init__(self, event_features):
    self.event_features = event_features

    self.temp_data = self.event_features.copy()

  def reset_data(self):
    self.temp_data = self.event_features.copy()

  def filter_out(self, column, value):
    self.temp_data = self.temp_data[self.temp_data[column] != value]
  
  def groupby_counts(self, column, include_unique_flags=False):
    """
    Get counts for a column, with optional unique flag counts.
    
    Args:
        column (str): Column name to count
        include_unique_flags (bool): If True, adds columns showing counts of rows that are only flagged by this specific flag
        
    Returns:
        pd.DataFrame: Counts with percentages and optional unique flag counts
    """
    # Get basic counts
    group_stats = self.temp_data.groupby(column).size().to_frame(name='Count')
    group_stats['%'] = (group_stats['Count'] / group_stats['Count'].sum()) * 100
    
    # If this is a flag column and unique flags are requested, calculate unique flag counts
    if 'FLAG' in column and include_unique_flags:
        # Get all other flag columns
        flag_cols = [col for col in self.temp_data.columns if 'FLAG' in col and col != column]
        
        # For rows where this flag is 1, check if any other flags are 1
        if 1 in group_stats.index:
            # Get rows where this flag is 1
            flagged_rows = self.temp_data[self.temp_data[column] == 1]
            # Count rows where this is the only flag set to 1
            unique_flagged = flagged_rows[~flagged_rows[flag_cols].eq(1).any(axis=1)]
            unique_count = len(unique_flagged)
            
            # Add to stats
            group_stats.loc[1, 'Unique_Flag_Count'] = unique_count
            group_stats.loc[1, 'Unique_Flag_%'] = (unique_count / group_stats.loc[1, 'Count']) * 100
    
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
    result = self.temp_data.groupby(categorical_column)[continuous_column].agg(['mean', 'std', 'sem', 'sum', 'min', 'max', 'median'])
    result.columns.name = categorical_column
    return result
  
  def unique_subids_per_category(self, column, subid_column='subid'):
    unique_counts = self.temp_data.groupby(column)[subid_column].nunique().to_frame(name=f'N_subjects_by_{column}')
    unique_counts.columns.name = column
    return unique_counts
  
  def multi_groupby_counts(self, column, groubpy_columns=['SubID','Dataset_Identifier']):
    counts = self.temp_data.groupby(groubpy_columns)[column].value_counts()
    counts = counts.reset_index(name=f'{column}_counts')
    return counts

  def multi_groubpy_row_counts(self, groubpy_columns=['SubID','Dataset_Identifier']):
    row_counts = self.temp_data.groupby(groubpy_columns).size()
    row_counts = row_counts.reset_index(name='row_count')
    return row_counts

  def multi_groupby_continuous_stats(self, continuous_column, groubpy_columns=['SubID','Dataset_Identifier']):
    result = self.temp_data.groupby(groubpy_columns)[continuous_column].agg(['mean', 'std', 'sem', 'sum', 'min', 'max', 'median'])
    result.columns.name = '_'.join(groubpy_columns)
    return result

  def continuous_stats(self, continuous_column):
    stats = self.temp_data[continuous_column].agg(['mean', 'std', 'sem', 'min', 'max', 'sum', 'count', 'median'])
    stats_df = stats.reset_index(name=continuous_column)
    stats_df.columns = ['Statistic', continuous_column]
    return stats_df

  def continuous_stats_for_columns(self, column_list):
    all_stats = []
    for column in column_list:
      stats_df = self.continuous_stats(column)
      stats_df = stats_df.set_index('Statistic')  # Set Statistic as the index
      stats_df.columns = [column]  # Rename the column with the specific column name
      all_stats.append(stats_df)
    
    combined_stats_df = pd.concat(all_stats, axis=1)
    return combined_stats_df

  def get_pearson_correlation(self, col1, col2):

    self.temp_data[col1] = pd.to_numeric(self.temp_data[col1], errors='coerce')
    self.temp_data[col2] = pd.to_numeric(self.temp_data[col2], errors='coerce')

    nan_count_col1 = self.temp_data[col1].isna().sum()
    nan_count_col2 = self.temp_data[col2].isna().sum()

    filtered_data = self.temp_data.dropna(subset=[col1, col2])

    col1_data = filtered_data[col1].tolist()
    col2_data = filtered_data[col2].tolist()
    count = len(col2_data)

    correlation, p_value = stats.pearsonr(col1_data, col2_data)
    self.reset_data()

    return correlation, p_value, count, nan_count_col1, nan_count_col2

  def get_pearson_correlations(self, repeated_col, column_list):
    r_results = []
    for col in column_list:
      correlation, p_value, count, nan_count1, nan_count2 = self.get_pearson_correlation(repeated_col, col)
      r_results.append({
        "Column": col,
        "Repeated_Column": repeated_col,
        "Correlation": correlation,
        "P_Value": p_value,
        "Count": count,
        f"Null Count in {repeated_col}": nan_count1,
        f"Null Count in Assessed Column": nan_count2,
      })
    
    result_df = pd.DataFrame(r_results)
    result_df.set_index('Column', inplace=True)
    return result_df

  def get_subid_level_stats(self, column_types_dict):
    """
    Generate subid-level statistics for a mix of continuous and categorical columns.
    
    Args:
        column_types_dict (dict): Dictionary where keys are column names and values are either 'numeric' or 'categorical'
        
    Returns:
        pd.DataFrame: Summary statistics for each column at the subid level with header attribute
    """
    all_stats = []
    
    for column, col_type in column_types_dict.items():
        if col_type == 'numeric':
            # For numeric columns, get continuous stats grouped by subid
            stats = self.temp_data.groupby('subid')[column].agg(['mean', 'std', 'sem', 'min', 'max', 'count', 'median'])
            # Create multi-index columns with original column name as first level
            stats.columns = pd.MultiIndex.from_product([[column], stats.columns])
            all_stats.append(stats)
        elif col_type == 'categorical':
            # For categorical columns, get counts grouped by subid
            counts = self.temp_data.groupby(['subid', column]).size().unstack(fill_value=0)
            # Create multi-index columns with original column name as first level
            counts.columns = pd.MultiIndex.from_product([[column], counts.columns])
            all_stats.append(counts)
    
    # Combine all statistics into a single dataframe
    if all_stats:
        result_df = pd.concat(all_stats, axis=1)
        # Add header attribute
        result_df.attrs['header'] = {
            'description': f'Subid-level statistics summary (n={len(result_df.index)})',
        }
        return result_df
    else:
        return pd.DataFrame()