"""Serializable scoring facade consumed by the API and batch pipeline."""

from datetime import datetime, timezone
from pathlib import Path
import joblib
import numpy as np
from ml.data_generation import generate_transactions
from ml.validation import validate_records
from ml.features import engineer, FEATURE_NAMES, stamp
from ml.training import train_models
from ml.evaluation import evaluate, threshold_report, curve_report
from ml.monitoring import numerical_drift, categorical_drift
from ml.explainability import explain


def rules(row, config=None):
    config = config or {}
    hits = []
    if row[1] >= config.get("amount_ratio", 4):
        hits.append(
            dict(
                rule="amount_deviation",
                score=35,
                description="Amount exceeds configured prior-median ratio",
            )
        )
    if row[2] >= config.get("hourly_count", 3):
        hits.append(
            dict(
                rule="hourly_velocity",
                score=30,
                description="Prior hourly count exceeds configured threshold",
            )
        )
    if row[8] and row[6]:
        hits.append(
            dict(
                rule="foreign_new_device",
                score=25,
                description="Foreign transaction from a first-seen device",
            )
        )
    if row[10] >= 0.5:
        hits.append(
            dict(rule="ip_risk", score=25, description="Elevated synthetic IP risk")
        )
    return min(100, sum(h["score"] for h in hits)), hits


