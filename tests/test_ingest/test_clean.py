"""Tests for bimkg.ingest.clean."""

from __future__ import annotations

import pandas as pd
import pytest

from bimkg import config
from bimkg.ingest.clean import (
    ANALYSIS_VOLUME_PATTERNS,
    EMPTY_GUID,
    REFINING_RULE,
    REFINING_RULE_VERSION,
    add_adjacency_symmetric_closure,
    add_flags,
    add_lineage,
    add_si_units,
    add_title,
    build_bim_adjacency_silver,
    build_bim_connected_groups_silver,
    build_bim_hierarchy_silver,
    build_bim_objects_gold,
    build_bim_objects_silver,
    load_hierarchy_from_all_properties,
)

# ---------------------------------------------------------------------------
# Silver layer integration tests
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def silver_objects() -> pd.DataFrame:
    return build_bim_objects_silver()


@pytest.fixture(scope="module")
def silver_adjacency() -> pd.DataFrame:
    return build_bim_adjacency_silver()


@pytest.fixture(scope="module")
def silver_hierarchy() -> pd.DataFrame:
    return build_bim_hierarchy_silver()


@pytest.fixture(scope="module")
def silver_groups() -> pd.DataFrame:
    return build_bim_connected_groups_silver()


@pytest.fixture(scope="module")
def gold_objects() -> pd.DataFrame:
    return build_bim_objects_gold()


def test_silver_objects_row_count(silver_objects: pd.DataFrame) -> None:
    assert len(silver_objects) == config.EXPECTED_OBJECT_COUNT


def test_silver_objects_level_is_int(silver_objects: pd.DataFrame) -> None:
    assert silver_objects["level"].dtype.name in ("Int64", "int64")
    levels = set(silver_objects["level"].dropna().unique())
    assert levels == {0, 1, 2, 3, 4, 5, 6, 7, 8, 9}


def test_silver_adjacency_row_count(silver_adjacency: pd.DataFrame) -> None:
    assert len(silver_adjacency) == config.EXPECTED_ADJACENCY_COUNT


def test_silver_adjacency_columns(silver_adjacency: pd.DataFrame) -> None:
    for col in (
        "source_object_id",
        "target_object_id",
        "relation_type",
        "distance_m",
        "overlap_volume_m3",
    ):
        assert col in silver_adjacency.columns


def test_silver_adjacency_relation_types(silver_adjacency: pd.DataFrame) -> None:
    types = set(silver_adjacency["relation_type"].unique())
    assert types <= {"overlap", "touch", "neartouch"}


def test_silver_hierarchy_row_count(silver_hierarchy: pd.DataFrame) -> None:
    assert len(silver_hierarchy) == config.EXPECTED_OBJECT_COUNT


def test_silver_hierarchy_root_is_null(silver_hierarchy: pd.DataFrame) -> None:
    # Exactly one object has no parent (the root)
    null_parents = silver_hierarchy["parent_id"].isna().sum()
    assert null_parents == 1
    # That object must be at level 0
    root = silver_hierarchy[silver_hierarchy["parent_id"].isna()]
    assert root["level"].iloc[0] == 0


def test_silver_hierarchy_no_empty_guid(silver_hierarchy: pd.DataFrame) -> None:
    # Empty GUID sentinel should be converted to None, never appear as value
    assert (silver_hierarchy["parent_id"] == EMPTY_GUID).sum() == 0


def test_silver_connected_groups_row_count(silver_groups: pd.DataFrame) -> None:
    assert len(silver_groups) == config.EXPECTED_CONNECTED_GROUPS


def test_silver_connected_groups_giant(silver_groups: pd.DataFrame) -> None:
    assert silver_groups["group_size"].max() == config.EXPECTED_GIANT_GROUP_SIZE


# ---------------------------------------------------------------------------
# Gold layer integration tests
# ---------------------------------------------------------------------------


def test_gold_row_count(gold_objects: pd.DataFrame) -> None:
    assert len(gold_objects) == config.EXPECTED_OBJECT_COUNT


def test_gold_has_lineage_columns(gold_objects: pd.DataFrame) -> None:
    for col in (
        "original_class",
        "refined_class",
        "refining_rule",
        "refining_rule_version",
        "ingested_at_utc",
    ):
        assert col in gold_objects.columns


def test_gold_lineage_rule_constant(gold_objects: pd.DataFrame) -> None:
    assert (gold_objects["refining_rule"] == REFINING_RULE).all()
    assert (gold_objects["refining_rule_version"] == REFINING_RULE_VERSION).all()


def test_gold_original_equals_refined_initially(gold_objects: pd.DataFrame) -> None:
    # In Phase 1a, refined_class is initialized to original_class
    # (downstream phases may override refined_class)
    assert (gold_objects["original_class"] == gold_objects["refined_class"]).all()


def test_gold_has_flags(gold_objects: pd.DataFrame) -> None:
    for col in (
        "is_container",
        "is_bbox_placeholder",
        "is_analysis_volume",
        "has_own_geometry",
        "graph_participant",
    ):
        assert col in gold_objects.columns
        assert gold_objects[col].dtype == bool


def test_gold_flag_counts(gold_objects: pd.DataFrame) -> None:
    # Based on empirically verified values for 2026-04-07 snapshot
    assert gold_objects["is_container"].sum() == 3353  # same as giant group complement
    assert gold_objects["is_bbox_placeholder"].sum() == 671
    assert gold_objects["is_analysis_volume"].sum() == 145
    assert gold_objects["has_own_geometry"].sum() == 7985


def test_gold_parent_id_coverage(gold_objects: pd.DataFrame) -> None:
    # Exactly one null parent (the root)
    assert gold_objects["parent_id"].notna().sum() == 12008
    assert gold_objects["parent_id"].isna().sum() == 1


