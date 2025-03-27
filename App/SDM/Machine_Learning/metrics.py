import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, mean_squared_error, mean_absolute_error, r2_score, confusion_matrix

import numpy as np
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, 
    f1_score, roc_auc_score, confusion_matrix
)

def compute_binary_metrics(y_true, y_pred, y_prob=None):
    """
    Compute evaluation metrics for binary classification.

    Parameters:
    - y_true (array-like): True labels (0 or 1).
    - y_pred (array-like): Predicted labels (0 or 1).
    - y_prob (array-like, optional): Predicted probabilities for the positive class (1).

    Returns:
    - dict: Dictionary containing accuracy, precision, recall, F1-score, ROC-AUC, and confusion matrix.
    """
    return {
        'accuracy': accuracy_score(y_true, y_pred),
        'precision': precision_score(y_true, y_pred, zero_division=0),
        'recall': recall_score(y_true, y_pred, zero_division=0),
        'f1_score': f1_score(y_true, y_pred, zero_division=0),
        'roc_auc': roc_auc_score(y_true, y_prob) if y_prob is not None else None,
        'confusion_matrix': confusion_matrix(y_true, y_pred),
    }

def compute_classification_metrics(y_true, y_pred, y_prob=None):
    """Compute classification metrics from full dataset results."""
    return {
        'accuracy': accuracy_score(y_true, y_pred),
        'precision': precision_score(y_true, y_pred, average='weighted', zero_division=0),
        'recall': recall_score(y_true, y_pred, average='weighted', zero_division=0),
        'f1_score': f1_score(y_true, y_pred, average='weighted', zero_division=0),
        'roc_auc': roc_auc_score(y_true, y_prob, average='weighted') if y_prob is not None else None,
        'confusion_matrix': confusion_matrix(y_true, y_pred),
    }

def compute_regression_metrics(y_true, y_pred):
    """Compute regression metrics from full dataset results."""
    mse = mean_squared_error(y_true, y_pred)
    return {
        'mse': mse,
        'rmse': np.sqrt(mse),
        'mae': mean_absolute_error(y_true, y_pred),
        'r2': r2_score(y_true, y_pred),
    }
