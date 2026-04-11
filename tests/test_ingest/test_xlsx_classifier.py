"""Tests for bimkg.ingest.xlsx_classifier.

Unit tests cover the 3-tier classification logic. Integration tests load the
actual 2026-04-07 AllProperties CSV, run the Python classifier independently,
and verify 100% agreement with the XLSX ``Class`` column.

Any disagreement between the two signals either a bug in the Python port
or an unexpected edge case in the C# original — both worth investigating.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from bimkg import config
from bimkg.ingest.xlsx_classifier import (
    clean_display_string,
    infer_class,
)

# ---------------------------------------------------------------------------
# Unit tests: clean_display_string
# ---------------------------------------------------------------------------


class TestCleanDisplayString:
    def test_strips_prefix(self) -> None:
        assert clean_display_string("DisplayString:Pipe-1-0001") == "Pipe-1-0001"

    def test_case_insensitive_prefix(self) -> None:
        assert clean_display_string("displaystring:Pipe") == "Pipe"
        assert clean_display_string("DISPLAYSTRING:Pipe") == "Pipe"

    def test_trims_whitespace(self) -> None:
        assert clean_display_string("DisplayString:  Pipe  ") == "Pipe"

    def test_no_prefix_passthrough(self) -> None:
        assert clean_display_string("Pipe-1-0001") == "Pipe-1-0001"

    def test_empty(self) -> None:
        assert clean_display_string("") == ""
        assert clean_display_string(None) == ""


# ---------------------------------------------------------------------------
# Unit tests: Tier 1 - explicit Class property
# ---------------------------------------------------------------------------


class TestTier1ExplicitClass:
    def test_direct_class_property(self) -> None:
        props = {"항목|Class": "Piping"}
        assert infer_class(props) == "Piping"

    def test_class_display_name(self) -> None:
        props = {"SmartPlant 3D|ClassDisplayName": "Equipment"}
        assert infer_class(props) == "Equipment"

    def test_display_string_prefix_stripped(self) -> None:
        props = {"Item|Class": "DisplayString:Structure"}
        assert infer_class(props) == "Structure"

    def test_class_without_category(self) -> None:
        props = {"Class": "HVAC"}
        assert infer_class(props) == "HVAC"

    def test_empty_class_falls_through(self) -> None:
        # Empty Class value → fall through to Tier 2/3
        props = {"Class": "", "SmartPlant 3D|Pipeline": "P-001"}
        assert infer_class(props) == "Piping"

    def test_meta_keys_ignored(self) -> None:
        # __-prefixed keys should not be evaluated
        props = {"__Class": "ShouldBeIgnored", "SmartPlant 3D|Pipeline": "P"}
        assert infer_class(props) == "Piping"


# ---------------------------------------------------------------------------
# Unit tests: Tier 2 - property key inference
# ---------------------------------------------------------------------------


class TestTier2PropertyKeys:
    def test_pipeline_property_wins(self) -> None:
        props = {"SmartPlant 3D|Pipeline": "P-001"}
        assert infer_class(props) == "Piping"

    def test_piperun_triggers_piping(self) -> None:
        props = {"SmartPlant 3D|PipeRun": "PR-001"}
        assert infer_class(props) == "Piping"

    def test_piping_word_in_key_triggers(self) -> None:
        props = {"SmartPlant 3D|Piping Spec": "150#"}
        assert infer_class(props) == "Piping"

    def test_equipment_property(self) -> None:
        props = {"SmartPlant 3D|Equipment Name": "V-101"}
        assert infer_class(props) == "Equipment"

    def test_eqp_type_triggers_equipment(self) -> None:
        props = {"SmartPlant 3D|Eqp Type 0": "Vessel"}
        assert infer_class(props) == "Equipment"

    def test_piping_wins_over_equipment(self) -> None:
        # Both pipeline and equipment properties: Piping wins
        props = {
            "SmartPlant 3D|Pipeline": "P-001",
            "SmartPlant 3D|Equipment Name": "V-101",
        }
        assert infer_class(props) == "Piping"


# ---------------------------------------------------------------------------
# Unit tests: Tier 3 - keyword substring matching
# ---------------------------------------------------------------------------


class TestTier3Keywords:
    def test_piping_keyword_in_display_name(self) -> None:
        assert infer_class({}, display_name="Valve-1-0042") == "Piping"

    def test_equipment_keyword_in_sys_path(self) -> None:
        # "equipment" keyword matches EQUIPMENT_KEYWORDS → Equipment
        # Note: piping is evaluated first, but no piping keyword is present.
        assert infer_class(
            {}, sys_path="TRAINING\\A2\\U04\\Equipment\\Widget"
        ) == "Equipment"

    def test_vessel_keyword_equipment(self) -> None:
        assert infer_class({}, display_name="Vessel-1-0001") == "Equipment"

    def test_beam_keyword_structure(self) -> None:
        # PR #3 (word boundaries): "Beam-1-0042" has non-word char after "Beam"
        # so \bbeam\b matches. Compound underscore words like "Beam_Block" would
        # NOT match because "_" is a word char — this was the old behavior.
        assert infer_class({}, display_name="Beam-1-0042") == "Structure"

    def test_cable_keyword_electrical(self) -> None:
        # PR #3: "Cable Tray" has whitespace so both "cable" and "tray" match
        # individually. Compound "Cableway" would NOT match \bcable\b.
        assert infer_class({}, display_name="Cable Tray-1") == "Electrical"

    def test_duct_keyword_hvac(self) -> None:
        assert infer_class({}, display_name="Duct Part 1") == "HVAC"

    def test_instrument_keyword(self) -> None:
        assert infer_class({}, display_name="Instrument Housing") == "Instrumentation"

    def test_piping_priority_over_structure(self) -> None:
        # PR #3: "Pipe-Beam-1" has whitespace-free hyphen separators.
        # \bpipe\b matches "Pipe" (word boundary at "-"), so Piping wins
        # via Tier 3 ordering (Piping evaluated before Structure).
        assert infer_class({}, display_name="Pipe-Beam-1") == "Piping"

    def test_pipe_rack_is_not_piping(self) -> None:
        """PR #3 negative lookahead: 'Pipe Rack' should not be Piping."""
        result = infer_class({}, display_name="Refining Pipe Rack")
        assert result != "Piping"

    def test_default_other(self) -> None:
        assert infer_class({}, display_name="Unknown Widget") == "Other"

    def test_empty_all(self) -> None:
        assert infer_class({}) == "Other"

    def test_word_boundary_rejects_underscore_compound(self) -> None:
        """PR #3: 'Beam_BlockExposed' does NOT match \\bbeam\\b because
        '_' is a word character in regex. This is the intended behavior
        aligned with DXTnavis C# regex semantics.
        """
        # "beam_blockexposed" has no word boundary between "beam" and "_block"
        result = infer_class({}, display_name="Beam_BlockExposed_All_Conc")
        assert result == "Other"


