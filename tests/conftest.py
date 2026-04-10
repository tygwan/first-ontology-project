"""Shared pytest fixtures."""

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from bimkg import config


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Absolute path to the project root."""
    return config.PROJECT_ROOT


@pytest.fixture(scope="session")
def data_raw_dir() -> Path:
    """Path to the 2026-04-07 raw data snapshot."""
    return config.DATA_RAW


@pytest.fixture(scope="session")
def existing_sqlite_db() -> Path:
    """Path to the existing semantic SQLite DB (may not exist in CI).

    Tests that require this DB should skip when it's missing.
    """
    return config.SQLITE_DB


@pytest.fixture
def sqlite_ro(existing_sqlite_db: Path) -> Iterator[sqlite3.Connection]:
    """Read-only connection to the existing semantic SQLite DB.

    Skips the test if the DB file is not present.
    """
    if not existing_sqlite_db.exists():
        pytest.skip(f"SQLite DB not found at {existing_sqlite_db}")
    uri = f"file:{existing_sqlite_db}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        yield conn
    finally:
        conn.close()