def test_gold_has_centroid_for_all(gold_objects: pd.DataFrame) -> None:
    assert gold_objects["centroid_x"].notna().all()
    assert gold_objects["centroid_y"].notna().all()
    assert gold_objects["centroid_z"].notna().all()


def test_gold_has_group_for_all(gold_objects: pd.DataFrame) -> None:
    assert gold_objects["group_id"].notna().all()
    assert gold_objects["group_size"].notna().all()


def test_gold_si_units_parsed(gold_objects: pd.DataFrame) -> None:
    # Empirical parse counts from the 2026-04-07 snapshot
    assert gold_objects["dry_weight_kg"].notna().sum() == 5135
    assert gold_objects["length_m"].notna().sum() == 1690
    assert gold_objects["design_pressure_kpa"].notna().sum() == 2356
    assert gold_objects["design_temperature_c"].notna().sum() == 2356
    assert gold_objects["npd_end1_m"].notna().sum() == 2926


def test_gold_title_fallback(gold_objects: pd.DataFrame) -> None:
    # Every row must have a non-empty title (Foundry requirement)
    assert gold_objects["title"].notna().all()
    assert (gold_objects["title"].str.len() > 0).all()


# ---------------------------------------------------------------------------
# Unit tests for pure helpers
# ---------------------------------------------------------------------------


class TestAddFlags:
    def test_is_container_detected(self) -> None:
        df = pd.DataFrame(
            {
                "mesh_quality": ["skipped_container", "full_mesh"],
                "adjacency_count": [0, 5],
                "has_real_mesh": [False, True],
                "display_name": ["A", "B"],
            }
        )
        out = add_flags(df)
        assert out["is_container"].tolist() == [True, False]

    def test_is_container_needs_both_conditions(self) -> None:
        # skipped_container but has adjacencies → NOT container
        df = pd.DataFrame(
            {
                "mesh_quality": ["skipped_container"],
                "adjacency_count": [1],
                "has_real_mesh": [False],
                "display_name": ["X"],
            }
        )
        assert not add_flags(df)["is_container"].iloc[0]

    def test_is_analysis_volume(self) -> None:
        df = pd.DataFrame(
            {
                "mesh_quality": ["full_mesh", "full_mesh"],
                "adjacency_count": [10, 10],
                "has_real_mesh": [True, True],
                "display_name": ["Insulation Volume-001", "Beam-002"],
            }
        )
        out = add_flags(df)
        assert out["is_analysis_volume"].tolist() == [True, False]

    def test_graph_participant_excludes_flagged(self) -> None:
        df = pd.DataFrame(
            {
                "mesh_quality": ["skipped_container", "box_placeholder", "full_mesh"],
                "adjacency_count": [0, 5, 10],
                "has_real_mesh": [False, False, True],
                "display_name": ["A", "B", "C"],
            }
        )
        out = add_flags(df)
        assert out["graph_participant"].tolist() == [False, False, True]


class TestAddTitle:
    def test_uses_display_name_when_present(self) -> None:
        df = pd.DataFrame(
            {"object_id": ["id-1", "id-2"], "display_name": ["Pipe-1", "Valve-1"]}
        )
        assert add_title(df)["title"].tolist() == ["Pipe-1", "Valve-1"]

    def test_falls_back_to_object_id(self) -> None:
        df = pd.DataFrame(
            {"object_id": ["id-1", "id-2"], "display_name": [None, ""]}
        )
        assert add_title(df)["title"].tolist() == ["id-1", "id-2"]

    def test_mixed(self) -> None:
        df = pd.DataFrame(
            {"object_id": ["a", "b", "c"], "display_name": ["Real", None, "   "]}
        )
        result = add_title(df)["title"].tolist()
        assert result == ["Real", "b", "c"]


class TestAdjacencySymmetricClosure:
    def test_doubles_row_count(self) -> None:
        adj = pd.DataFrame(
            {
                "source_object_id": ["a", "c"],
                "target_object_id": ["b", "d"],
                "source_name": ["A", "C"],
                "target_name": ["B", "D"],
                "distance_m": [1.0, 2.0],
                "overlap_volume_m3": [0.1, 0.2],
                "relation_type": ["overlap", "touch"],
                "source_category": ["X", "Y"],
                "target_category": ["Y", "Z"],
                "tolerance_m": [0.15, 0.15],
            }
        )
        out = add_adjacency_symmetric_closure(adj)
        assert len(out) == 4
        # Original + reversed
        assert set(zip(out["source_object_id"], out["target_object_id"])) == {
            ("a", "b"),
            ("b", "a"),
            ("c", "d"),
            ("d", "c"),
        }


class TestAnalysisVolumePatterns:
    def test_insulation_volume_included(self) -> None:
        assert "Insulation Volume" in ANALYSIS_VOLUME_PATTERNS

    def test_obstruction_volume_included(self) -> None:
        assert "Obstruction Volume" in ANALYSIS_VOLUME_PATTERNS


class TestLoadHierarchy:
    def test_returns_all_rows(self) -> None:
        df = load_hierarchy_from_all_properties()
        assert len(df) == config.EXPECTED_OBJECT_COUNT

    def test_columns(self) -> None:
        df = load_hierarchy_from_all_properties()
        assert list(df.columns) == ["object_id", "parent_id", "level"]

    def test_empty_guid_converted_to_none(self) -> None:
        df = load_hierarchy_from_all_properties()
        assert (df["parent_id"] == EMPTY_GUID).sum() == 0
        assert df["parent_id"].isna().sum() == 1  # exactly one root
