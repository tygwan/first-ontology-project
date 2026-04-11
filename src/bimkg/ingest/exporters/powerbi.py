"""Regenerate the 12-file Power BI star schema from the Gold tables.

Output location: ``data/powerbi/2026-04-07/``

This file replaces the legacy C#-generated bundle that now lives under
``data/backup/dxtnavis-csharp-20260411/powerbi/2026-04-07/``. The new
bundle uses the XLSX-anchored classification (6 classes instead of 5),
adds SI-unit columns, derived flags, and 4-column lineage.

Schema::

    fact_objects.csv              65 cols, 12,009 rows
      pk = object_id
      fk = group_id -> dim_group
      fk = class_raw -> dim_class
      fk = level -> dim_level
      fk = mesh_quality -> dim_meshq
      fk = verdict -> dim_verdict
      fk = sp3d_pipeline -> dim_pipeline (nullable)

    fact_adjacency.csv            110,173 rows (directed, producer-based)
    fact_adjacency_undirected.csv 110,173 rows (pair-deduplicated)
    bridge_group_member.csv       12,009 rows (object <-> group)

    dim_class.csv                  6 rows  (Piping, Structure, ...)
    dim_level.csv                 10 rows  (Level 0-9)
    dim_pipeline.csv             147 rows  (Pipeline names + summary)
    dim_meshq.csv                  5 rows  (MeshQuality values)
    dim_verdict.csv                5 rows  (Verdict values)
    dim_group.csv              3,355 rows  (Connected group stats)

    README.md                     Human-readable schema explanation

Removed from legacy (no schedule data in Phase 1a):
    - fact_schedule_links.csv
    - dim_task.csv
"""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

import pandas as pd

from bimkg import config
from bimkg.ingest.clean import (
    build_bim_adjacency_silver,
    build_bim_connected_groups_silver,
)

# ---------------------------------------------------------------------------
# Curated column list for fact_objects.csv
# ---------------------------------------------------------------------------

#: 65 columns picked from the 216-column Gold table for fact_objects.csv.
#: The selection prioritizes business-relevant fields: IDs, classification,
#: pipeline/equipment attributes, geometry coordinates, mesh validation,
#: SI-unit parsed quantities, derived flags, group membership, and lineage.
#:
#: ``in_giant_group`` is derived at export time as ``group_size == giant``.
FACT_OBJECTS_COLUMNS: list[str] = [
    # 식별 (6)
    "object_id",
    "title",
    "display_name",
    "parent_id",
    "level",
    "system_path",
    # 분류 (5)
    "class_raw",
    "refined_class",
    "original_class",
    "nav_class_display_name",
    "nav_item_type",
    # 배관 (6)
    "sp3d_pipeline",
    "sp3d_pipe_run",
    "sp3d_npd",
    "sp3d_spec_name",
    "sp3d_specification",
    "sp3d_flow_direction",
    # 장비 (5)
    "sp3d_equipment_name",
    "sp3d_eqp_type_0",
    "sp3d_eqp_type_1",
    "sp3d_eqp_type_2",
    "sp3d_eqp_type_3",
    # 자재 (4)
    "sp3d_material",
    "sp3d_material_grade",
    "sp3d_material_name",
    "sp3d_material_type",
    # 시공 (3)
    "sp3d_construction_type",
    "sp3d_status",
    "sp3d_location",
    # 기하 (9)
    "centroid_x",
    "centroid_y",
    "centroid_z",
    "bbox_min_x",
    "bbox_min_y",
    "bbox_min_z",
    "bbox_max_x",
    "bbox_max_y",
    "bbox_max_z",
    # 메시/검증 (5)
    "mesh_quality",
    "verdict",
    "has_real_mesh",
    "vertex_count",
    "triangle_count",
    # SI 단위 (9)
    "dry_weight_kg",
    "wet_weight_kg",
    "length_m",
    "width_m",
    "depth_m",
    "design_pressure_kpa",
    "design_temperature_c",
    "npd_end1_m",
    "npd_end2_m",
    # 플래그 (5)
    "is_container",
    "is_bbox_placeholder",
    "is_analysis_volume",
    "has_own_geometry",
    "graph_participant",
    # 그룹 (3) — in_giant_group is derived
    "group_id",
    "group_size",
    # lineage (5)
    "refining_rule",
    "refining_rule_version",
    "ingested_at_utc",
    "adjacency_count",
    "child_count",
    # classification confidence (2) — Phase 1e addition
    "classification_confidence",
    "classification_confidence_reason",
]


