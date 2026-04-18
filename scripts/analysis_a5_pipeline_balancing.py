"""A5 - Pipeline Balancing.

147 pipelines 전체 분포 + IQR outlier + typical profile + prefix 분류.

Outputs:
  notebooks/figures/a5-pipeline-balancing/
    01_distribution_boxplots.png       (4 metric IQR)
    02_outlier_table.png               (typical vs outlier table as fig)
    03_prefix_groups.png               (pipeline name prefix 분포 → 플랜트 구조)
    04_typical_profile_radar.png       (median profile)
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE = Path("data/ontology/2026-04-12")
FIG = Path("notebooks/figures/a5-pipeline-balancing")
FIG.mkdir(parents=True, exist_ok=True)
OUT_CSV = Path("data/analysis")
OUT_CSV.mkdir(exist_ok=True)

plt.rcParams.update({
    "font.size": 10, "axes.titlesize": 12,
    "figure.dpi": 100, "savefig.dpi": 300, "savefig.bbox": "tight",
})

pipe = pd.read_parquet(BASE / "bim_pipelines.parquet")
print(f"Pipelines: {len(pipe)}")

# ---------------------------------------------------------------------------
# Prefix classification
# ---------------------------------------------------------------------------

def prefix_group(name):
    if not isinstance(name, str): return "UNKNOWN"
    if name.startswith("TRN") or name.startswith("P-101") or name.startswith("P-102"):
        return "TRN / P-10xxx (training)"
    if name.startswith("03-") or name.startswith("04-") or name.startswith("1210-"):
        return "03- / 04- (refinery unit)"
    if name.startswith("PR01-"): return "PR01- (process area 1)"
    if name.startswith("U01-") or name.startswith("U02-") or name.startswith("U20-") or name.startswith("U24-"):
        return "Uxx- (unit areas)"
    if name.startswith("SC-"): return "SC- (Sulphur recovery)"
    if name.startswith("S-"): return "S- (steam / service)"
    if name.startswith("400-") or name.startswith("300-"): return "3xx- / 4xx- (area codes)"
    if name.startswith("P-"): return "P-xxx (process)"
    return "Other (meta / misc)"

pipe["prefix_group"] = pipe["pipeline_name"].apply(prefix_group)

# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

metrics_main = ["component_count", "pipe_run_count", "total_dry_weight_kg",
                "max_pressure_kpa", "max_temperature_c"]
summary = pipe[metrics_main].describe(percentiles=[.25, .5, .75]).T
print(summary.round(2))

# IQR outliers for complexity / weight / pressure
def iqr_outliers(series, k=1.5):
    q1, q3 = series.quantile(.25), series.quantile(.75)
    return series[series > q3 + k * (q3 - q1)]

outliers_comp = pipe[pipe.index.isin(iqr_outliers(pipe["component_count"]).index)].sort_values(
    "component_count", ascending=False
)
outliers_weight = pipe[pipe.index.isin(iqr_outliers(pipe["total_dry_weight_kg"]).index)].sort_values(
    "total_dry_weight_kg", ascending=False
)
outliers_pressure = pipe[pipe["max_pressure_kpa"] > 1].sort_values(
    "max_pressure_kpa", ascending=False
)

print(f"\nOutliers — component_count > IQR upper: {len(outliers_comp)}")
print(f"Outliers — weight > IQR upper: {len(outliers_weight)}")
print(f"Outliers — pressure > 1 kPa: {len(outliers_pressure)}")

# ---------------------------------------------------------------------------
# Figure 01 — Distribution box plots
# ---------------------------------------------------------------------------

fig, axes = plt.subplots(2, 2, figsize=(14, 9))
plot_metrics = [
    ("component_count", "Component Count", axes[0][0], False),
    ("total_dry_weight_kg", "Total Dry Weight (kg)", axes[0][1], True),
    ("max_pressure_kpa", "Max Pressure (kPa)", axes[1][0], True),
    ("max_temperature_c", "Max Temperature (°C)", axes[1][1], False),
]
for col, title, ax, logy in plot_metrics:
    data = pipe[col].dropna()
    bp = ax.boxplot(data, vert=True, patch_artist=True, widths=0.5,
                    boxprops=dict(facecolor="#4A90E2", alpha=0.7),
                    medianprops=dict(color="#E74C3C", lw=2))
    ax.scatter(np.full(len(data), 1) + np.random.uniform(-0.15, 0.15, len(data)),
               data, alpha=0.3, s=15, color="#2C3E50")
    ax.set_title(f"{title}\n(n={len(data)}, median={data.median():.2f}, max={data.max():.2f})")
    ax.set_ylabel(title)
    if logy:
        ax.set_yscale("symlog", linthresh=1)
    ax.grid(alpha=0.3)
    ax.set_xticks([])
    # outlier labels
    q3 = data.quantile(.75); iqr = q3 - data.quantile(.25)
    upper = q3 + 1.5 * iqr
    top = data[data > upper].nlargest(5)
    for v, idx in zip(top.values, top.index):
        name = pipe.loc[idx, "pipeline_name"]
        ax.annotate(name[:12], (1.15, v), fontsize=7, color="red")

plt.suptitle("147 Pipelines — 분포 + IQR Outliers",
             fontsize=13, fontweight="bold")
plt.tight_layout()
plt.savefig(FIG / "01_distribution_boxplots.png")
plt.close()
print("  ✓ 01_distribution_boxplots.png")

# ---------------------------------------------------------------------------
# Figure 02 — Typical profile table vs outliers
# ---------------------------------------------------------------------------

typical = pipe[metrics_main].median()
fig, ax = plt.subplots(figsize=(12, 7))
ax.axis("off")

tbl_data = [["Metric", "Typical (median)", "Outlier example (name, value)"]]
for m in metrics_main:
    med = typical[m]
    out_idx = pipe[m].idxmax()
    out_name = pipe.loc[out_idx, "pipeline_name"]
    out_val = pipe.loc[out_idx, m]
    tbl_data.append([m, f"{med:,.2f}", f"{out_name} → {out_val:,.2f}"])

table = ax.table(cellText=tbl_data, loc="center", cellLoc="left",
                 colWidths=[0.3, 0.25, 0.45])
table.auto_set_font_size(False); table.set_fontsize(10); table.scale(1, 1.8)
for i in range(len(tbl_data)):
    for j in range(3):
        cell = table[i, j]
        if i == 0:
            cell.set_facecolor("#4A90E2"); cell.set_text_props(weight="bold", color="white")
        elif i % 2 == 0:
            cell.set_facecolor("#F0F3F4")
ax.set_title("Typical Pipeline Profile vs Max Outliers",
             fontsize=13, fontweight="bold", pad=20)
plt.tight_layout()
plt.savefig(FIG / "02_typical_vs_outliers.png")
plt.close()
print("  ✓ 02_typical_vs_outliers.png")

# ---------------------------------------------------------------------------
# Figure 03 — Prefix grouping (플랜트 구조)
# ---------------------------------------------------------------------------

grp_stats = pipe.groupby("prefix_group").agg(
    count=("pipeline_name", "size"),
    total_components=("component_count", "sum"),
    total_weight=("total_dry_weight_kg", "sum"),
    max_pressure=("max_pressure_kpa", "max"),
).reset_index().sort_values("count", ascending=False)

fig, axes = plt.subplots(1, 2, figsize=(15, 6))
axes[0].barh(grp_stats["prefix_group"][::-1], grp_stats["count"][::-1], color="#27AE60")
axes[0].set_title(f"Pipeline count by prefix\n({len(pipe)} pipelines → plant area 분류)",
                  fontweight="bold")
axes[0].set_xlabel("Pipeline count")
axes[0].grid(axis="x", alpha=0.3)
for i, v in enumerate(grp_stats["count"][::-1]):
    axes[0].text(v + 0.5, i, str(v), va="center", fontsize=9)

axes[1].barh(grp_stats["prefix_group"][::-1], grp_stats["total_components"][::-1], color="#F39C12")
axes[1].set_title(f"Total components by prefix\n(prefix 별 플랜트 규모 비중)",
                  fontweight="bold")
axes[1].set_xlabel("Total component count")
axes[1].grid(axis="x", alpha=0.3)
for i, v in enumerate(grp_stats["total_components"][::-1]):
    axes[1].text(v + 30, i, f"{int(v):,}", va="center", fontsize=9)

plt.suptitle("Prefix 별 플랜트 구조 분석", fontsize=13, fontweight="bold")
plt.tight_layout()
plt.savefig(FIG / "03_prefix_groups.png")
plt.close()
print("  ✓ 03_prefix_groups.png")

# ---------------------------------------------------------------------------
# Figure 04 — Typical profile radar
# ---------------------------------------------------------------------------

radar_metrics = ["component_count", "pipe_run_count", "total_dry_weight_kg",
                 "flange_count", "tee_count"]
# normalize each to [0,1] using max across dataset
norm = pipe[radar_metrics].copy()
max_vals = norm.max()
norm_typical = (pipe[radar_metrics].median() / max_vals).fillna(0)
# 3 comparison cases
comparison = {
    "Typical (median)": norm_typical,
    "SC-168 (hot line)": (pipe[pipe["pipeline_name"]=="SC-168"][radar_metrics].iloc[0] / max_vals),
    "P-10147 (TRN complex)": (pipe[pipe["pipeline_name"]=="P-10147"][radar_metrics].iloc[0] / max_vals),
    "P-10162 (heaviest)": (pipe[pipe["pipeline_name"]=="P-10162"][radar_metrics].iloc[0] / max_vals),
}

N = len(radar_metrics)
angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
angles += angles[:1]

fig, ax = plt.subplots(figsize=(9, 9), subplot_kw=dict(polar=True))
colors = ["#95A5A6", "#E74C3C", "#4A90E2", "#F39C12"]
for (name, vals), color in zip(comparison.items(), colors):
    v = vals.values.tolist(); v += v[:1]
    ax.plot(angles, v, "o-", lw=2, label=name, color=color)
    ax.fill(angles, v, alpha=0.15, color=color)
ax.set_theta_offset(np.pi / 2); ax.set_theta_direction(-1)
ax.set_xticks(angles[:-1])
ax.set_xticklabels([m.replace("_", " ") for m in radar_metrics], fontsize=9)
ax.set_ylim(0, 1.05)
ax.set_title("Pipeline Profile Radar\n(각 축 = 147 pipelines 중 최대값 대비 비율)",
             fontweight="bold", pad=30)
ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=9)
plt.tight_layout()
plt.savefig(FIG / "04_typical_profile_radar.png")
plt.close()
print("  ✓ 04_typical_profile_radar.png")

# ---------------------------------------------------------------------------
# Export data
# ---------------------------------------------------------------------------

pipe_enriched = pipe[["pipeline_name", "prefix_group"] + metrics_main +
                     ["flange_count", "tee_count", "mesh_coverage_pct"]]
pipe_enriched.to_csv(OUT_CSV / "a5_pipeline_enriched.csv", index=False)
print(f"\n✅ Done.")
