import pytest
from conftest import _root
from backend.app.db.session import SessionLocal
from backend.app.models.entities import ModelVersion
from sqlalchemy import select
from backend.app.services.pipeline import create_run, ingest
from ml import generate_transactions
from backend.app.schemas.requests import TransactionInput
from pydantic import ValidationError


def headers(client, username="admin"):
    response = client.post("/api/v1/auth/login", json={"username": username, "password": "test-password-123"})
    assert response.status_code == 200
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def test_auth_and_roles(client):
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200
    assert client.get("/api/v1/transactions").status_code == 401
    assert client.post("/api/v1/pipeline/runs", json={}, headers=headers(client, "analyst")).status_code == 403
    assert client.get("/api/v1/transactions", headers={"Authorization": "Bearer bad"}).status_code == 401


def test_scored_api_and_metrics(client):
    auth = headers(client)
    response = client.get("/api/v1/transactions?page_size=5", headers=auth)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 700
    assert len(data["items"]) == 5
    tid = data["items"][0]["transaction_id"]
    risk = client.get(f"/api/v1/transactions/{tid}/risk", headers=auth).json()
    assert 0 <= risk["risk_score"] <= 100
    assert risk["model_version"]
    assert client.get(f"/api/v1/transactions/{tid}/explanation", headers=auth).json()["contributions"]
    assert client.get("/api/v1/evaluation/metrics", headers=auth).json()["sample_count"] == 140
    assert client.get("/api/v1/evaluation/metrics?threshold=50", headers=auth).status_code == 422
    assert client.get("/api/v1/transactions?search=%27%20OR%201=1--", headers=auth).json()["total"] == 0


def test_case_workflow_audit_and_immutable_resolution(client):
    auth = headers(client, "investigator")
    case = client.get("/api/v1/alerts", headers=auth).json()["items"][0]
    url = f"/api/v1/alerts/{case['id']}"
    assert client.post(url + "/notes", json={"text": "First"}, headers=auth).status_code == 403
    assert client.post(url + "/assign", json={"username": "investigator"}, headers=auth).status_code == 200
    assert client.post(url + "/status", json={"status": "Under Review"}, headers=auth).status_code == 200
    assert client.post(url + "/notes", json={"text": "Synthetic pattern reviewed"}, headers=auth).status_code == 200
    assert client.post(url + "/disposition", json={"disposition": "Inconclusive", "confirmed": False}, headers=auth).status_code == 409
    result = client.post(url + "/disposition", json={"disposition": "Inconclusive", "confirmed": True}, headers=auth)
    assert result.status_code == 200
    assert result.json()["status"] == "Resolved"
    assert len(result.json()["history"]) == 4
    assert client.post(url + "/notes", json={"text": "Cannot mutate"}, headers=auth).status_code == 409


def test_validation_quarantine_and_idempotency(client):
    records = generate_transactions(n=50, seed=99, customers=10)
    invalid = [dict(records[0], amount=-1), dict(records[1], timestamp="2099-01-01T00:00:00Z"), {"transaction_id": "missing"}]
    with SessionLocal() as db:
        run = create_run(db, {"test": True})
        accepted, rejected, duplicates = ingest(db, records + invalid + [records[0]], run.id)
        assert (len(accepted), rejected, duplicates) == (50, 3, 1)
        db.commit()
        again, rejected, duplicates = ingest(db, records, run.id)
        assert not again and duplicates == 50


def test_escalation_reassignment_and_idempotent_actions(client):
    admin = headers(client)
    investigator = headers(client, "investigator")
    analyst = headers(client, "analyst")
    case = client.get("/api/v1/alerts?status=New", headers=admin).json()["items"][0]
    filtered = client.get("/api/v1/alerts", params={"search": case["transaction_id"], "risk_band": case["risk_band"]}, headers=admin).json()
    assert filtered["total"] == 1
    url = f"/api/v1/alerts/{case['id']}"
    assert client.post(url + "/assign", json={"username": "analyst"}, headers=admin).status_code == 422
    assert client.post(url + "/assign", json={"username": "admin"}, headers=analyst).status_code == 403
    client.post(url + "/assign", json={"username": "investigator"}, headers=admin)
    client.post(url + "/assign", json={"username": "investigator"}, headers=admin)
    response = client.post(url + "/escalate", json={"reason": "Manual investigation required"}, headers=investigator)
    assert response.status_code == 200
    assert response.json()["status"] == "Escalated"
    duplicate = client.post(url + "/escalate", json={"reason": "Manual investigation required"}, headers=investigator)
    assert len(duplicate.json()["history"]) == 2
    response = client.post(url + "/assign", json={"username": "admin"}, headers=admin)
    assert response.json()["assigned_to"] == "admin"
    assert client.post(url + "/notes", json={"text": "Not owner"}, headers=investigator).status_code == 403


def test_unknown_labels_and_model_readiness(client):
    auth = headers(client)
    record = generate_transactions(n=50, seed=105, customers=10)[0]
    record.pop("ground_truth_fraud_label")
    result = client.post("/api/v1/transactions", json=record, headers=auth)
    assert result.status_code == 201
    detail = client.get("/api/v1/transactions/" + record["transaction_id"], headers=auth).json()
    assert detail.get("ground_truth_fraud_label") is None
    with SessionLocal.begin() as db:
        active = db.scalar(select(ModelVersion).where(ModelVersion.active.is_(True)))
        version = active.version
        active.active = False
    try:
        assert client.get("/ready").status_code == 503
        assert client.get("/api/v1/evaluation/metrics", headers=auth).status_code == 503
    finally:
        with SessionLocal.begin() as db:
            db.get(ModelVersion, version).active = True


def test_utc_labels_and_currency_validation():
    record = generate_transactions(n=50, seed=106, customers=10)[0]
    record["timestamp"] = "2026-01-02T05:30:00+05:30"
    item = TransactionInput.model_validate(record).model_dump(mode="json")
    assert item["timestamp"] == "2026-01-02T00:00:00.000000+00:00"
    for changes in [{"ground_truth_fraud_label": "fraud"}, {"ground_truth_fraud_label": 2}, {"currency": "USD"}]:
        with pytest.raises(ValidationError):
            TransactionInput.model_validate({**record, **changes})


def test_missing_artifact_readiness(client):
    with SessionLocal.begin() as db:
        model = db.scalar(select(ModelVersion).where(ModelVersion.active.is_(True)))
        version, original = model.version, model.artifact_path
        model.artifact_path = str(_root / "missing.joblib")
    try:
        assert client.get("/ready").status_code == 503
    finally:
        with SessionLocal.begin() as db:
            db.get(ModelVersion, version).artifact_path = original


def test_documented_response_schemas_and_operational_reads(client):
    auth = headers(client)
    for path in [
        "/dashboard",
        "/models",
        "/pipeline/runs",
        "/system/status",
        "/monitoring/drift",
        "/monitoring/performance",
        "/evaluation/thresholds",
    ]:
        response = client.get("/api/v1" + path, headers=auth)
        assert response.status_code == 200, (path, response.text)
    schema = client.get("/openapi.json").json()
    assert schema["paths"]["/api/v1/auth/login"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "LoginResponse"
    )
    assert schema["paths"]["/api/v1/transactions"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
