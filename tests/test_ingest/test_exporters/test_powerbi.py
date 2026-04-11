"""Tests for bimkg.ingest.exporters.powerbi."""

from __future__ import annotations

import pandas as pd
import pytest

from bimkg import config
from bimkg.ingest.exporters.powerbi import (
    FACT_OBJECTS_COLUMNS,
    run_powerbi_export,
)


@pytest.fixture(scope="module")
def powerbi_summary():
    return run_powerbi_export()


# ---------------------------------------------------------------------------
# Row count tests
# ---------------------------------------------------------------------------


def test_fact_objects_rows(powerbi_summary) -> None:
    assert powerbi_summary["fact_objects_rows"] == config.EXPECTED_OBJECT_COUNT


def test_fact_adjacency_rows(powerbi_summary) -> None:
    assert (
        powerbi_summary["fact_adjacency_rows"] == config.EXPECTED_ADJACENCY_COUNT
    )


def test_fact_adjacency_undirected_rows(powerbi_summary) -> None:
    # Producer output already has one row per undirected pair
    assert (
        powerbi_summary["fact_adjacency_undirected_rows"]
        == config.EXPECTED_ADJACENCY_COUNT
    )


def test_bridge_group_member_rows(powerbi_summary) -> None:
    assert (
        powerbi_summary["bridge_group_member_rows"] == config.EXPECTED_OBJECT_COUNT
    )


def test_dim_class_has_six_classes(powerbi_summary) -> None:
    assert powerbi_summary["dim_class_rows"] == 6


def test_dim_level_has_ten_levels(powerbi_summary) -> None:
    assert powerbi_summary["dim_level_rows"] == 10


def test_dim_pipeline_count(powerbi_summary) -> None:
    # XLSX-based Pipeline_Summary had 146 rows + "Pipelines" header
    # Our derivation from gold filters the header and gives ~147 real pipelines
    assert 140 <= powerbi_summary["dim_pipeline_rows"] <= 160


def test_dim_group_rows(powerbi_summary) -> None:
    assert (
        powerbi_summary["dim_group_rows"] == config.EXPECTED_CONNECTED_GROUPS
    )


# ---------------------------------------------------------------------------
# File existence tests
# ---------------------------------------------------------------------------


def test_all_powerbi_files_created(powerbi_summary) -> None:
    expected_files = [
        "fact_objects.csv",
        "fact_adjacency.csv",
        "fact_adjacency_undirected.csv",
        "bridge_group_member.csv",
        "dim_class.csv",
        "dim_level.csv",
        "dim_pipeline.csv",
        "dim_meshq.csv",
        "dim_verdict.csv",
        "dim_group.csv",
        "README.md",
    ]
    for filename in expected_files:
        path = config.POWERBI_DIR / filename
        assert path.exists(), f"Missing: {filename}"
        assert path.stat().st_size > 0, f"Empty: {filename}"


# ---------------------------------------------------------------------------
# CSV content / schema tests
# ---------------------------------------------------------------------------


def test_fact_objects_has_expected_columns(powerbi_summary) -> None:
    df = pd.read_csv(config.POWERBI_DIR / "fact_objects.csv", nrows=1)
    # All curated columns + the derived in_giant_group
    expected_cols = set(FACT_OBJECTS_COLUMNS) | {"in_giant_group"}
    assert set(df.columns) == expected_cols


def test_fact_objects_has_66_plus_1_columns(powerbi_summary) -> None:
    df = pd.read_csv(config.POWERBI_DIR / "fact_objects.csv", nrows=1)
    # 66 curated columns in FACT_OBJECTS_COLUMNS + 1 derived (in_giant_group) = 67
    # (Phase 1e added classification_confidence + classification_confidence_reason)
    assert len(FACT_OBJECTS_COLUMNS) == 66
    assert len(df.columns) == 67


def test_fact_objects_in_giant_group_count(powerbi_summary) -> None:
    df = pd.read_csv(config.POWERBI_DIR / "fact_objects.csv")
    assert df["in_giant_group"].sum() == config.EXPECTED_GIANT_GROUP_SIZE


def test_dim_class_values(powerbi_summary) -> None:
    df = pd.read_csv(config.POWERBI_DIR / "dim_class.csv")
    classes = set(df["class_name"])
    assert classes == {
        "Piping",
        "Structure",
        "Equipment",
        "Electrical",
        "HVAC",
        "Other",
    }


def test_dim_class_percentages_sum_to_1(powerbi_summary) -> None:
    df = pd.read_csv(config.POWERBI_DIR / "dim_class.csv")
    assert abs(df["percentage"].sum() - 1.0) < 1e-6


def test_dim_meshq_values(powerbi_summary) -> None:
    df = pd.read_csv(config.POWERBI_DIR / "dim_meshq.csv")
    # Expected: full_mesh, skipped_container, box_placeholder, fbx_supplemented
    assert len(df) >= 4
    assert df["is_container"].dtype == bool
    assert df["is_container"].sum() >= 2  # skipped_container + box_placeholder


def test_fact_adjacency_has_edge_id(powerbi_summary) -> None:
    df = pd.read_csv(config.POWERBI_DIR / "fact_adjacency.csv")
    assert "edge_id" in df.columns
    assert df["edge_id"].is_unique


def test_fact_adjacency_undirected_has_pair_id(powerbi_summary) -> None:
    df = pd.read_csv(config.POWERBI_DIR / "fact_adjacency_undirected.csv")
    assert "pair_id" in df.columns
    assert df["pair_id"].is_unique
    assert "object_a" in df.columns
    assert "object_b" in df.columns


def test_fact_adjacency_undirected_is_ordered(powerbi_summary) -> None:
    """Every (object_a, object_b) pair must satisfy object_a <= object_b."""
    df = pd.read_csv(config.POWERBI_DIR / "fact_adjacency_undirected.csv")
    assert (df["object_a"] <= df["object_b"]).all()


# ---------------------------------------------------------------------------
# FK integrity
# ---------------------------------------------------------------------------


def test_bridge_group_fk_integrity(powerbi_summary) -> None:
    bridge = pd.read_csv(config.POWERBI_DIR / "bridge_group_member.csv")
    dim_group = pd.read_csv(config.POWERBI_DIR / "dim_group.csv")
    fact_objects = pd.read_csv(config.POWERBI_DIR / "fact_objects.csv")

    # Every bridge.object_id must exist in fact_objects
    assert set(bridge["object_id"]).issubset(set(fact_objects["object_id"]))
    # Every bridge.group_id must exist in dim_group
    assert set(bridge["group_id"]).issubset(set(dim_group["group_id"]))


def test_fact_objects_group_fk(powerbi_summary) -> None:
    fact = pd.read_csv(config.POWERBI_DIR / "fact_objects.csv")
    dim_group = pd.read_csv(config.POWERBI_DIR / "dim_group.csv")
    assert set(fact["group_id"].dropna()).issubset(set(dim_group["group_id"]))


def test_fact_adjacency_endpoints_in_fact_objects(powerbi_summary) -> None:
    fact_obj = pd.read_csv(
        config.POWERBI_DIR / "fact_objects.csv", usecols=["object_id"]
    )
    adj = pd.read_csv(
        config.POWERBI_DIR / "fact_adjacency.csv",
        usecols=["source_object_id", "target_object_id"],
    )
    valid_ids = set(fact_obj["object_id"])
    assert set(adj["source_object_id"]).issubset(valid_ids)
    assert set(adj["target_object_id"]).issubset(valid_ids)