# ---------------------------------------------------------------------------
# Dim class color mapping (for consistent Power BI visuals)
# ---------------------------------------------------------------------------

CLASS_COLORS: dict[str, str] = {
    "Piping": "#1f77b4",
    "Structure": "#ff7f0e",
    "Equipment": "#2ca02c",
    "Electrical": "#d62728",
    "HVAC": "#9467bd",
    "Other": "#7f7f7f",
}

CLASS_ORDER: dict[str, int] = {
    "Piping": 1,
    "Structure": 2,
    "Equipment": 3,
    "Electrical": 4,
    "HVAC": 5,
    "Other": 6,
}


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------


class PowerBIExportSummary(TypedDict):
    output_dir: str
    fact_objects_rows: int
    fact_adjacency_rows: int
    fact_adjacency_undirected_rows: int
    bridge_group_member_rows: int
    dim_class_rows: int
    dim_level_rows: int
    dim_pipeline_rows: int
    dim_meshq_rows: int
    dim_verdict_rows: int
    dim_group_rows: int


# ---------------------------------------------------------------------------
# Table builders
# ---------------------------------------------------------------------------


def build_fact_objects(gold: pd.DataFrame) -> pd.DataFrame:
    """Select the 65 curated columns and add ``in_giant_group``.

    Missing columns (not yet populated in Gold) are filled with None so the
    output schema is stable even if the source table evolves.
    """
    out_cols: list[str] = []
    data: dict[str, pd.Series] = {}

    for col in FACT_OBJECTS_COLUMNS:
        if col in gold.columns:
            data[col] = gold[col]
        else:
            data[col] = pd.Series([None] * len(gold), index=gold.index)
        out_cols.append(col)

    df = pd.DataFrame(data, columns=out_cols)

    giant_size = int(gold["group_size"].max())
    df["in_giant_group"] = gold["group_size"] == giant_size

    return df


def build_dim_class(gold: pd.DataFrame) -> pd.DataFrame:
    """One row per distinct refined_class in the Gold table."""
    counts = gold["refined_class"].value_counts().reset_index()
    counts.columns = ["class_name", "object_count"]
    counts["class_order"] = counts["class_name"].map(CLASS_ORDER).fillna(99).astype(int)
    counts["color_hex"] = counts["class_name"].map(CLASS_COLORS).fillna("#cccccc")
    total = int(counts["object_count"].sum())
    counts["percentage"] = counts["object_count"] / total
    return counts.sort_values("class_order").reset_index(drop=True)[
        ["class_name", "class_order", "color_hex", "object_count", "percentage"]
    ]


def build_dim_level(gold: pd.DataFrame) -> pd.DataFrame:
    """One row per level 0-9 with counts."""
    counts = gold["level"].value_counts().reset_index()
    counts.columns = ["level", "object_count"]
    return counts.sort_values("level").reset_index(drop=True)


def build_dim_pipeline(gold: pd.DataFrame) -> pd.DataFrame:
    """Aggregate pipeline statistics from piping objects.

    Produces one row per distinct ``sp3d_pipeline`` value (nulls excluded)
    with: object_count, pipe_run_count, primary_npd, all_npds, specs.
    """
    piping = gold[
        gold["sp3d_pipeline"].notna() & (gold["sp3d_pipeline"] != "")
    ].copy()

    grouped = piping.groupby("sp3d_pipeline", as_index=False).agg(
        object_count=("object_id", "count"),
        pipe_run_count=("sp3d_pipe_run", "nunique"),
    )
    grouped = grouped.rename(columns={"sp3d_pipeline": "pipeline_name"})

    npds = (
        piping.groupby("sp3d_pipeline")["sp3d_npd"]
        .apply(
            lambda s: (
                s.dropna().value_counts().index[0]
                if not s.dropna().empty
                else None
            )
        )
        .reset_index()
        .rename(columns={"sp3d_pipeline": "pipeline_name", "sp3d_npd": "primary_npd"})
    )

    all_npds = (
        piping.groupby("sp3d_pipeline")["sp3d_npd"]
        .apply(lambda s: ", ".join(sorted(set(s.dropna()))))
        .reset_index()
        .rename(columns={"sp3d_pipeline": "pipeline_name", "sp3d_npd": "all_npds"})
    )

    specs = (
        piping.groupby("sp3d_pipeline")["sp3d_specification"]
        .apply(lambda s: ", ".join(sorted({v for v in s.dropna() if v})))
        .reset_index()
        .rename(
            columns={"sp3d_pipeline": "pipeline_name", "sp3d_specification": "specs"}
        )
    )

    return (
        grouped.merge(npds, on="pipeline_name", how="left")
        .merge(all_npds, on="pipeline_name", how="left")
        .merge(specs, on="pipeline_name", how="left")
        .sort_values("pipeline_name")
        .reset_index(drop=True)
    )


