"""Generate ydata-profiling reports for the Gold tables.

Produces self-contained HTML reports for portfolio review:

    docs/reference/profiling/{SNAPSHOT}/bim_objects_enriched.html
    docs/reference/profiling/{SNAPSHOT}/bim_adjacency_sym.html
    docs/reference/profiling/{SNAPSHOT}/summary.json

The reports cover variable types, missing values, distributions, correlations,
and quality alerts — everything a Data Analyst / Data Scientist would inspect
before building dashboards or models.

Usage:
    .venv/bin/python scripts/profile_gold_table.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from time import perf_counter

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import pandas as pd
from ydata_profiling import ProfileReport

from bimkg import config


# Profiling config tuned for a 12K-row × 219-col table on a laptop.
PROFILING_CONFIG = {
    "title": "BIM Gold Table Profile",
    "explorative": True,
    "minimal": False,
    # Skip expensive bivariate plots — 219 cols would explode pairwise plots.
    "interactions": {"continuous": False},
    "correlations": {
        "auto": {"calculate": True},
        "pearson": {"calculate": True},
        "spearman": {"calculate": False},
        "kendall": {"calculate": False},
        "phi_k": {"calculate": False},
        "cramers": {"calculate": False},
    },
    "missing_diagrams": {"matrix": True, "bar": True, "heatmap": False},
    "samples": {"head": 10, "tail": 10},
    "duplicates": {"head": 10},
    "vars": {
        "num": {"low_categorical_threshold": 0},
        "cat": {"length": True, "characters": False, "words": False},
    },
    "progress_bar": False,
    "html": {"minify_html": True, "use_local_assets": True},
}


def profile_table(parquet_path: Path, output_html: Path, title: str) -> dict:
    print(f"\n[*] Loading {parquet_path.name}...")
    t0 = perf_counter()
    df = pd.read_parquet(parquet_path)
    print(f"    {len(df):,} rows × {len(df.columns)} cols  (loaded in {perf_counter() - t0:.1f}s)")

    print(f"[*] Profiling -> {output_html.name}...")
    t0 = perf_counter()
    cfg = dict(PROFILING_CONFIG)
    cfg["title"] = title
    report = ProfileReport(df, **cfg)
    output_html.parent.mkdir(parents=True, exist_ok=True)
    report.to_file(output_html)
    elapsed = perf_counter() - t0
    print(f"    Wrote {output_html.stat().st_size:,} bytes in {elapsed:.1f}s")

    desc = report.get_description()
    table_meta = desc.table

    return {
        "source": str(parquet_path.relative_to(PROJECT_ROOT)),
        "report": str(output_html.relative_to(PROJECT_ROOT)),
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "memory_mb": round(table_meta.get("memory_size", 0) / 1_048_576, 2),
        "duplicates": int(table_meta.get("n_duplicates", 0)),
        "missing_cells_pct": round(table_meta.get("p_cells_missing", 0) * 100, 3),
        "variable_types": {str(k): int(v) for k, v in table_meta.get("types", {}).items()},
        "alerts": [str(a) for a in desc.alerts],
        "elapsed_seconds": round(elapsed, 1),
    }


def main() -> int:
    out_dir = PROJECT_ROOT / "docs" / "reference" / "profiling" / config.SNAPSHOT
    out_dir.mkdir(parents=True, exist_ok=True)

    targets = [
        (
            config.ENRICHED_OBJECTS,
            out_dir / "bim_objects_enriched.html",
            f"BIM Objects (Gold) — {config.SNAPSHOT}",
        ),
        (
            config.ENRICHED_ADJACENCY_SYM,
            out_dir / "bim_adjacency_sym.html",
            f"BIM Adjacency Symmetric (Gold) — {config.SNAPSHOT}",
        ),
    ]

    summary = {"snapshot": config.SNAPSHOT, "tables": []}
    for parquet, html, title in targets:
        if not parquet.exists():
            print(f"[!] Skip {parquet} (not found)")
            continue
        summary["tables"].append(profile_table(parquet, html, title))

    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n[OK] Summary: {summary_path}")
    print(f"[OK] {len(summary['tables'])} tables profiled.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
