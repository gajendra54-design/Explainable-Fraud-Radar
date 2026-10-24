"""Bounded quarantine retention. Dry-run by default; never purge case evidence."""

import argparse
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from backend.app.db.session import SessionLocal
from backend.app.models.entities import Audit, PipelineRun, Quarantine


def purge_quarantine(db, *, days: int, apply: bool = False, at: datetime | None = None):
    if days < 1:
        raise ValueError("Retention must be at least one day")
    cutoff = ((at or datetime.now(timezone.utc)) - timedelta(days=days)).isoformat()
    expired_runs = select(PipelineRun.id).where(
        PipelineRun.completed_at < cutoff,
        PipelineRun.status.in_(["completed", "failed"]),
    )
    ids = list(db.scalars(select(Quarantine.id).where(Quarantine.run_id.in_(expired_runs))))
    if apply and ids:
        # SQL subquery avoids parameter-count limits on large quarantine datasets.
        db.execute(delete(Quarantine).where(Quarantine.run_id.in_(expired_runs)))
        db.add(Audit(actor="retention-worker", action="quarantine_retention", details={"cutoff": cutoff, "deleted": len(ids)}))
        db.commit()
    return {"dry_run": not apply, "cutoff": cutoff, "eligible_records": len(ids), "deleted": len(ids) if apply else 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--apply", action="store_true", help="Delete expired rejected payloads, retaining run counts and audit evidence")
    args = parser.parse_args()
    with SessionLocal() as db:
        print(json.dumps(purge_quarantine(db, days=args.days, apply=args.apply)))


if __name__ == "__main__":
    main()
