import numpy as np
from ml.features import FEATURE_NAMES, FEATURE_DESCRIPTIONS


def explain(bundle, row):
    z = bundle["scaler"].transform(np.asarray(row).reshape(1, -1))[0]
    contributions = z * bundle["logistic"].coef_[0]
    base = float(bundle["logistic"].intercept_[0])
    output = base + float(contributions.sum())
    items = [
        dict(
            feature=name,
            description=description,
            value=float(value),
            baseline=float(baseline),
            contribution=float(contribution),
            direction="increases" if contribution > 0 else "decreases",
        )
        for name, description, value, baseline, contribution in zip(
            FEATURE_NAMES,
            FEATURE_DESCRIPTIONS,
            row,
            bundle["scaler"].mean_,
            contributions,
        )
    ]
    return dict(
        method="Exact logistic linear attribution",
        units="log-odds",
        baseline=base,
        output_log_odds=output,
        probability=float(1 / (1 + np.exp(-output))),
        contributions=sorted(
            items, key=lambda item: abs(item["contribution"]), reverse=True
        ),
        model_version=bundle["version"],
        limitations="Attributions explain model behavior, not causation or confirmed fraud. Baseline is the training mean feature vector.",
    )
