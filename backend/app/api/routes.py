from collections import defaultdict
import time
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.models.entities import User, Transaction, Prediction, Alert, Note, Audit, ModelVersion, PipelineRun, now
from backend.app.schemas.requests import (
    Login,
    TransactionInput,
    Batch,
    PipelineConfig,
    Assignment,
    NoteInput,
    Escalation,
    Disposition,
    StatusInput,
)
from backend.app.security.auth import current_user, require, token
from backend.app.security.rate_limit import authenticate, login_attempts  # noqa: F401 - test reset compatibility
from backend.app.services.pipeline import load_engine, ingest, save_prediction, create_run

from backend.app.schemas import responses as out

router = APIRouter(prefix="/api/v1")


def serialized(obj):
    return {column.name: getattr(obj, column.name) for column in obj.__table__.columns}


def user_info(user):
    return {"id": user.id, "username": user.username, "role": user.role}


def need_model(db):
    try:
        model = load_engine(db)
    except (OSError, ValueError):
        raise HTTPException(503, "Active model artifact is unavailable")
    if model is None:
        raise HTTPException(503, "No active model. Run the seed pipeline first.")
    return model


def case_row(db, case):
    prediction = db.get(Prediction, case.transaction_id)
    return {
        **serialized(case),
        "risk_score": prediction.risk_score,
        "risk_band": prediction.risk_band,
        "model_version": prediction.model_version,
    }


def transaction_row(db, row):
    prediction = db.get(Prediction, row.id)
    case = db.scalar(select(Alert).where(Alert.transaction_id == row.id))
    return {
        **row.data,
        "risk_score": prediction.risk_score if prediction else None,
        "risk_band": prediction.risk_band if prediction else None,
        "model_version": prediction.model_version if prediction else None,
        "status": case.status if case else "No alert",
    }


def get_case(db, case_id):
    case = db.scalar(select(Alert).where(Alert.id == case_id).with_for_update())
    if not case:
        raise HTTPException(404, "Case not found")
    return case


def case_detail(db, case):
    return {
        **case_row(db, case),
        "transaction": db.get(Transaction, case.transaction_id).data,
        "prediction": db.get(Prediction, case.transaction_id).data,
        "notes": [serialized(n) for n in db.scalars(select(Note).where(Note.case_id == case.id).order_by(Note.id))],
        "history": [serialized(e) for e in db.scalars(select(Audit).where(Audit.case_id == case.id).order_by(Audit.id))],
    }


def audit(db, user, case, action, details):
    db.add(Audit(case_id=case.id, actor=user.username, action=action, details=details))


def can_edit(case, user):
    if case.status == "Resolved":
        raise HTTPException(409, "Resolved cases are immutable")
    if user.role != "administrator" and case.assigned_to != user.username:
        raise HTTPException(403, "Assign the case to yourself before editing")


@router.post("/auth/login", response_model=out.LoginResponse)
def login(body: Login, request: Request, db: Session = Depends(get_db)):
    key = request.client.host if request.client else "unknown"
    user = authenticate(db, body.username, body.password, key)
    return {"access_token": token(user, db), "token_type": "bearer", "user": user_info(user)}


@router.get("/auth/me", response_model=out.UserResponse)
def me(user=Depends(current_user)):
    return user_info(user)


@router.get("/users", response_model=list[out.UserResponse])
def users(db: Session = Depends(get_db), user=Depends(current_user)):
    return [user_info(u) for u in db.scalars(select(User))]


@router.get("/system/status", response_model=out.SystemResponse)
def system(db: Session = Depends(get_db), user=Depends(current_user)):
    model = db.scalar(select(ModelVersion).where(ModelVersion.active.is_(True)))
    return {
        "status": "ready" if model else "needs_seed",
        "synthetic_only": True,
        "model_version": model.version if model else None,
        "database": "connected",
    }


