"""Build Silver and Gold tables from the 2026-04-07 raw sources.

The Silver layer is a 1:1 typed version of each raw source (Parquet-ready,
snake_case columns, strict types). The Gold layer is ``bim_objects_enriched``:
XLSX + validation + geometry + connected_groups joined together, with
derived flags, SI-unit parsing (reusing ``unit_parser``), title fallback,
and a 4-column lineage scheme.

Entry points::

    build_bim_objects_silver()         -> 12,009 rows, 135 columns (XLSX only)
    build_bim_adjacency_silver()       -> 110,173 rows (producer adjacency)
    build_bim_connected_groups_silver()->  3,355 rows (one per group)
    build_bim_hierarchy_silver()       -> 12,009 rows (object_id, parent_id, level)

    build_bim_objects_gold()           -> 12,009 rows, ~175 columns
                                          (Silver + validation + geometry +
                                           group stats + flags + SI units +
                                           lineage + title)

Enrichment sources
------------------
- ``validation.csv`` is the richest metadata file: it provides ``ParentId``,
  ``GroupId``, ``MeshQuality``, ``HasRealMesh``, ``AdjacencyCount``, ``Verdict``
  and more. This replaces any need to join from ``AllProperties.csv`` for
  Phase 1a.
- ``geometry.csv`` is the only source for ``CentroidX/Y/Z`` and ``MinX/Y/Z``/
  ``MaxX/Y/Z`` coordinates.
- ``connected_groups.csv`` provides per-group statistics (size, BBox,
  centroid). We join on ``group_id`` and drop the giant semicolon-delimited
  ``MemberObjectIds`` column since object-to-group membership comes from
  ``validation.group_id``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from bimkg import config
from bimkg.ingest.unit_parser import (
    parse_length,
    parse_npd,
    parse_pressure,
    parse_temperature,
    parse_weight,
)
from bimkg.ingest.xlsx_loader import load_xlsx_pivot

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REFINING_RULE: str = "xlsx_refined_exporter"
REFINING_RULE_VERSION: str = "DXTnavis@main (snapshot 20260407-192047)"

#: Sentinel GUID used by DXTnavis to mark "no parent" (root object).
#: We convert this to ``None`` so ``parent_id IS NULL`` queries work correctly.
EMPTY_GUID: str = "00000000-0000-0000-0000-000000000000"

#: Display-name substrings that mark an object as an engineering analysis
#: volume (e.g. insulation thickness envelope) rather than a physical part.
#: These objects keep their original ``refined_class`` but are excluded from
#: the adjacency graph via ``graph_participant=False``.
ANALYSIS_VOLUME_PATTERNS: tuple[str, ...] = (
    "Insulation Volume",
    "Obstruction Volume",
    "Fireproofing Volume",
    "Acoustic Volume",
)

# ---------------------------------------------------------------------------
# Ancillary CSV column renames
# ---------------------------------------------------------------------------

GEOMETRY_RENAMES: dict[str, str] = {
    "ObjectId": "object_id",
    # Drop DisplayName and Category (duplicates of XLSX fields, unreliable)
    "MinX": "bbox_min_x",
    "MinY": "bbox_min_y",
    "MinZ": "bbox_min_z",
    "MaxX": "bbox_max_x",
    "MaxY": "bbox_max_y",
    "MaxZ": "bbox_max_z",
    "CentroidX": "centroid_x",
    "CentroidY": "centroid_y",
    "CentroidZ": "centroid_z",
    "Volume": "bbox_volume_m3",
    "HasMesh": "has_mesh_geom",  # duplicated in validation; kept for audit
    "MeshUri": "mesh_uri",
    "MeshQuality": "mesh_quality_geom",  # dup of validation; primary source is validation
    "VertexCount": "vertex_count_geom",
    "TriangleCount": "triangle_count_geom",
}

GEOMETRY_DROP_COLS: tuple[str, ...] = ("DisplayName", "Category")

VALIDATION_RENAMES: dict[str, str] = {
    "ObjectId": "object_id",
    "ClassDisplayName": "nav_class_display_name",
    # ParentId is dropped — validation.csv only populates it for 294/12,009
    # rows. The authoritative source is AllProperties.csv (see
    # load_hierarchy_from_all_properties).
    "Level": "level_val",  # avoid collision with XLSX level
    "IsLeaf": "is_leaf",
    "ChildCount": "child_count",
    "HasGeometry": "has_geometry",
    "IsHidden": "is_hidden",
    "HasGeometryProperty": "has_geometry_property",
    "GeoP_Primitives": "geop_primitives",
    "GeoP_HasTriangles": "geop_has_triangles",
    "GeoP_HasLines": "geop_has_lines",
    "GeoP_Solid": "geop_solid",
    "GeoP_HasText": "geop_has_text",
    "GeoP_HasSnapPoints": "geop_has_snap_points",
    "GeoP_HasPoints": "geop_has_points",
    "GeoP_Fragments": "geop_fragments",
    "HasBBox": "has_bbox",
    "BBoxVolume": "bbox_volume_val",  # dup with geometry.Volume; prefer geometry
    "ContainerStatus": "container_status",
    "TessResult": "tess_result",
    "TessFailureReason": "tess_failure_reason",
    "MeshQuality": "mesh_quality",  # PRIMARY (validation is authoritative here)
    "VertexCount": "vertex_count",
    "TriangleCount": "triangle_count",
    "AdjacencyCount": "adjacency_count",
    "GroupId": "group_id",
    "GlbExists": "glb_exists",
    "GlbSizeBytes": "glb_size_bytes",
    "HasMesh": "has_mesh",
    "HasRealMesh": "has_real_mesh",
    "Verdict": "verdict",
}

#: Columns dropped from validation.csv because they are either duplicates of
#: XLSX columns or have poor coverage in validation (parent_id is in only
#: 294/12,009 rows; the authoritative source is AllProperties.csv).
VALIDATION_DROP_COLS: tuple[str, ...] = ("DisplayName", "ParentId")

ADJACENCY_RENAMES: dict[str, str] = {
    "SourceObjectId": "source_object_id",
    "TargetObjectId": "target_object_id",
    "SourceName": "source_name",
    "TargetName": "target_name",
    "Distance": "distance_m",
    "OverlapVolume": "overlap_volume_m3",
    "RelationType": "relation_type",
    "SourceCategory": "source_category",
    "TargetCategory": "target_category",
    "Tolerance": "tolerance_m",
}

CONNECTED_GROUPS_RENAMES: dict[str, str] = {
    "GroupId": "group_id",
    "ElementCount": "group_size",
    "EdgeCount": "group_edge_count",
    "TotalVolume": "group_total_volume",
    "DominantCategory": "group_dominant_category",
    "BBoxMinX": "group_bbox_min_x",
    "BBoxMinY": "group_bbox_min_y",
    "BBoxMinZ": "group_bbox_min_z",
    "BBoxMaxX": "group_bbox_max_x",
    "BBoxMaxY": "group_bbox_max_y",
    "BBoxMaxZ": "group_bbox_max_z",
    "CentroidX": "group_centroid_x",
    "CentroidY": "group_centroid_y",
    "CentroidZ": "group_centroid_z",
}

CONNECTED_GROUPS_DROP_COLS: tuple[str, ...] = ("MemberObjectIds",)


# ---------------------------------------------------------------------------
# Raw loaders
# ---------------------------------------------------------------------------


def load_geometry(path: Path | None = None) -> pd.DataFrame:
    df = pd.read_csv(path or config.RAW_GEOMETRY)
    df = df.drop(columns=list(GEOMETRY_DROP_COLS), errors="ignore")
    return df.rename(columns=GEOMETRY_RENAMES)


def load_validation(path: Path | None = None) -> pd.DataFrame:
    df = pd.read_csv(path or config.RAW_VALIDATION)
    df = df.drop(columns=list(VALIDATION_DROP_COLS), errors="ignore")
    return df.rename(columns=VALIDATION_RENAMES)


def load_adjacency(path: Path | None = None) -> pd.DataFrame:
    df = pd.read_csv(path or config.RAW_ADJACENCY)
    return df.rename(columns=ADJACENCY_RENAMES)


def load_connected_groups(path: Path | None = None) -> pd.DataFrame:
    df = pd.read_csv(path or config.RAW_CONNECTED_GROUPS)
    df = df.drop(columns=list(CONNECTED_GROUPS_DROP_COLS), errors="ignore")
    return df.rename(columns=CONNECTED_GROUPS_RENAMES)


def load_hierarchy_from_all_properties(
    path: Path | None = None,
) -> pd.DataFrame:
    """Load (object_id, parent_id, level) from ``AllProperties.csv``.

    The empty GUID sentinel ``00000000-0000-0000-0000-000000000000`` is
    converted to ``None`` so the root object appears as ``parent_id IS NULL``
    rather than a reference to a non-existent object.

    Why this file? ``validation.csv`` only populates ``ParentId`` for 294
    of the 12,009 rows (mostly at Level 8-9), whereas ``AllProperties.csv``
    has complete coverage. ``RefinedXlsxExporter`` also drops ``ParentId``
    from its output, so this is the only authoritative source.
    """
    df = pd.read_csv(
        path or config.RAW_ALL_PROPERTIES,
        usecols=["ObjectId", "ParentId", "Level"],
        low_memory=False,
    )
    df = df.rename(
        columns={
            "ObjectId": "object_id",
            "ParentId": "parent_id",
            "Level": "level",
        }
    )
    df["parent_id"] = df["parent_id"].where(df["parent_id"] != EMPTY_GUID, None)
    df["level"] = pd.to_numeric(df["level"], errors="coerce").astype("Int64")
    return df


# ---------------------------------------------------------------------------
# Silver layer
# ---------------------------------------------------------------------------


def build_bim_objects_silver(
    xlsx_path: Path | None = None,
) -> pd.DataFrame:
    """Silver: XLSX with snake_case columns and ``level`` cast to Int64."""
    df = load_xlsx_pivot(xlsx_path or config.RAW_REFINING_XLSX)
    df["level"] = pd.to_numeric(df["level"], errors="coerce").astype("Int64")
    return df


def build_bim_adjacency_silver(
    adj_path: Path | None = None,
) -> pd.DataFrame:
    """Silver: producer adjacency edges, renamed."""
    return load_adjacency(adj_path)


def build_bim_connected_groups_silver(
    groups_path: Path | None = None,
) -> pd.DataFrame:
    """Silver: one row per connected group (3,355 rows)."""
    return load_connected_groups(groups_path)


def build_bim_hierarchy_silver(
    all_properties_path: Path | None = None,
) -> pd.DataFrame:
    """Silver: (object_id, parent_id, level) from AllProperties.csv.

    The root object (``level=0``) has ``parent_id=None`` after the empty
    GUID sentinel is stripped.
    """
    return load_hierarchy_from_all_properties(all_properties_path)


# ---------------------------------------------------------------------------
# Gold layer helpers
# ---------------------------------------------------------------------------


def add_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Derive 5 boolean flags from mesh quality / adjacency / name patterns.

    Requires columns: ``mesh_quality``, ``adjacency_count``, ``has_real_mesh``,
    ``display_name``.
    """
    out = df.copy()

    out["is_container"] = (
        (out["mesh_quality"] == "skipped_container")
        & (out["adjacency_count"].fillna(0) == 0)
    )

    out["is_bbox_placeholder"] = out["mesh_quality"] == "box_placeholder"

    pattern = "|".join(ANALYSIS_VOLUME_PATTERNS)
    out["is_analysis_volume"] = (
        out["display_name"].fillna("").str.contains(pattern, regex=True, case=False)
    )

    out["has_own_geometry"] = out["has_real_mesh"].fillna(False).astype(bool)

    out["graph_participant"] = (
        ~out["is_container"]
        & ~out["is_bbox_placeholder"]
        & ~out["is_analysis_volume"]
    )

    return out


