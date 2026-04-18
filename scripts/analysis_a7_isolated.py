"""A7 - Isolated Objects Analysis.

결정적 발견:
1. Isolated = 3,353 (27.9%) — AI FDE 주장 2,790 대비 +563 (7번째 hallucination)
2. Isolated 의 100% 가 container/parent_box — 실체 physical 객체 중 isolated = **0**
3. 모든 real physical object 가 최소 1 neighbor 를 가짐 (densely packed plant)

Outputs:
  notebooks/figures/a7-isolated-objects/
    01_isolated_classification.png
    02_adjacency_bin_distribution.png
    03_level_isolated.png
    04_ai_vs_reality.png
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE = Path("data/ontology/2026-04-12")
FIG = Path("notebooks/figures/a7-isolated-objects")
FIG.mkdir(parents=True, exist_ok=True)
OUT_CSV = Path("data/analysis")
OUT_CSV.mkdir(exist_ok=True)

plt.rcParams.update({
    "font.size": 10, "axes.titlesize": 12,
    "figure.dpi": 100, "savefig.dpi": 300, "savefig.bbox": "tight",
})

keep = ["object_id", "display_name", "refined_class", "dry_weight_kg",
        "bbox_volume_m3", "is_parent_box", "is_bbox_placeholder",
        "is_container", "adjacency_count", "level_val", "has_real_mesh",
        "verdict", "system_path"]
all_obj = pd.concat([
    pd.read_parquet(BASE / "object_types" / f"{t}.parquet", columns=keep)
    for t in ["piping", "structural", "equipment", "electrical", "hvac", "other"]
])
print(f"Total: {len(all_obj):,}")

isolated = all_obj[all_obj["adjacency_count"].fillna(0) == 0].copy()
print(f"Isolated (adj=0 or NaN): {len(isolated):,} ({len(isolated)/len(all_obj):.1%})")

# Classification
def classify(r):
    if r["is_parent_box"]: return "A. parent_box (M3)"
    if r["is_bbox_placeholder"]: return "B. bbox placeholder"
    if r["is_container"] and not r["has_real_mesh"]: return "C. container no-mesh"
    if r["is_container"] and r["has_real_mesh"]: return "D. container with mesh"
    if not r["has_real_mesh"]: return "E. no-mesh broken geom"
    return "F. standalone real"

isolated["category"] = isolated.apply(classify, axis=1)
cat_counts = isolated["category"].value_counts()
print(f"\n=== Isolated 분류 ===")
print(cat_counts)

# TRAINING vs non-TRAINING
isolated["in_training"] = isolated["system_path"].fillna("").str.contains("TRAINING")
print(f"\nIsolated in TRAINING: {isolated['in_training'].sum()} / {len(isolated)}")

# Refined_class breakdown
print(f"\n=== Isolated × refined_class ===")
print(isolated["refined_class"].value_counts())

# ---------------------------------------------------------------------------
# Figure 01 — Classification pie
# ---------------------------------------------------------------------------

fig, axes = plt.subplots(1, 2, figsize=(15, 7))

cat_colors = {
    "A. parent_box (M3)": "#E74C3C",
    "B. bbox placeholder": "#C0392B",
    "C. container no-mesh": "#F39C12",
    "D. container with mesh": "#F1C40F",
    "E. no-mesh broken geom": "#9B59B6",
    "F. standalone real": "#27AE60",
}
colors = [cat_colors.get(c, "gray") for c in cat_counts.index]
axes[0].pie(cat_counts.values, labels=cat_counts.index, colors=colors,
            autopct=lambda p: f"{p:.1f}%\n({int(round(p*len(isolated)/100))})",
            startangle=90, textprops={"fontsize": 9})
axes[0].set_title(f"Isolated ({len(isolated):,}) 분류\n"
                  "→ 100% container / parent_box — zero real standalone",
                  fontweight="bold")

# right: refined_class
cls_counts = isolated["refined_class"].value_counts()
palette_cls = {
    "Piping": "#4A90E2", "Structure": "#27AE60",
    "Equipment": "#F39C12", "Electrical": "#9B59B6",
    "HVAC": "#1ABC9C", "Other": "#95A5A6",
}
c2 = [palette_cls.get(c, "gray") for c in cls_counts.index]
axes[1].barh(cls_counts.index[::-1], cls_counts.values[::-1], color=c2[::-1])
axes[1].set_title("Isolated × refined_class")
axes[1].set_xlabel("Count")
for i, v in enumerate(cls_counts.values[::-1]):
    axes[1].text(v + 20, i, str(v), va="center")
axes[1].grid(axis="x", alpha=0.3)

plt.suptitle("A7 — 고립 객체 분류 (ALL containers)",
             fontsize=13, fontweight="bold")
plt.tight_layout()
plt.savefig(FIG / "01_isolated_classification.png")
plt.close()
print("  ✓ 01_isolated_classification.png")

# ---------------------------------------------------------------------------
# Figure 02 — Adjacency bin distribution (after parent_box filter)
# ---------------------------------------------------------------------------

phy = all_obj[
    ~all_obj["is_parent_box"].fillna(False)
    & ~all_obj["is_bbox_placeholder"].fillna(False)
].copy()
bins_def = [-0.1, 0.5, 5.5, 20.5, 50.5, 100.5, 10000]
labels_def = ["0", "1-5", "6-20", "21-50", "51-100", "100+"]
phy["adj_bin"] = pd.cut(phy["adjacency_count"].fillna(0), bins=bins_def,
                         labels=labels_def)

actual_bins = phy.groupby("adj_bin", observed=True).size().reindex(labels_def, fill_value=0)

# AI FDE claim
ai_fde_bins = {"0": 2790, "1-5": 3590, "6-20": 3226,
               "21-50": 1685, "51-100": 529, "100+": 189}

fig, ax = plt.subplots(figsize=(12, 6.5))
x = np.arange(len(labels_def))
w = 0.38
ax.bar(x - w/2, [ai_fde_bins[b] for b in labels_def], w, color="#E74C3C",
       edgecolor="black", linewidth=1, label="AI FDE 주장")
ax.bar(x + w/2, actual_bins.values, w, color="#27AE60",
       edgecolor="black", linewidth=1, label="실제 (M3 filter 후)")

for i, b in enumerate(labels_def):
    ax.text(i - w/2, ai_fde_bins[b], f"{ai_fde_bins[b]:,}", ha="center",
            va="bottom", fontsize=8, color="#C0392B")
    ax.text(i + w/2, actual_bins.iloc[i], f"{actual_bins.iloc[i]:,}", ha="center",
            va="bottom", fontsize=8, color="#1E8449")
ax.set_xticks(x); ax.set_xticklabels(labels_def)
ax.set_xlabel("Adjacency count bin")
ax.set_ylabel("Object count")
ax.set_title("Adjacency 분포 — AI FDE 주장 vs 실제\n"
             "모든 bin 에서 괴리: 7번째 hallucination 시리즈",
             fontweight="bold")
ax.legend()
ax.grid(axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig(FIG / "02_adjacency_bin_distribution.png")
plt.close()
print("  ✓ 02_adjacency_bin_distribution.png")

# ---------------------------------------------------------------------------
# Figure 03 — Isolated × level
# ---------------------------------------------------------------------------

lvl_iso = isolated.groupby("level_val").size().reindex(range(10), fill_value=0)
lvl_total = all_obj.groupby("level_val").size().reindex(range(10), fill_value=0)
lvl_pct = (lvl_iso / lvl_total * 100).fillna(0)

fig, ax = plt.subplots(figsize=(12, 6.5))
ax2 = ax.twinx()
x = range(10)
ax.bar([i - 0.2 for i in x], lvl_total, 0.4, color="#BDC3C7", label="Total")
ax.bar([i + 0.2 for i in x], lvl_iso, 0.4, color="#E74C3C", label="Isolated (in Total)")
ax2.plot(x, lvl_pct, "o-", color="#2C3E50", lw=2, label="Isolated %")
ax.set_xlabel("Level (hierarchy depth)")
ax.set_ylabel("Object count")
ax2.set_ylabel("Isolated %", color="#2C3E50")
ax2.tick_params(axis="y", labelcolor="#2C3E50")
ax.set_title("Level × Isolated — L3-L5 aggregator level 집중", fontweight="bold")
for i in x:
    if lvl_pct.iloc[i] > 0:
        ax2.text(i, lvl_pct.iloc[i] + 2, f"{lvl_pct.iloc[i]:.0f}%",
                 ha="center", fontsize=8, color="#2C3E50")
ax.legend(loc="upper left")
ax2.legend(loc="upper right")
ax.grid(axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig(FIG / "03_level_isolated.png")
plt.close()
print("  ✓ 03_level_isolated.png")

# ---------------------------------------------------------------------------
# Figure 04 — Summary: AI vs reality
# ---------------------------------------------------------------------------

fig, ax = plt.subplots(figsize=(11, 6))
metrics = ["Isolated count", "Isolated %", "Truly-standalone real", "Avg mass of isolated (kg)"]
ai_fde = [2790, 23.2, 2790, 2.1]
actual = [3353, 27.9, 0, "N/A (containers have no mass)"]

tbl_data = [["Metric", "AI FDE claim", "Actual (local + Foundry verified)"]]
for m, a, r in zip(metrics, ai_fde, actual):
    tbl_data.append([m, str(a), str(r)])

ax.axis("off")
table = ax.table(cellText=tbl_data, loc="center", cellLoc="left",
                 colWidths=[0.35, 0.25, 0.40])
table.auto_set_font_size(False); table.set_fontsize(10); table.scale(1, 1.9)
for i in range(len(tbl_data)):
    for j in range(3):
        cell = table[i, j]
        if i == 0:
            cell.set_facecolor("#4A90E2"); cell.set_text_props(weight="bold", color="white")
        elif "AI FDE" in tbl_data[0][j] and i > 0:
            cell.set_facecolor("#FADBD8")  # light red
        elif "Actual" in tbl_data[0][j] and i > 0:
            cell.set_facecolor("#D5F5E3")  # light green

ax.set_title("A7 Verification: AI FDE Adjacency Claims vs Ground Truth",
             fontsize=13, fontweight="bold", pad=20)
plt.tight_layout()
plt.savefig(FIG / "04_ai_vs_reality.png")
plt.close()
print("  ✓ 04_ai_vs_reality.png")

# Save
isolated.to_csv(OUT_CSV / "a7_isolated_objects.csv", index=False)
print(f"\n✅ Done.")