@router.get("/dashboard", response_model=out.DashboardResponse)
def dashboard(db: Session = Depends(get_db), user=Depends(current_user)):
    total = db.scalar(select(func.count()).select_from(Transaction))
    alerts = db.scalar(select(func.count()).select_from(Alert))
    counts = db.execute(select(Prediction.risk_band, func.count()).group_by(Prediction.risk_band)).all()
    trend = defaultdict(lambda: {"transactions": 0, "alerts": 0})
    for timestamp, alert_id in db.execute(select(Transaction.timestamp, Alert.id).outerjoin(Alert, Alert.transaction_id == Transaction.id)):
        trend[timestamp[:10]]["transactions"] += 1
        trend[timestamp[:10]]["alerts"] += int(alert_id is not None)
    model = db.scalar(select(ModelVersion).where(ModelVersion.active.is_(True)))
    labelled = [
        t.data.get("ground_truth_fraud_label")
        for t in db.scalars(select(Transaction))
        if t.data.get("ground_truth_fraud_label") is not None
    ]
    last_run = db.scalar(select(PipelineRun).order_by(PipelineRun.started_at.desc()).limit(1))
    return {
        "transactions": total,
        "alerts": alerts,
        "high_risk": sum(count for band, count in counts if band.lower() in ("high", "critical")),
        "open_cases": db.scalar(select(func.count()).select_from(Alert).where(Alert.status != "Resolved")),
        "model_version": model.version if model else None,
        "pipeline_health": last_run.status if last_run else "not_started",
        "drift_status": "available" if model else "unavailable",
        "fraud_rate": sum(labelled) / len(labelled) if labelled else None,
        "false_positive_rate": model.metrics.get("false_positive_rate") if model else None,
        "trend": [{"date": date, **value} for date, value in sorted(trend.items())],
        "risk_distribution": [{"band": band, "count": count} for band, count in counts],
        "recent_alerts": [case_row(db, case) for case in db.scalars(select(Alert).order_by(Alert.id.desc()).limit(6))],
    }


@router.get("/transactions", response_model=out.PageResponse[out.TransactionResponse])
def transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = "",
    risk_band: str | None = None,
    channel: str | None = None,
    min_amount: float | None = Query(None, ge=0),
    max_amount: float | None = Query(None, ge=0),
    date_from: str | None = None,
    date_to: str | None = None,
    status: str | None = None,
    sort: str = "timestamp",
    order: str = "desc",
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    query = select(Transaction).outerjoin(Prediction, Prediction.transaction_id == Transaction.id)
    if search:
        query = query.where(Transaction.id.contains(search, autoescape=True))
    if risk_band:
        query = query.where(func.lower(Prediction.risk_band) == risk_band.lower())
    if channel:
        query = query.where(Transaction.channel == channel)
    if min_amount is not None:
        query = query.where(Transaction.amount >= min_amount)
    if max_amount is not None:
        query = query.where(Transaction.amount <= max_amount)
    if date_from:
        query = query.where(Transaction.timestamp >= date_from)
    if date_to:
        query = query.where(Transaction.timestamp <= date_to)
    if status:
        query = query.join(Alert, Alert.transaction_id == Transaction.id).where(Alert.status == status)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    column = {"timestamp": Transaction.timestamp, "amount": Transaction.amount, "risk_score": Prediction.risk_score}.get(
        sort, Transaction.timestamp
    )
    query = query.order_by(column.asc() if order == "asc" else column.desc()).offset((page - 1) * page_size).limit(page_size)
    return {"items": [transaction_row(db, row) for row in db.scalars(query)], "total": total, "page": page, "page_size": page_size}


@router.get("/transactions/{transaction_id}", response_model=out.TransactionDetailResponse)
def transaction_detail(transaction_id: str, db: Session = Depends(get_db), user=Depends(current_user)):
    row = db.get(Transaction, transaction_id)
    if not row:
        raise HTTPException(404, "Transaction not found")
    prediction = db.get(Prediction, row.id)
    case = db.scalar(select(Alert).where(Alert.transaction_id == row.id))
    related = db.scalars(
        select(Transaction)
        .where(Transaction.account_id == row.account_id, Transaction.timestamp < row.timestamp)
        .order_by(Transaction.timestamp.desc())
        .limit(10)
    )
    return {
        **transaction_row(db, row),
        "prediction": prediction.data if prediction else None,
        "alert": case_row(db, case) if case else None,
        "related_transactions": [transaction_row(db, r) for r in related],
    }


@router.get("/transactions/{transaction_id}/risk", response_model=out.PredictionResponse)
def risk(transaction_id: str, db: Session = Depends(get_db), user=Depends(current_user)):
    prediction = db.get(Prediction, transaction_id)
    if not prediction:
        raise HTTPException(404, "Prediction not found")
    return prediction.data


@router.get("/transactions/{transaction_id}/explanation", response_model=out.ExplanationResponse)
def explanation(transaction_id: str, db: Session = Depends(get_db), user=Depends(current_user)):
    return risk(transaction_id, db, user).get("explanation", {})


@router.post("/score", response_model=out.PredictionResponse)
def score(body: TransactionInput, db: Session = Depends(get_db), user=Depends(require("investigator", "administrator"))):
    model = need_model(db)
    item = body.model_dump(mode="json")
    history = [
        t.data
        for t in db.scalars(
            select(Transaction)
            .where(
                Transaction.account_id == body.account_id, Transaction.timestamp < item["timestamp"], Transaction.id != body.transaction_id
            )
            .order_by(Transaction.timestamp)
        )
    ]
    return model.score(item, history=history)


