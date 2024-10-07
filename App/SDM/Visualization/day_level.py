import pandas as pd
import matplotlib.pyplot as plt

# title = 'Distribution of Device Turned On Duration'
title = 'Distribution of Device Worn Duration'
# variable = 'device_turned_on_duration'
variable = 'device_worn_duration'

df = pd.read_excel('/Users/nathandidier/Desktop/Brown PhD/Merrill Lab/ARC_Burst1_day_level_quality_metrics.xlsx')

df = df.sort_values(by=['SubID', 'DayNo'])

# Step 2: Group by 'SubID' and filter first and last 'DayNo' for each group
first_last_df = df.groupby('SubID').agg(
    first_day=('DayNo', 'first'),
    last_day=('DayNo', 'last')
).reset_index()

# Step 3: Filter the original DataFrame to retain only rows corresponding to the first and last DayNo
filtered_df = df[df['DayNo'].isin(first_last_df['first_day']) | df['DayNo'].isin(first_last_df['last_day'])]

filtered_df = filtered_df[filtered_df['SubID']!=1006]

plt.figure(figsize=(12, 6))
plt.hist(filtered_df[variable], bins=24, edgecolor='black')
plt.title(title)
plt.xlabel(variable)
plt.ylabel('Frequency')

plt.savefig(f'/Users/nathandidier/Desktop/Brown PhD/Merrill Lab/{variable}_histogram.png')