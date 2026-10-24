import pytest
from sqlalchemy import select
from backend.app.models.entities import PipelineRun, Transaction
from backend.app.services import jobs, pipeline
from database_helpers import isolated_sessions


@pytest.fixture
def sessions(tmp_path, monkeypatch):
    with isolated_sessions(tmp_path, "queue.db") as factory:
        monkeypatch.setattr(jobs, "SessionLocal", factory)
        monkeypatch.setattr(pipeline, "SessionLocal", factory)
        monkeypatch.setattr(pipeline, "ARTIFACT_DIR", tmp_path / "artifacts")
        yield factory


def enqueue(sessions, seed=302):
    with sessions() as db:
        return pipeline.create_run(db, {"transactions": 500, "customers": 30, "seed": seed, "fraud_rate": 0.1}).id


def test_restart_recovers_expired_lease_and_fences_old_owner(sessions):
    run_id = enqueue(sessions)
    first = jobs.claim_run()
    assert first[0] == run_id
    assert jobs.claim_run() is None
    with sessions.begin() as db:
        db.get(PipelineRun, run_id).lease_expires_at = jobs.utc_after(-1)
    second = jobs.claim_run()
    assert second[2] != first[2]
    assert not jobs.renew_lease(run_id, first[2])
    with sessions.begin() as db:
        with pytest.raises(jobs.LeaseLost):
            jobs.fence(db, run_id, first[2])
        assert jobs.fence(db, run_id, second[2]).attempts == 2


def test_bounded_retries_and_persistent_queue(sessions):
    run_id = enqueue(sessions)
    for attempt in range(3):
        claim = jobs.claim_run()
        jobs.record_failure(run_id, claim[2], ValueError("controlled test failure"), 0.1)
        with sessions.begin() as db:
            run = db.get(PipelineRun, run_id)
            assert run.attempts == attempt + 1
            assert run.status == ("failed" if attempt == 2 else "queued")
            run.next_attempt_at = None
    assert jobs.claim_run() is None


def test_worker_commits_and_replay_creates_no_duplicates(sessions):
    from backend.app.worker import execute_one

    run_id = enqueue(sessions)
    assert execute_one()
    with sessions() as db:
        run = db.get(PipelineRun, run_id)
        assert run.status == "completed" and run.processed == 500 and run.attempts == 1, run.error
        assert run.lease_owner is None
    replay = enqueue(sessions)
    assert execute_one()
    with sessions() as db:
        run = db.get(PipelineRun, replay)
        assert run.processed == 0 and run.duplicates == 500
        assert len(list(db.scalars(select(Transaction)))) == 500


def test_only_one_concurrent_worker_claims(sessions):
    from concurrent.futures import ThreadPoolExecutor

    enqueue(sessions)
    enqueue(sessions, seed=303)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: jobs.claim_run(), range(2)))
    assert sum(result is not None for result in results) == 1