@router.post("/transactions", status_code=201, response_model=out.PipelineResponse)
def add_transaction(body: TransactionInput, db: Session = Depends(get_db), user=Depends(require("administrator"))):
    return add_batch(Batch(records=[body.model_dump(mode="json")]), db, user)


@router.post("/transactions/batch", status_code=201, response_model=out.PipelineResponse)
def add_batch(body: Batch, db: Session = Depends(get_db), user=Depends(require("administrator"))):
    started = time.perf_counter()
    model = need_model(db)
    run = create_run(db, {"kind": "ingestion", "rows": len(body.records)})
    accepted, rejected, duplicates = ingest(db, body.records, run.id)
    version = db.scalar(select(ModelVersion).where(ModelVersion.active.is_(True))).version
    for item in sorted(accepted, key=lambda r: r["timestamp"]):
        history = [
            t.data
            for t in db.scalars(
                select(Transaction)
                .where(Transaction.account_id == item["account_id"], Transaction.timestamp < item["timestamp"])
                .order_by(Transaction.timestamp)
            )
        ]
        save_prediction(db, item["transaction_id"], model.score(item, history=history), version)
    run.processed, run.rejected, run.duplicates, run.status = len(accepted), rejected, duplicates, "completed"
    run.completed_at, run.duration_seconds = now(), time.perf_counter() - started
    db.commit()
    return serialized(run)


