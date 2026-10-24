from datetime import datetime, timezone
from sqlalchemy import String, Float, Integer, ForeignKey, JSON, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.db.session import Base


def now():
    return datetime.now(timezone.utc).isoformat()


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20))


class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)


class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"))


class Transaction(Base):
    __tablename__ = "transactions"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    timestamp: Mapped[str] = mapped_column(String(50), index=True)
    amount: Mapped[float] = mapped_column(Float)
    channel: Mapped[str] = mapped_column(String(40), index=True)
    data: Mapped[dict] = mapped_column(JSON)


class ModelVersion(Base):
    __tablename__ = "model_versions"
    version: Mapped[str] = mapped_column(String(100), primary_key=True)
    created_at: Mapped[str] = mapped_column(String(50), default=now)
    info: Mapped[dict] = mapped_column(JSON)
    metrics: Mapped[dict] = mapped_column(JSON)
    artifact_path: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=False)


class Prediction(Base):
    __tablename__ = "risk_predictions"
    transaction_id: Mapped[str] = mapped_column(ForeignKey("transactions.id"), primary_key=True)
    model_version: Mapped[str] = mapped_column(ForeignKey("model_versions.version"))
    risk_score: Mapped[float] = mapped_column(Float, index=True)
    risk_band: Mapped[str] = mapped_column(String(20), index=True)
    data: Mapped[dict] = mapped_column(JSON)


class Alert(Base):
    __tablename__ = "cases"
    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[str] = mapped_column(ForeignKey("transactions.id"), unique=True)
    status: Mapped[str] = mapped_column(String(30), default="New", index=True)
    assigned_to: Mapped[str | None] = mapped_column(ForeignKey("users.username"), nullable=True)
    disposition: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[str] = mapped_column(String(50), default=now)


class Note(Base):
    __tablename__ = "case_notes"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    author: Mapped[str] = mapped_column(String(80))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(50), default=now)


class Audit(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id"), nullable=True, index=True)
    actor: Mapped[str] = mapped_column(String(80))
    action: Mapped[str] = mapped_column(String(80))
    details: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(String(50), default=now)


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    status: Mapped[str] = mapped_column(String(30))
    started_at: Mapped[str] = mapped_column(String(50), default=now)
    completed_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    processed: Mapped[int] = mapped_column(Integer, default=0)
    rejected: Mapped[int] = mapped_column(Integer, default=0)
    duplicates: Mapped[int] = mapped_column(Integer, default=0)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0)
    config: Mapped[dict] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    job_type: Mapped[str] = mapped_column(String(30), default="training")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    lease_owner: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lease_expires_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    heartbeat_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    next_attempt_at: Mapped[str | None] = mapped_column(String(50), nullable=True)


class Quarantine(Base):
    __tablename__ = "quarantined_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("pipeline_runs.id"))
    record: Mapped[dict] = mapped_column(JSON)
    reason: Mapped[str] = mapped_column(Text)
