"""Shared fixtures for all backend tests that need a real PostgreSQL database
(not SQLite) — the schema relies on Postgres-specific behavior (native
UUID/JSONB columns, functional indexes, ON DELETE RESTRICT/SET NULL
semantics, RLS) that SQLite cannot faithfully emulate. See
docs/migration-guidelines.md#7-testing-migrations.
"""

from collections.abc import Generator
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

API_ROOT = Path(__file__).resolve().parents[1]


def _test_database_url() -> str:
    base_url = get_settings().database_url
    parsed = urlparse(base_url)
    test_path = f"{parsed.path}_test" if not parsed.path.endswith("_test") else parsed.path
    return urlunparse(parsed._replace(path=test_path))


def _maintenance_database_url(test_url: str) -> str:
    parsed = urlparse(test_url)
    return urlunparse(parsed._replace(path="/postgres"))


def _ensure_database_exists(test_url: str) -> None:
    db_name = urlparse(test_url).path.lstrip("/")
    maintenance_engine = create_engine(_maintenance_database_url(test_url))
    try:
        with maintenance_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": db_name}
            ).first()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    finally:
        maintenance_engine.dispose()


@pytest.fixture(scope="session")
def db_engine() -> Generator[Engine, None, None]:
    test_url = _test_database_url()
    _ensure_database_exists(test_url)

    alembic_cfg = Config(str(API_ROOT / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(API_ROOT / "migrations"))
    alembic_cfg.set_main_option("sqlalchemy.url", test_url)
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(test_url)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine: Engine) -> Generator[Session, None, None]:
    """Each test runs inside a transaction that is rolled back afterward, so
    tests never see each other's data and the schema only needs migrating once
    per test session."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(bind=connection, expire_on_commit=False)
    session = session_factory()

    yield session

    session.close()
    if transaction.is_active:
        # A failed flush (e.g. an expected IntegrityError from a constraint
        # test) already deactivates the transaction; only roll back if it's
        # still live to avoid a harmless-but-noisy SAWarning.
        transaction.rollback()
    connection.close()
