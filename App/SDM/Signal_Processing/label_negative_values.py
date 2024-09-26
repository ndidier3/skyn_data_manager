
def label_negative_values(df):
  # negative_TAC_reassigned = [tac if tac >= 0 else 0 for tac in df['TAC'].tolist()]
  # df['TAC'] = negative_TAC_reassigned
  # df['TAC_negative_reassigned'] = negative_TAC_reassigned
  df['negative_tac'] = [1 if tac <= 0 else 0 for tac in df['TAC'].tolist()]
  # df['TAC_negative_reassigned'] = negative_TAC_reassigned
  df['below_neg10_tac'] = [1 if tac <= -10 else 0 for tac in df['TAC'].tolist()]

  return df