"""Shared failed-login limiter. Raw usernames/IP addresses are not persisted."""

import hashlib
import time
from fastapi import HTTPException
from sqlalchemy import select, text, delete
from backend.app.db.session import SessionLocal
from backend.app.models.auth_sessions import LoginAttemptBucket
from backend.app.models.entities import User
from backend.app.security.auth import verify_password

WINDOW_SECONDS = 60
PAIR_LIMIT = 10
IP_LIMIT = 50


def bucket_keys(username, address):
    pair = hashlib.sha256(("pair\0" + username + "\0" + address).encode()).hexdigest()
    ip = hashlib.sha256(("ip\0" + address).encode()).hexdigest()
    return pair, ip


def cleanup_buckets(db, limit=100, current=None):
    current = time.time() if current is None else current
    keys = list(
        db.scalars(
            select(LoginAttemptBucket.key)
            .where(LoginAttemptBucket.expires_at <= current)
            .order_by(LoginAttemptBucket.expires_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
    )
    if keys:
        db.execute(delete(LoginAttemptBucket).where(LoginAttemptBucket.key.in_(keys)))
    return len(keys)


def authenticate(db, username, password, address, current=None):
    """Hold rate-limit locks through password checking and session creation commit."""
    current = time.time() if current is None else current
    pair, ip = bucket_keys(username, address)
    if db.bind.dialect.name == "postgresql":
        for key in sorted((pair, ip)):
            lock_id = int.from_bytes(bytes.fromhex(key[:16]), "big", signed=True)
            db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_id})
    else:
        db.execute(text("BEGIN IMMEDIATE"))
    cleanup_buckets(db, current=current)
    buckets = {}
    for key, limit in [(pair, PAIR_LIMIT), (ip, IP_LIMIT)]:
        bucket = db.get(LoginAttemptBucket, key)
        failures = [stamp for stamp in bucket.failed_at if stamp > current - WINDOW_SECONDS] if bucket else []
        if len(failures) >= limit:
            db.rollback()
            raise HTTPException(429, "Too many failed login attempts; retry after the rolling one-minute window")
        buckets[key] = (bucket, failures)
    user = db.scalar(select(User).where(User.username == username).with_for_update())
    if user and verify_password(password, user.password_hash):
        # Reset this account/source window; successful logins cannot reset IP spraying protection.
        if buckets[pair][0]:
            db.delete(buckets[pair][0])
        return user
    for key, (bucket, failures) in buckets.items():
        if bucket is None:
            bucket = LoginAttemptBucket(key=key, failed_at=[], expires_at=current + WINDOW_SECONDS)
            db.add(bucket)
        bucket.failed_at = failures + [current]
        bucket.expires_at = current + WINDOW_SECONDS
    db.commit()
    raise HTTPException(401, "Invalid username or password")


class AttemptResetHelper:
    """Backward-compatible test reset, not exposed by any HTTP endpoint."""

    def clear(self):
        with SessionLocal.begin() as db:
            db.execute(delete(LoginAttemptBucket))


login_attempts = AttemptResetHelper()
