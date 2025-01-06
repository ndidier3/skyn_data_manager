import pandas as pd
from datetime import datetime, timedelta
# import pyreadstat
# conda activate spss-conversion
pyreadstat = "comment me out and activate pyreadstat!"

# .sav file to convert
path = 'Inputs/Metadata/MORNING_taken.sav'
out = 'Inputs/Metadata/ACE_Morning.xlsx'

def convert_ceesecs_to_date(ceesecs_timestamp):
    if pd.isnull(ceesecs_timestamp):
        return pd.NaT
    ceesecs_epoch = datetime(1582, 10, 14)
    return ceesecs_epoch + timedelta(seconds=ceesecs_timestamp)

df, metadata = pyreadstat.read_sav(path, apply_value_formats=True) 
# df['SurveySubmittedDate'] = df['SurveySubmittedDate'].apply(convert_ceesecs_to_date)
# df['daybefore'] = df['daybefore'].apply(convert_ceesecs_to_date)
# df['drkstarttime_m'] = df['drkstarttime_m'].apply(convert_ceesecs_to_date)
# df['drkendtime_m'] = df['drkendtime_m'].apply(convert_ceesecs_to_date)
df['SURVEYTIME'] = df['SURVEYTIME'].apply(convert_ceesecs_to_date)

# Convert variable labels (column_names_to_labels) to a DataFrame
dict_metadata = {
  'Variable': list(metadata.column_names_to_labels.keys()),
  'Text': list(metadata.column_names_to_labels.values()),
  'Options': [],
  'DataType': list(metadata.readstat_variable_types.values()),
  'MeasureType': list(metadata.variable_measure.values()),
  'StorageWidth': list(metadata.variable_storage_width.values()),
  'DisplayWidth': list(metadata.variable_display_width.values())
}

for variable in dict_metadata['Variable']:
  try:
    label_key = metadata.variable_to_label[variable]
    labels = metadata.value_labels[label_key]
    result = " | ".join(f"{key}, {value}" for key, value in labels.items())
    dict_metadata['Options'].append(result)
  except:
    dict_metadata['Options'].append("")

# used_surveys = {}
# unique_surveys = df['Survey'].unique().tolist()
# for s in unique_surveys:
#   used_surveys[f'Used_{s}'] = []

# for variable in dict_metadata['Variable']:
#   filtered_df = df[df[variable].notna() & (df[variable] != "")]
#   used_surveys_for_variable = filtered_df['Survey'].unique().tolist()
#   for s in unique_surveys:
#     if s in used_surveys_for_variable:
#       used_surveys[f'Used_{s}'].append(1)
#     else:
#       used_surveys[f'Used_{s}'].append(0)

# dict_metadata.update(used_surveys)
var_labels_df = pd.DataFrame(dict_metadata)

# with pd.ExcelWriter('ACE_Key.xlsx') as writer:
with pd.ExcelWriter(out) as writer:
    df.to_excel(writer, sheet_name='Data', index=False)  # Save the data
    var_labels_df.to_excel(writer, sheet_name='KEY', index=False)  # Save variable labels

