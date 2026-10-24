from datetime import datetime, timedelta, timezone
from collections import defaultdict
from sqlalchemy import select
from backend.app.models.entities import Transaction, Prediction, ModelVersion
from backend.app.models.monitoring import VerifiedLabel
from ml.evaluation import evaluate


def parse_time(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def live_performance(db, maturity_days=7, window_days=365, minimum_labels=20, now=None):
    current = now or datetime.now(timezone.utc)
    start = current - timedelta(days=window_days)
    maturity_cutoff = current - timedelta(days=maturity_days)
    rows = [
        (tx, prediction)
        for tx, prediction in db.execute(select(Transaction, Prediction).join(Prediction, Prediction.transaction_id == Transaction.id))
        if start <= parse_time(tx.timestamp) <= current
    ]
    mature = [(tx, pred) for tx, pred in rows if parse_time(tx.timestamp) <= maturity_cutoff]
    labels = {label.transaction_id: label for label in db.scalars(select(VerifiedLabel)) if parse_time(label.verified_at) <= current}
    labeled = [(tx, pred, labels[tx.id]) for tx, pred in mature if tx.id in labels]
    total_labeled = sum(tx.id in labels for tx, _ in rows)
    groups = defaultdict(list)
    for _, pred in mature:
        groups[pred.model_version]  # Include models whose mature predictions have no labels yet.
    for tx, pred, label in labeled:
        groups[pred.model_version].append((tx, pred, label))
    results = []
    for version, records in groups.items():
        model = db.get(ModelVersion, version)
        threshold = float(model.info.get("threshold", 0.5)) if model else 0.5
        population = sum(pred.model_version == version for _, pred in mature)
        coverage = len(records) / population if population else 0
        eligible = len(records) >= minimum_labels
        metrics = (
            evaluate([r[2].label for r in records], [float(r[1].data["probability"]) for r in records], threshold) if eligible else None
        )
        baseline = model.metrics.get("f1") if model else None
        degradation = bool(metrics is not None and coverage >= 0.8 and baseline is not None and metrics["f1"] < baseline - 0.1)
        results.append(
            {
                "model_version": version,
                "labeled_count": len(records),
                "mature_count": population,
                "label_coverage": coverage,
                "metrics": metrics,
                "status": "insufficient_labels" if not eligible else "provisional" if coverage < 0.8 else "ready",
                "baseline_f1": baseline,
                "performance_degradation": degradation,
                "comparison_note": "Training benchmark is synthetic and may differ from this selected population.",
            }
        )
    mature_coverage = len(labeled) / len(mature) if mature else 0
    status = (
        "no_transactions"
        if not rows
        else "awaiting_maturity"
        if not mature
        else "insufficient_labels"
        if any(result["status"] == "insufficient_labels" for result in results)
        else "provisional"
        if any(result["status"] == "provisional" for result in results)
        else "ready"
    )
    return {
        "source": "independently submitted verified labels",
        "window_start": start.isoformat(),
        "window_end": current.isoformat(),
        "maturity_cutoff": maturity_cutoff.isoformat(),
        "maturity_days": maturity_days,
        "minimum_labels": minimum_labels,
        "transaction_count": len(rows),
        "mature_count": len(mature),
        "immature_count": len(rows) - len(mature),
        "labeled_count": total_labeled,
        "mature_labeled_count": len(labeled),
        "label_coverage": total_labeled / len(rows) if rows else 0,
        "mature_label_coverage": mature_coverage,
        "status": status,
        "models": results,
        "performance_degradation": any(r["performance_degradation"] for r in results),
        "limitations": "Only submitted verified labels enter live metrics. Unknown outcomes are excluded, never assumed legitimate. Partial labels can cause selection bias. A 7-day default age is a configurable maturity assumption, not proof all outcomes arrived. No automatic model promotion.",
    }
