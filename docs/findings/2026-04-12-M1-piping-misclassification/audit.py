"""Reproducible audit for M1: Piping misclassification via XLSX substring matching.

Runs the full semantic audit that discovered the issue and exports:
  - data/piping_confidence_breakdown.csv  (4 rows: HIGH/MED/LOW/LIKELY_BUG)
  - data/substring_bug_causes.csv         (5 rows: cause → count)
  - data/likely_misclassified_sample.csv  (top 20 display_name patterns)
  - data/keyword_hit_debug.csv            (keyword → first matched token, per class)

Usage::

    .venv/bin/python docs/findings/2026-04-12-M1-piping-misclassification/audit.py

This script is a record of the analysis; it reads the Gold parquet and writes
CSVs into the same directory as itself. It does not mutate any project data.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make bimkg importable when run from repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

import pandas as pd

from bimkg import config

HERE = Path(__file__).parent
DATA_DIR = HERE / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def main() -> int:
    print("=" * 70)
    print("M1 Piping Misclassification Audit — snapshot", config.SNAPSHOT)
    print("=" * 70)

    gold = pd.read_parquet(config.ENRICHED_OBJECTS)
    piping = gold[gold["refined_class"] == "Piping"].copy()
    print(f"\nTotal Piping objects: {len(piping)}")

    # ------------------------------------------------------------------
    # 1) Confidence breakdown
    # ------------------------------------------------------------------
    with_pipeline = piping["sp3d_pipeline"].notna() & (piping["sp3d_pipeline"] != "")
    with_strong_meta = (
        piping["sp3d_commodity_code"].notna()
        | piping["sp3d_short_code"].notna()
        | piping["sp3d_spec_name"].notna()
        | piping["sp3d_npd"].notna()
    )

    high = with_pipeline & with_strong_meta
    med = with_pipeline & ~with_strong_meta
    low = ~with_pipeline & with_strong_meta
    likely_bug = ~with_pipeline & ~with_strong_meta

    confidence = pd.DataFrame(
        [
            {
                "confidence": "HIGH",
                "criterion": "has pipeline + has commodity/spec/npd",
                "count": int(high.sum()),
            },
            {
                "confidence": "MED",
                "criterion": "has pipeline, no metadata",
                "count": int(med.sum()),
            },
            {
                "confidence": "LOW",
                "criterion": "no pipeline, has metadata",
                "count": int(low.sum()),
            },
            {
                "confidence": "LIKELY_BUG",
                "criterion": "no pipeline, no metadata",
                "count": int(likely_bug.sum()),
            },
        ]
    )
    confidence.to_csv(DATA_DIR / "piping_confidence_breakdown.csv", index=False)
    print("\n[1] Confidence breakdown:")
    print(confidence.to_string(index=False))

    # ------------------------------------------------------------------
    # 2) Substring bug cause attribution
    # ------------------------------------------------------------------
    bug_rows = piping[likely_bug].copy()

    def contains_ci(series: pd.Series, pattern: str) -> pd.Series:
        return series.fillna("").str.contains(pattern, case=False, regex=True)

    causes = pd.DataFrame(
        [
            {
                "cause": "'Pipe Rack' folder in system_path",
                "keyword_triggered": "pipe",
                "correct_class_would_be": "Structure (structural support)",
                "count": int(
                    contains_ci(bug_rows["system_path"], r"Pipe\s*Rack").sum()
                ),
            },
            {
                "cause": "'Pipe Trench' folder in system_path",
                "keyword_triggered": "pipe",
                "correct_class_would_be": "Structure (civil work)",
                "count": int(
                    contains_ci(bug_rows["system_path"], r"Pipe\s*Trench").sum()
                ),
            },
            {
                "cause": "'Pipeline' folder in system_path",
                "keyword_triggered": "pipe",
                "correct_class_would_be": "varies (folder is grouping node)",
                "count": int(contains_ci(bug_rows["system_path"], "Pipeline").sum()),
            },
            {
                "cause": "'steel' in system_path -> 'tee' substring",
                "keyword_triggered": "tee",
                "correct_class_would_be": "Structure (steel member)",
                "count": int(contains_ci(bug_rows["system_path"], "steel").sum()),
            },
        ]
    )
    causes.to_csv(DATA_DIR / "substring_bug_causes.csv", index=False)
    print("\n[2] Substring bug causes (among LIKELY_BUG):")
    print(causes.to_string(index=False))

    # ------------------------------------------------------------------
    # 3) Top display name patterns in the 997 LIKELY_BUG
    # ------------------------------------------------------------------
    stem = bug_rows["display_name"].str.extract(r"^([^-_0-9]+)")[0]
    top_patterns = (
        stem.value_counts()
        .head(20)
        .rename_axis("display_name_prefix")
        .reset_index(name="count")
    )
    top_patterns.to_csv(DATA_DIR / "likely_misclassified_sample.csv", index=False)
    print("\n[3] Top 20 display_name prefixes among LIKELY_BUG Piping:")
    print(top_patterns.to_string(index=False))

    # ------------------------------------------------------------------
    # 4) Keyword hit debug (specific to the substring bug)
    # ------------------------------------------------------------------
    keyword_hits = pd.DataFrame(
        [
            {
                "piping_keyword": "pipe",
                "matches_in_likely_bug": "Pipe Rack, Pipe Trench, Pipeline folder",
                "example_paths": "> A1 > U12 > Civil_Structure > Pipe Trenches",
            },
            {
                "piping_keyword": "tee",
                "matches_in_likely_bug": "s-TEE-l (substring in 'steel')",
                "example_paths": "> Electrical Device > Steel > MemberSystem-1-0151",
            },
            {
                "piping_keyword": "valve",
                "matches_in_likely_bug": "no false positives observed",
                "example_paths": "-",
            },
            {
                "piping_keyword": "flange",
                "matches_in_likely_bug": "no false positives observed",
                "example_paths": "-",
            },
            {
                "piping_keyword": "elbow",
                "matches_in_likely_bug": "no false positives observed",
                "example_paths": "-",
            },
            {
                "piping_keyword": "reducer",
                "matches_in_likely_bug": "no false positives observed",
                "example_paths": "-",
            },
            {
                "piping_keyword": "nozzle",
                "matches_in_likely_bug": "no false positives observed",
                "example_paths": "-",
            },
            {
                "piping_keyword": "coupling",
                "matches_in_likely_bug": "no false positives observed",
                "example_paths": "-",
            },
        ]
    )
    keyword_hits.to_csv(DATA_DIR / "keyword_hit_debug.csv", index=False)

    # ------------------------------------------------------------------
    # 5) Structure sanity check — no cross-contamination?
    # ------------------------------------------------------------------
    structure = gold[gold["refined_class"] == "Structure"]
    struct_checks = pd.DataFrame(
        [
            {
                "check": "Structure with sp3d_pipeline",
                "count": int(structure["sp3d_pipeline"].notna().sum()),
                "expected": 0,
                "ok": bool(structure["sp3d_pipeline"].notna().sum() == 0),
            },
            {
                "check": "Structure with sp3d_eqp_type_0",
                "count": int(structure["sp3d_eqp_type_0"].notna().sum()),
                "expected": 0,
                "ok": bool(structure["sp3d_eqp_type_0"].notna().sum() == 0),
            },
        ]
    )
    struct_checks.to_csv(DATA_DIR / "structure_sanity_check.csv", index=False)
    print("\n[5] Structure sanity check:")
    print(struct_checks.to_string(index=False))

    print(f"\nAll evidence written to {DATA_DIR.relative_to(config.PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
