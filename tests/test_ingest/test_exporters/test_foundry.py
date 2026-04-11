"""Tests for bimkg.ingest.exporters.foundry."""

from __future__ import annotations

import pandas as pd
import pytest

from bimkg import config
from bimkg.ingest.exporters.foundry import (
    OBJECT_TYPE_MAP,
    run_foundry_export,
)


@pytest.fixture(scope="module")
def foundry_summary():
    return run_foundry_export()


# ---------------------------------------------------------------------------
# Object Type row counts (cross-validated with Gold class distribution)
# ---------------------------------------------------------------------------


def test_piping_count(foundry_summary) -> None:
    """2026-04-12 post-fix: Piping shrunk from 4,014 to 3,062 (-952)."""
    assert foundry_summary["object_type_rows"]["piping.parquet"] == 3062


def test_structural_count(foundry_summary) -> None:
    """2026-04-12 post-fix: Structure shrunk from 5,926 to 4,840 (-1,086)."""
    assert foundry_summary["object_type_rows"]["structural.parquet"] == 4840


def test_equipment_count(foundry_summary) -> None:
    """2026-04-12 post-fix: Equipment shrunk from 851 to 770 (-81)."""
    assert foundry_summary["object_type_rows"]["equipment.parquet"] == 770


def test_electrical_count(foundry_summary) -> None:
    """2026-04-12 post-fix: Electrical grew from 449 to 1,053 (+604)."""
    assert foundry_summary["object_type_rows"]["electrical.parquet"] == 1053


def test_hvac_count(foundry_summary) -> None:
    """2026-04-12 post-fix: HVAC grew from 72 to 125 (+53)."""
    assert foundry_summary["object_type_rows"]["hvac.parquet"] == 125


def test_other_count(foundry_summary) -> None:
    """2026-04-12 post-fix: Other grew from 697 to 2,159 (+1,462)."""
    assert foundry_summary["object_type_rows"]["other.parquet"] == 2159


def test_total_object_type_rows_match_total_objects(foundry_summary) -> None:
    total = sum(foundry_summary["object_type_rows"].values())
    assert total == config.EXPECTED_OBJECT_COUNT


# ---------------------------------------------------------------------------
# Link Type row counts
# ---------------------------------------------------------------------------


def test_adjacent_to_is_single_direction(foundry_summary) -> None:
    """Producer adjacency is stored as-is (110,173), not doubled."""
    assert (
        foundry_summary["link_adjacent_to_rows"]
        == config.EXPECTED_ADJACENCY_COUNT
    )


def test_has_parent_excludes_root(foundry_summary) -> None:
    """Root object has no parent, so 12,008 rows."""
    assert foundry_summary["link_has_parent_rows"] == 12008


def test_belongs_to_pipeline_count(foundry_summary) -> None:
    """Matches the number of Piping objects with a non-null pipeline
    attribute (2,926 in the 2026-04-07 snapshot)."""
    assert foundry_summary["link_belongs_to_pipeline_rows"] == 2926


def test_in_group_count(foundry_summary) -> None:
    assert (
        foundry_summary["link_in_group_rows"] == config.EXPECTED_OBJECT_COUNT
    )


# ---------------------------------------------------------------------------
# File existence
# ---------------------------------------------------------------------------


def test_all_object_type_parquets_exist(foundry_summary) -> None:
    for _, (filename, _type_name) in OBJECT_TYPE_MAP.items():
        path = config.ONTOLOGY_OBJECT_TYPES / filename
        assert path.exists(), f"Missing: {filename}"


def test_all_link_type_parquets_exist(foundry_summary) -> None:
    expected = [
        "adjacent_to.parquet",
        "has_parent.parquet",
        "belongs_to_pipeline.parquet",
        "in_group.parquet",
    ]
    for filename in expected:
        path = config.ONTOLOGY_LINK_TYPES / filename
        assert path.exists(), f"Missing: {filename}"


# ---------------------------------------------------------------------------
# Schema / content tests
# ---------------------------------------------------------------------------