def build_dim_meshq(gold: pd.DataFrame) -> pd.DataFrame:
    """Mesh quality dimension with is_container flag."""
    counts = gold["mesh_quality"].value_counts(dropna=False).reset_index()
    counts.columns = ["mesh_quality", "object_count"]
    counts["is_container"] = counts["mesh_quality"].isin(
        {"skipped_container", "box_placeholder"}
    )
    return counts.reset_index(drop=True)


def build_dim_verdict(gold: pd.DataFrame) -> pd.DataFrame:
    """Verdict dimension with is_ok flag."""
    counts = gold["verdict"].value_counts(dropna=False).reset_index()
    counts.columns = ["verdict", "object_count"]
    counts["is_ok"] = counts["verdict"].isin({"OK_MESH", "OK_FBX"})
    return counts.reset_index(drop=True)


def build_dim_group(groups: pd.DataFrame) -> pd.DataFrame:
    """Copy the Silver connected groups dimension, add is_giant_group."""
    out = groups.copy()
    giant_size = int(out["group_size"].max())
    out["is_giant_group"] = out["group_size"] == giant_size
    out["is_singleton"] = out["group_size"] == 1
    return out.reset_index(drop=True)


def build_bridge_group_member(gold: pd.DataFrame) -> pd.DataFrame:
    """Bridge table: ``object_id -> group_id`` (12,009 rows)."""
    return gold[["object_id", "group_id"]].reset_index(drop=True)


def build_fact_adjacency(adj_silver: pd.DataFrame) -> pd.DataFrame:
    """Directed producer adjacency (110,173 rows) with a stable ``edge_id``."""
    out = adj_silver.copy().reset_index(drop=True)
    out.insert(0, "edge_id", out.index.astype(int) + 1)
    return out


def build_fact_adjacency_undirected(adj_silver: pd.DataFrame) -> pd.DataFrame:
    """Pair-deduplicated adjacency with a stable ``pair_id``.

    The producer output already contains each undirected pair exactly once,
    so we only sort the endpoints for stability and strip direction columns.
    """
    out = adj_silver.copy()

    # Order endpoints lexicographically so (A,B) and (B,A) collapse
    left = out["source_object_id"]
    right = out["target_object_id"]
    out["object_a"] = left.where(left <= right, right)
    out["object_b"] = right.where(left <= right, left)

    out = (
        out[
            [
                "object_a",
                "object_b",
                "relation_type",
                "distance_m",
                "overlap_volume_m3",
                "tolerance_m",
            ]
        ]
        .drop_duplicates(subset=["object_a", "object_b"])
        .reset_index(drop=True)
    )
    out.insert(0, "pair_id", out.index.astype(int) + 1)
    return out


# ---------------------------------------------------------------------------
# README generation
# ---------------------------------------------------------------------------


