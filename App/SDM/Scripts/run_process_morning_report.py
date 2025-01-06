from SDM.Run.process_morning_report import process_morning_report

path = 'Inputs/Metadata/ACE_Morning.xlsx'
data_out = 'Results/ACE/EMA/ACE_Morning_Processed.xlsx'
plot_out_duration = 'Results/ACE/EMA/NonWear_Duration_by_Day.png'
plot_out_count = 'Results/ACE/EMA/NonWear_Count_by_Day.png'

process_morning_report(path, data_out, plot_out_duration, plot_out_count)