@router.get("/alerts", response_model=out.PageResponse[out.CaseResponse])
@router.get("/cases", response_model=out.PageResponse[out.CaseResponse])
def cases(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    assigned_to: str | None = None,
    search: str = "",
    risk_band: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    query = select(Alert)
    if status:
        query = query.where(Alert.status == status)
    if assigned_to:
        query = query.where(Alert.assigned_to == assigned_to)
    if search:
        query = query.where(Alert.transaction_id.contains(search, autoescape=True))
    if risk_band:
        query = query.join(Prediction, Prediction.transaction_id == Alert.transaction_id).where(
            func.lower(Prediction.risk_band) == risk_band.lower()
        )
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    return {
        "items": [case_row(db, c) for c in db.scalars(query.order_by(Alert.id.desc()).offset((page - 1) * page_size).limit(page_size))],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/alerts/{case_id}", response_model=out.CaseDetailResponse)
def alert_detail(case_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    return case_detail(db, get_case(db, case_id))


@router.get("/cases/{case_id}/history", response_model=list[out.AuditResponse])
def history(case_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    return case_detail(db, get_case(db, case_id))["history"]


@router.post("/alerts/{case_id}/assign", response_model=out.CaseDetailResponse)
def assign(case_id: int, body: Assignment, db: Session = Depends(get_db), user=Depends(require("investigator", "administrator"))):
    case = get_case(db, case_id)
    if case.status == "Resolved":
        raise HTTPException(409, "Resolved cases are immutable")
    if user.role != "administrator" and (body.username != user.username or case.assigned_to not in (None, user.username)):
        raise HTTPException(403, "Only administrators may reassign another investigator’s case")
    assignee = db.scalar(select(User).where(User.username == body.username))
    if not assignee or assignee.role not in ("investigator", "administrator"):
        raise HTTPException(422, "Assignee must be an investigator or administrator")
    if case.assigned_to == body.username:
        return case_detail(db, case)
    audit(db, user, case, "assigned", {"previous": case.assigned_to, "assigned_to": body.username})
    case.assigned_to, case.status = body.username, "Assigned"
    db.commit()
    return case_detail(db, case)


@router.post("/alerts/{case_id}/notes", response_model=out.CaseDetailResponse)
def note(case_id: int, body: NoteInput, db: Session = Depends(get_db), user=Depends(require("investigator", "administrator"))):
    case = get_case(db, case_id)
    can_edit(case, user)
    db.add(Note(case_id=case.id, author=user.username, text=body.text))
    audit(db, user, case, "note_added", {"text": body.text})
    db.commit()
    return case_detail(db, case)


@router.post("/alerts/{case_id}/status", response_model=out.CaseDetailResponse)
def status_change(case_id: int, body: StatusInput, db: Session = Depends(get_db), user=Depends(require("investigator", "administrator"))):
    case = get_case(db, case_id)
    can_edit(case, user)
    if case.status == body.status:
        return case_detail(db, case)
    if case.status not in ("Assigned", "Escalated"):
        raise HTTPException(409, "Assign a case before beginning review")
    audit(db, user, case, "status_changed", {"previous": case.status, "status": body.status})
    case.status = body.status
    db.commit()
    return case_detail(db, case)


@router.post("/alerts/{case_id}/escalate", response_model=out.CaseDetailResponse)
def escalate(case_id: int, body: Escalation, db: Session = Depends(get_db), user=Depends(require("investigator", "administrator"))):
    case = get_case(db, case_id)
    can_edit(case, user)
    if case.status == "Escalated":
        return case_detail(db, case)
    if case.status not in ("Assigned", "Under Review"):
        raise HTTPException(409, "Only assigned or reviewed cases can be escalated")
    case.status = "Escalated"
    audit(db, user, case, "escalated", {"reason": body.reason})
    db.commit()
    return case_detail(db, case)


@router.post("/alerts/{case_id}/disposition", response_model=out.CaseDetailResponse)
def disposition(case_id: int, body: Disposition, db: Session = Depends(get_db), user=Depends(require("investigator", "administrator"))):
    case = get_case(db, case_id)
    if case.status == "Resolved" and case.disposition == body.disposition and body.confirmed:
        if user.role == "administrator" or case.assigned_to == user.username:
            return case_detail(db, case)
    can_edit(case, user)
    if not body.confirmed or case.status not in ("Under Review", "Escalated"):
        raise HTTPException(409, "Review the case and explicitly confirm the disposition")
    case.disposition, case.status = body.disposition, "Resolved"
    audit(db, user, case, "disposition_recorded", {"disposition": body.disposition, "verified_ground_truth_changed": False})
    db.commit()
    return case_detail(db, case)


@router.get("/evaluation/metrics", response_model=out.MetricsResponse)
def metrics(threshold: float | None = Query(None, ge=0, le=1), db: Session = Depends(get_db), user=Depends(current_user)):
    return need_model(db).metrics(threshold=threshold)


@router.get("/evaluation/confusion-matrix", response_model=out.MetricsResponse)
def confusion(threshold: float | None = Query(None, ge=0, le=1), db: Session = Depends(get_db), user=Depends(current_user)):
    return need_model(db).metrics(threshold=threshold)


@router.get("/evaluation/thresholds", response_model=list[out.MetricsResponse])
def thresholds(db: Session = Depends(get_db), user=Depends(current_user)):
    return need_model(db).thresholds()


@router.get("/models", response_model=list[out.ModelResponse])
def models(db: Session = Depends(get_db), user=Depends(current_user)):
    return [serialized(m) for m in db.scalars(select(ModelVersion).order_by(ModelVersion.created_at.desc()))]


@router.get("/models/{version}", response_model=out.ModelResponse)
def model_detail(version: str, db: Session = Depends(get_db), user=Depends(current_user)):
    model = db.get(ModelVersion, version)
    if not model:
        raise HTTPException(404, "Model not found")
    return serialized(model)


@router.post("/models/{version}/activate", response_model=out.ModelResponse)
def activate_model(version: str, db: Session = Depends(get_db), user=Depends(require("administrator"))):
    target = db.get(ModelVersion, version)
    if not target:
        raise HTTPException(404, "Model not found")
    for model in db.scalars(select(ModelVersion)):
        model.active = model.version == version
    db.add(Audit(actor=user.username, action="model_activated", details={"version": version}))
    db.commit()
    return serialized(target)


@router.get("/monitoring/drift", response_model=out.DriftResponse)
def drift(window_size: int = Query(1000, ge=50, le=10000), db: Session = Depends(get_db), user=Depends(current_user)):
    records = [t.data for t in db.scalars(select(Transaction).order_by(Transaction.timestamp.desc()).limit(window_size))][::-1]
    model = need_model(db)
    history = [t.data for t in db.scalars(select(Transaction).order_by(Transaction.timestamp))]
    report = model.drift_report(current=records, history=history) if records else model.drift_report()
    report["current_source"] = "latest persisted transactions"
    report["window_size"] = len(records)
    report["label_coverage"] = sum(r.get("ground_truth_fraud_label") is not None for r in records) / len(records) if records else 0
    report["window_feature_limitation"] = (
        "Current features use all persisted strictly earlier history; absent source history cannot be reconstructed."
    )
    return report


@router.get("/monitoring/performance", response_model=out.PerformanceResponse)
def performance(db: Session = Depends(get_db), user=Depends(current_user)):
    return {
        "metrics": need_model(db).metrics(),
        "label_source": "synthetic_generator",
        "label_coverage": 1,
        "window_maturity": "complete synthetic benchmark",
        "investigator_decisions_used_as_truth": False,
    }


@router.get("/pipeline/runs", response_model=out.PageResponse[out.PipelineResponse])
def runs(db: Session = Depends(get_db), user=Depends(current_user)):
    items = [serialized(r) for r in db.scalars(select(PipelineRun).order_by(PipelineRun.started_at.desc()).limit(100))]
    return {"items": items, "total": len(items), "page": 1, "page_size": 100}


@router.post("/pipeline/runs", status_code=202, response_model=out.PipelineResponse)
def pipeline(body: PipelineConfig, db: Session = Depends(get_db), user=Depends(require("administrator"))):
    run = create_run(db, body.model_dump())
    return serialized(run)
