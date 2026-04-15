"""Generate the M5 impact timeline figure at DPI 300.

Produces a single PNG under ``figures/``:

  impact_timeline.png   Horizontal per-dataset Gantt-style timeline showing
                        each of the 8 Foundry datasets across three states
                        (initial upload → post-cast broken → post-rollback).

Usage::

    .venv/bin/python docs/findings/2026-04-16-M5-timestamp-schema-mismatch/make_figures.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

HERE = Path(__file__).parent
FIG_DIR = HERE / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams["figure.dpi"] = 300
plt.rcParams["savefig.dpi"] = 300
plt.rcParams["font.family"] = "DejaVu Sans"

# Project palette
COLOR_WORKING = "#00C471"  # green
COLOR_BROKEN = "#FF9800"   # orange
COLOR_BLUE = "#3182F6"     # blue (annotation accent)


# (dataset, category, state @ t0 initial upload, state @ t1 post-cast, state @ t2 post-rollback)
# states: "working" or "broken"
ROWS = [
    ("bim_piping",     "Object Type", "working", "broken",  "working"),
    ("bim_structural", "Object Type", "working", "broken",  "working"),
    ("bim_equipment",  "Object Type", "working", "broken",  "working"),
    ("bim_electrical", "Object Type", "working", "broken",  "working"),
    ("bim_hvac",       "Object Type", "working", "broken",  "working"),
    ("bim_other",      "Object Type", "working", "broken",  "working"),
    ("bim_pipelines",  "Aggregate",   "broken",  "broken",  "working"),
    ("bim_piperuns",   "Aggregate",   "broken",  "broken",  "working"),
]

# Three time columns (normalized 0..1 x-axis)
# t0 [0.00, 0.33]  initial upload
# t1 [0.33, 0.66]  after cast_timestamp_columns.py
# t2 [0.66, 1.00]  after fix_dataset_schema.py
SEGMENTS = [
    (0.00, 0.33, "2026-04-15 AM\nInitial upload", 2),
    (0.33, 0.66, "2026-04-15 PM\ncast_timestamp_columns.py", 3),
    (0.66, 1.00, "2026-04-16\nfix_dataset_schema.py", 4),
]


def _color(state: str) -> str:
    return COLOR_WORKING if state == "working" else COLOR_BROKEN


def main() -> int:
    print("Generating M5 figures (DPI 300)...")
    fig, ax = plt.subplots(figsize=(12, 6.5))

    n = len(ROWS)
    bar_h = 0.62

    for i, (name, cat, s0, s1, s2) in enumerate(ROWS):
        y = n - 1 - i  # top-to-bottom order
        for (x0, x1, _lbl, _idx), state in zip(SEGMENTS, [s0, s1, s2]):
            ax.barh(
                y,
                width=x1 - x0,
                left=x0,
                height=bar_h,
                color=_color(state),
                edgecolor="black",
                linewidth=0.8,
            )
            ax.text(
                (x0 + x1) / 2,
                y,
                state.upper(),
                ha="center",
                va="center",
                fontsize=8,
                color="white",
                weight="bold",
            )

        # Dataset label on the left (name + category)
        ax.text(
            -0.015,
            y,
            f"{name}\n({cat})",
            ha="right",
            va="center",
            fontsize=9,
            family="monospace",
        )

    # Column headers — placed above the chart
    for (x0, x1, lbl, _idx) in SEGMENTS:
        ax.text(
            (x0 + x1) / 2,
            n - 0.2,
            lbl,
            ha="center",
            va="bottom",
            fontsize=9,
            color=COLOR_BLUE,
            weight="bold",
        )

    # Vertical divider lines
    for (x0, _x1, _lbl, _idx) in SEGMENTS[1:]:
        ax.axvline(x0, color="#555", linestyle="--", linewidth=0.7, alpha=0.6)

    ax.set_xlim(-0.22, 1.02)
    ax.set_ylim(-0.8, n + 0.3)
    ax.set_yticks([])
    ax.set_xticks([])
    for spine in ("top", "right", "left", "bottom"):
        ax.spines[spine].set_visible(False)

    ax.set_title(
        "M5 — ingested_at_utc Schema State Across 8 Foundry Datasets\n"
        "UI Preview + Spark reads: BROKEN during cast window, restored by String rollback",
        fontsize=12,
        pad=28,
    )

    # Legend
    legend_handles = [
        Patch(facecolor=COLOR_WORKING, edgecolor="black", label="WORKING (String / ISO 8601)"),
        Patch(facecolor=COLOR_BROKEN, edgecolor="black", label="BROKEN (Parquet DATE INT64)"),
    ]
    ax.legend(
        handles=legend_handles,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.08),
        ncol=2,
        frameon=False,
        fontsize=10,
    )

    plt.tight_layout()
    out = FIG_DIR / "impact_timeline.png"
    plt.savefig(out, bbox_inches="tight")
    plt.close()
    print(f"  wrote {out}")
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
