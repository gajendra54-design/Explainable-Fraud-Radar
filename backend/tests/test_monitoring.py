from datetime import datetime, timedelta, timezone
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.app.api.monitoring import router
from backend.app.db.session import Base, get_db
from backend.app.models.entities import User, Customer, Account, Transaction, Prediction, ModelVersion, Audit
from backend.app.models.monitoring import VerifiedLabel, MonitoringIncident
from backend.app.security.auth import current_user
from backend.app.services.monitoring import live_performance


@pytest.fixture
def setup():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    instant = datetime.now(timezone.utc)
    with sessions.begin() as db:
        user = User(username="verifier", password_hash="unused", role="administrator")
        db.add_all([user, Customer(id="C")])
        db.flush()
        db.add(Account(id="A", customer_id="C"))
        db.add(ModelVersion(version="test-model", info={"threshold": 0.5}, metrics={"f1": 0.8}, artifact_path="unused", active=True))
        db.flush()
        for index in range(30):
            timestamp = (instant - timedelta(days=1 if index == 0 else 30)).isoformat()
            data = {
                "transaction_id": f"T{index}",
                "account_id": "A",
                "customer_id": "C",
                "timestamp": timestamp,
                "amount": 100,
                "ground_truth_fraud_label": 1,
            }
            db.add(Transaction(id=f"T{index}", account_id="A", timestamp=timestamp, amount=100, channel="Online", data=data))
            db.flush()
            probability = 0.9 if index % 2 else 0.1
            db.add(
                Prediction(
                    transaction_id=f"T{index}",
                    model_version="test-model",
                    risk_score=probability * 100,
                    risk_band="high",
                    data={"probability": probability},
                )
            )
    state = {"role": "administrator"}
    app = FastAPI()
    app.include_router(router)

    def database():
        with sessions() as db:
            yield db

    def identity():
        return User(id=1, username="verifier", password_hash="unused", role=state["role"])

    app.dependency_overrides[get_db] = database
    app.dependency_overrides[current_user] = identity
    with TestClient(app) as client:
        yield client, sessions, state, instant
    engine.dispose()


def label_payload(ids):
    return {
        "labels": [
            {
                "transaction_id": f"T{i}",
                "label": i % 2,
                "source": "independent synthetic verification",
                "evidence": "Verified by separate simulation outcome registry",
                "verified_at": datetime.now(timezone.utc).isoformat(),
            }
            for i in ids
        ]
    }


def test_labels_require_admin_and_are_atomic_immutable_and_idempotent(setup):
    client, sessions, state, _ = setup
    state["role"] = "investigator"
    assert client.post("/api/v1/monitoring/verified-labels", json=label_payload([1])).status_code == 403
    state["role"] = "administrator"
    invalid = label_payload([1, 99])
    assert client.post("/api/v1/monitoring/verified-labels", json=invalid).status_code == 404
    with sessions() as db:
        assert db.scalar(select(VerifiedLabel)) is None
    payload = label_payload([1, 2])
    assert client.post("/api/v1/monitoring/verified-labels", json=payload).json()["accepted"] == 2
    assert client.post("/api/v1/monitoring/verified-labels", json=payload).json()["duplicates"] == 2
    payload["labels"][0]["label"] = 0
    assert client.post("/api/v1/monitoring/verified-labels", json=payload).status_code == 409
    with sessions() as db:
        assert len(list(db.scalars(select(Audit)))) == 2
        assert db.get(VerifiedLabel, "T1").label == 1


def test_live_performance_excludes_unknown_and_immature_labels(setup):
    client, sessions, _, _ = setup
    url = "/api/v1/monitoring/live-performance?minimum_labels=2"
    empty = client.get(url).json()
    assert empty["transaction_count"] == 30 and empty["mature_count"] == 29
    assert empty["label_coverage"] == 0  # Raw ground truth is never reused.
    assert empty["models"][0]["metrics"] is None
    assert client.post("/api/v1/monitoring/verified-labels", json=label_payload([0, 1, 2])).status_code == 200
    result = client.get(url).json()
    assert result["labeled_count"] == 3 and result["mature_labeled_count"] == 2
    assert result["status"] == "provisional"
    assert result["models"][0]["metrics"]["sample_count"] == 2
    assert result["models"][0]["metrics"]["f1"] == 1
    assert result["models"][0]["performance_degradation"] is False


