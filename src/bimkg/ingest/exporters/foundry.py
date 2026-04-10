"""Generate Palantir Foundry Object Type + Link Type parquet outputs.

Output location: ``data/ontology/2026-04-07/``

Structure::

    ontology/2026-04-07/
      object_types/
        piping.parquet         PipingComponent
        structural.parquet     StructuralMember
        equipment.parquet      Equipment
        electrical.parquet     ElectricalComponent
        hvac.parquet           HvacComponent
        other.parquet          OtherObject
      link_types/
        adjacent_to.parquet    AdjacentTo (symmetric)
        has_parent.parquet     HasParent
        belongs_to_pipeline.parquet  BelongsToPipeline
        in_group.parquet       InConnectedGroup

Design decisions
----------------

1. **Object Types: all-in-one columns.** Every class-specific parquet file
   keeps all 216 Gold columns (dropped rows are the only difference). This
   lets Foundry users decide the column filter and Property Set layout at
   the platform level rather than being forced by us up-front.

2. **Link Type symmetry: single direction + flag.** ``adjacent_to.parquet``
   stores each edge once (the producer output, 110,173 rows). In Foundry
   the Link Type is marked symmetric; we do not duplicate the reversed edge.

3. **All-in-one column schema** is identical across the 6 files so Foundry
   can treat them uniformly when joining or running cross-class queries.
"""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

import pandas as pd

from bimkg import config
from bimkg.ingest.clean import build_bim_adjacency_silver

# ---------------------------------------------------------------------------
# Object Type mapping
# ---------------------------------------------------------------------------

#: Map ``refined_class`` → (filename, Foundry Object Type name).
OBJECT_TYPE_MAP: dict[str, tuple[str, str]] = {
    "Piping": ("piping.parquet", "PipingComponent"),
    "Structure": ("structural.parquet", "StructuralMember"),
    "Equipment": ("equipment.parquet", "Equipment"),
    "Electrical": ("electrical.parquet", "ElectricalComponent"),
    "HVAC": ("hvac.parquet", "HvacComponent"),
    "Other": ("other.parquet", "OtherObject"),
}


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------


class FoundryExportSummary(TypedDict):
    object_types_dir: str
    link_types_dir: str
    object_type_rows: dict[str, int]
    link_adjacent_to_rows: int
    link_has_parent_rows: int
    link_belongs_to_pipeline_rows: int
    link_in_group_rows: int


# ---------------------------------------------------------------------------
# Object Type builders
# ---------------------------------------------------------------------------


