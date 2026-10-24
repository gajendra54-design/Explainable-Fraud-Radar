import numpy as np
from scipy.stats import ks_2samp


def categorical_drift(reference, current, name):
    categories = sorted(set(reference) | set(current))
    p = np.array([reference.count(c) / len(reference) for c in categories])
    q = np.array([current.count(c) / len(current) for c in categories])
    distance = float(np.abs(p - q).sum() / 2)
    return dict(
        feature=name,
        total_variation=distance,
        status="critical"
        if distance > 0.25
        else "warning"
        if distance > 0.1
        else "stable",
        categories=[
            dict(category=c, reference=float(a), current=float(b))
            for c, a, b in zip(categories, p, q)
        ],
    )


def numerical_drift(reference, current, name):
    reference, current = np.asarray(reference, float), np.asarray(current, float)
    edges = np.unique(np.quantile(reference, np.linspace(0, 1, 11)))
    if len(edges) < 2:
        edges = np.array([-np.inf, float(reference[0]) + 0.0001, np.inf])
    else:
        edges[0], edges[-1] = -np.inf, np.inf
    p = np.histogram(reference, edges)[0] / len(reference)
    q = np.histogram(current, edges)[0] / len(current)
    p, q = np.maximum(p, 1e-6), np.maximum(q, 1e-6)
    psi = float(np.sum((q - p) * np.log(q / p)))
    ks = ks_2samp(reference, current)
    return dict(
        feature=name,
        psi=psi,
        ks_statistic=float(ks.statistic),
        p_value=float(ks.pvalue),
        status="critical" if psi > 0.25 else "warning" if psi > 0.1 else "stable",
        reference_mean=float(reference.mean()),
        current_mean=float(current.mean()),
    )
