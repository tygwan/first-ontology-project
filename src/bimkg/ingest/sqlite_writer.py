"""Write Phase 1a tables to Parquet (Silver + Gold) and SQLite (Gold canonical).

This module is the terminal step of Phase 1a. It takes the DataFrames
produced by :mod:`bimkg.ingest.clean` and writes them to:

- ``data/clean/<snapshot>/*.parquet``     — Silver layer
- ``data/enriched/<snapshot>/*.parquet``  — Gold layer
- ``data/enriched/<snapshot>/bimkg.db``   — Gold canonical SQLite

``run_phase_1a`` is the single entry point that executes the full Silver →
Gold pipeline and writes all outputs. It returns a summary dict so callers
(tests, CLI, notebooks) can assert on row counts without re-reading files.

Parquet is used as the primary serialization format because:
1. It preserves explicit types (Int64 stays Int64, no stringification).
2. It is Palantir Foundry's native ingestion format.
3. It stores nullable booleans correctly where CSV would write ``1.0`` /
   ``0.0`` / ``nan``.

SQLite is kept as a convenience for interactive exploration (sqlite3 CLI,
DB browsers) and for ``bimkg.db`` to serve as the canonical local store
during downstream phases.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import TypedDict

import pandas as pd

from bimkg import config
from bimkg.ingest.clean import (
    add_adjacency_symmetric_closure,
    build_bim_adjacency_silver,
    build_bim_connected_groups_silver,
    build_bim_hierarchy_silver,
    build_bim_objects_gold,
    build_bim_objects_silver,
)


# ---------------------------------------------------------------------------
# Return type for run_phase_1a
# ---------------------------------------------------------------------------


class Phase1aSummary(TypedDict):
    silver_objects_rows: int
    silver_adjacency_rows: int
    silver_hierarchy_rows: int
    silver_connected_groups_rows: int
    gold_objects_rows: int
    gold_objects_columns: int
    gold_adjacency_sym_rows: int
    sqlite_path: str
    parquet_silver_dir: str
    parquet_gold_dir: str


# ---------------------------------------------------------------------------
# Low-level writers
# ---------------------------------------------------------------------------


def write_parquet(df: pd.DataFrame, path: Path) -> None:
    """Write a DataFrame to Parquet, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def write_sqlite(
    tables: dict[str, pd.DataFrame],
    db_path: Path,
) -> None:
    """Write multiple DataFrames to a single SQLite database file.

    Existing tables with the same names are replaced. The database file is
    overwritten if it exists (callers should delete the old file first if
    they want to retain history).
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    with sqlite3.connect(db_path) as conn:
        for table_name, df in tables.items():
            df.to_sql(table_name, conn, if_exists="replace", index=False)
        conn.commit()


# ---------------------------------------------------------------------------
# High-level output writers
# ---------------------------------------------------------------------------


def write_silver(
    silver_objects: pd.DataFrame,
    silver_adjacency: pd.DataFrame,
    silver_hierarchy: pd.DataFrame,
    silver_groups: pd.DataFrame,
) -> None:
    """Write all four Silver tables to ``data/clean/<snapshot>/``."""
    write_parquet(silver_objects, config.CLEAN_OBJECTS)
    write_parquet(silver_adjacency, config.CLEAN_ADJACENCY)
    write_parquet(silver_hierarchy, config.CLEAN_HIERARCHY)
    write_parquet(silver_groups, config.CLEAN_CONNECTED_GROUPS)


def write_gold(
    gold_objects: pd.DataFrame,
    gold_adjacency_sym: pd.DataFrame,
) -> None:
    """Write Gold Parquet + SQLite canonical store."""
    write_parquet(gold_objects, config.ENRICHED_OBJECTS)
    write_parquet(gold_adjacency_sym, config.ENRICHED_ADJACENCY_SYM)

    write_sqlite(
        tables={
            "bim_objects": gold_objects,
            "bim_adjacency": gold_adjacency_sym,
        },
        db_path=config.SQLITE_BIMKG,
    )


# ---------------------------------------------------------------------------
# Pipeline orchestration
# ---------------------------------------------------------------------------


def run_phase_1a() -> Phase1aSummary:
    """Execute the full Phase 1a Silver → Gold pipeline.

    Steps:
        1. Build Silver tables from raw sources (XLSX + CSVs)
        2. Write Silver Parquet files
        3. Build Gold ``bim_objects_enriched`` (joins + flags + SI + lineage)
        4. Build Gold ``bim_adjacency_sym`` (undirected closure)
        5. Write Gold Parquet files + SQLite canonical store

    Returns
    -------
    Phase1aSummary
        Dict with row counts, column counts, and output paths for verification.
    """
    # ---- Silver ----
    silver_objects = build_bim_objects_silver()
    silver_adjacency = build_bim_adjacency_silver()
    silver_hierarchy = build_bim_hierarchy_silver()
    silver_groups = build_bim_connected_groups_silver()

    write_silver(silver_objects, silver_adjacency, silver_hierarchy, silver_groups)

    # ---- Gold ----
    gold_objects = build_bim_objects_gold()
    gold_adjacency_sym = add_adjacency_symmetric_closure(silver_adjacency)

    write_gold(gold_objects, gold_adjacency_sym)

    return Phase1aSummary(
        silver_objects_rows=len(silver_objects),
        silver_adjacency_rows=len(silver_adjacency),
        silver_hierarchy_rows=len(silver_hierarchy),
        silver_connected_groups_rows=len(silver_groups),
        gold_objects_rows=len(gold_objects),
        gold_objects_columns=len(gold_objects.columns),
        gold_adjacency_sym_rows=len(gold_adjacency_sym),
        sqlite_path=str(config.SQLITE_BIMKG),
        parquet_silver_dir=str(config.DATA_CLEAN),
        parquet_gold_dir=str(config.DATA_ENRICHED),
    )