def _parse_or_none(parser, value):
    """Apply a parser to a scalar, handling NaN and empty strings."""
    if pd.isna(value):
        return None
    s = str(value).strip()
    if not s:
        return None
    return parser(s)


def add_si_units(df: pd.DataFrame) -> pd.DataFrame:
    """Parse SP3D string columns into SI-unit numeric columns."""
    out = df.copy()

    def _apply(col_src: str, parser) -> pd.Series:
        if col_src not in out.columns:
            return pd.Series([None] * len(out), index=out.index, dtype="object")
        return out[col_src].apply(lambda v: _parse_or_none(parser, v))

    out["dry_weight_kg"] = _apply("sp3d_dry_weight", parse_weight)
    out["wet_weight_kg"] = _apply("sp3d_wet_weight", parse_weight)
    out["length_m"] = _apply("sp3d_length", parse_length)
    out["width_m"] = _apply("sp3d_width", parse_length)
    out["depth_m"] = _apply("sp3d_depth", parse_length)
    out["height_m"] = _apply("sp3d_height", parse_length)
    out["bend_radius_m"] = _apply("sp3d_bend_radius", parse_length)
    out["design_pressure_kpa"] = _apply("sp3d_design_max_pressure", parse_pressure)
    out["design_temperature_c"] = _apply("sp3d_design_max_temperature", parse_temperature)

    # NPD returns a tuple (end1_m, end2_m) or None
    def _npd_end1(v):
        r = _parse_or_none(parse_npd, v)
        return r[0] if r else None

    def _npd_end2(v):
        r = _parse_or_none(parse_npd, v)
        return r[1] if r else None

    if "sp3d_npd" in out.columns:
        out["npd_end1_m"] = out["sp3d_npd"].apply(_npd_end1)
        out["npd_end2_m"] = out["sp3d_npd"].apply(_npd_end2)
    else:
        out["npd_end1_m"] = None
        out["npd_end2_m"] = None

    return out


