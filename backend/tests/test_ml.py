import copy
import numpy as np
import pytest
from ml import FraudEngine, generate_transactions
from ml.features import engineer
from ml.validation import validate_records
from ml.evaluation import evaluate, curve_report
from ml.monitoring import numerical_drift
from ml.training import chronological_boundaries


@pytest.fixture(scope="module")
def engine():
    return FraudEngine(generate_transactions(n=1200, customers=30, seed=19))


def test_generator_reproducible_and_validation():
    rows = generate_transactions(n=100)
    assert rows == generate_transactions(n=100)
    good, bad = validate_records(rows + [rows[0], dict(rows[1], amount=-1), dict(rows[2], timestamp="bad")])
    assert len(good) == 100 and len(bad) == 3


def test_features_no_future_or_target_leakage():
    rows = generate_transactions(n=100, customers=3)
    original = engineer(rows)
    changed = copy.deepcopy(rows)
    for row in changed:
        row["ground_truth_fraud_label"] = 1 - row["ground_truth_fraud_label"]
        row["fraud_scenario_type"] = "different"
    np.testing.assert_array_equal(original, engineer(changed))
    changed[-1]["amount"] = 1e10
    np.testing.assert_array_equal(original[:-1], engineer(changed)[:-1])
    changed = copy.deepcopy(rows[:2])
    changed[1]["timestamp"] = changed[0]["timestamp"]
    changed[1]["customer_id"] = changed[0]["customer_id"]
    changed[1]["account_id"] = changed[0]["account_id"]
    assert engineer(changed)[1, 3] == 0


def test_explanation_reconstructs_probability(engine):
    result = engine.score(engine.data[-1])
    explanation = result["explanation"]
    reconstructed = explanation["baseline"] + sum(i["contribution"] for i in explanation["contributions"])
    assert reconstructed == pytest.approx(explanation["output_log_odds"])
    assert 1 / (1 + np.exp(-reconstructed)) == pytest.approx(result["probability"])
    assert 0 <= result["risk_score"] <= 100
    assert 0 <= result["anomaly_score"] <= 1
    info = engine.model_info()
    assert info["train_end"] < info["validation_start"] < info["test_start"]


def test_online_offline_feature_parity(engine):
    for index in [0, 10, 100, 1199]:
        online = engine.score(engine.data[index])
        np.testing.assert_allclose(list(online["features"].values()), engine.x[index])


def test_metrics_definitions():
    m = evaluate([1, 1, 0, 0], [0.9, 0.1, 0.8, 0.2])
    assert m["confusion_matrix"] == [[1, 1], [1, 1]]
    assert m["precision"] == m["recall"] == m["false_positive_rate"] == 0.5
    assert evaluate([0, 0], [0.1, 0.2])["roc_auc"] is None


def test_shift_detected():
    rng = np.random.default_rng(42)
    reference = rng.normal(size=1000)
    assert numerical_drift(reference, reference, "amount")["psi"] == 0
    assert numerical_drift(reference, rng.normal(4, 1, 1000), "amount")["status"] == "critical"


def test_persistence_and_training_reproducibility(engine, tmp_path):
    engine.save(tmp_path / "model.joblib")
    restored = FraudEngine.load(tmp_path / "model.joblib")
    assert restored.score(engine.data[-1])["probability"] == engine.score(engine.data[-1])["probability"]
    duplicate = FraudEngine(engine.data, seed=42)
    assert duplicate.version == engine.version
    assert engine.metrics()["pr_auc"] > 0.1


@pytest.mark.parametrize(
    "changes",
    [
        {"amount": 0},
        {"amount": float("nan")},
        {"amount": float("inf")},
        {"amount": True},
        {"timestamp": "2099-01-01T00:00:00+00:00"},
        {"timestamp": "2026-01-01"},
        {"timestamp": "1999-01-01T00:00:00+00:00"},
        {"currency": "BAD"},
        {"currency": "USD"},
        {"currency": "EUR"},
        {"currency": "GBP"},
        {"currency": "SGD"},
        {"transaction_id": None},
        {"transaction_id": []},
        {"customer_id": 1},
        {"account_id": None},
        {"ip_risk_indicator": 1.1},
        {"ip_risk_indicator": float("nan")},
        {"account_age_days": -1},
    ],
)
def test_validation_quarantines_malformed(changes):
    row = generate_transactions(n=50)[0]
    valid, invalid = validate_records([dict(row, **changes)])
    assert not valid and len(invalid) == 1 and invalid[0]["reasons"]


