from cProfile import label
from skyn_data_manager import skynDataManager
import pandas as pd
import glob
from skyn_occasion_processor import skynOccasionProcessor
from utils.Reporting.plotting import *

# test_data = skynDataManager('C:/Users/ndidier/Desktop/skyn_data_manager/raw/Pilot/')

# test_data.load_bulk_skyn_Occasions(make_plots=True)
# grand_df = pd.DataFrame(columns=['Artifacts', 'Temperature_C', 'Motion'])
# for subid, Occasion in test_data.skyn_Occasions.items():
#   data = Occasion.cleaned_dataset[['Artifacts', 'Temperature_C', 'Motion']]
#   grand_df.append(data)

# grand_df = pd.DataFrame(columns=['Artifacts', 'Temperature_C_Norm', 'Motion_Norm'])

# import glob
# filelist = glob.glob('C:/Users/ndidier/Desktop/skyn_data_manager/processed/data/*')
# for file in filelist:
#   df = pd.read_excel(file)
#   df = df[['Artifacts', 'Temperature_C_Norm', 'Motion_Norm', 'Temperature_C', 'Motion']]
#   print(df)
#   grand_df = pd.concat([grand_df, df])
# grand_df.to_excel('C:/Users/ndidier/Desktop/grand_df.xlsx')

# import matplotlib.pyplot as plt

# n, bins, patches = plt.hist(x=df['Artifacts'], bins='auto', color='#0504aa',
#                             alpha=0.7, rwidth=0.85)
# plt.grid(axis='y', alpha=0.75)
# plt.xlabel('Value')
# plt.ylabel('Frequency')
# plt.title('My Very Own Histogram')
# plt.text(23, 45, r'$\mu=15, b=3$')
# maxfreq = n.max()
# # Set a clean upper y-axis limit.
# plt.ylim(ymax=np.ceil(maxfreq / 10) * 10 if maxfreq % 10 else maxfreq + 10)

# df = pd.read_excel('C:/Users/ndidier/Desktop/grand_df.xlsx')
# df = df.sort_values(by="Temperature_C_Norm")
# df.reset_index(inplace=True)
# indices = [int((i/5) * (len(df)-1)) for i in range(0,5)]
# print('indices', indices)
# temp_values = [df.loc[index, 'Temperature_C_Norm'] for index in indices]
# print(temp_values)
# counts = []
# for i in range(0, len(indices)):
#   if i > 0:
#     counts.append(df.loc[indices[i-1]:indices[i], 'Artifacts'].value_counts())
# print(counts)

# df = df.sort_values(by="Motion_Norm")
# df.reset_index(inplace=True)
# indices = [int((i/5) * (len(df)-1)) for i in range(0,5)]
# print('indices', indices)
# motion_values = [df.loc[index, 'Motion_Norm'] for index in indices]
# print(motion_values)
# counts = []
# for i in range(0, len(indices)):
#   if i > 0:
#     counts.append(df.loc[indices[i-1]:indices[i], 'Artifacts'].value_counts())
# print(counts)


# for path in test_data.Occasion_paths:
#   Occasion = skynOccasionProcessor(path)
#   print(path)
#   Occasion.process_with_default_settings(make_plots=True)

  #Occasion.plot_column('motion')

# for subid, Occasion in test_data.skyn_Occasions.items():
#   print(subid, Occasion.stats)

# test = skynOccasionProcessor('C:/Users/ndidier/Desktop/skyn_data_manager/raw/MARS/MARS309 - #5004 - Non.csv')

# test.process_with_default_settings(make_plots=True)

# test = skynOccasionProcessor('C:/Users/ndidier/Desktop/skyn_data_manager/raw/MARS/MARS468 - #5032 - Non.csv')

# test.process_with_default_settings(make_plots=True)

from utils.Reporting.export import *

# test = skynOccasionProcessor('C:/Users/ndidier/Desktop/skyn_data_manager/raw/MARS/MARS531 - #5039 - Non.csv')

# test.process_with_default_settings(make_plots=True)

# # print(test.stats)

test = load('C:/Users/ndidier/Desktop/skyn_data_manager/features', 'Skyn Manager - MARS')

test_data_new = skynDataManager('C:/Users/ndidier/Desktop/skyn_data_manager/raw/MARS/')

test_data_new.occasions = test.occasions
#test_data_new.models = test.models
# print('BOB')
test_data_new.load_bulk_skyn_occasions(make_plots=True, force_refresh=False)

# test_data_new.principal_component_analysis('Cleaned')
# test_data_new.principal_component_analysis('Raw')

# save(test_data_new, test_data_new.export_folder, 'Skyn Manager - MARS')

# test.export_stats()
# test.cross_validation()
# test.create_report_by_occasion()

# test.export_stats()
# test.create_random_forest()

#ML_with_lr(test.stats, test_size=0.25)