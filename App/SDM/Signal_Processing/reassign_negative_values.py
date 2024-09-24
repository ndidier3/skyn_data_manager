
def reassign_negative_values(df):
  negative_TAC_reassigned = [tac if tac >= 0 else 0 for tac in df['TAC'].tolist()]
  df['TAC'] = negative_TAC_reassigned
  df['TAC_negative_reassigned'] = negative_TAC_reassigned
  df['negative_reassigned_zero'] = [1 if tac >= 0 else 0 for tac in df['TAC'].tolist()]
  return df