import numpy as np
from sklearn.metrics import (
    confusion_matrix,
    average_precision_score,
    roc_auc_score,
    precision_recall_curve,
    roc_curve,
)


def curve_report(y, scores, max_points=100):
    """Chart samples only; exact AUC metrics use all held-out predictions."""
    y, scores = np.asarray(y), np.asarray(scores)
    if len(y) == 0 or len(np.unique(y)) < 2:
        return {
            "precision_recall": [],
            "roc": [],
            "available": False,
            "reason": "Both positive and negative verified labels are required",
        }
    precision, recall, pr_thresholds = precision_recall_curve(y, scores)
    fpr, tpr, roc_thresholds = roc_curve(y, scores)
    pr_indices = np.unique(
        np.linspace(0, len(precision) - 1, min(max_points, len(precision))).astype(int)
    )
    roc_indices = np.unique(
        np.linspace(0, len(fpr) - 1, min(max_points, len(fpr))).astype(int)
    )
    return {
        "available": True,
        "precision_recall": [
            {
                "precision": float(precision[i]),
                "recall": float(recall[i]),
                "threshold": float(pr_thresholds[i])
                if i < len(pr_thresholds)
                else None,
            }
            for i in pr_indices
        ],
        "roc": [
            {
                "false_positive_rate": float(fpr[i]),
                "true_positive_rate": float(tpr[i]),
                "threshold": float(roc_thresholds[i])
                if np.isfinite(roc_thresholds[i])
                else None,
            }
            for i in roc_indices
        ],
    }


def evaluate(y, scores, threshold=0.5):
    y, scores = np.asarray(y), np.asarray(scores)
    predicted = scores >= threshold
    tn, fp, fn, tp = (
        int(v) for v in confusion_matrix(y, predicted, labels=[0, 1]).ravel()
    )
    precision, recall = tp / max(tp + fp, 1), tp / max(tp + fn, 1)
    capacity = max(1, int(len(y) * 0.05))
    return dict(
        threshold=float(threshold),
        true_positives=tp,
        true_negatives=tn,
        false_positives=fp,
        false_negatives=fn,
        precision=precision,
        recall=recall,
        f1=2 * precision * recall / max(precision + recall, 1e-12),
        specificity=tn / max(tn + fp, 1),
        false_positive_rate=fp / max(fp + tn, 1),
        pr_auc=float(average_precision_score(y, scores)) if y.sum() else 0.0,
        roc_auc=float(roc_auc_score(y, scores)) if len(np.unique(y)) == 2 else None,
        confusion_matrix=[[tn, fp], [fn, tp]],
        alert_volume=int(predicted.sum()),
        alert_rate_per_1000=float(predicted.mean() * 1000),
        investigation_hours=float(predicted.sum() * 10 / 60),
        precision_at_capacity=float(y[np.argsort(-scores)[:capacity]].mean()),
        review_capacity=capacity,
        sample_count=len(y),
        fraud_prevalence=float(y.mean()),
    )


def threshold_report(y, scores):
    return [evaluate(y, scores, float(t)) for t in np.arange(0.05, 1, 0.05)]
