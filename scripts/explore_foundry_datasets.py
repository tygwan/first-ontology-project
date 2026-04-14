"""Profile all 11 Foundry datasets and produce a Markdown report.

Uses new foundry-sdk (v2) which supports `read_table()` API on modern datasets.
The legacy palantir-sdk fails here with "unresolved end transaction rid".

Output: docs/analysis/foundry-dataset-profiles-YYYY-MM-DD.md

Usage:
    export FOUNDRY_TOKEN=...
    python scripts/explore_foundry_datasets.py
"""
from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

import pandas as pd

pd.set_option("future.infer_string", False)

from foundry_sdk import FoundryClient, UserTokenAuth

HOSTNAME = "datayoon.usw-18.palantirfoundry.com"
PROJECT = "/Datayoon-09825c/BIM-KG"

DATASETS = {
    "bim_piping": "object",
    "bim_structural": "object",
    "bim_equipment": "object",
    "bim_electrical": "object",
    "bim_hvac": "object",
    "bim_other": "object",
    "bim_adjacent_to": "link",
    "bim_has_parent": "link",
    "bim_belongs_to_pipeline": "link",
    "bim_in_group": "link",
}

OBJECT_KEY_COLS = [
    "object_id", "display_name", "refined_class",
    "sp3d_pipeline", "sp3d_system_path",
    "centroid_x", "centroid_y", "centroid_z",
    "bbox_volume_m3", "dry_weight_kg",
    "design_pressure_kpa", "design_temperature_c",
    "mesh_quality", "mesh_uri",
    "classification_confidence",
]


def connect() -> FoundryClient:
    token = os.environ.get("FOUNDRY_TOKEN")
    if not token:
        sys.exit("FOUNDRY_TOKEN env var required")
    return FoundryClient(auth=UserTokenAuth(token=token), hostname=HOSTNAME)


def profile_numeric(s: pd.Series) -> str:
    non_null = s.dropna()
    if non_null.empty:
        return "all-null"
    return (
        f"min={non_null.min():.2f} p50={non_null.median():.2f} "
        f"p95={non_null.quantile(0.95):.2f} max={non_null.max():.2f}"
    )


def profile_categorical(s: pd.Series, top_n: int = 5) -> str:
    counts = s.value_counts().head(top_n)
    total = len(s)
    return ", ".join(f"`{v}` ({c:,}, {100*c/total:.1f}%)" for v, c in counts.items())


def profile_dataset(name: str, kind: str, df: pd.DataFrame, out: list[str]):
    out.append(f"\n### `{name}` ({kind})\n")
    out.append(f"- **Shape**: {len(df):,} rows × {len(df.columns)} cols")

    dtypes = df.dtypes.value_counts().to_dict()
    dtype_summary = ", ".join(f"{v} {k}" for k, v in dtypes.items())
    out.append(f"- **Column types**: {dtype_summary}")

    null_rates = df.isnull().mean()
    mostly_null = (null_rates > 0.5).sum()
    mostly_full = (null_rates < 0.01).sum()
    out.append(f"- **Completeness**: {mostly_full} cols ≥99% filled, {mostly_null} cols ≥50% null")

    out.append(f"\n**Key attributes**:")
    if kind == "object":
        for col in OBJECT_KEY_COLS:
            if col not in df.columns:
                continue
            null_pct = 100 * df[col].isnull().mean()
            s = df[col].dropna()
            if s.empty:
                out.append(f"- `{col}`: all-null")
                continue
            if pd.api.types.is_numeric_dtype(s):
                out.append(f"- `{col}` ({null_pct:.0f}% null): {profile_numeric(s)}")
            else:
                distinct = s.nunique()
                if distinct <= 10:
                    out.append(
                        f"- `{col}` ({null_pct:.0f}% null, {distinct} distinct): "
                        f"{profile_categorical(s)}"
                    )
                else:
                    sample = ", ".join(f"`{str(v)[:40]}`" for v in s.head(3))
                    out.append(
                        f"- `{col}` ({null_pct:.0f}% null, {distinct:,} distinct): e.g., {sample}"
                    )
    else:
        out.append(f"- **Columns**: {', '.join(f'`{c}`' for c in df.columns)}")
        for col in df.columns:
            if col.endswith("_id") or col.endswith("_object_id"):
                distinct = df[col].nunique()
                out.append(f"- `{col}`: {distinct:,} distinct values")
            elif df[col].dtype == object and df[col].nunique() <= 10:
                out.append(f"- `{col}`: {profile_categorical(df[col])}")


