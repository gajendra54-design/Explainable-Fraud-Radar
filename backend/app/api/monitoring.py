from datetime import datetime, timezone
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.models.entities import Audit, Transaction, User, now
from backend.app.models.monitoring import VerifiedLabel, MonitoringIncident, MonitoringIncidentEvent
from backend.app.security.auth import current_user, require
from backend.app.services.monitoring import live_performance, parse_time
from backend.app.services.pipeline import load_engine
from backend.app.schemas.monitoring_responses import (
    VerifiedLabelsResponse,
    LivePerformanceResponse,
    MonitoringListResponse,
    MonitoringDetailResponse,
)

router = APIRouter(prefix="/api/v1/monitoring", tags=["Verified outcomes and monitoring investigations"])


class LabelInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    transaction_id: str = Field(min_length=1, max_length=100)
    label: StrictInt = Field(ge=0, le=1)
    source: str = Field(min_length=3, max_length=120)
    evidence: str = Field(min_length=10, max_length=4000)
    verified_at: datetime

    @field_validator("verified_at")
    @classmethod
    def validate_time(cls, value):
        if value.tzinfo is None or value > datetime.now(timezone.utc):
            raise ValueError("verified_at must be timezone-aware and not in the future")
        return value.astimezone(timezone.utc)


class LabelBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    labels: list[LabelInput] = Field(min_length=1, max_length=1000)


class IncidentInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(min_length=5, max_length=180)
    summary: str = Field(min_length=10, max_length=4000)
    severity: Literal["warning", "critical"] = "warning"


class IncidentEventInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    note: str = Field(min_length=5, max_length=4000)
    status: Literal["Open", "Investigating", "Resolved"]
    confirmed: bool = False


def serialize(row):
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}


def incident_detail(db, incident):
    return {
        **serialize(incident),
        "history": [
            serialize(e)
            for e in db.scalars(
                select(MonitoringIncidentEvent)
                .where(MonitoringIncidentEvent.incident_id == incident.id)
                .order_by(MonitoringIncidentEvent.id)
            )
        ],
    }


@router.post("/verified-labels", response_model=VerifiedLabelsResponse)
def submit_labels(body: LabelBatch, db: Session = Depends(get_db), user: User = Depends(require("administrator"))):
    ids = [r.transaction_id for r in body.labels]
    if len(ids) != len(set(ids)):
        raise HTTPException(422, "Duplicate transaction IDs within label batch")
    prepared = []
    duplicates = 0
    for label in body.labels:
        tx = db.get(Transaction, label.transaction_id)
        if tx is None:
            raise HTTPException(404, f"Transaction {label.transaction_id} not found")
        if label.verified_at < parse_time(tx.timestamp):
            raise HTTPException(422, "Verification cannot predate the transaction")
        existing = db.get(VerifiedLabel, label.transaction_id)
        if existing:
            if existing.label != label.label or existing.source != label.source or existing.evidence != label.evidence:
                raise HTTPException(409, "Verified labels are immutable; conflicting outcome requires an independent correction procedure")
            duplicates += 1
        else:
            prepared.append(
                VerifiedLabel(
                    **label.model_dump(exclude={"verified_at"}), verified_at=label.verified_at.isoformat(), recorded_by=user.username
                )
            )
    for row in prepared:
        db.add(row)
        db.add(
            Audit(
                actor=user.username,
                action="verified_label_recorded",
                details={"transaction_id": row.transaction_id, "label": row.label, "source": row.source},
            )
        )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A label was concurrently recorded; reload before retrying")
    return {"accepted": len(prepared), "duplicates": duplicates, "source": "verified_labels", "investigator_dispositions_used": False}


@router.get("/live-performance", response_model=LivePerformanceResponse)
def performance(
    maturity_days: int = Query(7, ge=0, le=365),
    window_days: int = Query(365, ge=1, le=3650),
    minimum_labels: int = Query(20, ge=2, le=10000),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    return live_performance(db, maturity_days, window_days, minimum_labels)


@router.get("/incidents", response_model=MonitoringListResponse)
def incidents(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db), user: User = Depends(current_user)
):
    return {
        "items": [
            serialize(r)
            for r in db.scalars(
                select(MonitoringIncident).order_by(MonitoringIncident.id.desc()).offset((page - 1) * page_size).limit(page_size)
            )
        ],
        "total": db.scalar(select(func.count()).select_from(MonitoringIncident)),
        "page": page,
        "page_size": page_size,
    }


@router.post("/incidents", status_code=201, response_model=MonitoringDetailResponse)
def create_incident(body: IncidentInput, db: Session = Depends(get_db), user: User = Depends(require("administrator", "investigator"))):
    try:
        engine = load_engine(db)
    except (OSError, ValueError):
        raise HTTPException(503, "Active model artifact is unavailable")
    if engine is None:
        raise HTTPException(503, "An active model is required for a drift investigation")
    history = [r.data for r in db.scalars(select(Transaction).order_by(Transaction.timestamp, Transaction.id))]
    if not history:
        raise HTTPException(409, "No transaction window available")
    report = engine.drift_report(current=history[-1000:], history=history)
    report["model_version"] = engine.version
    report["captured_at"] = now()
    incident = MonitoringIncident(**body.model_dump(), status="Open", report=report, created_by=user.username)
    db.add(incident)
    db.flush()
    db.add(MonitoringIncidentEvent(incident_id=incident.id, actor=user.username, note=body.summary, previous_status=None, status="Open"))
    db.add(
        Audit(
            actor=user.username,
            action="monitoring_incident_opened",
            details={"incident_id": incident.id, "severity": body.severity, "model_version": engine.version},
        )
    )
    db.commit()
    return incident_detail(db, incident)


@router.get("/incidents/{incident_id}", response_model=MonitoringDetailResponse)
def get_incident(incident_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    row = db.get(MonitoringIncident, incident_id)
    if row is None:
        raise HTTPException(404, "Monitoring incident not found")
    return incident_detail(db, row)


@router.post("/incidents/{incident_id}/events", response_model=MonitoringDetailResponse)
def update_incident(
    incident_id: int,
    body: IncidentEventInput,
    db: Session = Depends(get_db),
    user: User = Depends(require("administrator", "investigator")),
):
    row = db.scalar(select(MonitoringIncident).where(MonitoringIncident.id == incident_id).with_for_update())
    if row is None:
        raise HTTPException(404, "Monitoring incident not found")
    if row.status == "Resolved":
        raise HTTPException(409, "Resolved monitoring investigations are immutable")
    if body.status == "Resolved" and not body.confirmed:
        raise HTTPException(409, "Confirm resolution before closing the investigation")
    if row.status == "Investigating" and body.status == "Open":
        raise HTTPException(409, "Investigation cannot return to Open")
    previous = row.status
    row.status = body.status
    row.updated_at = now()
    db.add(MonitoringIncidentEvent(incident_id=row.id, actor=user.username, note=body.note, previous_status=previous, status=body.status))
    db.add(
        Audit(
            actor=user.username,
            action="monitoring_incident_updated",
            details={"incident_id": row.id, "previous_status": previous, "status": body.status},
        )
    )
    db.commit()
    return incident_detail(db, row)