def test_object_types_keep_all_columns(foundry_summary) -> None:
    """Every class parquet must preserve all 216 Gold columns (all-in-one)."""
    gold = pd.read_parquet(config.ENRICHED_OBJECTS)
    for _, (filename, _type_name) in OBJECT_TYPE_MAP.items():
        df = pd.read_parquet(config.ONTOLOGY_OBJECT_TYPES / filename)
        assert set(df.columns) == set(gold.columns), (
            f"{filename} columns differ from Gold"
        )


def test_object_ids_are_unique_in_each_object_type(foundry_summary) -> None:
    for _, (filename, _type_name) in OBJECT_TYPE_MAP.items():
        df = pd.read_parquet(
            config.ONTOLOGY_OBJECT_TYPES / filename, columns=["object_id"]
        )
        assert df["object_id"].is_unique
        assert df["object_id"].notna().all()


def test_object_ids_do_not_overlap_across_classes(foundry_summary) -> None:
    """Each object belongs to exactly one Object Type."""
    all_ids: set[str] = set()
    for _, (filename, _type_name) in OBJECT_TYPE_MAP.items():
        df = pd.read_parquet(
            config.ONTOLOGY_OBJECT_TYPES / filename, columns=["object_id"]
        )
        ids = set(df["object_id"])
        overlap = all_ids & ids
        assert not overlap, f"Overlap with previous classes: {overlap}"
        all_ids |= ids
    assert len(all_ids) == config.EXPECTED_OBJECT_COUNT


def test_link_adjacent_to_has_is_symmetric_flag(foundry_summary) -> None:
    df = pd.read_parquet(config.ONTOLOGY_LINK_TYPES / "adjacent_to.parquet")
    assert "is_symmetric" in df.columns
    assert df["is_symmetric"].all()


def test_link_has_parent_schema(foundry_summary) -> None:
    df = pd.read_parquet(config.ONTOLOGY_LINK_TYPES / "has_parent.parquet")
    assert set(df.columns) == {
        "child_object_id",
        "parent_object_id",
        "child_level",
    }
    assert df["parent_object_id"].notna().all()


def test_link_belongs_to_pipeline_schema(foundry_summary) -> None:
    df = pd.read_parquet(
        config.ONTOLOGY_LINK_TYPES / "belongs_to_pipeline.parquet"
    )
    assert set(df.columns) == {"object_id", "pipeline_name", "pipe_run_name"}
    assert df["pipeline_name"].notna().all()


def test_link_in_group_has_giant_flag(foundry_summary) -> None:
    df = pd.read_parquet(config.ONTOLOGY_LINK_TYPES / "in_group.parquet")
    assert "is_giant_group" in df.columns
    assert df["is_giant_group"].sum() == config.EXPECTED_GIANT_GROUP_SIZE


# ---------------------------------------------------------------------------
# Cross-referential integrity
# ---------------------------------------------------------------------------


def test_link_adjacent_to_endpoints_exist(foundry_summary) -> None:
    """Every adjacency endpoint must exist in one of the Object Type files."""
    all_ids: set[str] = set()
    for _, (filename, _type_name) in OBJECT_TYPE_MAP.items():
        df = pd.read_parquet(
            config.ONTOLOGY_OBJECT_TYPES / filename, columns=["object_id"]
        )
        all_ids |= set(df["object_id"])

    adj = pd.read_parquet(
        config.ONTOLOGY_LINK_TYPES / "adjacent_to.parquet",
        columns=["source_object_id", "target_object_id"],
    )
    assert set(adj["source_object_id"]).issubset(all_ids)
    assert set(adj["target_object_id"]).issubset(all_ids)


def test_link_has_parent_endpoints_exist(foundry_summary) -> None:
    all_ids: set[str] = set()
    for _, (filename, _type_name) in OBJECT_TYPE_MAP.items():
        df = pd.read_parquet(
            config.ONTOLOGY_OBJECT_TYPES / filename, columns=["object_id"]
        )
        all_ids |= set(df["object_id"])

    parent = pd.read_parquet(
        config.ONTOLOGY_LINK_TYPES / "has_parent.parquet",
        columns=["child_object_id", "parent_object_id"],
    )
    assert set(parent["child_object_id"]).issubset(all_ids)
    assert set(parent["parent_object_id"]).issubset(all_ids)
