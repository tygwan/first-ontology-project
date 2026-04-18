"""A1 - Clash Detection Ranking.

110,173 adjacency overlap edges 전수 분석:
- parent-box contamination 제외
- overlap / mass / pressure 복합 스코어
- Top 100 clash 랭킹 + refined_class 쌍 매트릭스

Outputs:
  notebooks/figures/a1-clash-ranking/
    01_score_distribution.png
    02_refined_class_matrix.png
    03_top_clashes_scatter.png
    04_pipeline_clash_breakdown.png
  data/analysis/a1_clash_ranking_top100.csv
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE = Path("data/ontology/2026-04-12")
FIG = Path("notebooks/figures/a1-clash-ranking")
FIG.mkdir(parents=True, exist_ok=True)
OUT_CSV = Path("data/analysis")
OUT_CSV.mkdir(exist_ok=True)

plt.rcParams.update({
    "font.size": 10, "axes.titlesize": 12,
    "figure.dpi": 100, "savefig.dpi": 300, "savefig.bbox": "tight",
})

PALETTE = {
    "Piping": "#4A90E2", "Structure": "#27AE60",
    "Equipment": "#F39C12", "Electrical": "#9B59B6",
    "HVAC": "#1ABC9C", "Other": "#95A5A6",
}

# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

print("[1/5] Loading data...")
adj = pd.read_parquet(BASE / "link_types" / "adjacent_to.parquet")
link_pipe = pd.read_parquet(BASE / "link_types" / "belongs_to_pipeline.parquet")
pipelines = pd.read_parquet(BASE / "bim_pipelines.parquet")[
    ["pipeline_name", "max_pressure_kpa", "max_temperature_c"]
]

keep_cols = ["object_id", "display_name", "refined_class", "dry_weight_kg",
             "design_pressure_kpa", "design_temperature_c",
             "is_parent_box", "is_bbox_placeholder", "verdict"]
obj_all = pd.concat([
    pd.read_parquet(BASE / "object_types" / f"{t}.parquet", columns=keep_cols)
    for t in ["piping", "structural", "equipment", "electrical", "hvac", "other"]
])
print(f"  adj={len(adj):,} / obj={len(obj_all):,} / pipelines={len(pipelines)}")

# ---------------------------------------------------------------------------
# Enrich edges with src/tgt attributes
# ---------------------------------------------------------------------------

print("[2/5] Enriching edges...")
sfx_src = {c: f"src_{c}" for c in keep_cols if c != "object_id"}
sfx_tgt = {c: f"tgt_{c}" for c in keep_cols if c != "object_id"}
e = adj.merge(
    obj_all.rename(columns=sfx_src),
    left_on="source_object_id", right_on="object_id", how="left",
).drop("object_id", axis=1)
e = e.merge(
    obj_all.rename(columns=sfx_tgt),
    left_on="target_object_id", right_on="object_id", how="left",
).drop("object_id", axis=1)

# pipeline attribution (src side if Piping in a pipeline)
pipe_map = link_pipe.merge(pipelines, on="pipeline_name", how="left")
e = e.merge(
    pipe_map[["object_id", "pipeline_name", "max_pressure_kpa"]].rename(
        columns={"object_id": "src_id", "pipeline_name": "src_pipeline",
                 "max_pressure_kpa": "src_pipe_max_p"}
    ),
    left_on="source_object_id", right_on="src_id", how="left",
).drop("src_id", axis=1)
e = e.merge(
    pipe_map[["object_id", "pipeline_name", "max_pressure_kpa"]].rename(
        columns={"object_id": "tgt_id", "pipeline_name": "tgt_pipeline",
                 "max_pressure_kpa": "tgt_pipe_max_p"}
    ),
    left_on="target_object_id", right_on="tgt_id", how="left",
).drop("tgt_id", axis=1)

print(f"  enriched edges: {len(e):,}")

# ---------------------------------------------------------------------------
# Filter + scoring
# ---------------------------------------------------------------------------

print("[3/5] Filtering + scoring...")
before = len(e)
# 1) overlap only
e = e[e["relation_type"] == "overlap"]
# 2) exclude parent-box contamination (either side)
e = e[~(e["src_is_parent_box"].fillna(False) | e["tgt_is_parent_box"].fillna(False))]
# 3) exclude bbox placeholders
e = e[~(e["src_is_bbox_placeholder"].fillna(False) | e["tgt_is_bbox_placeholder"].fillna(False))]
# 4) exclude self-pipeline clashes (same pipeline = internal adjacency)
e = e[~((e["src_pipeline"].notna()) & (e["src_pipeline"] == e["tgt_pipeline"]))]
# 5) minimum overlap 0.001 m³ (1 liter)
e = e[e["overlap_volume_m3"] >= 0.001]
print(f"  {before:,} → {len(e):,} (M3 parent/placeholder 제외 + overlap only + 최소 1L)")

# Composite score
e["mass_total"] = e["src_dry_weight_kg"].fillna(0) + e["tgt_dry_weight_kg"].fillna(0)
e["pipe_max_p"] = e[["src_pipe_max_p", "tgt_pipe_max_p"]].fillna(0).max(axis=1)
# design_pressure on objects (piping has it)
e["obj_max_p"] = e[["src_design_pressure_kpa", "tgt_design_pressure_kpa"]].fillna(0).max(axis=1)
e["max_p"] = e[["pipe_max_p", "obj_max_p"]].max(axis=1)

# 3 scores
e["score_overlap"] = e["overlap_volume_m3"]
e["score_mass"] = e["overlap_volume_m3"] * e["mass_total"]
e["score_pressure"] = e["overlap_volume_m3"] * (e["max_p"] + 1)   # +1 to avoid 0 where no pressure data
e["score_composite"] = np.log1p(e["overlap_volume_m3"]) * np.log1p(e["mass_total"]) * np.log1p(e["max_p"] + 1)

# Top 100
top100 = e.nlargest(100, "score_composite").copy()
top100_cols = [
    "src_display_name", "src_refined_class", "src_dry_weight_kg",
    "tgt_display_name", "tgt_refined_class", "tgt_dry_weight_kg",
    "overlap_volume_m3", "max_p", "mass_total",
    "score_composite", "score_overlap", "score_mass", "score_pressure",
    "src_pipeline", "tgt_pipeline",
]
top100[top100_cols].to_csv(OUT_CSV / "a1_clash_ranking_top100.csv", index=False)
print(f"  Top 100 saved → {OUT_CSV / 'a1_clash_ranking_top100.csv'}")

# Additional rankings — different lenses
e_cross = e[e["src_refined_class"] != e["tgt_refined_class"]].copy()
top50_cross = e_cross.nlargest(50, "score_composite")[top100_cols]
top50_cross.to_csv(OUT_CSV / "a1_clash_ranking_cross_type_top50.csv", index=False)

top50_pressure = e[e["max_p"] > 0].nlargest(50, "score_pressure")[top100_cols]
top50_pressure.to_csv(OUT_CSV / "a1_clash_ranking_pressure_weighted_top50.csv", index=False)

print(f"  Cross-type top50 + Pressure-weighted top50 also saved")

# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------

print("[4/5] Generating figures...")

# 01 — score distribution (4 panel)
fig, axes = plt.subplots(2, 2, figsize=(14, 8))
for ax, (col, title, log) in zip(axes.flat, [
    ("overlap_volume_m3", "Overlap Volume (m³)", True),
    ("mass_total", "Combined Mass (kg)", True),
    ("max_p", "Max Pressure (kPa, pipeline or object)", False),
    ("score_composite", "Composite Score (log-log-log)", False),
]):
    vals = e[col].dropna()
    vals = vals[vals > 0] if log else vals
    ax.hist(vals, bins=60, color="#4A90E2", edgecolor="white", alpha=0.8)
    if log:
        ax.set_xscale("log")
    ax.set_title(f"{title}\n(n={len(vals):,}, median={vals.median():.3g})")
    ax.set_ylabel("# edges")
    ax.grid(alpha=0.3)
plt.suptitle("Clash Score Distributions (after filtering parent-box + <1L overlap)",
             fontsize=13, fontweight="bold")
plt.tight_layout()
plt.savefig(FIG / "01_score_distribution.png")
plt.close()
print("  ✓ 01_score_distribution.png")

# 02 — refined_class pair matrix
pair = e.groupby(["src_refined_class", "tgt_refined_class"]).agg(
    edges=("overlap_volume_m3", "size"),
    total_vol=("overlap_volume_m3", "sum"),
    max_vol=("overlap_volume_m3", "max"),
).reset_index()
classes = ["Piping", "Structure", "Equipment", "Electrical", "HVAC", "Other"]
mat_count = pair.pivot(index="src_refined_class", columns="tgt_refined_class",
                       values="edges").reindex(index=classes, columns=classes).fillna(0)
mat_vol = pair.pivot(index="src_refined_class", columns="tgt_refined_class",
                     values="total_vol").reindex(index=classes, columns=classes).fillna(0)

fig, axes = plt.subplots(1, 2, figsize=(15, 6))
for ax, mat, title, cmap in [
    (axes[0], mat_count, "Edge Count", "Blues"),
    (axes[1], mat_vol, "Total Overlap Volume (m³)", "Reds"),
]:
    im = ax.imshow(mat.values, cmap=cmap)
    ax.set_xticks(range(len(classes))); ax.set_xticklabels(classes, rotation=45, ha="right")
    ax.set_yticks(range(len(classes))); ax.set_yticklabels(classes)
    ax.set_title(title)
    for i in range(len(classes)):
        for j in range(len(classes)):
            v = mat.values[i, j]
            if v > 0:
                ax.text(j, i, f"{int(v):,}" if title == "Edge Count" else f"{v:.1f}",
                        ha="center", va="center",
                        color="white" if v > mat.values.max() * 0.5 else "black",
                        fontsize=8)
    plt.colorbar(im, ax=ax, shrink=0.8)
plt.suptitle("Clash Matrix — refined_class × refined_class", fontsize=13, fontweight="bold")
plt.tight_layout()
plt.savefig(FIG / "02_refined_class_matrix.png")
plt.close()
print("  ✓ 02_refined_class_matrix.png")

# 03 — Top 100 scatter (mass vs overlap, color by max_p)
fig, ax = plt.subplots(figsize=(12, 7))
sc = ax.scatter(top100["mass_total"] + 0.1, top100["overlap_volume_m3"],
                c=top100["max_p"], s=80, cmap="plasma", alpha=0.75,
                edgecolors="black", linewidths=0.5)
cbar = plt.colorbar(sc, ax=ax); cbar.set_label("Max Pressure (kPa)")
# hilite top 5
top5 = top100.head(5)
for _, r in top5.iterrows():
    label = f"{r['src_display_name'][:20]}\n↔ {r['tgt_display_name'][:20]}"
    ax.annotate(label, (r["mass_total"] + 0.1, r["overlap_volume_m3"]),
                fontsize=7, xytext=(8, 8), textcoords="offset points",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="lightyellow", alpha=0.8))
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlabel("Combined mass (kg)"); ax.set_ylabel("Overlap volume (m³)")
ax.set_title(f"Top 100 Clash Candidates — mass vs overlap (color=pressure)\n"
             f"Filtered from {before:,} → {len(e):,} edges")
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(FIG / "03_top_clashes_scatter.png")
plt.close()
print("  ✓ 03_top_clashes_scatter.png")

# 04 — Three lenses panel (composite / cross-type / pressure-weighted top 5 each)
fig, axes = plt.subplots(3, 1, figsize=(14, 10))
lenses = [
    ("Composite (log-log-log)", top100.head(10), "score_composite", "#3498DB"),
    ("Cross-type only (different refined_class)",
     e_cross.nlargest(10, "score_composite"), "score_composite", "#E67E22"),
    ("Pressure-weighted (p>0 only)",
     e[e["max_p"] > 0].nlargest(10, "score_pressure"), "score_pressure", "#E74C3C"),
]
for ax, (title, top, col, color) in zip(axes, lenses):
    labels = [
        f"{r['src_display_name'][:22]} [{r['src_refined_class'][:4]}]  ↔  "
        f"{r['tgt_display_name'][:22]} [{r['tgt_refined_class'][:4]}]"
        for _, r in top.iterrows()
    ]
    vals = top[col].values
    y = np.arange(len(top))
    ax.barh(y, vals, color=color, alpha=0.8)
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=7)
    ax.invert_yaxis()
    ax.set_title(f"Top 10 — {title}", fontsize=11, fontweight="bold")
    ax.set_xlabel(col)
    ax.grid(axis="x", alpha=0.3)
    # annotate overlap & mass
    for i, (_, r) in enumerate(top.iterrows()):
        ax.text(vals[i], i,
                f" ov={r['overlap_volume_m3']:.1f}m³ / m={r['mass_total']:.0f}kg / p={r['max_p']:.0f}",
                va="center", fontsize=7, color="dimgray")
plt.suptitle("Clash Rankings — 3 lenses", fontsize=13, fontweight="bold")
plt.tight_layout()
plt.savefig(FIG / "04_three_lenses.png")
plt.close()
print("  ✓ 04_three_lenses.png")

# ---------------------------------------------------------------------------
# Print Top 10 to console
# ---------------------------------------------------------------------------

print("\n[5/5] Top 10 composite score clashes:\n")
for i, (_, r) in enumerate(top100.head(10).iterrows(), 1):
    print(f" {i:>2}. [{r['src_refined_class']:<10}] {r['src_display_name'][:30]:<30}"
          f"  ↔  [{r['tgt_refined_class']:<10}] {r['tgt_display_name'][:30]:<30}"
          f"  | ov={r['overlap_volume_m3']:>8.2f} m³"
          f" mass={r['mass_total']:>10.1f} kg"
          f" p={r['max_p']:>7.1f} kPa")

# Stats summary
print(f"\n--- Summary ---")
print(f"Initial overlap edges:     {adj[adj['relation_type']=='overlap'].shape[0]:,}")
print(f"After parent-box filter:   {len(e):,}")
print(f"Edges with pipeline info:  {e['src_pipeline'].notna().sum():,} (src) | "
      f"{e['tgt_pipeline'].notna().sum():,} (tgt)")
print(f"Edges with pressure > 0:   {(e['max_p'] > 0).sum():,}")
print(f"\n✅ Done. Files in {FIG}/ and {OUT_CSV}/")