def cross_dataset_analysis(dfs: dict[str, pd.DataFrame], out: list[str]):
    out.append("\n## Cross-Dataset Analysis\n")

    obj_dfs = {k: v for k, v in dfs.items() if not any(
        link in k for link in ("adjacent_to", "has_parent", "belongs_to", "in_group")
    )}

    out.append("### 1. Object ID disjoint check\n")
    all_ids: set = set()
    cumulative_overlap = 0
    for name, df in obj_dfs.items():
        if "object_id" not in df.columns:
            out.append(f"- `{name}`: no object_id column")
            continue
        ids = set(df["object_id"].dropna())
        overlap = len(all_ids & ids)
        cumulative_overlap += overlap
        all_ids |= ids
        out.append(f"- `{name}`: {len(ids):,} objects (overlap with earlier sets: {overlap})")
    out.append(f"- **Total unique object_ids**: {len(all_ids):,}")
    out.append(f"- **Expected**: 12,009 (disjoint)")
    out.append(f"- **Total cumulative overlap**: {cumulative_overlap}  "
               f"{'✓ clean' if cumulative_overlap == 0 else '⚠ check'}\n")

    out.append("### 2. `sp3d_system_path` prefix patterns\n")
    for name, df in obj_dfs.items():
        if "sp3d_system_path" not in df.columns:
            continue
        paths = df["sp3d_system_path"].dropna()
        if paths.empty:
            continue
        first_seg = paths.str.split(r"[/\\]").str[0].value_counts().head(3)
        top = ", ".join(f"`{k}` ({v:,})" for k, v in first_seg.items())
        out.append(f"- `{name}`: top prefixes = {top}")

    out.append("\n### 3. Shared `sp3d_system_path` across classes\n")
    class_paths = {}
    for name, df in obj_dfs.items():
        if "sp3d_system_path" in df.columns:
            class_paths[name] = set(df["sp3d_system_path"].dropna())
    if len(class_paths) >= 2:
        names = list(class_paths.keys())
        for i, a in enumerate(names):
            for b in names[i+1:]:
                shared = len(class_paths[a] & class_paths[b])
                if shared > 0:
                    out.append(f"- `{a}` ∩ `{b}`: **{shared:,}** shared paths  "
                               f"(potential cross-class link)")

    out.append("\n### 4. Link Type connectivity\n")
    for link_name in ("bim_adjacent_to", "bim_has_parent",
                      "bim_belongs_to_pipeline", "bim_in_group"):
        if link_name not in dfs:
            continue
        ldf = dfs[link_name]
        cols = ", ".join(f"`{c}`" for c in ldf.columns)
        out.append(f"- `{link_name}`: {len(ldf):,} rows, cols: {cols}")

    # 5. group_id 분포 (hidden group relationship)
    if "bim_in_group" in dfs:
        out.append("\n### 5. Group membership distribution\n")
        g = dfs["bim_in_group"].groupby(
            [c for c in dfs["bim_in_group"].columns if "group" in c.lower()][0]
        ).size()
        out.append(f"- Total groups: {g.nunique() if hasattr(g, 'nunique') else len(g):,}")
        out.append(f"- Largest group: {g.max():,} objects")
        out.append(f"- Singleton groups: {(g == 1).sum():,}")
        out.append(f"- Multi-element groups: {(g > 1).sum():,}")


