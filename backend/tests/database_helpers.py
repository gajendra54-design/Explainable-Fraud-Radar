"""Isolated relational fixtures for SQLite or a dedicated PostgreSQL test database."""

import os
import re
import uuid
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.schema import CreateSchema, DropSchema
from sqlalchemy.orm import sessionmaker
from backend.app.db.session import Base


@contextmanager
def isolated_sessions(tmp_path, filename):
    url = os.getenv("TEST_DATABASE_URL", "")
    if url.startswith("postgresql"):
        schema = "radar_test_" + uuid.uuid4().hex
        administration = create_engine(url)
        with administration.begin() as connection:
            connection.execute(CreateSchema(schema))
        engine = create_engine(
            url, connect_args={"options": "-csearch_path=" + schema}, execution_options={"schema_translate_map": {None: schema}}
        )
        try:
            Base.metadata.create_all(engine)
            yield sessionmaker(engine, expire_on_commit=False)
        finally:
            engine.dispose()
            # Only remove this fixture's generated namespace, never the supplied database.
            if not re.fullmatch(r"radar_test_[0-9a-f]{32}", schema):
                raise RuntimeError("Refusing to remove an unexpected test schema")
            with administration.begin() as connection:
                connection.execute(DropSchema(schema, cascade=True))
            administration.dispose()
    else:
        engine = create_engine("sqlite:///" + str(tmp_path / filename), connect_args={"check_same_thread": False})
        try:
            Base.metadata.create_all(engine)
            yield sessionmaker(engine, expire_on_commit=False)
        finally:
            engine.dispose()
