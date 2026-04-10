"""Tests for bimkg.ingest.xlsx_loader."""

from __future__ import annotations

import pandas as pd
import pytest

from bimkg import config
from bimkg.ingest.xlsx_loader import (
    EXPLICIT_RENAMES,
    _snake_case,
    load_xlsx_pivot,
    normalize_column_name,
    normalize_columns,
)

# ---------------------------------------------------------------------------
# Unit: _snake_case
# ---------------------------------------------------------------------------


class TestSnakeCase:
    def test_simple_word(self) -> None:
        assert _snake_case("Pipe") == "pipe"

    def test_camel_case(self) -> None:
        assert _snake_case("PipeRun") == "pipe_run"

    def test_pascal_case(self) -> None:
        assert _snake_case("DryCGX") == "dry_cgx"

    def test_all_upper(self) -> None:
        assert _snake_case("NPD") == "npd"

    def test_spaced(self) -> None:
        assert _snake_case("Dry Weight") == "dry_weight"

    def test_spaced_with_digit(self) -> None:
        assert _snake_case("Eqp Type 0") == "eqp_type_0"

    def test_mixed_case_spaced(self) -> None:
        assert _snake_case("BOM description") == "bom_description"

    def test_special_chars(self) -> None:
        assert _snake_case("Is-A_Thing") == "is_a_thing"

    def test_repeated_underscores(self) -> None:
        assert _snake_case("foo__bar") == "foo_bar"

    def test_leading_trailing(self) -> None:
        assert _snake_case("_foo_") == "foo"


# ---------------------------------------------------------------------------
# Unit: normalize_column_name
# ---------------------------------------------------------------------------


class TestNormalizeColumnName:
    def test_meta_class(self) -> None:
        assert normalize_column_name("Class") == "class_raw"

    def test_meta_object_id(self) -> None:
        assert normalize_column_name("ObjectId(GUID)") == "object_id"

    def test_sp3d_prefix(self) -> None:
        assert normalize_column_name("SmartPlant 3D|Dry Weight") == "sp3d_dry_weight"

    def test_sp3d_camel_case(self) -> None:
        assert normalize_column_name("SmartPlant 3D|DryCGX") == "sp3d_dry_cgx"

    def test_sp3d_acronym(self) -> None:
        assert normalize_column_name("SmartPlant 3D|NPD") == "sp3d_npd"

    def test_sp3d_eqp_type(self) -> None:
        assert normalize_column_name("SmartPlant 3D|Eqp Type 0") == "sp3d_eqp_type_0"

    def test_sp3d_pipe_run(self) -> None:
        assert normalize_column_name("SmartPlant 3D|PipeRun") == "sp3d_pipe_run"

    def test_nav_item(self) -> None:
        assert normalize_column_name("항목|GUID") == "nav_item_guid"

    def test_nav_material(self) -> None:
        assert normalize_column_name("재질|분산.빨간색") == "nav_material_diffuse_r"

    def test_nav_geom(self) -> None:
        assert normalize_column_name("형상|삼각형") == "nav_geom_triangles"

    def test_unknown_prefix_fallback(self) -> None:
        # Unknown category should still produce something usable
        result = normalize_column_name("Unknown|Foo Bar")
        assert "unknown" in result
        assert "foo_bar" in result


# ---------------------------------------------------------------------------
# Unit: normalize_columns (collision detection)
# ---------------------------------------------------------------------------


class TestNormalizeColumns:
    def test_basic(self) -> None:
        df = pd.DataFrame(
            {"Class": [1], "ObjectId(GUID)": ["x"], "SmartPlant 3D|Dry Weight": [1]}
        )
        result = normalize_columns(df)
        assert list(result.columns) == [
            "class_raw",
            "object_id",
            "sp3d_dry_weight",
        ]

    def test_collision_raises(self) -> None:
        # Two columns that normalize to the same name
        df = pd.DataFrame({"Dry Weight": [1], "dry_weight": [2]})
        with pytest.raises(ValueError, match="collisions"):
            normalize_columns(df)


# ---------------------------------------------------------------------------
# Integration: full XLSX load against 2026-04-07 snapshot
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def xlsx_df() -> pd.DataFrame:
    if not config.RAW_REFINING_XLSX.exists():
        pytest.skip(f"XLSX not found at {config.RAW_REFINING_XLSX}")
    return load_xlsx_pivot(config.RAW_REFINING_XLSX)


def test_load_xlsx_shape(xlsx_df: pd.DataFrame) -> None:
    assert xlsx_df.shape == (config.EXPECTED_OBJECT_COUNT, 135)


def test_load_xlsx_has_meta_columns(xlsx_df: pd.DataFrame) -> None:
    for col in ["class_raw", "object_id", "display_name", "system_path", "level"]:
        assert col in xlsx_df.columns


def test_load_xlsx_no_pipe_in_columns(xlsx_df: pd.DataFrame) -> None:
    # All columns should be snake_case, no literal "|" remaining
    for col in xlsx_df.columns:
        assert "|" not in col, f"Column still has pipe: {col!r}"


def test_load_xlsx_no_korean_in_columns(xlsx_df: pd.DataFrame) -> None:
    # All Korean-prefixed columns should be translated
    for col in xlsx_df.columns:
        # No Hangul characters (U+AC00-U+D7AF range)
        has_hangul = any("\uac00" <= ch <= "\ud7af" for ch in col)
        assert not has_hangul, f"Column still has Korean: {col!r}"


def test_load_xlsx_class_distribution(xlsx_df: pd.DataFrame) -> None:
    # Six expected classes from the XLSX snapshot
    counts = xlsx_df["class_raw"].value_counts().to_dict()
    assert counts["Structure"] == 5926
    assert counts["Piping"] == 4014
    assert counts["Equipment"] == 851
    assert counts["Other"] == 697
    assert counts["Electrical"] == 449
    assert counts["HVAC"] == 72


def test_load_xlsx_unique_object_ids(xlsx_df: pd.DataFrame) -> None:
    assert xlsx_df["object_id"].nunique() == config.EXPECTED_OBJECT_COUNT
    assert xlsx_df["object_id"].notna().all()


def test_explicit_renames_all_different(xlsx_df: pd.DataFrame) -> None:
    # Every explicit rename target must be unique
    targets = list(EXPLICIT_RENAMES.values())
    assert len(targets) == len(set(targets))