def _render_readme(summary: PowerBIExportSummary) -> str:
    return f"""# Power BI Star Schema — DXTnavis {config.SNAPSHOT}

Generated by `bimkg.ingest.exporters.powerbi.run_powerbi_export()`.
Source: `data/enriched/{config.SNAPSHOT}/bim_objects_enriched.parquet`

## Files

| File | Rows | Purpose |
|---|---:|---|
| `fact_objects.csv` | {summary["fact_objects_rows"]:,} | Per-object fact (PK: `object_id`). 66 cols including derived flags, SI units, lineage. |
| `fact_adjacency.csv` | {summary["fact_adjacency_rows"]:,} | Directed producer spatial edges. |
| `fact_adjacency_undirected.csv` | {summary["fact_adjacency_undirected_rows"]:,} | Pair-deduplicated edges. |
| `bridge_group_member.csv` | {summary["bridge_group_member_rows"]:,} | Object ↔ connected group. |
| `dim_class.csv` | {summary["dim_class_rows"]} | Refined class taxonomy (6 classes). |
| `dim_level.csv` | {summary["dim_level_rows"]} | Level 0-9. |
| `dim_pipeline.csv` | {summary["dim_pipeline_rows"]} | Piping system identifiers. |
| `dim_meshq.csv` | {summary["dim_meshq_rows"]} | Mesh quality values. |
| `dim_verdict.csv` | {summary["dim_verdict_rows"]} | Validation verdict values. |
| `dim_group.csv` | {summary["dim_group_rows"]:,} | Connected components with BBox. |

## Star schema

```
dim_class ─┐
dim_level ─┤
dim_meshq ─┼─> fact_objects <─── fact_adjacency (source + target on object_id)
dim_verdict─┤     ▲
dim_pipeline┘     │
                  │
              bridge_group_member ──> dim_group
```

## Changes from legacy C# bundle

- **6 classes** (Piping, Structure, Equipment, Electrical, HVAC, Other)
  instead of 5. Support class is no longer used — it is absorbed into
  Structure / Piping based on the physical context.
- **SI unit columns** added: `dry_weight_kg`, `length_m`, `design_pressure_kpa`,
  `design_temperature_c`, `npd_end1_m`, etc.
- **Derived flags** added: `is_container`, `is_bbox_placeholder`,
  `is_analysis_volume`, `has_own_geometry`, `graph_participant`.
- **Lineage columns** added: `original_class`, `refined_class`,
  `refining_rule`, `refining_rule_version`, `ingested_at_utc`.
- **Schedule tables removed**: `fact_schedule_links.csv` and `dim_task.csv`
  are not included (no schedule data in Phase 1a; will be reinstated in
  Phase 4+ if scheduling analytics are implemented).

## Quick start

1. Power BI Desktop -> Get Data -> Text/CSV
2. Select each of the 10 files. UTF-8 BOM handles Korean automatically.
3. Modeling -> Manage Relationships, set up the star schema above.
4. Build pages.

## Regeneration

```bash
.venv/bin/python -c "from bimkg.ingest.exporters.powerbi import run_powerbi_export; print(run_powerbi_export())"
```
"""


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def _write_csv(df: pd.DataFrame, path: Path) -> None:
    """Write CSV with UTF-8 BOM so Power BI autodetects Korean text."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def run_powerbi_export(
    gold_path: Path | None = None,
    output_dir: Path | None = None,
) -> PowerBIExportSummary:
    """Build and write all Power BI CSV files."""
    gold = pd.read_parquet(gold_path or config.ENRICHED_OBJECTS)
    adj_silver = build_bim_adjacency_silver()
    groups_silver = build_bim_connected_groups_silver()
    out_dir = output_dir or config.POWERBI_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    fact_objects = build_fact_objects(gold)
    fact_adjacency = build_fact_adjacency(adj_silver)
    fact_adjacency_undirected = build_fact_adjacency_undirected(adj_silver)
    bridge_group_member = build_bridge_group_member(gold)
    dim_class = build_dim_class(gold)
    dim_level = build_dim_level(gold)
    dim_pipeline = build_dim_pipeline(gold)
    dim_meshq = build_dim_meshq(gold)
    dim_verdict = build_dim_verdict(gold)
    dim_group = build_dim_group(groups_silver)

    _write_csv(fact_objects, out_dir / "fact_objects.csv")
    _write_csv(fact_adjacency, out_dir / "fact_adjacency.csv")
    _write_csv(fact_adjacency_undirected, out_dir / "fact_adjacency_undirected.csv")
    _write_csv(bridge_group_member, out_dir / "bridge_group_member.csv")
    _write_csv(dim_class, out_dir / "dim_class.csv")
    _write_csv(dim_level, out_dir / "dim_level.csv")
    _write_csv(dim_pipeline, out_dir / "dim_pipeline.csv")
    _write_csv(dim_meshq, out_dir / "dim_meshq.csv")
    _write_csv(dim_verdict, out_dir / "dim_verdict.csv")
    _write_csv(dim_group, out_dir / "dim_group.csv")

    summary = PowerBIExportSummary(
        output_dir=str(out_dir),
        fact_objects_rows=len(fact_objects),
        fact_adjacency_rows=len(fact_adjacency),
        fact_adjacency_undirected_rows=len(fact_adjacency_undirected),
        bridge_group_member_rows=len(bridge_group_member),
        dim_class_rows=len(dim_class),
        dim_level_rows=len(dim_level),
        dim_pipeline_rows=len(dim_pipeline),
        dim_meshq_rows=len(dim_meshq),
        dim_verdict_rows=len(dim_verdict),
        dim_group_rows=len(dim_group),
    )

    (out_dir / "README.md").write_text(_render_readme(summary), encoding="utf-8")
    return summary
