import pandas as pd
from datetime import datetime
from App.SDM.Analysis.dayFeatures import dayFeatures

# Define paths
user_root = '/users/ndidier'
project_root = f'{user_root}/SDM/skyn_data_manager'
processed_data_folder = f'{project_root}/Inputs/Skyn_Data_PROCESSED/LINC'
cohort_name = 'LINC'

# Get today's date for file naming
today = datetime.today().strftime('%m.%d.%Y')

# Initialize day features analysis
day_features = dayFeatures(processed_data_folder)

# Export results to Excel
day_features.export_workbook_days(
    f'{project_root}/Results/{cohort_name}/{cohort_name}_day_stats_{today}.xlsx'
)

print(f"Day-level analysis complete. Results saved to: {cohort_name}_day_stats_{today}.xlsx") 