def build_object_types(gold: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Split the Gold table into one DataFrame per ``refined_class``.

    Returns a dict keyed by the canonical filename (not the full path).
    Each value is a full 216-column slice of the Gold table.
    """
    out: dict[str, pd.DataFrame] = {}
    for class_name, (filename, _type_name) in OBJECT_TYPE_MAP.items():
        slice_df = gold[gold["refined_class"] == class_name].reset_index(drop=True)
        out[filename] = slice_df
    return out


# ---------------------------------------------------------------------------
# Link Type builders
# ---------------------------------------------------------------------------


def build_link_adjacent_to(adj_silver: pd.DataFrame) -> pd.DataFrame:
    """Producer adjacency edges as a Link Type dataset.

    Columns: ``source_object_id``, ``target_object_id``, ``relation_type``,
    ``distance_m``, ``overlap_volume_m3``, ``tolerance_m``, ``is_symmetric``.

    The ``is_symmetric`` column is constant True to document that Foundry
    should treat the Link Type as symmetric regardless of direction.
    """
    out = adj_silver[
        [
            "source_object_id",
            "target_object_id",
            "relation_type",
            "distance_m",
            "overlap_volume_m3",
            "tolerance_m",
        ]
    ].copy()
    out["is_symmetric"] = True
    return out.reset_index(drop=True)


def build_link_has_parent(gold: pd.DataFrame) -> pd.DataFrame:
    """Parent-child hierarchy as a Link Type dataset.

    Excludes the root (its ``parent_id`` is NULL after empty-GUID
    normalization in Phase 1a). Result: 12,008 rows.

    Columns: ``child_object_id``, ``parent_object_id``, ``child_level``.
    """
    out = gold[gold["parent_id"].notna()][
        ["object_id", "parent_id", "level"]
    ].rename(
        columns={
            "object_id": "child_object_id",
            "parent_id": "parent_object_id",
            "level": "child_level",
        }
    )
    return out.reset_index(drop=True)


def build_link_belongs_to_pipeline(gold: pd.DataFrame) -> pd.DataFrame:
    """Piping objects with a non-null pipeline as a Link Type dataset.

    Columns: ``object_id``, ``pipeline_name``, ``pipe_run_name``.

    The target side (``pipeline_name``) is a string rather than a reference
    to a Pipeline object — in Foundry you would materialize a Pipeline
    Object Type in Phase 2 and replace this column with a proper FK.
    """
    piping_mask = (
        (gold["refined_class"] == "Piping")
        & gold["sp3d_pipeline"].notna()
        & (gold["sp3d_pipeline"] != "")
    )
    out = gold[piping_mask][
        ["object_id", "sp3d_pipeline", "sp3d_pipe_run"]
    ].rename(
        columns={
            "sp3d_pipeline": "pipeline_name",
            "sp3d_pipe_run": "pipe_run_name",
        }
    )
    return out.reset_index(drop=True)


def build_link_in_group(gold: pd.DataFrame) -> pd.DataFrame:
    """Connected group membership as a Link Type dataset (12,009 rows).

    Columns: ``object_id``, ``group_id``, ``is_giant_group``.
    """
    giant_size = int(gold["group_size"].max())
    out = gold[["object_id", "group_id", "group_size"]].copy()
    out["is_giant_group"] = out["group_size"] == giant_size
    return out[["object_id", "group_id", "is_giant_group"]].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def _write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def run_foundry_export(
    gold_path: Path | None = None,
    output_dir: Path | None = None,
) -> FoundryExportSummary:
    """Build and write all Foundry Object Type and Link Type parquet files."""
    gold = pd.read_parquet(gold_path or config.ENRICHED_OBJECTS)
    adj_silver = build_bim_adjacency_silver()
    out_root = output_dir or config.DATA_ONTOLOGY

    object_types_dir = out_root / "object_types"
    link_types_dir = out_root / "link_types"
    object_types_dir.mkdir(parents=True, exist_ok=True)
    link_types_dir.mkdir(parents=True, exist_ok=True)

    # Object Types
    object_tables = build_object_types(gold)
    for filename, df in object_tables.items():
        _write_parquet(df, object_types_dir / filename)

    # Link Types
    link_adjacent_to = build_link_adjacent_to(adj_silver)
    link_has_parent = build_link_has_parent(gold)
    link_belongs_to_pipeline = build_link_belongs_to_pipeline(gold)
    link_in_group = build_link_in_group(gold)

    _write_parquet(link_adjacent_to, link_types_dir / "adjacent_to.parquet")
    _write_parquet(link_has_parent, link_types_dir / "has_parent.parquet")
    _write_parquet(
        link_belongs_to_pipeline, link_types_dir / "belongs_to_pipeline.parquet"
    )
    _write_parquet(link_in_group, link_types_dir / "in_group.parquet")

    return FoundryExportSummary(
        object_types_dir=str(object_types_dir),
        link_types_dir=str(link_types_dir),
        object_type_rows={
            filename: len(df) for filename, df in object_tables.items()
        },
        link_adjacent_to_rows=len(link_adjacent_to),
        link_has_parent_rows=len(link_has_parent),
        link_belongs_to_pipeline_rows=len(link_belongs_to_pipeline),
        link_in_group_rows=len(link_in_group),
    )
