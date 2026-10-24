"""Run with python -m backend.app.worker; jobs survive API/worker restarts."""

import argparse
import json
import logging
import signal
import threading
from backend.app.services.jobs import claim_run
from backend.app.services.pipeline import run_pipeline


def execute_one():
    job = claim_run()
    if job is None:
        return False
    run_id, config, owner = job
    try:
        run_pipeline(run_id, config, lease_owner=owner)
    except Exception as exc:
        logging.error(json.dumps({"run_id": run_id, "error_type": type(exc).__name__, "event": "pipeline_attempt_failed"}))
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--poll-seconds", type=float, default=2)
    args = parser.parse_args()
    stop = threading.Event()
    for name in ("SIGINT", "SIGTERM"):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), lambda *_: stop.set())
    while not stop.is_set():
        try:
            executed = execute_one()
        except Exception as exc:
            logging.error(json.dumps({"event": "worker_database_error", "error_type": type(exc).__name__}))
            executed = False
        if args.once:
            return
        if not executed:
            stop.wait(max(0.1, args.poll_seconds))


if __name__ == "__main__":
    main()
