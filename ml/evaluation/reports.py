"""Small report payloads derived from the fitted data and models."""

from collections import Counter
import numpy as np
from ml.features import FEATURE_NAMES


def describe(values):
    array = np.asarray(values, dtype=float)
    return dict(
        count=len(array),
        min=float(array.min()),
        max=float(array.max()),
        mean=float(array.mean()),
        std=float(array.std()),
        p25=float(np.quantile(array, 0.25)),
        median=float(np.median(array)),
        p75=float(np.quantile(array, 0.75)),
        p95=float(np.quantile(array, 0.95)),
        p99=float(np.quantile(array, 0.99)),
    )


def analytical_reports(engine):
    rows = engine.data
    a, b = engine.bundle["splits"]
    return {
        "eda": {
            "synthetic": True,
            "amount_lkr": describe([r["amount"] for r in rows]),
            "account_age_days": describe([r["account_age_days"] for r in rows]),
            "channels": dict(Counter(r["channel"] for r in rows)),
            "merchant_categories": dict(Counter(r["merchant_category"] for r in rows)),
            "features": {
                name: describe(engine.x[:, i]) for i, name in enumerate(FEATURE_NAMES)
            },
        },
        "scenario_distributions": {
            "synthetic": True,
            "all": dict(Counter(r["fraud_scenario_type"] for r in rows)),
            "train": dict(Counter(r["fraud_scenario_type"] for r in rows[:a])),
            "validation": dict(Counter(r["fraud_scenario_type"] for r in rows[a:b])),
            "test": dict(Counter(r["fraud_scenario_type"] for r in rows[b:])),
        },
        "feature_importance": {
            "model_version": engine.version,
            "source": "Fitted training estimators only",
            "limitations": "Standardized logistic coefficients measure model log-odds sensitivity; forest impurity importance can favor continuous or high-cardinality features. Neither proves causality.",
            "features": [
                {
                    "feature": name,
                    "logistic_standardized_coefficient": float(coefficient),
                    "random_forest_impurity_importance": float(importance),
                }
                for name, coefficient, importance in zip(
                    FEATURE_NAMES,
                    engine.bundle["logistic"].coef_[0],
                    engine.bundle["forest"].feature_importances_,
                )
            ],
        },
    }