# ---------------------------------------------------------------------------
# Integration test: 100% oracle agreement with 2026-04-07 XLSX
# ---------------------------------------------------------------------------

XLSX_PATH = config.RAW_REFINING_XLSX

ALL_PROPERTIES_PATH = config.RAW_ALL_PROPERTIES


@pytest.fixture(scope="module")
def xlsx_classifications() -> pd.DataFrame:
    """Load the XLSX pivot sheet and return only the columns we need."""
    if not XLSX_PATH.exists():
        pytest.skip(f"XLSX not found at {XLSX_PATH}")
    df = pd.read_excel(XLSX_PATH, sheet_name="Refining_ObjectID_Pivot")
    return df[["ObjectId(GUID)", "Class", "DisplayName", "System Path"]].copy()


@pytest.fixture(scope="module")
def all_properties() -> pd.DataFrame:
    if not ALL_PROPERTIES_PATH.exists():
        pytest.skip(f"AllProperties CSV not found at {ALL_PROPERTIES_PATH}")
    df = pd.read_csv(ALL_PROPERTIES_PATH, encoding="utf-8", low_memory=False)
    return df


def _row_to_properties(row: pd.Series, exclude: set[str]) -> dict[str, str]:
    """Convert an AllProperties row to a property dict.

    Keeps only non-empty values, excludes meta columns, and converts NaN→"".
    """
    out: dict[str, str] = {}
    for col, val in row.items():
        if col in exclude:
            continue
        if pd.isna(val):
            continue
        s = str(val)
        if s == "" or s == "nan":
            continue
        out[col] = s
    return out


def test_oracle_100_percent_agreement(
    xlsx_classifications: pd.DataFrame,
    all_properties: pd.DataFrame,
) -> None:
    """Run Python infer_class on every object in AllProperties CSV and
    verify 100% agreement with the XLSX Class column."""

    # Columns in AllProperties that are meta (not real SP3D properties)
    meta_cols = {"ObjectId", "ParentId", "Level", "객체이름"}

    # Map XLSX classifications by ObjectId for O(1) lookup
    xlsx_map = dict(
        zip(
            xlsx_classifications["ObjectId(GUID)"],
            xlsx_classifications["Class"],
        )
    )
    xlsx_display = dict(
        zip(
            xlsx_classifications["ObjectId(GUID)"],
            xlsx_classifications["DisplayName"],
        )
    )
    xlsx_syspath = dict(
        zip(
            xlsx_classifications["ObjectId(GUID)"],
            xlsx_classifications["System Path"].fillna(""),
        )
    )

    total = 0
    agree = 0
    disagreements: list[tuple[str, str, str, str]] = []

    for _, row in all_properties.iterrows():
        obj_id = row.get("ObjectId")
        if pd.isna(obj_id) or obj_id not in xlsx_map:
            continue

        expected = xlsx_map[obj_id]
        # Use XLSX's already-computed display name and system path as inputs,
        # since that is what the C# code saw when it ran.
        display_name = xlsx_display.get(obj_id, "") or ""
        sys_path = xlsx_syspath.get(obj_id, "") or ""

        props = _row_to_properties(row, exclude=meta_cols)
        actual = infer_class(props, sys_path=sys_path, display_name=display_name)

        total += 1
        if actual == expected:
            agree += 1
        elif len(disagreements) < 20:
            disagreements.append((str(obj_id), str(expected), str(actual), display_name))

    assert total > 0, "No objects found in the cross-reference"
    agreement_rate = agree / total
    print(f"\nTotal: {total}, Agree: {agree}, Rate: {agreement_rate:.4%}")

    if disagreements:
        print("\nFirst 20 disagreements:")
        for obj_id, expected, actual, name in disagreements:
            print(f"  {obj_id[:8]}... | expected={expected:10} actual={actual:10} | {name}")

    assert agreement_rate == 1.0, (
        f"Expected 100% agreement with XLSX oracle, got {agreement_rate:.4%} "
        f"({total - agree} disagreements out of {total})"
    )
