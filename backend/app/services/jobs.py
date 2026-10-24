"""Database-fenced training leases; no broker or process-local coordination required."""

import os
import threading
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, text, update
from backend.app.db.session import SessionLocal
from backend.app.models.entities import PipelineRun

LEASE_SECONDS = max(15, int(os.getenv("PIPELINE_LEASE_SECONDS", "90")))


def utc_after(seconds=0):
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat(timespec="microseconds")


class LeaseLost(RuntimeError):
    pass


def claim_run(run_id=None):
    """Serialize claimers; only one training job may persist a dataset at a time."""
    current = utc_after()
    with SessionLocal.begin() as db:
        if db.bind.dialect.name == "postgresql":
            db.execute(text("SELECT pg_advisory_xact_lock(71822041)"))
        else:
            db.execute(text("BEGIN IMMEDIATE"))
        running = db.scalar(
            select(PipelineRun)
            .where(PipelineRun.job_type == "training", PipelineRun.status == "running")
            .order_by(PipelineRun.started_at)
            .limit(1)
        )
        if running:
            if running.lease_expires_at and running.lease_expires_at > current:
                return None
            # If the expired owner is in its final atomic commit, don't bypass it.
            candidate = db.scalar(
                select(PipelineRun)
                .where(PipelineRun.id == running.id)
                .with_for_update(skip_locked=True)
                .execution_options(populate_existing=True)
            )
            if candidate is None or (run_id and candidate.id != run_id):
                return None
            if candidate.lease_expires_at and candidate.lease_expires_at > current:
                return None
        else:
            query = select(PipelineRun).where(PipelineRun.job_type == "training", PipelineRun.status == "queued")
            if run_id:
                query = query.where(PipelineRun.id == run_id)
            candidate = db.scalar(query.order_by(PipelineRun.started_at).limit(1).with_for_update(skip_locked=True))
            if candidate is None or (candidate.next_attempt_at and candidate.next_attempt_at > current):
                return None
        if candidate.attempts >= candidate.max_attempts:
            candidate.status, candidate.completed_at = "failed", current
            candidate.error = "Worker lease expired; maximum execution attempts exhausted"
            candidate.lease_owner, candidate.lease_expires_at = None, None
            return None
        candidate.status, candidate.lease_owner = "running", str(uuid.uuid4())
        candidate.attempts += 1
        candidate.heartbeat_at, candidate.lease_expires_at = current, utc_after(LEASE_SECONDS)
        candidate.next_attempt_at, candidate.completed_at = None, None
        db.flush()
        return candidate.id, dict(candidate.config), candidate.lease_owner


def renew_lease(run_id, owner):
    current = utc_after()
    with SessionLocal.begin() as db:
        result = db.execute(
            update(PipelineRun)
            .where(
                PipelineRun.id == run_id,
                PipelineRun.status == "running",
                PipelineRun.lease_owner == owner,
                PipelineRun.lease_expires_at > current,
            )
            .values(heartbeat_at=current, lease_expires_at=utc_after(LEASE_SECONDS))
        )
        return result.rowcount == 1


def fence(db, run_id, owner):
    run = db.scalar(select(PipelineRun).where(PipelineRun.id == run_id).with_for_update())
    if not run or run.status != "running" or run.lease_owner != owner or not run.lease_expires_at or run.lease_expires_at <= utc_after():
        raise LeaseLost("Execution lease expired or was reassigned; no data committed")
    return run


def record_failure(run_id, owner, error, duration):
    with SessionLocal.begin() as db:
        run = db.scalar(select(PipelineRun).where(PipelineRun.id == run_id).with_for_update())
        if not run or run.lease_owner != owner or run.status != "running":
            return
        run.error, run.duration_seconds = f"{type(error).__name__}: {error}"[:2000], duration
        retry = run.attempts < run.max_attempts
        run.status, run.completed_at = ("queued", None) if retry else ("failed", utc_after())
        run.next_attempt_at = utc_after(min(60, 2**run.attempts)) if retry else None
        run.lease_owner, run.lease_expires_at = None, None


class Heartbeat:
    def __init__(self, run_id, owner):
        self.run_id, self.owner = run_id, owner
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        while not self.stop.wait(LEASE_SECONDS / 3):
            try:
                if not renew_lease(self.run_id, self.owner):
                    return
            except Exception:
                # A DB outage cannot extend ownership. Final commit must pass fencing.
                return

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.stop.set()
        self.thread.join(timeout=1)
