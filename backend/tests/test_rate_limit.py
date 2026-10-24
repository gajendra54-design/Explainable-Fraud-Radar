import time
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from backend.app.models.entities import User
from backend.app.models.auth_sessions import AuthSession, LoginAttemptBucket
from backend.app.security.auth import hash_password
from backend.app.security.rate_limit import authenticate, bucket_keys
from backend.app.security.cleanup import cleanup_expired
from database_helpers import isolated_sessions


@pytest.fixture
def sessions(tmp_path):
    with isolated_sessions(tmp_path, "auth.db") as factory:
        with factory.begin() as db:
            db.add(User(username="account", role="analyst", password_hash=hash_password("right-password")))
        yield factory


def failed(factory, username="account", at=None):
    with factory() as db:
        try:
            authenticate(db, username, "wrong", "192.0.2.1", current=at)
        except HTTPException as exc:
            return exc.status_code
    raise AssertionError("Invalid password authenticated")


def test_failed_window_persists_across_new_sessions_and_expires(sessions):
    at = time.time()
    assert [failed(sessions, at=at + i / 10) for i in range(10)] == [401] * 10
    assert failed(sessions, at=at + 2) == 429
    # Simulates a restarted API using a fresh session factory with the same database.
    restarted = sessionmaker(sessions.kw["bind"], expire_on_commit=False)
    assert failed(restarted, at=at + 3) == 429
    assert failed(restarted, at=at + 62) == 401


def test_success_resets_pair_but_not_ip_spray_bucket(sessions):
    at = time.time()
    for _ in range(3):
        assert failed(sessions, at=at) == 401
    with sessions() as db:
        assert authenticate(db, "account", "right-password", "192.0.2.1", current=at).username == "account"
        db.commit()
    pair, ip = bucket_keys("account", "192.0.2.1")
    with sessions() as db:
        assert db.get(LoginAttemptBucket, pair) is None
        assert len(db.get(LoginAttemptBucket, ip).failed_at) == 3


def test_parallel_requests_share_exact_failure_capacity(sessions):
    at = time.time()
    with ThreadPoolExecutor(max_workers=6) as executor:
        results = list(executor.map(lambda _: failed(sessions, at=at), range(15)))
    assert results.count(401) == 10
    assert results.count(429) == 5


def test_ip_spraying_and_bounded_expiry_cleanup(sessions):
    at = time.time()
    for i in range(50):
        assert failed(sessions, username=f"unknown-{i}", at=at) == 401
    assert failed(sessions, username="another-name", at=at) == 429
    with sessions.begin() as db:
        uid = db.scalar(select(User.id))
        for i in range(4):
            db.add(AuthSession(id=f"expired-{i}", user_id=uid, expires_at="2001-01-01T00:00:00+00:00"))
        db.add(AuthSession(id="active", user_id=uid, expires_at="2099-01-01T00:00:00+00:00"))
        for bucket in db.scalars(select(LoginAttemptBucket)):
            bucket.expires_at = at - 1
    with sessions.begin() as db:
        assert cleanup_expired(db, limit=2) == {"expired_sessions": 2, "expired_login_buckets": 2}
    with sessions() as db:
        assert db.get(AuthSession, "active") is not None
        assert len(list(db.scalars(select(AuthSession)))) == 3
