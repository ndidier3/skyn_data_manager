def cv_custom(estimator, features, X, y):
  cv_results = {
    'subid': [],
    'y_truth': [],
    'predictions': [],
    'predicted_prob': [],
    'prediction_correct': [],
    'prediction_result': []
  }
  cv_stats = {
    'pred_count': 0,
    'folds': 0,
    'correct': 0,
    'accuracy': 0.0,
    'auc_roc': 'NA',
    'TP': 0,
    'TN': 0,
    'FP': 0,
    'FN': 0
  }
  for subid in features['subid'].unique().tolist():
    #the split
    X_train = X[features['subid']!=subid]
    y_train = y[features['subid']!=subid]
    X_test = X[features['subid']==subid]
    y_test = y[features['subid']==subid].tolist()

    #train
    fitted = estimator.fit(X_train, y_train)
    
    #results updates
    cv_results["subid"].append(subid)
    cv_results['y_truth'].append(y_test)
    predictions = fitted.predict(X_test)
    cv_results['predictions'].append(predictions)
    probabilities = fitted.predict_proba(X_test)
    cv_results['predicted_prob'].append(probabilities)
    correct_predictions = [y_test[i]==predictions[i] for i in range(0, len(predictions))]
    cv_results['prediction_correct'].append(correct_predictions)

    TPs = [((y_test[i]==predictions[i]) and (predictions[i]==1)) for i in range(0, len(predictions))]
    TNs = [((y_test[i]==predictions[i]) and (predictions[i]==0)) for i in range(0, len(predictions))]
    FPs = [((y_test[i]!=predictions[i]) and (predictions[i]==1)) for i in range(0, len(predictions))]
    FNs = [((y_test[i]!=predictions[i]) and (predictions[i]==0)) for i in range(0, len(predictions))]
    
    cv_results['prediction_result'].append([['TP','TN','FP','FN'][i] for i, result in enumerate([TPs, TNs, FPs, FNs]) if any(result)])
    #stat updates
    cv_stats['folds'] += 1
    cv_stats['pred_count'] += len(y_test)
    cv_stats['correct'] += sum(correct_predictions)
    cv_stats['accuracy'] = cv_stats['correct'] / cv_stats['pred_count']
    cv_stats['TP'] += sum(TPs)
    cv_stats['TN'] += sum(TNs)
    cv_stats['FP'] += sum(FPs)
    cv_stats['FN'] += sum(FNs)
  
  return cv_results, cv_stats