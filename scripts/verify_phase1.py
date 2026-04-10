"""Quick verification snapshot of Phase 1 outputs.

Run::

    .venv/bin/python scripts/verify_phase1.py

Prints a human-readable summary of:
- Row counts in Gold bim_objects_enriched.parquet and bimkg.db
- Class distribution (6 classes)
- Flag distribution (5 flags)
- SI unit coverage (11 fields)
- Level distribution
- Pipeline top 10
- Lineage metadata
- Known anomalies (Pipelines label, eqp_type_0 coverage, etc.)

The script does not modify any files. Use it as a diagnostic before moving
to Phase 2 or after any pipeline change to spot regressions quickly.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

# Make sure the package is importable when run directly
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from bimkg import config


def banner(text: str) -> None:
    print()
    print("=" * 70)
    print(text)
    print("=" * 70)


def section(text: str) -> None:
    print()
    print(f"--- {text} ---")


def main() -> int:
    banner(f"Phase 1 Verification Snapshot — snapshot {config.SNAPSHOT}")

    if not config.ENRICHED_OBJECTS.exists():
        print(f"ERROR: Gold file not found at {config.ENRICHED_OBJECTS}")
        print("Run Phase 1a first:")
        print("  python -c 'from bimkg.ingest.sqlite_writer import run_phase_1a; run_phase_1a()'")
        return 1

    gold = pd.read_parquet(config.ENRICHED_OBJECTS)

    section("File inventory")
    files = [
        config.CLEAN_OBJECTS,
        config.CLEAN_ADJACENCY,
        config.CLEAN_HIERARCHY,
        config.CLEAN_CONNECTED_GROUPS,
        config.ENRICHED_OBJECTS,
        config.ENRICHED_ADJACENCY_SYM,
        config.SQLITE_BIMKG,
    ]
    for p in files:
        status = "OK " if p.exists() else "MISS"
        size_mb = p.stat().st_size / 1024 / 1024 if p.exists() else 0.0
        rel = p.relative_to(config.PROJECT_ROOT)
        print(f"  [{status}] {rel}  ({size_mb:6.1f} MB)")

    section("Gold bim_objects_enriched.parquet shape")
    print(f"  Rows:    {len(gold):>6,}")
    print(f"  Columns: {len(gold.columns):>6}")

    section("Class distribution (refined_class)")
    cls = gold["refined_class"].value_counts()
    total = len(gold)
    for name, count in cls.items():
        pct = count / total * 100
        print(f"  {name:12} : {count:>6,}  ({pct:5.1f}%)")

    section("Flag distribution")
    flags = [
        "is_container",
        "is_bbox_placeholder",
        "is_analysis_volume",
        "has_own_geometry",
        "graph_participant",
    ]
    for f in flags:
        n = int(gold[f].sum())
        pct = n / total * 100
        print(f"  {f:22} : {n:>6,}  ({pct:5.1f}%)")

    section("SI unit coverage")
    si_fields = [
        ("dry_weight_kg", "kg"),
        ("wet_weight_kg", "kg"),
        ("length_m", "m"),
        ("width_m", "m"),
        ("depth_m", "m"),
        ("height_m", "m"),
        ("design_pressure_kpa", "kPa"),
        ("design_temperature_c", "°C"),
        ("npd_end1_m", "m"),
        ("bend_radius_m", "m"),
    ]
    for col, unit in si_fields:
        if col not in gold.columns:
            continue
        n = int(gold[col].notna().sum())
        if n > 0:
            mn = float(gold[col].min())
            mx = float(gold[col].max())
            print(f"  {col:22} : {n:>5} rows  ({mn:>12.3f} - {mx:>12.3f} {unit})")
        else:
            print(f"  {col:22} : (no data)")

    section("Hierarchy level distribution")
    levels = gold["level"].value_counts().sort_index()
    for lvl, count in levels.items():
        print(f"  Level {lvl}: {count:>5,}")

    section("Mesh quality distribution")
    for mq, count in gold["mesh_quality"].value_counts().items():
        print(f"  {mq:22} : {count:>5,}")

    section("Top 10 pipelines (by object count)")
    piping = gold[gold["sp3d_pipeline"].notna() & (gold["sp3d_pipeline"] != "")]
    for name, count in piping["sp3d_pipeline"].value_counts().head(10).items():
        print(f"  {name:24} : {count:>4}")

    section("Equipment Eqp Type 0 coverage")
    eq = gold[gold["refined_class"] == "Equipment"]
    with_type = int(eq["sp3d_eqp_type_0"].notna().sum())
    print(f"  Equipment total     : {len(eq):>5}")
    print(f"  With Eqp Type 0     : {with_type:>5}  ({with_type/len(eq)*100:5.1f}%)")
    if with_type:
        for name, count in eq["sp3d_eqp_type_0"].value_counts().head(5).items():
            print(f"    {name:22} : {count:>4}")

    section("Lineage (same for all rows)")
    print(f"  refining_rule         : {gold['refining_rule'].iloc[0]}")
    print(f"  refining_rule_version : {gold['refining_rule_version'].iloc[0]}")
    print(f"  ingested_at_utc       : {gold['ingested_at_utc'].iloc[0]}")

    section("SQLite canonical store")
    with sqlite3.connect(config.SQLITE_BIMKG) as conn:
        n_obj = conn.execute("SELECT COUNT(*) FROM bim_objects").fetchone()[0]
        n_adj = conn.execute("SELECT COUNT(*) FROM bim_adjacency").fetchone()[0]
    print(f"  bim_objects rows   : {n_obj:>6,}")
    print(f"  bim_adjacency rows : {n_adj:>6,}  (symmetric closure, 2x producer edges)")

    section("Root object")
    root = gold[gold["parent_id"].isna()]
    if len(root) == 1:
        r = root.iloc[0]
        print(f"  object_id    : {r['object_id']}")
        print(f"  display_name : {r['display_name']}")
        print(f"  level        : {r['level']}  (should be 0)")
    else:
        print(f"  WARN: expected exactly 1 root, found {len(root)}")

    section("Known anomalies (for your awareness)")
    pipelines_label_count = int(piping[piping["sp3d_pipeline"] == "Pipelines"].shape[0])
    print(f"  'Pipelines' label in sp3d_pipeline : {pipelines_label_count} objects")
    print(f"    -> This is a suspicious value, likely SP3D metadata leak")
    print(f"    -> Document: docs/analysis/phase-1-verification-guide.md §6.1")
    print()
    print(f"  Equipment without eqp_type_0 : {len(eq) - with_type} objects")
    print(f"    -> Expected (SP3D taxonomy only populated for 153/851)")
    print(f"    -> Document: docs/analysis/phase-1-verification-guide.md §6.2")

    banner("Verification snapshot complete")
    print()
    print("Next: read docs/analysis/phase-1-verification-guide.md for the")
    print("manual check list (§3) and Power BI import guide (§4).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
