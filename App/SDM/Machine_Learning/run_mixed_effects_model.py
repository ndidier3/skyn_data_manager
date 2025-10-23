from SDM.Machine_Learning.model import Model
from sklearn.metrics import mean_absolute_error
import pandas as pd

def run_mixed_effects_model(df, predictors, outcome, grouping_column):
    
    # Define the outcome variable and predictor variables

    # Initialize the Model class with MixedLM model
    model_instance = Model(model=None, name='MixedLM', predictors=predictors, outcome=outcome, grouping_column=grouping_column)

    # Call the fit_cv function with the filtered DataFrame
    X = df[predictors + [grouping_column]]
    y = df[outcome]

    # Run cross-validation with the model
    model_instance.fit_cv(X, y, n_folds=3)

    # Get the evaluation metrics
    split_metrics_df, avg_metrics_df = model_instance.get_metrics_group_cv()

    # Print the evaluation results
    print("Model Evaluation - Split Metrics:")
    print(split_metrics_df)
    print("\nModel Evaluation - Average Metrics:")
    print(avg_metrics_df)

    result_df_filtered = model_instance.results_df.loc[:, ~model_instance.results_df.columns.isin(df.columns)]

    # Merge results back into the original dataframe
    final_df = pd.concat([df, result_df_filtered], axis=1)

    final_df.to_excel('Results/ARC_10/drink_total_preds.xlsx', index=False)

    passed = final_df[final_df['CURVE_VALID'] == 1]
    passed_not_null_idx = passed['y_pred_all'].notnull()
    passed_y_pred = passed.loc[passed_not_null_idx, 'y_pred_all']
    passed_y = passed.loc[passed_not_null_idx, 'drink_total']
    passed_mae = mean_absolute_error(passed_y, passed_y_pred)
    print('high quality MAE:')
    print(passed_mae)

    flagged = final_df[final_df['CURVE_VALID'] != 1]
    flagged_not_null_idx = flagged['y_pred_all'].notnull()
    flagged_y_pred = flagged.loc[flagged_not_null_idx, 'y_pred_all']
    flagged_y = flagged.loc[flagged_not_null_idx, 'drink_total']
    flagged_mae = mean_absolute_error(flagged_y, flagged_y_pred)
    print('low quality MAE:')
    print(flagged_mae)
    
    return model_instance, split_metrics_df, avg_metrics_df