class FraudEngine:
    def __init__(self, data=None, seed=42, risk_bands=(25, 50, 75), rule_config=None):
        if not 0 < risk_bands[0] < risk_bands[1] < risk_bands[2] < 100:
            raise ValueError(
                "Risk band thresholds must be increasing between 0 and 100"
            )
        self.risk_bands = tuple(risk_bands)
        self.rule_config = rule_config or {}
        self.data = sorted(
            data if data is not None else generate_transactions(seed=seed), key=stamp
        )
        valid, rejected = validate_records(self.data)
        if rejected:
            raise ValueError(f"Dataset failed validation: {rejected[:3]}")
        if any(r.get("ground_truth_fraud_label") not in (0, 1) for r in valid):
            raise ValueError(
                "Training requires explicit binary ground truth, never investigator opinions"
            )
        self.x = engineer(self.data)
        self.y = np.array([r["ground_truth_fraud_label"] for r in self.data])
        self.bundle = train_models(self.x, self.y, seed, [stamp(r) for r in self.data])
        self.version = self.bundle["version"]
        self.threshold = self.bundle["threshold"]

    def save(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)

    @classmethod
    def load(cls, path):
        # Only load trusted local artifacts. Pickle/joblib is not an untrusted upload format.
        return joblib.load(path)

    def _prediction(self, row):
        explanation = explain(self.bundle, row)
        probability = explanation["probability"]
        rule_score, hits = rules(row, self.rule_config)
        raw = float(
            -self.bundle["isolation"].score_samples(np.asarray(row).reshape(1, -1))[0]
        )
        anomaly = float(
            np.searchsorted(self.bundle["anomaly_reference"], raw)
            / len(self.bundle["anomaly_reference"])
        )
        # Operational score remains the supervised probability * 100; anomaly and rules are separate context.
        risk = round(probability * 100, 2)
        level = self._risk_level(risk)
        return dict(
            probability=probability,
            fraud_probability=probability,
            risk_score=risk,
            risk_level=level,
            risk_band=level,
            decision="review" if probability >= self.threshold else "monitor",
            is_alert=probability >= self.threshold,
            anomaly_score=anomaly,
            rule_score=rule_score,
            rule_hits=hits,
            triggered_rules=hits,
            model_version=self.version,
            prediction_timestamp=datetime.now(timezone.utc).isoformat(),
            threshold=self.threshold,
            reasons=[
                i["description"]
                for i in explanation["contributions"]
                if i["contribution"] > 0
            ][:3],
            features=dict(zip(FEATURE_NAMES, map(float, row))),
            explanation=explanation,
        )

    def score(self, transaction, history=None):
        # Strictly earlier history, excluding replay of the scored transaction.
        past = [
            r
            for r in (self.data if history is None else history)
            if r["account_id"] == transaction["account_id"]
            and r["transaction_id"] != transaction["transaction_id"]
            and stamp(r) < stamp(transaction)
        ]
        return self._prediction(engineer(past + [transaction])[-1])

    def _risk_level(self, risk):
        moderate, high, critical = self.risk_bands
        return (
            "critical"
            if risk >= critical
            else "high"
            if risk >= high
            else "moderate"
            if risk >= moderate
            else "low"
        )

    def batch_score(self, records, history=None):
        past = self.data if history is None else history
        combined = list({r["transaction_id"]: r for r in past + records}.values())
        return [self.score(r, combined) for r in records]

    def score_dataset(self):
        # Vectorize expensive model calls once for the startup dataset.
        probabilities = self.bundle["logistic"].predict_proba(
            self.bundle["scaler"].transform(self.x)
        )[:, 1]
        raw = -self.bundle["isolation"].score_samples(self.x)
        predictions = []
        for row, p, a in zip(self.x, probabilities, raw):
            explanation = explain(self.bundle, row)
            rule_score, hits = rules(row, self.rule_config)
            risk = round(float(p) * 100, 2)
            level = self._risk_level(risk)
            predictions.append(
                dict(
                    probability=float(p),
                    fraud_probability=float(p),
                    risk_score=risk,
                    risk_level=level,
                    risk_band=level,
                    decision="review" if p >= self.threshold else "monitor",
                    is_alert=bool(p >= self.threshold),
                    anomaly_score=float(
                        np.searchsorted(self.bundle["anomaly_reference"], a)
                        / len(self.bundle["anomaly_reference"])
                    ),
                    rule_score=rule_score,
                    rule_hits=hits,
                    triggered_rules=hits,
                    model_version=self.version,
                    threshold=self.threshold,
                    prediction_timestamp=datetime.now(timezone.utc).isoformat(),
                    features=dict(zip(FEATURE_NAMES, map(float, row))),
                    reasons=[
                        i["description"]
                        for i in explanation["contributions"]
                        if i["contribution"] > 0
                    ][:3],
                    explanation=explanation,
                )
            )
        return predictions

    def metrics(self, threshold=None):
        a, b = self.bundle["splits"]
        x = self.x[b:]
        y = self.y[b:]
        logistic = self.bundle["logistic"].predict_proba(
            self.bundle["scaler"].transform(x)
        )[:, 1]
        forest = self.bundle["forest"].predict_proba(x)[:, 1]
        anomaly = np.searchsorted(
            self.bundle["anomaly_reference"], -self.bundle["isolation"].score_samples(x)
        ) / len(self.bundle["anomaly_reference"])
        rule = np.array([rules(row, self.rule_config)[0] / 100 for row in x])
        threshold = self.threshold if threshold is None else threshold
        result = evaluate(y, logistic, threshold)
        result["curves"] = curve_report(y, logistic)
        result.update(
            model_version=self.version,
            split="chronological held-out test (last 20%)",
            synthetic=True,
            models=[
                dict(name=name, **evaluate(y, scores, t))
                for name, scores, t in [
                    ("Logistic regression", logistic, threshold),
                    ("Random forest", forest, 0.5),
                    ("Isolation forest", anomaly, 0.95),
                    ("Rules", rule, 0.5),
                ]
            ],
            by_channel=[
                dict(channel=channel, **evaluate(y[mask], logistic[mask], threshold))
                for channel in sorted(set(r["channel"] for r in self.data[b:]))
                for mask in [np.array([r["channel"] == channel for r in self.data[b:]])]
            ],
            by_scenario=[
                dict(
                    scenario=s,
                    sample_count=int(
                        sum(r["fraud_scenario_type"] == s for r in self.data[b:])
                    ),
                    detection_rate=float(
                        np.mean(
                            (logistic >= threshold)[
                                [r["fraud_scenario_type"] == s for r in self.data[b:]]
                            ]
                        )
                    ),
                )
                for s in sorted(set(r["fraud_scenario_type"] for r in self.data[b:]))
            ],
        )
        return result

    def thresholds(self):
        b = self.bundle["splits"][1]
        return threshold_report(
            self.y[b:],
            self.bundle["logistic"].predict_proba(
                self.bundle["scaler"].transform(self.x[b:])
            )[:, 1],
        )

    def model_info(self):
        a, b = self.bundle["splits"]
        return dict(
            version=self.version,
            model_version=self.version,
            algorithm="Logistic regression",
            status="demo-approved",
            seed=self.bundle["seed"],
            features=FEATURE_NAMES,
            feature_version="chronological-v1",
            threshold=self.threshold,
            risk_bands=self.risk_bands,
            rule_config=self.rule_config,
            train_count=a,
            validation_count=b - a,
            test_count=len(self.data) - b,
            train_end=self.data[a - 1]["timestamp"],
            validation_start=self.data[a]["timestamp"],
            validation_end=self.data[b - 1]["timestamp"],
            test_start=self.data[b]["timestamp"],
            scoring_strategy="100 × logistic probability; anomaly percentile and rule score shown separately",
            selection="Validation F1 maximized subject to 15% alert capacity where feasible",
            approval="Synthetic demo only; no automatic model promotion",
        )

    def drift_report(self, current=None, history=None):
        a, b = self.bundle["splits"]
        reference = self.x[:a]
        if current is None:
            current_x = self.x[b:]
        else:
            if not current:
                raise ValueError(
                    "Current monitoring window must contain at least one record"
                )
            # Reuse all available prior history, deduplicate replays, then select
            # the current window after chronological feature computation.
            combined = list(
                {
                    r["transaction_id"]: r
                    for r in (self.data if history is None else history) + current
                }.values()
            )
            all_features = engineer(combined)
            positions = {r["transaction_id"]: i for i, r in enumerate(combined)}
            current_x = np.asarray(
                [all_features[positions[r["transaction_id"]]] for r in current]
            )
        features = [
            numerical_drift(reference[:, i], current_x[:, i], name)
            for i, name in enumerate(FEATURE_NAMES)
        ]
        current_records = self.data[b:] if current is None else current
        categories = [
            categorical_drift(
                [r.get(key, "missing") for r in self.data[:a]],
                [r.get(key, "missing") for r in current_records],
                key,
            )
            for key in ("channel", "merchant_category")
        ]
        reference_scores = self.bundle["logistic"].predict_proba(
            self.bundle["scaler"].transform(reference)
        )[:, 1]
        current_scores = self.bundle["logistic"].predict_proba(
            self.bundle["scaler"].transform(current_x)
        )[:, 1]
        prediction = numerical_drift(
            reference_scores, current_scores, "fraud_probability"
        )
        return dict(
            status="critical"
            if any(f["status"] == "critical" for f in features)
            else "warning"
            if any(f["status"] == "warning" for f in features)
            else "stable",
            features=features,
            categorical_features=categories,
            prediction_drift=prediction,
            missing_rates={
                key: sum(r.get(key) is None for r in current_records)
                / len(current_records)
                for key in ("amount", "channel", "merchant_category", "device_id")
            },
            predicted_positive_rate=float((current_scores >= self.threshold).mean()),
            reference_count=len(reference),
            current_count=len(current_x),
            label_coverage=1.0 if current is None else None,
            recommendation="Investigate changes; validate before any model promotion.",
            limitations="PSI > 0.10 warning, > 0.25 critical are heuristics. KS p-values depend on sample size. Drift alone does not establish concept drift.",
            performance=self.metrics(),
            concept_drift="Not established; requires mature verified outcome windows",
        )

    def dataset_summary(self):
        return dict(
            records=len(self.data),
            customers=len(set(r["customer_id"] for r in self.data)),
            fraud_prevalence=float(self.y.mean()),
            start=self.data[0]["timestamp"],
            end=self.data[-1]["timestamp"],
            synthetic=True,
        )