def add_lineage(df: pd.DataFrame) -> pd.DataFrame:
    """Add the 4-column lineage scheme + ingestion timestamp.

    ``original_class`` and ``refined_class`` are both initialized from
    ``class_raw`` (= XLSX Class). Downstream phases may override
    ``refined_class`` based on additional signals, but ``original_class``
    is immutable audit-trail.
    """
    out = df.copy()
    out["original_class"] = out["class_raw"]
    out["refined_class"] = out["class_raw"]
    out["refining_rule"] = REFINING_RULE
    out["refining_rule_version"] = REFINING_RULE_VERSION
    out["ingested_at_utc"] = datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    )
    return out


def add_title(df: pd.DataFrame) -> pd.DataFrame:
    """Set the Foundry ``title`` property: display_name with object_id fallback."""
    out = df.copy()
    raw_name = out["display_name"].fillna("").astype(str).str.strip()
    out["title"] = raw_name.where(raw_name != "", out["object_id"])
    return out


def add_adjacency_symmetric_closure(
    adj: pd.DataFrame,
) -> pd.DataFrame:
    """Return an undirected version of the adjacency table.

    For every ``(A, B)`` edge in ``adj`` with its relation_type and metrics,
    emit both ``(A, B)`` and ``(B, A)`` rows with identical metadata so
    downstream graph analytics can treat the adjacency graph as symmetric
    without special-casing direction.
    """
    reversed_df = adj.rename(
        columns={
            "source_object_id": "target_object_id",
            "target_object_id": "source_object_id",
            "source_name": "target_name",
            "target_name": "source_name",
            "source_category": "target_category",
            "target_category": "source_category",
        }
    )
    return pd.concat([adj, reversed_df], ignore_index=True)


