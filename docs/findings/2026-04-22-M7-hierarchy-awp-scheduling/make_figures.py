"""Generate matplotlib figures for M7 finding.

Produces 4 charts in figures/:
  01_object_source_coverage.png  - Pipeline / SP3D-no-Pipe / Navisworks-only breakdown
  02_estimate_vs_actual.png      - README estimates vs audited actuals
  03_hierarchy_depth_dist.png    - Object count by system_path depth
  04_task_count_simulation.png   - Tasks per grouping strategy (depth 2-7)

Reads from data/*.csv produced by audit.py.

Usage::

    .venv/bin/python docs/findings/2026-04-22-M7-hierarchy-awp-scheduling/make_figures.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).parent
DATA_DIR = HERE / "data"
FIG_DIR = HERE / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

COLOR_PIPELINE = "#1f77b4"   # blue — current scheduler scope
COLOR_GAP = "#d62728"        # red — missed by current scheduler
COLOR_NAV = "#7f7f7f"        # gray — non-physical
COLOR_ESTIMATE = "#aec7e8"   # light blue
COLOR_ACTUAL = "#1f77b4"     # blue
COLOR_README_LINE = "#ff7f0e"  # orange — README claim line

plt.rcParams["figure.dpi"] = 110
plt.rcParams["savefig.dpi"] = 300
plt.rcParams["font.family"] = "DejaVu Sans"


def fig_01_object_source_coverage() -> None:
    df = pd.read_csv(DATA_DIR / "coverage_by_source.csv")
    # Compose 3-bucket donut: Pipeline / SP3D-no-Pipe / Nav-only
    pipeline = df.loc[df["category"] == "has Pipeline (sp3d_pipeline)", "count"].iloc[0]
    sp3d_no_pipe = df.loc[df["category"] == "SP3D w/o Pipeline", "count"].iloc[0]
    nav_only = df.loc[df["category"] == "Navisworks-only", "count"].iloc[0]
    total = pipeline + sp3d_no_pipe + nav_only

    sizes = [pipeline, sp3d_no_pipe, nav_only]
    labels = [
        f"Pipeline (current\nscheduler scope)\n{pipeline:,} ({pipeline/total*100:.1f}%)",
        f"SP3D w/o Pipeline\n(missed)\n{sp3d_no_pipe:,} ({sp3d_no_pipe/total*100:.1f}%)",
        f"Navisworks-only\n(non-physical)\n{nav_only:,} ({nav_only/total*100:.1f}%)",
    ]
    colors = [COLOR_PIPELINE, COLOR_GAP, COLOR_NAV]

    fig, ax = plt.subplots(figsize=(9, 6))
    wedges, _ = ax.pie(
        sizes,
        labels=labels,
        colors=colors,
        startangle=90,
        wedgeprops={"width": 0.45, "edgecolor": "white", "linewidth": 2},
        textprops={"fontsize": 10},
    )
    ax.text(0, 0, f"{total:,}\nobjects", ha="center", va="center",
            fontsize=14, fontweight="bold")
    ax.set_title(
        "M7 — Object Source Coverage Gap\n"
        "Current Pipeline-only scheduler covers 24.4%; 75.6% missed",
        fontsize=12, fontweight="bold", pad=20,
    )

    out = FIG_DIR / "01_object_source_coverage.png"
    plt.tight_layout()
    plt.savefig(out, bbox_inches="tight")
    plt.close()
    print(f"  wrote {out.relative_to(HERE)}")


def fig_02_estimate_vs_actual() -> None:
    # Estimates baked into README §1.2 + §2.2 vs audited actuals
    classes = ["Structure", "Electrical", "Equipment", "Other+HVAC", "Eqp Type 0"]
    estimate = [1200, 400, 300, 3000, 300]
    actual = [2577, 792, 697, 898, 153]

    x = range(len(classes))
    width = 0.38

    fig, ax = plt.subplots(figsize=(10, 5.5))
    b1 = ax.bar([i - width/2 for i in x], estimate, width,
                label="README estimate (~)", color=COLOR_ESTIMATE, edgecolor="black")
    b2 = ax.bar([i + width/2 for i in x], actual, width,
                label="Audited actual", color=COLOR_ACTUAL, edgecolor="black")

    for bar, val in zip(b1, estimate):
        ax.text(bar.get_x() + bar.get_width()/2, val + 50,
                f"~{val:,}", ha="center", fontsize=9)
    for bar, val in zip(b2, actual):
        ax.text(bar.get_x() + bar.get_width()/2, val + 50,
                f"{val:,}", ha="center", fontsize=9, fontweight="bold")

    # Diff annotation under each pair
    for i, (e, a) in enumerate(zip(estimate, actual)):
        diff_pct = (a - e) / e * 100
        sign = "+" if diff_pct > 0 else ""
        ax.text(i, -250, f"{sign}{diff_pct:.0f}%",
                ha="center", fontsize=10,
                color="red" if abs(diff_pct) > 30 else "black",
                fontweight="bold")

    ax.set_xticks(list(x))
    ax.set_xticklabels(classes)
    ax.set_ylabel("Object count")
    ax.set_title(
        "M7 — README Estimates vs Audited Actuals\n"
        "All 5 estimates wrong by 49-132%",
        fontsize=12, fontweight="bold",
    )
    ax.legend(loc="upper right")
    ax.set_ylim(-500, max(max(estimate), max(actual)) * 1.15)
    ax.axhline(0, color="black", linewidth=0.5)

    out = FIG_DIR / "02_estimate_vs_actual.png"
    plt.tight_layout()
    plt.savefig(out, bbox_inches="tight")
    plt.close()
    print(f"  wrote {out.relative_to(HERE)}")


def fig_03_hierarchy_depth_dist() -> None:
    df = pd.read_csv(DATA_DIR / "hierarchy_level_distribution.csv")
    fig, ax = plt.subplots(figsize=(10, 5))

    colors = ["#7f7f7f"] * len(df)
    # Highlight the README-claimed AWP levels (2,3,4)
    for i, row in df.iterrows():
        if row["level_val"] in (2, 3, 4):
            colors[i] = COLOR_PIPELINE

    bars = ax.bar(df["level_val"].astype(str), df["count"], color=colors, edgecolor="black")
    for bar, val, role in zip(bars, df["count"], df["awp_role_claim"]):
        ax.text(bar.get_x() + bar.get_width()/2, val + 50,
                f"{val:,}", ha="center", fontsize=9)
        ax.text(bar.get_x() + bar.get_width()/2, -200,
                role, ha="center", fontsize=8, rotation=0,
                color="red" if role in ("Area", "Unit", "Discipline") else "gray")

    ax.set_xlabel("level_val (Navisworks tree depth)")
    ax.set_ylabel("Object count")
    ax.set_title(
        "M7 — Hierarchy Level Distribution (level_val column)\n"
        "Bulk of objects at depth 6-8, NOT depth 2-4 as AWP hypothesis assumed",
        fontsize=12, fontweight="bold",
    )
    ax.set_ylim(-400, max(df["count"]) * 1.1)
    ax.axhline(0, color="black", linewidth=0.5)

    out = FIG_DIR / "03_hierarchy_depth_dist.png"
    plt.tight_layout()
    plt.savefig(out, bbox_inches="tight")
    plt.close()
    print(f"  wrote {out.relative_to(HERE)}")


def fig_04_task_count_simulation() -> None:
    df = pd.read_csv(DATA_DIR / "task_count_simulation.csv")

    # Separate baseline (pipeline-only) from depth-N simulations
    baseline = df.iloc[0]  # Pipeline-only
    depth_rows = df.iloc[1:].copy()
    # Extract depth number from strategy string
    depth_rows["depth"] = depth_rows["strategy"].str.extract(r"depth (\d+)").astype(int)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.plot(depth_rows["depth"], depth_rows["n_tasks"],
            marker="o", color=COLOR_PIPELINE, linewidth=2, markersize=10,
            label="Hierarchy fallback — n_tasks vs prefix depth")
    for d, n in zip(depth_rows["depth"], depth_rows["n_tasks"]):
        ax.text(d, n * 1.15, f"{n:,}", ha="center", fontsize=9, fontweight="bold")

    ax.axhline(baseline["n_tasks"], color=COLOR_PIPELINE, linestyle="--",
               linewidth=1.5,
               label=f"Pipeline-only (current) = {int(baseline['n_tasks'])} tasks (24% coverage)")
    ax.axhline(677, color=COLOR_README_LINE, linestyle=":", linewidth=2,
               label="README §1.3 projection: ~677 tasks")

    ax.set_yscale("log")
    ax.set_xlabel("system_path prefix depth (n)")
    ax.set_ylabel("Number of tasks (log scale)")
    ax.set_title(
        "M7 — Task Count vs Grouping Strategy\n"
        "README ~677 projection lies between depth-5 (299) and depth-6 (938) — not principled",
        fontsize=12, fontweight="bold",
    )
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(True, alpha=0.3, which="both")

    out = FIG_DIR / "04_task_count_simulation.png"
    plt.tight_layout()
    plt.savefig(out, bbox_inches="tight")
    plt.close()
    print(f"  wrote {out.relative_to(HERE)}")


def main() -> int:
    print("Generating M7 figures...")
    fig_01_object_source_coverage()
    fig_02_estimate_vs_actual()
    fig_03_hierarchy_depth_dist()
    fig_04_task_count_simulation()
    print(f"Done. {len(list(FIG_DIR.glob('*.png')))} PNGs in {FIG_DIR.relative_to(HERE.parent.parent.parent)}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
