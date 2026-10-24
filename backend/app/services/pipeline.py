import time
import uuid
import joblib
from pathlib import Path
from sqlalchemy import select
from pydantic import ValidationError
from backend.app.core.config import ARTIFACT_DIR, ALERT_THRESHOLD
from backend.app.db.session import SessionLocal
from backend.app.models.entities import Customer, Account, Transaction, Prediction, ModelVersion, Alert, PipelineRun, Quarantine, now
from backend.app.schemas.requests import TransactionInput
from backend.app.services.jobs import claim_run, fence, Heartbeat, record_failure

_engines = {}


def load_engine(db):
    version = db.scalar(select(ModelVersion).where(ModelVersion.active.is_(True)))
    if not version:
        return None
    if not Path(version.artifact_path).is_file():
        raise FileNotFoundError("Active model artifact is unavailable")
    if version.version not in _engines:
        _engines[version.version] = joblib.load(version.artifact_path)
    return _engines[version.version]


def ingest(db, records, run_id):
    accepted, rejected, duplicates = [], 0, 0
    seen = set()
    for raw in records:
        try:
            item = TransactionInput.model_validate(raw).model_dump(mode="json")
            tid = item["transaction_id"]
            if tid in seen or db.get(Transaction, tid):
                duplicates += 1
                continue
            seen.add(tid)
            account = db.get(Account, item["account_id"])
            if account and account.customer_id != item["customer_id"]:
                raise ValueError("Account/customer reference mismatch")
            if not db.get(Customer, item["customer_id"]):
                db.add(Customer(id=item["customer_id"]))
                db.flush()
            if not account:
                db.add(Account(id=item["account_id"], customer_id=item["customer_id"]))
                db.flush()
            db.add(
                Transaction(
                    id=tid,
                    account_id=item["account_id"],
                    timestamp=item["timestamp"],
                    amount=item["amount"],
                    channel=item["channel"],
                    data=item,
                )
            )
            db.flush()
            accepted.append(item)
        except (ValidationError, ValueError) as exc:
            rejected += 1
            db.add(Quarantine(run_id=run_id, record=raw, reason=str(exc)))
    return accepted, rejected, duplicates


def save_prediction(db, transaction_id, prediction, version):
    score = float(prediction["risk_score"])
    band = prediction.get("risk_band") or ("Critical" if score >= 75 else "High" if score >= 50 else "Moderate" if score >= 25 else "Low")
    db.add(Prediction(transaction_id=transaction_id, model_version=version, risk_score=score, risk_band=band, data=prediction))
    if (score >= ALERT_THRESHOLD) if ALERT_THRESHOLD is not None else prediction.get("is_alert", score >= 50):
        db.add(Alert(transaction_id=transaction_id))


def run_pipeline(run_id, config, lease_owner=None):
    if lease_owner is None:
        claimed = claim_run(run_id)
        if claimed is None:
            with SessionLocal() as db:
                run = db.get(PipelineRun, run_id)
                if run and run.status == "completed":
                    return
            raise RuntimeError("Job is not claimable; another worker may own the training lease")
        _, config, lease_owner = claimed
    started = time.perf_counter()
    heartbeat = Heartbeat(run_id, lease_owner)
    heartbeat.__enter__()
    try:
        from ml import FraudEngine, generate_transactions

        records = generate_transactions(
            n=config["transactions"], seed=config["seed"], customers=config["customers"], fraud_rate=config["fraud_rate"]
        )
        model = FraudEngine(records, seed=config["seed"])
        predictions = model.score_dataset()
        info = model.model_info()
        version = info.get("version", info.get("model_version", "model-" + run_id[:8]))
        ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        artifact = ARTIFACT_DIR / (version + ".joblib")
        temporary_artifact = ARTIFACT_DIR / (version + "-" + lease_owner + ".tmp")
        joblib.dump(model, temporary_artifact)
        with SessionLocal.begin() as db:
            run = fence(db, run_id, lease_owner)
            existing = db.get(ModelVersion, version)
            if not existing:
                temporary_artifact.replace(artifact)
                first_model = db.scalar(select(ModelVersion).where(ModelVersion.active.is_(True))) is None
                db.add(
                    ModelVersion(
                        version=version, info=info, metrics=model.metrics(), artifact_path=str(artifact.resolve()), active=first_model
                    )
                )
                db.flush()
            accepted, rejected, duplicates = ingest(db, records, run_id)
            accepted_ids = {r["transaction_id"] for r in accepted}
            for record, prediction in zip(model.data, predictions):
                if record["transaction_id"] in accepted_ids:
                    save_prediction(db, record["transaction_id"], prediction, version)
            run.status, run.processed, run.rejected, run.duplicates = "completed", len(accepted), rejected, duplicates
            run.completed_at, run.duration_seconds = now(), time.perf_counter() - started
            run.lease_owner, run.lease_expires_at, run.error = None, None, None
        _engines[version] = model
    except Exception as exc:
        record_failure(run_id, lease_owner, exc, time.perf_counter() - started)
        raise
    finally:
        heartbeat.__exit__()
        if "temporary_artifact" in locals():
            temporary_artifact.unlink(missing_ok=True)


def create_run(db, config):
    ingestion = config.get("kind") == "ingestion"
    run = PipelineRun(
        id=str(uuid.uuid4()), status="running" if ingestion else "queued", job_type="ingestion" if ingestion else "training", config=config
    )
    db.add(run)
    db.commit()
    return run
