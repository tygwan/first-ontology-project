"""Tests for bimkg.ingest.sqlite_writer (full Phase 1a pipeline)."""

from __future__ import annotations

import sqlite3

import pandas as pd
import pytest

from bimkg import config
from bimkg.ingest.sqlite_writer import run_phase_1a


@pytest.fixture(scope="module")
def phase1a_summary():
    return run_phase_1a()


def test_summary_silver_counts(phase1a_summary) -> None:
    assert phase1a_summary["silver_objects_rows"] == config.EXPECTED_OBJECT_COUNT
    assert phase1a_summary["silver_adjacency_rows"] == config.EXPECTED_ADJACENCY_COUNT
    assert phase1a_summary["silver_hierarchy_rows"] == config.EXPECTED_OBJECT_COUNT
    assert (
        phase1a_summary["silver_connected_groups_rows"]
        == config.EXPECTED_CONNECTED_GROUPS
    )


def test_summary_gold_counts(phase1a_summary) -> None:
    assert phase1a_summary["gold_objects_rows"] == config.EXPECTED_OBJECT_COUNT
    # Gold has many columns (XLSX 135 + joins + flags + SI + lineage ≈ 216)
    assert phase1a_summary["gold_objects_columns"] > 200
    # Symmetric closure doubles the edge count
    assert (
        phase1a_summary["gold_adjacency_sym_rows"]
        == config.EXPECTED_ADJACENCY_COUNT * 2
    )


def test_silver_parquet_files_exist(phase1a_summary) -> None:
    assert config.CLEAN_OBJECTS.exists()
    assert config.CLEAN_ADJACENCY.exists()
    assert config.CLEAN_HIERARCHY.exists()
    assert config.CLEAN_CONNECTED_GROUPS.exists()


def test_gold_parquet_files_exist(phase1a_summary) -> None:
    assert config.ENRICHED_OBJECTS.exists()
    assert config.ENRICHED_ADJACENCY_SYM.exists()


def test_sqlite_db_exists(phase1a_summary) -> None:
    assert config.SQLITE_BIMKG.exists()


def test_sqlite_tables_exist(phase1a_summary) -> None:
    with sqlite3.connect(config.SQLITE_BIMKG) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "bim_objects" in tables
        assert "bim_adjacency" in tables


def test_sqlite_row_counts(phase1a_summary) -> None:
    with sqlite3.connect(config.SQLITE_BIMKG) as conn:
        obj_rows = conn.execute("SELECT COUNT(*) FROM bim_objects").fetchone()[0]
        adj_rows = conn.execute("SELECT COUNT(*) FROM bim_adjacency").fetchone()[0]
    assert obj_rows == config.EXPECTED_OBJECT_COUNT
    assert adj_rows == config.EXPECTED_ADJACENCY_COUNT * 2


def test_silver_parquet_roundtrip(phase1a_summary) -> None:
    """Loading the parquet back must yield the same row count."""
    df = pd.read_parquet(config.CLEAN_OBJECTS)
    assert len(df) == config.EXPECTED_OBJECT_COUNT
    assert "class_raw" in df.columns
    assert "object_id" in df.columns


def test_gold_parquet_roundtrip(phase1a_summary) -> None:
    df = pd.read_parquet(config.ENRICHED_OBJECTS)
    assert len(df) == config.EXPECTED_OBJECT_COUNT
    # All lineage columns round-tripped
    assert "original_class" in df.columns
    assert "refined_class" in df.columns
    assert "refining_rule" in df.columns
    assert "title" in df.columns
