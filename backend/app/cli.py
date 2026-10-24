import argparse
import os
from pathlib import Path
from sqlalchemy import select
from alembic.config import Config
from alembic import command
from backend.app.db.session import SessionLocal
from backend.app.models.entities import User
from backend.app.security.auth import hash_password
from backend.app.services.pipeline import create_run, run_pipeline


def main():
    parser = argparse.ArgumentParser(description="Fraud Radar administration")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    seed = sub.add_parser("seed")
    seed.add_argument("--transactions", type=int, default=3000)
    seed.add_argument("--seed", type=int, default=42)
    seed.add_argument("--customers", type=int, default=180)
    seed.add_argument("--fraud-rate", type=float, default=0.06)
    user = sub.add_parser("create-user")
    user.add_argument("--username", required=True)
    user.add_argument("--role", choices=["analyst", "investigator", "administrator"], default="analyst")
    args = parser.parse_args()
    if args.command == "init":
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        command.upgrade(config, "head")
        password = os.getenv("BOOTSTRAP_PASSWORD")
        username = os.getenv("BOOTSTRAP_USERNAME", "admin")
        with SessionLocal.begin() as db:
            if not db.scalar(select(User).where(User.username == username)):
                if not password or len(password) < 12:
                    raise SystemExit("Set BOOTSTRAP_PASSWORD to at least 12 characters")
                db.add(User(username=username, password_hash=hash_password(password), role="administrator"))
        print("Database migrated and administrator initialized.")
    elif args.command == "create-user":
        password = os.getenv("NEW_USER_PASSWORD")
        if not password or len(password) < 12:
            raise SystemExit("Set NEW_USER_PASSWORD to at least 12 characters")
        with SessionLocal.begin() as db:
            if db.scalar(select(User).where(User.username == args.username)):
                raise SystemExit("Username already exists")
            db.add(User(username=args.username, password_hash=hash_password(password), role=args.role))
    else:
        config = {"transactions": args.transactions, "seed": args.seed, "customers": args.customers, "fraud_rate": args.fraud_rate}
        with SessionLocal() as db:
            run = create_run(db, config)
        run_pipeline(run.id, config)
        print("Pipeline completed: " + run.id)


if __name__ == "__main__":
    main()
