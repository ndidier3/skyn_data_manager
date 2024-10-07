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

signal_quality_feature_key = pd.DataFrame(dict(zip(signal_quality_features, definitions)))