def main():
    print("Connecting to Foundry...")
    client = connect()

    # Resolve RIDs via filesystem API
    print("Resolving dataset RIDs...")
    rids = {}
    for name in DATASETS:
        try:
            res = client.filesystem.Resource.get_by_path(
                path=f"{PROJECT}/{name}", preview=True
            )
            rids[name] = res.rid
        except Exception as e:
            print(f"  ⚠️ {name}: {str(e)[:80]}")

    print(f"Found {len(rids)}/{len(DATASETS)} datasets.\n")

    # Read via new SDK
    dfs = {}
    out: list[str] = [
        f"# Foundry Dataset Profiles — BIM-KG",
        f"",
        f"**Generated**: {date.today().isoformat()} (SDK auto-profile)",
        f"**SDK**: foundry-sdk v2 (`read_table`)",
        f"**Purpose**: Pre-computed context for AI FDE conversations",
        f"**Project**: `{PROJECT}`",
        f"",
        f"Skim this first; saves AI FDE from recomputing basics.",
        f"",
        f"## Summary",
        f"",
        f"| Dataset | Type | Rows | Cols | Status |",
        f"|---|---|---:|---:|---|",
    ]

    summary: list[str] = []
    for name, kind in DATASETS.items():
        if name not in rids:
            summary.append(f"| `{name}` | {kind} | — | — | RID not found |")
            continue
        print(f"Reading {name}...")
        try:
            response = client.datasets.Dataset.read_table(rids[name], format="ARROW")
            df = response.to_pandas()
            dfs[name] = df
            summary.append(f"| `{name}` | {kind} | {len(df):,} | {len(df.columns)} | ✓ |")
        except Exception as e:
            err = str(e)[:60].replace('\n', ' ')
            summary.append(f"| `{name}` | {kind} | — | — | ❌ {err} |")
            print(f"  ⚠️ {name}: {type(e).__name__}: {str(e)[:100]}")

    out.extend(summary)
    out.append("")

    # Per-dataset profiles
    out.append("\n## Per-Dataset Profiles\n")
    for name, kind in DATASETS.items():
        if name in dfs:
            profile_dataset(name, kind, dfs[name], out)

    cross_dataset_analysis(dfs, out)

    # Prior findings
    out.append("\n## Prior Findings (already known)\n")
    out.append("Skip re-discovering these. See `docs/findings/` for archives.")
    out.append("")
    out.append("- **M1** (Piping misclassification): substring bug in DXTnavis regex. "
               "Fix applied; `classification_confidence` column marks affected rows.")
    out.append("- **M2** (Adjacency tiers): AABB-based → 3-tier classification "
               "(strong 13K / medium 87K / all 220K).")
    out.append("- **M3** (Parent box contamination): 448 hierarchy-container objects "
               "with `is_parent_box=True` skewed early adjacency counts.")
    out.append("- **M4** (FBX GUID mapping, 2026-04-15): 788 `fbx_supplemented` objects "
               "matched to GLB files via FBX Properties70 + centroid transform "
               "`Gold(x,y,z) = FBX(-x, z, y)`. 7 bonus SP3D columns found duplicated "
               "with XLSX; Gold schema unchanged. See "
               "`docs/findings/2026-04-15-M4-fbx-guid-mapping/`.")
    out.append("- 33 KPIs pre-computed (object/zone/pipeline/plant levels) in "
               "`src/bimkg/analytics/kpi.py`.")
    out.append("- 144 Louvain zones from spatial adjacency (`zones.py`).")
    out.append("- 147 distinct pipelines (`sp3d_pipeline` values).")
    out.append("- 3,355 connected groups (via `bim_in_group`).")

    # Suggested AI FDE prompts
    out.append("\n## Suggested AI FDE Starting Prompts\n")
    out.append("Given M1–M4 are resolved, ask AI FDE:\n")
    out.append("1. Patterns in `display_name` that suggest semantic sub-categories")
    out.append("2. Anomalies in the `sp3d_bom_desc` text corpus (NLP angle)")
    out.append("3. Relationships between `sp3d_support_assembly` and `group_id`")
    out.append("4. Whether any pipeline has unexpectedly sparse `bim_adjacent_to` density")
    out.append("5. Objects whose bbox_volume + mesh_quality combo suggests mis-labeling")
    out.append("6. Does `sp3d_system_path` hierarchy suggest implicit Ontology namespaces?")

    out_path = Path("docs/analysis") / f"foundry-dataset-profiles-{date.today().isoformat()}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(out))
    print(f"\n✓ Report: {out_path} ({out_path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