def test_degradation_requires_mature_coverage(setup):
    client, sessions, _, instant = setup
    payload = label_payload(range(1, 30))
    for record in payload["labels"]:
        record["label"] = 1 - record["label"]
    assert client.post("/api/v1/monitoring/verified-labels", json=payload).status_code == 200
    result = client.get("/api/v1/monitoring/live-performance").json()
    assert result["status"] == "ready" and result["performance_degradation"] is True
    with sessions() as db:
        future = live_performance(db, now=instant - timedelta(days=40))
        assert future["status"] == "no_transactions" and future["models"] == []


def test_label_payload_validation(setup):
    client, *_ = setup
    body = label_payload([1])
    body["labels"][0]["label"] = True
    assert client.post("/api/v1/monitoring/verified-labels", json=body).status_code == 422
    body = label_payload([1])
    body["labels"][0]["verified_at"] = "2001-01-01T00:00:00Z"
    assert client.post("/api/v1/monitoring/verified-labels", json=body).status_code == 422
    assert client.post("/api/v1/monitoring/verified-labels", json=label_payload([1, 1])).status_code == 422


def test_incident_snapshot_and_persistent_history(setup, monkeypatch):
    client, sessions, state, _ = setup

    class SnapshotEngine:
        version = "test-model"

        def drift_report(self, current, history):
            assert len(history) == 30 and len(current) == 30
            return {"status": "warning", "features": [{"feature": "amount_ratio", "psi": 0.15}]}

    monkeypatch.setattr("backend.app.api.monitoring.load_engine", lambda db: SnapshotEngine())
    body = {
        "title": "Amount distribution shifted",
        "summary": "Investigate transaction amount change in current window",
        "severity": "warning",
    }
    state["role"] = "analyst"
    assert client.post("/api/v1/monitoring/incidents", json=body).status_code == 403
    state["role"] = "investigator"
    created = client.post("/api/v1/monitoring/incidents", json=body)
    assert created.status_code == 201
    item = created.json()
    assert item["report"]["model_version"] == "test-model" and len(item["history"]) == 1
    url = f"/api/v1/monitoring/incidents/{item['id']}/events"
    updated = client.post(url, json={"note": "Reviewing current feature distribution", "status": "Investigating"})
    assert updated.status_code == 200 and len(updated.json()["history"]) == 2
    assert client.post(url, json={"note": "No further action after review", "status": "Resolved"}).status_code == 409
    resolved = client.post(url, json={"note": "Confirmed benign synthetic population change", "status": "Resolved", "confirmed": True})
    assert resolved.status_code == 200 and len(resolved.json()["history"]) == 3
    assert client.post(url, json={"note": "Attempting another change", "status": "Investigating"}).status_code == 409
    assert client.get("/api/v1/monitoring/incidents").json()["total"] == 1
    with sessions() as db:
        assert db.get(MonitoringIncident, item["id"]).status == "Resolved"
        assert len(list(db.scalars(select(Audit)))) == 3


def test_global_status_requires_each_models_minimum_labels(setup):
    client, sessions, _, _ = setup
    with sessions.begin() as db:
        db.add(ModelVersion(version="second-model", info={"threshold": 0.5}, metrics={}, artifact_path="unused", active=False))
        db.flush()
        for index in range(15, 30):
            db.get(Prediction, f"T{index}").model_version = "second-model"
    assert client.post("/api/v1/monitoring/verified-labels", json=label_payload(range(1, 30))).status_code == 200
    result = client.get("/api/v1/monitoring/live-performance").json()
    assert result["mature_label_coverage"] == 1
    assert result["mature_labeled_count"] == 29
    assert result["status"] == "insufficient_labels"
    assert len(result["models"]) == 2
    assert all(row["metrics"] is None for row in result["models"])


def test_monitoring_openapi_exposes_validated_output_contracts(setup):
    client, *_ = setup
    paths = client.get("/openapi.json").json()["paths"]
    for path, method, status, schema in [
        ("verified-labels", "post", "200", "VerifiedLabelsResponse"),
        ("live-performance", "get", "200", "LivePerformanceResponse"),
        ("incidents", "get", "200", "MonitoringListResponse"),
        ("incidents", "post", "201", "MonitoringDetailResponse"),
        ("incidents/{incident_id}", "get", "200", "MonitoringDetailResponse"),
        ("incidents/{incident_id}/events", "post", "200", "MonitoringDetailResponse"),
    ]:
        response = paths["/api/v1/monitoring/" + path][method]["responses"][status]
        assert response["content"]["application/json"]["schema"]["$ref"].endswith("/" + schema)
