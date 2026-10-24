# ruff: noqa: E402
import os
import tempfile
from pathlib import Path

_root = Path(tempfile.mkdtemp(prefix="radar-tests-"))
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL", "sqlite:///" + str(_root / "test.db"))
os.environ["ARTIFACT_DIR"] = str(_root / "artifacts")

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.session import SessionLocal
from backend.app.models.entities import User
from alembic.config import Config
from alembic import command
from backend.app.security.auth import hash_password
from backend.app.services.pipeline import create_run, run_pipeline


@pytest.fixture(scope="session")
def client():
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "head")
    with SessionLocal.begin() as db:
        for name, role in [("admin", "administrator"), ("investigator", "investigator"), ("analyst", "analyst")]:
            db.add(User(username=name, role=role, password_hash=hash_password("test-password-123")))
    config = {"transactions": 700, "seed": 11, "customers": 30, "fraud_rate": 0.12}
    with SessionLocal() as db:
        run = create_run(db, config)
    run_pipeline(run.id, config)
    with TestClient(app) as client:
        yield client
