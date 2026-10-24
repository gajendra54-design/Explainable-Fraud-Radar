"""Bounded cleanup of expired sessions and expired failed-login buckets."""

import argparse
from sqlalchemy import select, delete
from backend.app.db.session import SessionLocal
from backend.app.models.auth_sessions import AuthSession
from backend.app.models.entities import now
from backend.app.security.rate_limit import cleanup_buckets


def cleanup_expired(db, limit=1000):
    if not 1 <= limit <= 10000:
        raise ValueError("limit must be between 1 and 10000")
    ids = list(
        db.scalars(
            select(AuthSession.id)
            .where(AuthSession.expires_at <= now())
            .order_by(AuthSession.expires_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
    )
    if ids:
        db.execute(delete(AuthSession).where(AuthSession.id.in_(ids)))
    return {"expired_sessions": len(ids), "expired_login_buckets": cleanup_buckets(db, limit=limit)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=1000)
    args = parser.parse_args()
    with SessionLocal.begin() as db:
        result = cleanup_expired(db, args.limit)
    print(result)


if __name__ == "__main__":
    main()
