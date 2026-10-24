from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.exc import DBAPIError

from backend.app.db.session import SessionLocal
from backend.app.models.entities import Audit, PipelineRun, Quarantine
from backend.app.retention import purge_quarantine


def test_audit_database_rejects_mutation(client):  # noqa: F811
    with SessionLocal.begin() as db:
        event = Audit(actor="test", action="immutability_probe", details={"original": True})
        db.add(event)
        db.flush()
        event_id = event.id
    for statement in (
        update(Audit).where(Audit.id == event_id).values(actor="tampered"),
        delete(Audit).where(Audit.id == event_id),
    ):
        with pytest.raises(DBAPIError), SessionLocal.begin() as db:
            db.execute(statement)
    with SessionLocal() as db:
        assert db.get(Audit, event_id).actor == "test"


def test_retention_dry_run_and_bounded_deletion(client):  # noqa: F811
    at = datetime.now(timezone.utc)
    with SessionLocal.begin() as db:
        for name, age, status in [("old", 100, "completed"), ("recent", 1, "completed"), ("unfinished", 100, "running")]:
            run = PipelineRun(id="retention-" + name, status=status, config={}, completed_at=(at - timedelta(days=age)).isoformat())
            db.add(run)
            db.flush()
            db.add(Quarantine(run_id=run.id, record={"synthetic": True}, reason="test"))
    with SessionLocal() as db:
        preview = purge_quarantine(db, days=90, at=at)
        assert preview["eligible_records"] == 1
        assert preview["deleted"] == 0
        result = purge_quarantine(db, days=90, apply=True, at=at)
        assert result["deleted"] == 1
        assert db.scalar(select(Quarantine).where(Quarantine.run_id == "retention-recent"))
        assert db.scalar(select(Quarantine).where(Quarantine.run_id == "retention-unfinished"))
        assert db.get(PipelineRun, "retention-old")
        assert db.scalar(select(Audit).where(Audit.action == "quarantine_retention")).details["deleted"] == 1
        assert purge_quarantine(db, days=90, apply=True, at=at)["deleted"] == 0
        with pytest.raises(ValueError):
            purge_quarantine(db, days=0)
