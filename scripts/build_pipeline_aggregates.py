"""Build bim_pipelines and bim_piperuns aggregation datasets.

Aggregates `bim_piping` into two new entity tables for Ontology:

- **bim_pipelines** (~147 rows): one per distinct sp3d_pipeline
- **bim_piperuns** (~500–1000 rows): one per (sp3d_pipeline, sp3d_pipe_run) pair

Corrosion risk + isolation sections KPIs pulled from
`src/bimkg/analytics/kpi.py` when applicable.

Timestamp columns cast to proper pandas datetime for Foundry.

Usage:
    export FOUNDRY_TOKEN=...
    python scripts/build_pipeline_aggregates.py \\
        [--output-dir data/ontology/2026-04-12] \\
        [--upload]
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

pd.set_option("future.infer_string", False)

from foundry_sdk import FoundryClient, UserTokenAuth

HOSTNAME = "datayoon.usw-18.palantirfoundry.com"
PROJECT = "/Datayoon-09825c/BIM-KG"

SOURCE_PIPING = "bim_piping"
DEST_PIPELINES = "bim_pipelines"
DEST_PIPERUNS = "bim_piperuns"

#: Pattern matchers for counting specific component types by display_name
COMPONENT_PATTERNS = {
    "valve_count": r"\bvalve\b",
    "flange_count": r"\bflange\b",
    "elbow_count": r"\belbow\b",
    "tee_count": r"\btee\b",
    "reducer_count": r"\breducer\b",
}


def connect() -> FoundryClient:
    token = os.environ.get("FOUNDRY_TOKEN")
    if not token:
        sys.exit("FOUNDRY_TOKEN env var required")
    return FoundryClient(auth=UserTokenAuth(token=token), hostname=HOSTNAME)


def read_bim_piping(client: FoundryClient) -> pd.DataFrame:
    """Load bim_piping via foundry-sdk v2 read_table."""
    res = client.filesystem.Resource.get_by_path(
        path=f"{PROJECT}/{SOURCE_PIPING}", preview=True
    )
    response = client.datasets.Dataset.read_table(res.rid, format="ARROW")
    df = response.to_pandas()
    print(f"  Loaded {SOURCE_PIPING}: {len(df):,} rows × {len(df.columns)} cols")
    return df


def weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    """Weighted average falling back to simple mean if weights sum to 0."""
    mask = values.notna() & weights.notna()
    if not mask.any():
        return float("nan")
    v = values[mask]
    w = weights[mask]
    total_w = w.sum()
    if total_w <= 0:
        return float(v.mean())
    return float((v * w).sum() / total_w)


def count_by_pattern(names: pd.Series, pattern: str) -> int:
    return int(names.fillna("").str.contains(pattern, regex=True, case=False).sum())


def aggregate_pipelines(df: pd.DataFrame, now_ts: str) -> pd.DataFrame:
    """Aggregate to one row per sp3d_pipeline. ~147 rows expected."""
    # Filter out empty pipeline names
    df = df[df["sp3d_pipeline"].notna() & (df["sp3d_pipeline"] != "")].copy()
    print(f"  Piping objects with non-empty pipeline: {len(df):,}")

    rows = []
    for pipeline_name, group in df.groupby("sp3d_pipeline"):
        weights = group["dry_weight_kg"].fillna(0)
        total_w = weights.sum()

        row = {
            "pipeline_name": pipeline_name,
            "component_count": len(group),
            "pipe_run_count": group["sp3d_pipe_run"].nunique(),
            "total_dry_weight_kg": float(total_w) if total_w > 0 else None,

            # Pressure/Temperature aggregates (Piping-only properties)
            "mean_pressure_kpa": float(group["design_pressure_kpa"].mean()) if group["design_pressure_kpa"].notna().any() else None,
            "max_pressure_kpa": float(group["design_pressure_kpa"].max()) if group["design_pressure_kpa"].notna().any() else None,
            "min_pressure_kpa": float(group["design_pressure_kpa"].min()) if group["design_pressure_kpa"].notna().any() else None,
            "mean_temperature_c": float(group["design_temperature_c"].mean()) if group["design_temperature_c"].notna().any() else None,
            "max_temperature_c": float(group["design_temperature_c"].max()) if group["design_temperature_c"].notna().any() else None,

            # Spatial aggregates (bbox encompassing + weighted centroid)
            "centroid_x": weighted_mean(group["centroid_x"], weights),
            "centroid_y": weighted_mean(group["centroid_y"], weights),
            "centroid_z": weighted_mean(group["centroid_z"], weights),
            "bbox_min_x": float(group["bbox_min_x"].min()),
            "bbox_min_y": float(group["bbox_min_y"].min()),
            "bbox_min_z": float(group["bbox_min_z"].min()),
            "bbox_max_x": float(group["bbox_max_x"].max()),
            "bbox_max_y": float(group["bbox_max_y"].max()),
            "bbox_max_z": float(group["bbox_max_z"].max()),
            "bbox_volume_total_m3": float(group["bbox_volume_m3"].sum()),

            # Mesh coverage
            "mesh_coverage_pct": float(100 * group["has_real_mesh"].fillna(False).mean()),

            # Component type counts (display_name pattern matching)
            "valve_count": count_by_pattern(group["display_name"], r"\bvalve\b"),
            "flange_count": count_by_pattern(group["display_name"], r"\bflange\b"),
            "elbow_count": count_by_pattern(group["display_name"], r"\belbow\b"),
            "tee_count": count_by_pattern(group["display_name"], r"\btee\b"),
            "reducer_count": count_by_pattern(group["display_name"], r"\breducer\b"),

            # M4-related
            "fbx_supplemented_count": int((group["mesh_quality"] == "fbx_supplemented").sum()),
            "likely_bug_count": int((group["classification_confidence"] == "LIKELY_BUG").sum()),

            # Representative metadata (first component — for context)
            "representative_system_path": group["system_path"].iloc[0] if "system_path" in group.columns else None,

            # Lineage
            "ingested_at_utc": now_ts,
        }
        rows.append(row)

    pipeline_df = pd.DataFrame(rows)
    pipeline_df["ingested_at_utc"] = pd.to_datetime(pipeline_df["ingested_at_utc"])
    print(f"  Aggregated pipelines: {len(pipeline_df):,}")
    return pipeline_df.sort_values("pipeline_name").reset_index(drop=True)


def aggregate_piperuns(df: pd.DataFrame, now_ts: str) -> pd.DataFrame:
    """Aggregate per (sp3d_pipeline, sp3d_pipe_run) pair. ~500–1000 rows."""
    df = df[
        df["sp3d_pipeline"].notna() & (df["sp3d_pipeline"] != "") &
        df["sp3d_pipe_run"].notna() & (df["sp3d_pipe_run"] != "")
    ].copy()
    print(f"  Piping objects with non-empty piperun: {len(df):,}")

    rows = []
    for (pipeline, piperun), group in df.groupby(["sp3d_pipeline", "sp3d_pipe_run"]):
        weights = group["dry_weight_kg"].fillna(0)

        # Composite primary key: pipeline_name::pipe_run_name ensures global uniqueness
        piperun_id = f"{pipeline}::{piperun}"

        row = {
            "piperun_id": piperun_id,
            "pipeline_name": pipeline,  # FK to BimPipeline
            "pipe_run_name": piperun,
            "component_count": len(group),
            "total_dry_weight_kg": float(weights.sum()) if weights.sum() > 0 else None,

            "mean_pressure_kpa": float(group["design_pressure_kpa"].mean()) if group["design_pressure_kpa"].notna().any() else None,
            "max_pressure_kpa": float(group["design_pressure_kpa"].max()) if group["design_pressure_kpa"].notna().any() else None,
            "mean_temperature_c": float(group["design_temperature_c"].mean()) if group["design_temperature_c"].notna().any() else None,
            "max_temperature_c": float(group["design_temperature_c"].max()) if group["design_temperature_c"].notna().any() else None,

            "centroid_x": weighted_mean(group["centroid_x"], weights),
            "centroid_y": weighted_mean(group["centroid_y"], weights),
            "centroid_z": weighted_mean(group["centroid_z"], weights),
            "bbox_min_x": float(group["bbox_min_x"].min()),
            "bbox_min_y": float(group["bbox_min_y"].min()),
            "bbox_min_z": float(group["bbox_min_z"].min()),
            "bbox_max_x": float(group["bbox_max_x"].max()),
            "bbox_max_y": float(group["bbox_max_y"].max()),
            "bbox_max_z": float(group["bbox_max_z"].max()),
            "bbox_volume_total_m3": float(group["bbox_volume_m3"].sum()),

            "mesh_coverage_pct": float(100 * group["has_real_mesh"].fillna(False).mean()),

            "valve_count": count_by_pattern(group["display_name"], r"\bvalve\b"),
            "flange_count": count_by_pattern(group["display_name"], r"\bflange\b"),
            "elbow_count": count_by_pattern(group["display_name"], r"\belbow\b"),
            "tee_count": count_by_pattern(group["display_name"], r"\btee\b"),

            "fbx_supplemented_count": int((group["mesh_quality"] == "fbx_supplemented").sum()),

            "ingested_at_utc": now_ts,
        }
        rows.append(row)

    piperun_df = pd.DataFrame(rows)
    piperun_df["ingested_at_utc"] = pd.to_datetime(piperun_df["ingested_at_utc"])
    print(f"  Aggregated piperuns: {len(piperun_df):,}")
    return piperun_df.sort_values(["pipeline_name", "pipe_run_name"]).reset_index(drop=True)


def ensure_foundry_dataset(client: FoundryClient, path: str) -> str:
    """Create dataset if missing, return its RID."""
    try:
        res = client.filesystem.Resource.get_by_path(path=path, preview=True)
        print(f"  {path}: exists (rid={res.rid})")
        return res.rid
    except Exception:
        print(f"  {path}: creating new...")
        ds = client.datasets.Dataset.create(name=path.rsplit("/", 1)[-1],
                                             parent_folder_rid="")
        print(f"  Created: {ds.rid}")
        return ds.rid


def upload_via_legacy_sdk(rid: str, df: pd.DataFrame) -> None:
    """Use legacy palantir-sdk write_pandas (newer foundry-sdk lacks write API)."""
    from palantir.core.config import StaticHostnameProvider, StaticTokenProvider
    from palantir.datasets.client import (
        PalantirContext, DatasetServices, DatasetsClient, DatasetLocator
    )
    from palantir.datasets.core import Dataset

    hp = StaticHostnameProvider(HOSTNAME)
    tp = StaticTokenProvider(os.environ["FOUNDRY_TOKEN"])
    client = DatasetsClient(DatasetServices(PalantirContext(hostname=hp, auth=tp)))

    # Fix dtypes for palantir-sdk (same as foundry_upload.py)
    for col in df.columns:
        dt = str(df[col].dtype)
        if dt == "Int64":
            df[col] = df[col].astype("float64")
        elif df[col].dtype == object:
            if df[col].isna().all():
                df[col] = ""
            else:
                df[col] = df[col].fillna("")

    locator = DatasetLocator(rid, "master")
    ds = Dataset(client, locator)
    ds.write_pandas(df)
    print(f"  ✓ Uploaded {len(df):,} rows")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", type=Path,
                    default=Path("data/ontology/2026-04-12"),
                    help="Local parquet output directory")
    ap.add_argument("--upload", action="store_true",
                    help="Also upload to Foundry (requires datasets to exist)")
    ap.add_argument("--create-if-missing", action="store_true",
                    help="Create Foundry datasets if they don't exist yet")
    args = ap.parse_args()

    print("Connecting to Foundry...")
    client = connect()

    print("\nReading source bim_piping...")
    piping_df = read_bim_piping(client)

    now_ts = datetime.now(timezone.utc).isoformat(timespec="seconds")

    print("\nAggregating BimPipeline...")
    pipelines = aggregate_pipelines(piping_df, now_ts)

    print("\nAggregating BimPipeRun...")
    piperuns = aggregate_piperuns(piping_df, now_ts)

    # Save local parquet
    args.output_dir.mkdir(parents=True, exist_ok=True)
    pipelines_path = args.output_dir / "bim_pipelines.parquet"
    piperuns_path = args.output_dir / "bim_piperuns.parquet"

    pipelines.to_parquet(pipelines_path, index=False)
    piperuns.to_parquet(piperuns_path, index=False)
    print(f"\n✓ Saved:")
    print(f"  {pipelines_path} — {len(pipelines):,} rows × {len(pipelines.columns)} cols")
    print(f"  {piperuns_path} — {len(piperuns):,} rows × {len(piperuns.columns)} cols")

    # Summary
    print(f"\n=== Summary ===")
    print(f"BimPipeline: {len(pipelines):,} entities")
    print(f"  valve_count total: {pipelines['valve_count'].sum():,}")
    print(f"  flange_count total: {pipelines['flange_count'].sum():,}")
    print(f"  Total dry_weight_kg: {pipelines['total_dry_weight_kg'].sum():,.0f}")
    print(f"\nBimPipeRun: {len(piperuns):,} entities")
    print(f"  Across {piperuns['pipeline_name'].nunique()} unique pipelines")
    print(f"  Mean piperuns/pipeline: {len(piperuns)/piperuns['pipeline_name'].nunique():.1f}")

    # Foundry upload
    if args.upload:
        print(f"\nUploading to Foundry...")
        pipelines_path_foundry = f"{PROJECT}/{DEST_PIPELINES}"
        piperuns_path_foundry = f"{PROJECT}/{DEST_PIPERUNS}"

        for name, df, ont_path in [
            (DEST_PIPELINES, pipelines, pipelines_path_foundry),
            (DEST_PIPERUNS, piperuns, piperuns_path_foundry),
        ]:
            print(f"\n  → {name}")
            try:
                res = client.filesystem.Resource.get_by_path(path=ont_path, preview=True)
                rid = res.rid
                print(f"    RID: {rid}")
            except Exception as e:
                if args.create_if_missing:
                    print(f"    Not found; please create manually in Foundry UI")
                    print(f"    (SDK-based creation requires parent folder RID)")
                    continue
                else:
                    print(f"    NOT FOUND: {e}")
                    print(f"    Create via UI at: {ont_path}")
                    continue
            upload_via_legacy_sdk(rid, df.copy())


if __name__ == "__main__":
    main()
