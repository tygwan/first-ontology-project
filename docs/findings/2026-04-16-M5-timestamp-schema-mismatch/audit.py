"""Reproducible audit for M5: ``ingested_at_utc`` Parquet schema mismatch.

Scans the 8 local parquet files that were uploaded (and re-uploaded) to
Foundry during Phase 2 and reports the Parquet logical + physical type of
``ingested_at_utc`` for each. Compares against the post-rollback expected
schema (``string``) and flags mismatches.

This audit is intentionally offline-only: it reads **local** parquet files
(the canonical source for every Foundry upload) and does not require
``FOUNDRY_TOKEN``. The Foundry-side "DATE INT64" broken state is no longer
reachable — it was overwritten by ``scripts/fix_dataset_schema.py`` — so we
capture it as a static ``foundry_cast_state`` column from the session's
recorded evidence (see ``evidence/schema_state_before_after.csv``).

Usage::

    .venv/bin/python docs/findings/2026-04-16-M5-timestamp-schema-mismatch/audit.py

Output columns:
    dataset                 Foundry dataset name
    local_parquet_path      Relative path under data/ontology/2026-04-12/
    exists                  Whether the local parquet file was found
    physical_type           Parquet physical type for ingested_at_utc
    logical_type            Parquet logical type string (or "")
    arrow_type              pyarrow-reported Arrow type
    foundry_cast_state      Recorded state after D-AIFDE-7 cast (static evidence)
    foundry_post_rollback   Recorded state after fix_dataset_schema.py (static evidence)
    expected_local_type     Expected Arrow type for the *local* parquet
    local_mismatch          True if arrow_type != expected_local_type

Note: the 6 Object Type parquets are expected to be ``string`` locally,
while the 2 aggregate parquets (``bim_pipelines``, ``bim_piperuns``) are
expected to be ``timestamp[ns, tz=UTC]`` locally — the fix script converts
them to String on-the-fly during upload (see ``fix_dataset_schema.py``).
The Foundry-side post-rollback state is uniformly ``string`` for all 8.

No project data is mutated.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

HERE = Path(__file__).parent
EVIDENCE_DIR = HERE / "evidence"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

# Make bimkg importable when run from arbitrary cwd so SNAPSHOT resolution
# stays in sync with the rest of the project. This is optional — the audit
# falls back to a hard-coded 2026-04-12 snapshot directory if bimkg is
# unavailable.
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

try:
    from bimkg import config  # type: ignore
except Exception:  # pragma: no cover — audit must run without the package
    config = None  # noqa: N816


# --------------------------------------------------------------------------
# Dataset registry — matches scripts/fix_dataset_schema.py DATASETS tuple
# --------------------------------------------------------------------------

DATASETS: list[tuple[str, str]] = [
    ("bim_piping",     "data/ontology/2026-04-12/object_types/piping.parquet"),
    ("bim_structural", "data/ontology/2026-04-12/object_types/structural.parquet"),
    ("bim_equipment",  "data/ontology/2026-04-12/object_types/equipment.parquet"),
    ("bim_electrical", "data/ontology/2026-04-12/object_types/electrical.parquet"),
    ("bim_hvac",       "data/ontology/2026-04-12/object_types/hvac.parquet"),
    ("bim_other",      "data/ontology/2026-04-12/object_types/other.parquet"),
    ("bim_pipelines",  "data/ontology/2026-04-12/bim_pipelines.parquet"),
    ("bim_piperuns",   "data/ontology/2026-04-12/bim_piperuns.parquet"),
]

TS_COL = "ingested_at_utc"

# Recorded Foundry-side states from the 2026-04-16 investigation session.
# The DATE INT64 state is no longer reachable on Foundry because the
# rollback script overwrote it — preserved here as static audit evidence.
FOUNDRY_STATES: dict[str, tuple[str, str]] = {
    # dataset           -> (post_cast_state,        post_rollback_state)
    "bim_piping":       ("date (INT64) — broken", "string (ISO 8601)"),
    "bim_structural":   ("date (INT64) — broken", "string (ISO 8601)"),
    "bim_equipment":    ("date (INT64) — broken", "string (ISO 8601)"),
    "bim_electrical":   ("date (INT64) — broken", "string (ISO 8601)"),
    "bim_hvac":         ("date (INT64) — broken", "string (ISO 8601)"),
    "bim_other":        ("date (INT64) — broken", "string (ISO 8601)"),
    "bim_pipelines":    ("date (INT64) — broken", "string (ISO 8601)"),
    "bim_piperuns":     ("date (INT64) — broken", "string (ISO 8601)"),
}

# Expected Arrow type for the *local* parquet for each dataset. The 6
# Object Type parquets are String; the 2 aggregates keep Timestamp locally
# and are converted to String only at upload time by fix_dataset_schema.py.
EXPECTED_LOCAL_ARROW_TYPE: dict[str, str] = {
    "bim_piping":     "string",
    "bim_structural": "string",
    "bim_equipment":  "string",
    "bim_electrical": "string",
    "bim_hvac":       "string",
    "bim_other":      "string",
    "bim_pipelines":  "timestamp[ns, tz=UTC]",
    "bim_piperuns":   "timestamp[ns, tz=UTC]",
}

# Post-rollback Foundry state for every dataset (what read_table returns).
FOUNDRY_POST_ROLLBACK_TYPE = "string"


# --------------------------------------------------------------------------
# Inspection helpers
# --------------------------------------------------------------------------


def _resolve_project_root() -> Path:
    if config is not None:
        return Path(config.PROJECT_ROOT)
    return Path(__file__).resolve().parents[3]


def _inspect_parquet(path: Path) -> dict:
    """Return (physical_type, logical_type, arrow_type) for TS_COL in ``path``."""
    result = {"physical_type": "", "logical_type": "", "arrow_type": ""}
    if not path.exists():
        return result

    # Parquet-level introspection — catches the DATE INT64 case directly
    pf = pq.ParquetFile(path)
    schema = pf.schema_arrow  # pyarrow.Schema
    parquet_schema = pf.schema  # parquet-native schema (low-level)

    # Arrow-level type
    field = next((f for f in schema if f.name == TS_COL), None)
    if field is not None:
        result["arrow_type"] = str(field.type)

    # parquet-native physical + logical
    for i in range(len(parquet_schema)):
        col = parquet_schema.column(i)
        if col.name == TS_COL:
            result["physical_type"] = str(col.physical_type)
            logical = str(col.logical_type) if col.logical_type is not None else ""
            # parquet-cpp renders "None" for no logical type
            result["logical_type"] = "" if logical == "None" else logical
            break

    return result


# --------------------------------------------------------------------------
# Audit driver
# --------------------------------------------------------------------------


def main() -> int:
    print("=" * 74)
    snapshot = getattr(config, "SNAPSHOT", "2026-04-12") if config else "2026-04-12"
    print(f"M5 Timestamp Schema Mismatch Audit — snapshot {snapshot}")
    print("=" * 74)

    root = _resolve_project_root()
    rows: list[dict] = []
    for name, rel_path in DATASETS:
        path = root / rel_path
        info = _inspect_parquet(path)
        cast_state, post_rollback_state = FOUNDRY_STATES.get(name, ("", ""))
        expected_local = EXPECTED_LOCAL_ARROW_TYPE.get(name, "string")
        row = {
            "dataset": name,
            "local_parquet_path": rel_path,
            "exists": path.exists(),
            "physical_type": info["physical_type"],
            "logical_type": info["logical_type"],
            "arrow_type": info["arrow_type"],
            "foundry_cast_state": cast_state,
            "foundry_post_rollback": post_rollback_state,
            "expected_local_type": expected_local,
            "local_mismatch": (
                path.exists() and info["arrow_type"] != expected_local
            ),
        }
        rows.append(row)

    df = pd.DataFrame(rows)

    # Pretty console summary
    print()
    for _, r in df.iterrows():
        flag = "MISMATCH" if r["local_mismatch"] else "ok"
        arrow = r["arrow_type"] or "N/A"
        print(
            f"  {r['dataset']:<18s}  arrow={arrow:<30s}  "
            f"physical={r['physical_type'] or 'N/A':<12s}  {flag}"
        )

    n_mismatch = int(df["local_mismatch"].sum())
    print()
    print(f"  datasets scanned          : {len(df)}")
    print(f"  local mismatches          : {n_mismatch}  (vs per-dataset expected type)")
    print(f"  broken Foundry state (historic, recorded): "
          f"{sum(1 for s in FOUNDRY_STATES.values() if 'broken' in s[0])}")
    print(f"  Foundry post-rollback type: '{FOUNDRY_POST_ROLLBACK_TYPE}' (all 8 datasets)")

    out = EVIDENCE_DIR / "audit_report.csv"
    df.to_csv(out, index=False)
    print(f"\nwrote {out.relative_to(root)}")

    return 1 if n_mismatch else 0


if __name__ == "__main__":
    raise SystemExit(main())
