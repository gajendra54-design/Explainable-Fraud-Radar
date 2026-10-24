"""Verified outcomes and persisted monitoring investigations, separate from cases."""

from sqlalchemy import CheckConstraint, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.db.session import Base
from backend.app.models.entities import now


class VerifiedLabel(Base):
    __tablename__ = "verified_labels"
    __table_args__ = (CheckConstraint("label IN (0, 1)", name="ck_verified_label_binary"),)
    transaction_id: Mapped[str] = mapped_column(ForeignKey("transactions.id"), primary_key=True)
    label: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(120))
    evidence: Mapped[str] = mapped_column(Text)
    verified_at: Mapped[str] = mapped_column(String(50))
    recorded_at: Mapped[str] = mapped_column(String(50), default=now)
    recorded_by: Mapped[str] = mapped_column(ForeignKey("users.username"))


class MonitoringIncident(Base):
    __tablename__ = "monitoring_incidents"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(180))
    summary: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(30), default="Open", index=True)
    report: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(String(50), default=now)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.username"))
    updated_at: Mapped[str] = mapped_column(String(50), default=now)


class MonitoringIncidentEvent(Base):
    __tablename__ = "monitoring_incident_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("monitoring_incidents.id"), index=True)
    actor: Mapped[str] = mapped_column(ForeignKey("users.username"))
    note: Mapped[str] = mapped_column(Text)
    previous_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    status: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[str] = mapped_column(String(50), default=now)