def test_validation_nonobject_and_large_amount():
    row = dict(generate_transactions(n=50)[0], amount=1e10)
    valid, invalid = validate_records([None, [], row])
    assert valid == [row] and len(invalid) == 2


def test_account_age_consistent_and_monotonic():
    from datetime import datetime

    rows = generate_transactions(n=500, customers=5)
    origins = {}
    for row in rows:
        day = (datetime.fromisoformat(row["timestamp"]) - datetime.fromisoformat("2026-01-01T00:00:00+00:00")).days
        age_at_start = row["account_age_days"] - day
        assert origins.setdefault(row["account_id"], age_at_start) == age_at_start


def test_equal_timestamps_never_cross_split_boundaries():
    times = [0, 1, 2, 3, 4, 5, 5, 6, 7, 7, 8, 9]
    a, b = chronological_boundaries(times)
    assert times[a - 1] < times[a] and times[b - 1] < times[b]
    with pytest.raises(ValueError):
        chronological_boundaries([1] * 20)


def test_curves_are_bounded_and_single_class_is_explicit(engine):
    curves = engine.metrics()["curves"]
    assert curves["available"]
    assert 2 <= len(curves["precision_recall"]) <= 100
    assert 2 <= len(curves["roc"]) <= 100
    assert all(0 <= point["precision"] <= 1 and 0 <= point["recall"] <= 1 for point in curves["precision_recall"])
    assert curves["roc"][0]["false_positive_rate"] == 0
    assert curves["roc"][-1]["true_positive_rate"] == 1
    for labels in ([0, 0], [1, 1], []):
        report = curve_report(labels, [0.1] * len(labels))
        assert report["available"] is False and report["roc"] == []
    assert evaluate([1, 1], [0.9, 0.8])["roc_auc"] is None


def test_monitoring_current_window_preserves_history(engine):
    start = engine.bundle["splits"][1]
    automatic = engine.drift_report()
    explicit = engine.drift_report(current=engine.data[start:], history=engine.data)
    assert automatic["features"] == explicit["features"]
    assert automatic["prediction_drift"] == explicit["prediction_drift"]


def test_synthetic_quality_regression(engine):
    metrics = engine.metrics()
    # A deliberately loose deterministic benchmark guard, never a real-world promise.
    assert metrics["pr_auc"] > metrics["fraud_prevalence"]
    assert metrics["roc_auc"] > 0.65


def test_shared_customer_accounts_have_isolated_histories(engine):
    template = engine.data[0]
    first = dict(
        template,
        transaction_id="multi-1",
        customer_id="shared",
        account_id="account-A",
        timestamp="2026-01-01T10:00:00+00:00",
        amount=100,
        device_id="device-A",
        merchant_id="merchant-A",
    )
    other = dict(
        first,
        transaction_id="multi-2",
        account_id="account-B",
        timestamp="2026-01-01T10:01:00+00:00",
        amount=9000,
        device_id="device-B",
        merchant_id="merchant-B",
    )
    latest = dict(first, transaction_id="multi-3", timestamp="2026-01-01T10:02:00+00:00", amount=200)
    rows = [first, other, latest]
    offline = engineer(rows)
    assert offline[1, 1] == 3  # Account B cold-start baseline 3,000.
    assert offline[1, 2] == offline[1, 3] == 0
    assert offline[2, 1] == 2  # Account A baseline remains 100.
    assert offline[2, 2] == offline[2, 3] == 1
    assert offline[2, 5] == 2  # Other account's event does not reset elapsed time.
    assert offline[2, 6] == offline[2, 7] == 0
    for index, row in enumerate(rows):
        scored = engine.score(row, history=rows)
        np.testing.assert_allclose(list(scored["features"].values()), offline[index])