# ---------------------------------------------------------------------------
# Gold layer
# ---------------------------------------------------------------------------


def build_bim_objects_gold(
    xlsx_path: Path | None = None,
    validation_path: Path | None = None,
    geometry_path: Path | None = None,
    groups_path: Path | None = None,
    all_properties_path: Path | None = None,
) -> pd.DataFrame:
    """Build the enriched Gold table for ``bim_objects``.

    Join order::

        XLSX (12,009)
          + parent_id (AllProperties.csv)
          + validation.csv (mesh_quality, has_real_mesh, adjacency_count, ...)
          + geometry.csv   (centroid, bbox coords)
          + connected_groups.csv (group_size, group_edge_count, ...)
          -> add_flags
          -> add_si_units
          -> add_lineage
          -> add_title
    """
    silver = build_bim_objects_silver(xlsx_path)
    hierarchy = load_hierarchy_from_all_properties(all_properties_path)[
        ["object_id", "parent_id"]
    ]
    val = load_validation(validation_path)
    geom = load_geometry(geometry_path)
    groups = build_bim_connected_groups_silver(groups_path)

    merged = silver.merge(
        hierarchy, on="object_id", how="left", validate="one_to_one"
    )
    merged = merged.merge(val, on="object_id", how="left", validate="one_to_one")
    merged = merged.merge(geom, on="object_id", how="left", validate="one_to_one")
    merged = merged.merge(
        groups, on="group_id", how="left", validate="many_to_one"
    )

    merged = add_flags(merged)
    merged = add_si_units(merged)
    merged = add_lineage(merged)
    merged = add_title(merged)

    return merged
