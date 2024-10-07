import pandas as pd

signal_quality_features = [
  'device_turned_on', 
  'device_worn', 
  'prediction_strategy', 
  'negative_value', 
  'very_negative_value'
]

definitions = [
  '1 = Device Turned ON (TAC, Temp, and Motion recorded) | 0 = Device Turned OFF (null TAC, temp, and motion)',
  '1 = Device Worn (and device turned on) | 0 = Device NOT Worn (while device was on) | blank/null value (device was turned off)',
  'Non-wear detection is determined either by a TEMP CUTOFF (all readings with Temp < X Celcius [default X=28] are labeled non-wear) or MODEL (a trained Random Forest model that assesses temp/motion features) -- The trained MODEL is used by default, but the TEMP CUTOFF is used when the device is just equipped because certain temp/motion features that are required by the MODEL are not able to be generated.',
  'TAC is below 0 Celcius',
  'TAC is below -10 Celcius'
]

signal_quality_feature_key = pd.DataFrame({
    'Feature': signal_quality_features,
    'Definition': definitions
  })

signal_quality_aggregate_features = [
  'Dataset_ID',
  'DayNo',
  'device_turned_on_duration',
  'device_turned_on_percentage_of_day',
  'device_worn_duration',
  'device_worn_percentage_of_device_on',
  'device_worn_percentage_of_day',
  'negative_duration',
  'very_negative_duration'
]

definitions = [
    'First Digit = BurstID, Second-Third Digit = Final Day number of interest)',
    'Day ID assigned by script (labels first day found as 0, second as 1, etc.)',
    'Total amount of time (hours) where device was on (and actively producing signal readings)',
    'device_turned_on_duration / 24 (hours in a day)',
    'Total amount of time (hours) where device was worn (note: this assumes device was also turned on, so therefore this will always be less than device_turned_on_duration)' ,
    'device_worn_duration / device_turned_on_duration',
    'device_worn_duration / 24 (hours in a day)',
    'Total amount of time (hours) where TAC reading was below 0 Celcius',
    'Total amount of time (hours) where TAC reading was below -10 Celcius'
]

signal_quality_aggregate_feature_key = pd.DataFrame({
      'Feature': signal_quality_aggregate_features, 
      'Definition': definitions
    })