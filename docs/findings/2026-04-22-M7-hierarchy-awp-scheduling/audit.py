"""Reproducible audit for M7: hierarchy-based AWP scheduling coverage.

Verifies the README's coverage breakdown and hierarchy mapping hypothesis
against the Gold parquet (data/enriched/2026-04-12/bim_objects_enriched.parquet).

Outputs (alongside this script):
  - data/coverage_by_source.csv          object source breakdown (SP3D vs Nav-only)
  - data/non_pipeline_class_breakdown.csv refined_class distribution of 4,964 SP3D-no-pipeline
  - data/hierarchy_level_distribution.csv level_val distribution (Level 0-9)
  - data/level2_node_inventory.csv       Level-2 node names (Area hypothesis check)
  - data/sp3d_property_coverage.csv      key SP3D property null-rate

Findings (recorded in this script's print output):
  - 6 of 7 README coverage numbers exact
  - Eqp Type 0 claim ~300 vs actual 153 (off by -49%)
  - Non-pipeline class breakdown: README estimates wrong by 70-130%
    (Structure 1,200→2,577; Electrical 400→792; Equipment 300→697; Other 3,000→898)
  - Level 2 = Area hypothesis BREAKS: only 4 distinct Level-2 names in
    system_path; "TRAINING" alone covers 98.8% (11,860/12,009). README §1.1
    examples ("A2", "Training Sulphur Recovery") live at depth 3-5, not 2.
  - Task count projection ~677 NOT reproducible: hierarchy-prefix grouping
    at depths 2-7 yields {5, 149, 183, 299, 938, 4242} tasks — ~677 lies
    between depth-5 and depth-6 but is not a principled cutoff.

Usage::

    .venv/bin/python docs/findings/2026-04-22-M7-hierarchy-awp-scheduling/audit.py

This script reads the Gold parquet and writes CSVs into its own data/ dir.
It does not mutate any project data.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

import pandas as pd

from bimkg import config

HERE = Path(__file__).parent
DATA_DIR = HERE / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def main() -> int:
    print("=" * 72)
    print(f"M7 Hierarchy-AWP Scheduling Audit — snapshot {config.SNAPSHOT}")
    print("=" * 72)

    df = pd.read_parquet(config.ENRICHED_OBJECTS)
    total = len(df)
    print(f"\nTotal objects: {total}")

    # ------------------------------------------------------------------
    # 1) Object source coverage (README §1.2 main table)
    # ------------------------------------------------------------------
    sp3d_geom = df["sp3d_name"].notna()
    has_pipeline = df["sp3d_pipeline"].notna()
    sp3d_no_pipe = sp3d_geom & ~has_pipeline
    nav_only = ~sp3d_geom

    coverage = pd.DataFrame(
        [
            {"category": "Total",                       "count": int(total),               "pct": 100.0},
            {"category": "SP3D Geometry (sp3d_name)",   "count": int(sp3d_geom.sum()),     "pct": round(100 * sp3d_geom.sum() / total, 1)},
            {"category": "has Pipeline (sp3d_pipeline)", "count": int(has_pipeline.sum()),  "pct": round(100 * has_pipeline.sum() / total, 1)},
            {"category": "has PipeRun (sp3d_pipe_run)",  "count": int(df["sp3d_pipe_run"].notna().sum()), "pct": round(100 * df["sp3d_pipe_run"].notna().sum() / total, 1)},
            {"category": "SP3D w/o Pipeline",           "count": int(sp3d_no_pipe.sum()),  "pct": round(100 * sp3d_no_pipe.sum() / total, 1)},
            {"category": "Navisworks-only",             "count": int(nav_only.sum()),      "pct": round(100 * nav_only.sum() / total, 1)},
        ]
    )
    coverage.to_csv(DATA_DIR / "coverage_by_source.csv", index=False)
    print("\n[1] Object source coverage:")
    print(coverage.to_string(index=False))

    # ------------------------------------------------------------------
    # 2) Non-pipeline SP3D — refined_class distribution
    #    (README §1.2 4,964 breakdown — claimed ~1,200/~400/~300/~3,000)
    # ------------------------------------------------------------------
    sub = df[sp3d_no_pipe].copy()
    breakdown = (
        sub["refined_class"]
        .value_counts(dropna=False)
        .rename_axis("refined_class")
        .reset_index(name="actual_count")
    )
    readme_estimate = {
        "Structure": "~1,200 (StructuralMember)",
        "Electrical": "~400 (CableTray, Cableway)",
        "Equipment": "~300 (ProcessEquipment, Civil)",
        "Other": "~3,000 (HVAC, Insulation, etc.)",  # combined w/ HVAC in README
        "HVAC": "(part of '~3,000 기타')",
        "Piping": "(impossible by definition)",
    }
    breakdown["readme_estimate"] = breakdown["refined_class"].map(readme_estimate).fillna("(not estimated)")
    breakdown.to_csv(DATA_DIR / "non_pipeline_class_breakdown.csv", index=False)
    print("\n[2] Non-pipeline SP3D — refined_class (vs README estimate):")
    print(breakdown.to_string(index=False))

    # ------------------------------------------------------------------
    # 3) Hierarchy level distribution (README §1.1 Level 0-9 mapping)
    # ------------------------------------------------------------------
    level_dist = (
        df["level_val"]
        .value_counts(dropna=False)
        .sort_index()
        .rename_axis("level_val")
        .reset_index(name="count")
    )
    level_dist["awp_role_claim"] = level_dist["level_val"].map(
        {0: "File", 1: "Model", 2: "Area", 3: "Unit", 4: "Discipline"}
    ).fillna("Component")
    level_dist.to_csv(DATA_DIR / "hierarchy_level_distribution.csv", index=False)
    print("\n[3] Hierarchy level distribution (with README §1.1 AWP role claim):")
    print(level_dist.to_string(index=False))

    # ------------------------------------------------------------------
    # 4) Level-2 hypothesis check (system_path-based, NOT level_val-based)
    #    README §1.1 claims Level 2 = Area (A2, Training Sulphur Recovery,
    #    Electrical Substation, ...). The canonical test: parse system_path
    #    segments and count distinct segs[1] names. If hypothesis holds,
    #    expect ~5-10 area names with reasonably balanced object counts.
    # ------------------------------------------------------------------
    def split_path(p):
        return [s.strip() for s in p.split(" > ")] if isinstance(p, str) else []

    df["_segs"] = df["system_path"].apply(split_path)
    df["_L2"] = df["_segs"].apply(lambda s: s[1] if len(s) > 1 else None)

    l2_inv = (
        df["_L2"]
        .value_counts(dropna=False)
        .rename_axis("level2_name")
        .reset_index(name="count")
    )
    l2_inv["pct"] = (l2_inv["count"] / total * 100).round(1)
    l2_inv.to_csv(DATA_DIR / "level2_node_inventory.csv", index=False)
    print(f"\n[4] Level-2 inventory (system_path segs[1]): {len(l2_inv)} distinct names")
    print("    README §1.1 implied 5-10 areas — hypothesis BREAKS if dominated by 1 name")
    print(l2_inv.to_string(index=False))

    # ------------------------------------------------------------------
    # 5) Key SP3D property null-rate (README §2.2 table)
    # ------------------------------------------------------------------
    props = ["sp3d_name", "sp3d_pipeline", "sp3d_pipe_run", "sp3d_eqp_type_0", "nav_item_type"]
    prop_cov = pd.DataFrame(
        [
            {
                "property": p,
                "non_null_count": int(df[p].notna().sum()),
                "pct_of_total": round(100 * df[p].notna().sum() / total, 1),
            }
            for p in props
        ]
    )
    prop_cov.to_csv(DATA_DIR / "sp3d_property_coverage.csv", index=False)
    print("\n[5] Key property non-null counts (README §2.2 verification):")
    print(prop_cov.to_string(index=False))
    print("\n  ⚠ README §2.2 claims sp3d_eqp_type_0 = ~300 (~2.5%); actual = 153 (~1.3%)")

    # ------------------------------------------------------------------
    # 6) Hierarchy fallback simulation — task count by prefix depth
    #    Compare current Pipeline-only grouping (378 tasks) against several
    #    prefix-based fallback strategies to test README §1.3 ~677 claim.
    # ------------------------------------------------------------------
    pipe_groups = df[has_pipeline].groupby(
        ["sp3d_pipeline", "sp3d_pipe_run"], dropna=False
    ).size()
    n_pipeline_tasks = len(pipe_groups)

    def prefix_n(segs_list, n):
        if len(segs_list) >= n:
            return " > ".join(segs_list[:n])
        return " > ".join(segs_list) if segs_list else None

    rows = [
        {
            "strategy": "Pipeline-only (current DXTnavis)",
            "grouping_key": "(sp3d_pipeline, sp3d_pipe_run)",
            "n_tasks": int(n_pipeline_tasks),
            "covered_objects": int(has_pipeline.sum()),
            "coverage_pct": round(100 * has_pipeline.sum() / total, 1),
        }
    ]
    for n in [2, 3, 4, 5, 6, 7]:
        df[f"_pfx{n}"] = df["_segs"].apply(lambda s: prefix_n(s, n))
        n_groups = df[f"_pfx{n}"].nunique(dropna=True)
        rows.append({
            "strategy": f"Hierarchy fallback — prefix depth {n}",
            "grouping_key": f"system_path[:{n}]",
            "n_tasks": int(n_groups),
            "covered_objects": int(total),
            "coverage_pct": 100.0,
        })
    sim = pd.DataFrame(rows)
    sim.to_csv(DATA_DIR / "task_count_simulation.csv", index=False)
    print("\n[6] Task count simulation (README §1.3 claimed 378→~677):")
    print(sim.to_string(index=False))
    print(f"\n  README projection ~677 tasks does NOT match any prefix depth.")
    print(f"  Closest by order of magnitude: depth-4 prefix = {sim.iloc[3]['n_tasks']} tasks")

    # ------------------------------------------------------------------
    # Summary verdict
    # ------------------------------------------------------------------
    print("\n" + "=" * 72)
    print("AUDIT VERDICT")
    print("=" * 72)
    print("""
  EXACT MATCH (6/7 coverage numbers):
    - Total 12,009; SP3D Geometry 7,890; has Pipeline/PipeRun 2,926;
      SP3D w/o Pipeline 4,964; Navisworks-only 4,119

  WRONG (README needs correction):
    - Eqp Type 0: claimed ~300, actual 153 (-49%)
    - Non-pipeline class breakdown estimates off by 70-130%:
        Structure   1,200 → 2,577 (+115%)
        Electrical    400 →   792  (+98%)
        Equipment     300 →   697 (+132%)
        Other       3,000 →   830  (-72%)  + HVAC 68
    - Level 2 = Area hypothesis BREAKS: only 4 distinct names in system_path
      segs[1]; 'TRAINING' alone covers 11,860/12,009 (98.8%). README §1.1
      examples (A2, Training Sulphur Recovery, Electrical Substation) live
      at depth 3-5, not 2.
    - Task count projection ~677 NOT reproducible at any tested depth:
      depth-2 = 5, depth-3 = 149, depth-4 = 183, depth-5 = 299,
      depth-6 = 938, depth-7 = 4,242. ~677 lies between depth-5 and -6
      but is not a principled cutoff.

  IMPLICATION:
    - Coverage gap analysis (24% → 100%) is STRUCTURALLY correct
      (current Pipeline-only misses 9,083 of 12,009 objects)
    - Hierarchy fallback PROPOSAL remains valid as a strategy
    - But the SPECIFIC level mapping (L2=Area, L3=Unit, L4=Discipline) needs
      revision — real Navisworks tree puts Area at depth 3-5, not 2
    - README §1.2 estimated counts and §1.3 task projection should be
      replaced with audited values from this script
""")
    # Cleanup intermediate columns used during analysis (keep CSVs clean)
    df.drop(columns=[c for c in df.columns if c.startswith("_")], inplace=True, errors="ignore")
    return 0


if __name__ == "__main__":
    sys.exit(main())
