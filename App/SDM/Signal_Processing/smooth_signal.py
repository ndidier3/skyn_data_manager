from matplotlib import ticker
from scipy.signal import savgol_filter
import pandas as pd

def smooth_savgol(df, window_length = 71, polyorder = 3, tac_variable = 'TAC'):
    non_null_mask = df[tac_variable].notnull()
    smoothed = savgol_filter(df.loc[non_null_mask, tac_variable], window_length=window_length, polyorder=polyorder, mode='mirror')
    df.loc[non_null_mask, tac_variable] = smoothed
    return df
