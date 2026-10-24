"""Train-only preprocessing, chronological holdouts, reproducible artifacts."""

import hashlib
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from ml.evaluation import evaluate


def chronological_boundaries(timestamps):
    """Move boundaries right so a timestamp group never straddles a split."""
    n = len(timestamps)
    a, b = int(n * 0.6), int(n * 0.8)
    while a < n and timestamps[a] == timestamps[a - 1]:
        a += 1
    b = max(b, a + 1)
    while b < n and timestamps[b] == timestamps[b - 1]:
        b += 1
    if not 0 < a < b < n:
        raise ValueError(
            "Insufficient distinct timestamps for three chronological splits"
        )
    return a, b


def train_models(x, y, seed=42, timestamps=None):
    n = len(y)
    a = int(n * 0.6)
    b = int(n * 0.8)
    if timestamps is not None:
        a, b = chronological_boundaries(timestamps)
    if len(np.unique(y[:a])) < 2 or len(np.unique(y[a:b])) < 2:
        raise ValueError(
            "Training and validation require both classes; increase generated dataset size"
        )
    scaler = StandardScaler().fit(x[:a])
    z = scaler.transform(x)
    logistic = LogisticRegression(max_iter=1000, random_state=seed).fit(z[:a], y[:a])
    forest = RandomForestClassifier(
        n_estimators=80,
        max_depth=10,
        min_samples_leaf=5,
        class_weight="balanced",
        random_state=seed,
        n_jobs=1,
    ).fit(x[:a], y[:a])
    isolation = IsolationForest(
        n_estimators=80, contamination="auto", random_state=seed, n_jobs=1
    ).fit(x[:a][y[:a] == 0])
    validation = logistic.predict_proba(z[a:b])[:, 1]
    options = [evaluate(y[a:b], validation, t) for t in np.arange(0.05, 0.81, 0.025)]
    # Capacity is operational: optimize F1 subject to <= 15% review load if possible.
    eligible = [m for m in options if m["alert_volume"] <= (b - a) * 0.15]
    chosen = max(eligible or options, key=lambda m: m["f1"])
    digest = hashlib.sha256(x.tobytes() + y.tobytes() + str(seed).encode()).hexdigest()[
        :10
    ]
    return dict(
        scaler=scaler,
        logistic=logistic,
        forest=forest,
        isolation=isolation,
        threshold=chosen["threshold"],
        splits=(a, b),
        version=f"lr-v1-{digest}",
        seed=seed,
        validation_selection=chosen,
        anomaly_reference=np.sort(-isolation.score_samples(x[:a])),
        training_feature_mean=x[:a].mean(axis=0),
    )
