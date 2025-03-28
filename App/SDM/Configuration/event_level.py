import pandas as pd
from datetime import timedelta
from SDM.Configuration.configuration import get_closest_index_with_timestamp

def get_event_level_indices(
  subid, 
  dataset, 
  event_data, 
  drink_start_column='drkstarttime_m', 
  drink_total_column='totsd_all_m', 
  day_id_column='STUDYDAY', 
  extra_columns=[], 
  pad_hours_before=2, 
  pad_hours_after=24, 
  append_duplicates=False  # Control whether duplicates are appended -- usually repeated start/end indices is not desirable
):
  # Filter and sort event data by subject ID and drink start time
  event_data = event_data[(event_data['ID'] == str(subid)) | (event_data['ID'] == int(subid))]
  event_data = event_data.sort_values(by=drink_start_column, ignore_index=True)
  event_data.reset_index(drop=True, inplace=True)
  
  # Initialize results
  event_start_end_indices = []
  extra_info = []
  
  for i, row in event_data.iterrows():
    if row[drink_start_column]:
      # Calculate start and end indices
      start_index = get_closest_index_with_timestamp(dataset, row[drink_start_column] - timedelta(hours=pad_hours_before), time_diff_limit_hours=12)
      end_index = get_closest_index_with_timestamp(dataset, row[drink_start_column] + timedelta(hours=pad_hours_after), time_diff_limit_hours=12)
      
      if start_index is not None and end_index is not None:
        new_entry = [start_index, end_index, row[drink_total_column], row[day_id_column]]
        
        # Append only if duplicates are allowed or the entry is unique
        if append_duplicates or new_entry not in event_start_end_indices:
          event_start_end_indices.append(new_entry)
          extra_info.append(
            dict(zip([col for col in extra_columns], [row[col] for col in extra_columns]))
          )
      else:
        event_start_end_indices.append([None, None, row[drink_total_column], row[day_id_column]])
        extra_info.append(
            dict(zip([col for col in extra_columns], [row[col] for col in extra_columns]))
          )
  return event_start_end_indices, extra_info

def create_event_level_dataframe(subid, dataset_identifier, events):
  all_events_features = []

  for event in events:
    combined_features = {
      'subid': subid,
      'dataset_identifier': dataset_identifier,
      'event': event.event_number,
      'day_id': event.day_id,
      'drink_total': event.drink_total,
      'curve_not_found_reason': event.curve_not_found_reason
    }
    combined_features.update(event.extra_info)
    for d in event.all_features.values():
        combined_features.update(d)
    all_events_features.append(combined_features)

  return pd.DataFrame(all_events_features)