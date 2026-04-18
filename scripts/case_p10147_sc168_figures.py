"""Case Study: P-10147 (AI FDE 주장) vs SC-168 (실제 핫라인) 시각화.

Generates 6 PNGs into notebooks/figures/case-p10147-sc168/.

Usage:
    .venv/bin/python scripts/case_p10147_sc168_figures.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from _plot_style import setup_plot_style
setup_plot_style()

import numpy as np
import pandas as pd

BASE = Path("data/ontology/2026-04-12")
OUT = Path("notebooks/figures/case-p10147-sc168")
OUT.mkdir(parents=True, exist_ok=True)

# (rcParams handled by setup_plot_style)

COLOR_P = "#4A90E2"   # P-10147 blue
COLOR_SC = "#E74C3C"  # SC-168 red


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

pipe = pd.read_parquet(BASE / "bim_pipelines.parquet")
run = pd.read_parquet(BASE / "bim_piperuns.parquet")
piping = pd.read_parquet(BASE / "object_types" / "piping.parquet")
link_bt = pd.read_parquet(BASE / "link_types" / "belongs_to_pipeline.parquet")
adj = pd.read_parquet(BASE / "link_types" / "adjacent_to.parquet")

p10147_ids = set(link_bt[link_bt["pipeline_name"] == "P-10147"]["object_id"])
sc168_ids = set(link_bt[link_bt["pipeline_name"] == "SC-168"]["object_id"])


# ---------------------------------------------------------------------------
# 01 — 147 pipelines 4-metric ranking (P-10147 vs SC-168 hilite)
# ---------------------------------------------------------------------------

def fig01_rankings() -> None:
    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    metrics = [
        ("max_pressure_kpa", "Max Pressure (kPa)", "log"),
        ("max_temperature_c", "Max Temperature (°C)", "linear"),
        ("total_dry_weight_kg", "Total Dry Weight (kg)", "log"),
        ("component_count", "Component Count", "linear"),
    ]
    for ax, (col, title, scale) in zip(axes.flat, metrics):
        vals = pipe[col].fillna(0).values
        sorted_vals = np.sort(vals)[::-1]
        n = len(sorted_vals)
        ax.plot(range(1, n + 1), sorted_vals, color="lightgray", lw=1.5,
                label="All 147 pipelines")
        # hilite
        for pname, color, marker in [("P-10147", COLOR_P, "o"),
                                      ("SC-168", COLOR_SC, "s")]:
            rank = (-pipe[col].fillna(0)).rank(method="min").loc[
                pipe["pipeline_name"] == pname
            ].iloc[0]
            val = pipe.loc[pipe["pipeline_name"] == pname, col].iloc[0]
            if pd.isna(val):
                val = 0
            ax.scatter([rank], [val], color=color, s=120, zorder=5, marker=marker,
                       edgecolors="white", linewidths=2, label=f"{pname} (rank {int(rank)})")
        ax.set_title(title)
        ax.set_xlabel("Pipeline rank (1 = highest)")
        ax.set_ylabel(title)
        if scale == "log":
            ax.set_yscale("symlog", linthresh=1)
        ax.legend(loc="upper right", fontsize=8)
        ax.grid(alpha=0.3)

    plt.suptitle("P-10147 vs SC-168 position among 147 pipelines",
                 fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUT / "01_pipeline_rankings.png")
    plt.close()
    print("  ✓ 01_pipeline_rankings.png")


# ---------------------------------------------------------------------------
# 02 — PipeRun breakdown: P-10147 (17 runs) vs SC-168 (3 runs)
# ---------------------------------------------------------------------------

def fig02_piperun_breakdown() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(16, 8), gridspec_kw={"width_ratios": [4, 1]})

    for ax, pname, color in [(axes[0], "P-10147", COLOR_P), (axes[1], "SC-168", COLOR_SC)]:
        runs = run[run["pipeline_name"] == pname].sort_values(
            "total_dry_weight_kg", ascending=True
        )
        y = np.arange(len(runs))
        # stacked: components + weight
        ax.barh(y, runs["total_dry_weight_kg"].values, color=color, alpha=0.7,
                label="Weight (kg)")
        ax.set_yticks(y)
        ax.set_yticklabels(runs["pipe_run_name"].values, fontsize=8)
        ax.set_xlabel("Total Dry Weight (kg)")
        ax.set_title(f"{pname} - {len(runs)} pipe runs\n(total {runs['total_dry_weight_kg'].sum():.1f} kg, {runs['component_count'].sum()} components)")
        # annotate component count
        for i, (w, c) in enumerate(zip(runs["total_dry_weight_kg"], runs["component_count"])):
            ax.text(w + max(runs["total_dry_weight_kg"]) * 0.01, i,
                    f"{c} parts", va="center", fontsize=7, color="dimgray")
        ax.grid(axis="x", alpha=0.3)

    plt.suptitle("PipeRun breakdown - Complexity vs Simplicity", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUT / "02_piperun_breakdown.png")
    plt.close()
    print("  ✓ 02_piperun_breakdown.png")


# ---------------------------------------------------------------------------
# 03 — Component type distribution per pipeline
# ---------------------------------------------------------------------------

def fig03_component_types() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    for ax, (pname, pids, color) in zip(axes, [
        ("P-10147", p10147_ids, COLOR_P),
        ("SC-168", sc168_ids, COLOR_SC),
    ]):
        comps = piping[piping["object_id"].isin(pids)]
        counts = comps["sp3d_short_code"].fillna("(unknown)").value_counts().head(10)
        counts = counts.sort_values()
        ax.barh(counts.index, counts.values, color=color)
        ax.set_title(f"{pname} - Component Types (Top 10)\nTotal {len(comps)} components")
        ax.set_xlabel("Count")
        ax.grid(axis="x", alpha=0.3)

    plt.suptitle("Component type distribution", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUT / "03_component_types.png")
    plt.close()
    print("  ✓ 03_component_types.png")


# ---------------------------------------------------------------------------
# 04 — Adjacency 1-hop neighbors by refined_class
# ---------------------------------------------------------------------------

def fig04_adjacency_neighbors() -> None:
    # build neighbor mapping
    all_types = []
    for t in ["piping", "structural", "equipment", "electrical", "hvac", "other"]:
        df = pd.read_parquet(BASE / "object_types" / f"{t}.parquet",
                             columns=["object_id", "refined_class"])
        all_types.append(df)
    obj_all = pd.concat(all_types)

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    for ax, (pname, pids, color) in zip(axes, [
        ("P-10147", p10147_ids, COLOR_P),
        ("SC-168", sc168_ids, COLOR_SC),
    ]):
        out_e = adj[adj["source_object_id"].isin(pids) & ~adj["target_object_id"].isin(pids)]
        in_e = adj[adj["target_object_id"].isin(pids) & ~adj["source_object_id"].isin(pids)]
        nbr_ids = set(out_e["target_object_id"]) | set(in_e["source_object_id"])
        nbrs = obj_all[obj_all["object_id"].isin(nbr_ids)]
        counts = nbrs["refined_class"].value_counts()
        palette = {"Piping": "#4A90E2", "Structure": "#27AE60",
                   "Equipment": "#F39C12", "Electrical": "#9B59B6",
                   "HVAC": "#1ABC9C", "Other": "#95A5A6"}
        colors = [palette.get(c, "gray") for c in counts.index]
        wedges, texts, autotexts = ax.pie(
            counts.values, labels=counts.index, colors=colors,
            autopct=lambda pct: f"{pct:.0f}%\n({int(round(pct * len(nbrs) / 100))})",
            startangle=90, textprops={"fontsize": 9},
        )
        for t in autotexts:
            t.set_color("white")
            t.set_fontweight("bold")
        ax.set_title(f"{pname} - 1-hop neighbors ({len(nbrs)}) by refined_class",
                     color=color, fontweight="bold")

    plt.suptitle("Neighbor refined_class distribution - physical contact context",
                 fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUT / "04_adjacency_refined_class.png")
    plt.close()
    print("  ✓ 04_adjacency_refined_class.png")


# ---------------------------------------------------------------------------
# 05 — AI FDE 주장 vs 실제 대조
# ---------------------------------------------------------------------------

def fig05_ai_vs_reality() -> None:
    fig, ax = plt.subplots(figsize=(11, 6))

    metrics = ["total_dry_weight_kg", "max_pressure_kpa", "max_temperature_c"]
    labels = ["Weight\n(kg)", "Max Pressure\n(kPa)", "Max Temp\n(°C)"]
    claimed = [16870, 10467, 204]
    # actual
    p_row = pipe[pipe["pipeline_name"] == "P-10147"].iloc[0]
    actual = [p_row[m] for m in metrics]

    x = np.arange(len(metrics))
    w = 0.35
    ax.bar(x - w / 2, claimed, w, label="AI FDE claim",
           color="#E74C3C", edgecolor="black", linewidth=1)
    ax.bar(x + w / 2, actual, w, label="Actual ground truth",
           color="#27AE60", edgecolor="black", linewidth=1)
    for i, (c, a) in enumerate(zip(claimed, actual)):
        ax.text(i - w / 2, c, f"{c:,.0f}", ha="center", va="bottom", fontsize=10,
                color="#C0392B", fontweight="bold")
        ax.text(i + w / 2, a, f"{a:,.1f}", ha="center", va="bottom", fontsize=10,
                color="#1E8449", fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_title("P-10147 - AI FDE claim vs Foundry/local ground truth\n(Foundry SQL verified, AI summary hallucination confirmed)",
                 fontweight="bold")
    ax.set_yscale("symlog", linthresh=1)
    ax.legend(loc="upper right")
    ax.grid(axis="y", alpha=0.3)

    # annotation
    ax.text(0.02, 0.95,
            "Finding: AI FDE dataset_sql_query summary\ndeviates 10x+ from raw data.\nActual hot line is SC-168 (1207 kPa / 260C / 45 kg).",
            transform=ax.transAxes, fontsize=9, va="top",
            bbox=dict(facecolor="lightyellow", edgecolor="gray",
                      boxstyle="round,pad=0.5"))

    plt.tight_layout()
    plt.savefig(OUT / "05_ai_vs_reality.png")
    plt.close()
    print("  ✓ 05_ai_vs_reality.png")


# ---------------------------------------------------------------------------
# 06 — Safety radius: SC-168 주변 structural 구조물 집중도
# ---------------------------------------------------------------------------

def fig06_safety_context() -> None:
    all_types = []
    for t in ["piping", "structural", "equipment", "electrical", "hvac", "other"]:
        df = pd.read_parquet(BASE / "object_types" / f"{t}.parquet",
                             columns=["object_id", "display_name", "refined_class"])
        all_types.append(df)
    obj_all = pd.concat(all_types)

    fig, axes = plt.subplots(1, 2, figsize=(14, 7))
    for ax, (pname, pids, color) in zip(axes, [
        ("P-10147", p10147_ids, COLOR_P),
        ("SC-168", sc168_ids, COLOR_SC),
    ]):
        out_e = adj[adj["source_object_id"].isin(pids) & ~adj["target_object_id"].isin(pids)]
        in_e = adj[adj["target_object_id"].isin(pids) & ~adj["source_object_id"].isin(pids)]
        all_e = pd.concat([out_e, in_e])
        nbr_ids = set(all_e["source_object_id"]) | set(all_e["target_object_id"])
        nbr_ids -= pids
        nbrs = obj_all[obj_all["object_id"].isin(nbr_ids)].copy()
        # merge in max overlap per neighbor
        # merge overlap in
        max_ov = all_e.groupby(
            np.where(all_e["source_object_id"].isin(pids),
                     all_e["target_object_id"], all_e["source_object_id"])
        )["overlap_volume_m3"].max().rename("max_overlap_m3")
        nbrs = nbrs.merge(max_ov, left_on="object_id", right_index=True, how="left")
        top = nbrs.sort_values("max_overlap_m3", ascending=False).head(12)[::-1]
        palette = {"Piping": "#4A90E2", "Structure": "#27AE60",
                   "Equipment": "#F39C12", "Electrical": "#9B59B6",
                   "HVAC": "#1ABC9C", "Other": "#95A5A6"}
        colors = [palette.get(c, "gray") for c in top["refined_class"]]
        ax.barh(range(len(top)), top["max_overlap_m3"].values, color=colors)
        ax.set_yticks(range(len(top)))
        ax.set_yticklabels(
            [f"{n[:30]} [{c}]" for n, c in zip(top["display_name"], top["refined_class"])],
            fontsize=8,
        )
        ax.set_xlabel("Max overlap volume (m³)")
        ax.set_title(f"{pname} - Top 12 adjacent neighbors (by overlap)",
                     color=color, fontweight="bold")
        ax.grid(axis="x", alpha=0.3)

    plt.suptitle("Clash hotspots - Top 12 neighbors per pipeline",
                 fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUT / "06_safety_context.png")
    plt.close()
    print("  ✓ 06_safety_context.png")


# ---------------------------------------------------------------------------
# Run all
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"Output: {OUT}/")
    fig01_rankings()
    fig02_piperun_breakdown()
    fig03_component_types()
    fig04_adjacency_neighbors()
    fig05_ai_vs_reality()
    fig06_safety_context()
    print(f"\n✅ 6 figures saved to {OUT}/")
