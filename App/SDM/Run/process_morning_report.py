from SDM.EMA_Processors.morning_report import MorningReport

def process_morning_report(path, data_out, plot_out_duration, plot_out_count):
  morning = MorningReport(path)
  morning.export_processed_data(data_out)
  morning.plot_non_wear_duration_by_day(plot_out_duration)
  morning.plot_non_wear_count_by_day(plot_out_count)
