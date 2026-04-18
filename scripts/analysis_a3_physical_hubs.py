"""A3 - Physical Hub centrality.

AI FDE insights 주장 "Foundation 620톤 + 221 adj" 는 hallucination.
실제 물리 허브 = M3 필터 후 degree × weight 복합 centrality Top 20.

Outputs:
  notebooks/figures/a3-physical-hubs/
    01_hub_ranking.png              (Top 20 bar + composite score)
    02_degree_weight_scatter.png    (all 11K objects: degree vs weight)
    03_refined_class_hub_share.png  (which types dominate the hubs)
    04_slab_0901_neighbors.png      (#1 candidate drill-down)
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE = Path("data/ontology/2026-04-12")
FIG = Path("notebooks/figures/a3-physical-hubs")
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

keep = ["object_id", "display_name", "refined_class", "dry_weight_kg",
        "bbox_volume_m3", "is_parent_box", "is_bbox_placeholder",
        "is_container", "adjacency_count", "level_val", "parent_id",
        "verdict", "system_path"]
all_obj = pd.concat([
    pd.read_parquet(BASE / "object_types" / f"{t}.parquet", columns=keep)
    for t in ["piping", "structural", "equipment", "electrical", "hvac", "other"]
])
adj = pd.read_parquet(BASE / "link_types" / "adjacent_to.parquet")
parent = pd.read_parquet(BASE / "link_types" / "has_parent.parquet")
print(f"Total objects: {len(all_obj):,} | adjacency edges: {len(adj):,} | parent edges: {len(parent):,}")

# ---------------------------------------------------------------------------
# Physical hubs (exclude parent box + placeholder)
# ---------------------------------------------------------------------------

phy = all_obj[
    ~all_obj["is_parent_box"].fillna(False)
    & ~all_obj["is_bbox_placeholder"].fillna(False)
].copy()
print(f"Physical objects (M3 filter): {len(phy):,}")

# Composite centrality: log1p(adj) * log1p(mass+1)
phy["adj_count"] = phy["adjacency_count"].fillna(0)
phy["mass"] = phy["dry_weight_kg"].fillna(0)
phy["score_centrality"] = np.log1p(phy["adj_count"]) * np.log1p(phy["mass"] + 1)

top20 = phy.nlargest(20, "score_centrality").copy()
top20.to_csv(OUT_CSV / "a3_physical_hubs_top20.csv", index=False)

# Debunk AI FDE claim
print("\n=== AI FDE 주장 vs 실제 ===")
print("  AI FDE: Foundation | 221 adj | 620,130 kg")
print(f"  실제 max adj: {phy['adj_count'].max():.0f} ({phy.loc[phy['adj_count'].idxmax(), 'display_name']})")
print(f"  실제 max mass: {phy['mass'].max():,.0f} kg ({phy.loc[phy['mass'].idxmax(), 'display_name']})")
print(f"  221 adj 조건 충족 객체: {(phy['adj_count'] >= 221).sum()}개")
print(f"  620톤 조건 충족 객체: {(phy['mass'] >= 620000).sum()}개")
print(f"  동시 충족: {((phy['adj_count'] >= 221) & (phy['mass'] >= 620000)).sum()}개")

print("\n=== 실제 Top 10 physical hubs (composite score) ===")
for i, (_, r) in enumerate(top20.head(10).iterrows(), 1):
    mass_str = f"{r['mass']:>10,.0f} kg" if r['mass'] > 0 else "  no mass "
    print(f" {i:>2}. [{r['refined_class']:<10}] {r['display_name'][:32]:<32}"
          f"  adj={r['adj_count']:>4.0f}  {mass_str}  L{r['level_val']:.0f}")

# ---------------------------------------------------------------------------
# Figure 01 — Top 20 hub ranking
# ---------------------------------------------------------------------------

fig, ax = plt.subplots(figsize=(14, 8))
top20_r = top20.iloc[::-1]  # reverse for bottom-up reading
labels = [
    f"{r['display_name'][:30]}  [{r['refined_class'][:4]}]  L{r['level_val']:.0f}"
    for _, r in top20_r.iterrows()
]
colors = [PALETTE.get(c, "gray") for c in top20_r["refined_class"]]
bars = ax.barh(range(len(top20_r)), top20_r["score_centrality"], color=colors, alpha=0.85)
ax.set_yticks(range(len(top20_r))); ax.set_yticklabels(labels, fontsize=8)
ax.set_xlabel("Centrality score = log1p(adj_count) × log1p(mass+1)")
ax.set_title("Top 20 Physical Hubs — Real Centrality\n"
             "(M3 parent-box/placeholder 제거 후, adj × weight 복합)",
             fontweight="bold")
ax.grid(axis="x", alpha=0.3)
# Annotate values
for i, (_, r) in enumerate(top20_r.iterrows()):
    mass_txt = f"{r['mass']:>7,.0f}kg" if r['mass'] > 0 else "—"
    ax.text(r["score_centrality"], i,
            f"  adj={int(r['adj_count'])} / m={mass_txt}",
            va="center", fontsize=7, color="dimgray")
plt.tight_layout()
plt.savefig(FIG / "01_hub_ranking.png")
plt.close()
print("  ✓ 01_hub_ranking.png")

# ---------------------------------------------------------------------------
# Figure 02 — degree vs weight scatter (all objects)
# ---------------------------------------------------------------------------

fig, ax = plt.subplots(figsize=(12, 7))
for cls, color in PALETTE.items():
    sub = phy[phy["refined_class"] == cls]
    ax.scatter(sub["adj_count"] + 0.1, sub["mass"] + 0.1, c=color, s=10,
               alpha=0.4, label=f"{cls} (n={len(sub):,})", edgecolors="none")
# Highlight top 5
for _, r in top20.head(5).iterrows():
    ax.scatter([r["adj_count"] + 0.1], [r["mass"] + 0.1], s=150, facecolor="none",
               edgecolor="red", linewidth=2, zorder=5)
    ax.annotate(r["display_name"][:25],
                (r["adj_count"] + 0.1, r["mass"] + 0.1),
                fontsize=7, xytext=(8, 5), textcoords="offset points",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="lightyellow", alpha=0.8))
# AI FDE hallucinated point
ax.scatter([221], [620000], s=200, marker="x", color="red", linewidth=3,
           label="AI FDE 주장 (hallucinated)")
ax.annotate("AI FDE claim\n(no such object)", (221, 620000), fontsize=9,
            color="red", xytext=(15, 0), textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="mistyrose"))

ax.set_xscale("symlog", linthresh=1)
ax.set_yscale("symlog", linthresh=1)
ax.set_xlabel("adjacency_count (+0.1 to log)")
ax.set_ylabel("dry_weight_kg (+0.1 to log)")
ax.set_title("Degree vs Weight — All 11,161 Physical Objects\n"
             "(AI FDE 주장 지점은 실제 데이터 없음)",
             fontweight="bold")
ax.legend(loc="upper left", fontsize=8)
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(FIG / "02_degree_weight_scatter.png")
plt.close()
print("  ✓ 02_degree_weight_scatter.png")

# ---------------------------------------------------------------------------
# Figure 03 — refined_class share in Top 50/100/500 hubs
# ---------------------------------------------------------------------------

fig, ax = plt.subplots(figsize=(11, 6))
tiers = [("Top 20", 20), ("Top 50", 50), ("Top 100", 100), ("Top 500", 500)]
width = 0.18
x = np.arange(len(tiers))
classes = list(PALETTE.keys())
for i, cls in enumerate(classes):
    counts = [(phy.nlargest(n, "score_centrality")["refined_class"] == cls).sum()
              for _, n in tiers]
    ax.bar(x + (i - 2.5) * width, counts, width, label=cls, color=PALETTE[cls])
ax.set_xticks(x); ax.set_xticklabels([t for t, _ in tiers])
ax.set_ylabel("Count of hubs in tier")
ax.set_title("refined_class 별 hub 비중 — Tier 커질수록 분포 변화", fontweight="bold")
ax.legend(fontsize=8); ax.grid(axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig(FIG / "03_refined_class_hub_share.png")
plt.close()
print("  ✓ 03_refined_class_hub_share.png")

# ---------------------------------------------------------------------------
# Figure 04 — #1 hub drill-down: neighbors
# ---------------------------------------------------------------------------

# Use BaseSlab-001-0001 (massive 82t + 247 adj) as the drill-down case
hub_id = top20.iloc[0]["object_id"]
hub_name = top20.iloc[0]["display_name"]
hub_obj = top20.iloc[0]

# Find neighbors
nbr_ids = set(
    adj[adj["source_object_id"] == hub_id]["target_object_id"]
) | set(
    adj[adj["target_object_id"] == hub_id]["source_object_id"]
)
nbrs = all_obj[all_obj["object_id"].isin(nbr_ids)].copy()
nbr_cls = nbrs["refined_class"].value_counts()

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# left: neighbor refined_class pie
colors = [PALETTE.get(c, "gray") for c in nbr_cls.index]
axes[0].pie(nbr_cls.values, labels=nbr_cls.index, colors=colors,
            autopct=lambda p: f"{p:.0f}%\n({int(round(p*len(nbrs)/100))})",
            startangle=90, textprops={"fontsize": 9})
axes[0].set_title(f"#1 hub \"{hub_name[:30]}\" — {len(nbrs)} neighbors",
                  fontweight="bold")

# right: top 15 neighbors by their own centrality
nbrs_phy = nbrs[~nbrs["is_parent_box"].fillna(False)].copy()
nbrs_phy["mass"] = nbrs_phy["dry_weight_kg"].fillna(0)
nbrs_phy["adj_count"] = nbrs_phy["adjacency_count"].fillna(0)
nbrs_phy["score"] = np.log1p(nbrs_phy["adj_count"]) * np.log1p(nbrs_phy["mass"] + 1)
nbrs_top = nbrs_phy.nlargest(15, "score").iloc[::-1]

labels = [f"{r['display_name'][:25]} [{r['refined_class'][:4]}]"
          for _, r in nbrs_top.iterrows()]
c = [PALETTE.get(r["refined_class"], "gray") for _, r in nbrs_top.iterrows()]
axes[1].barh(range(len(nbrs_top)), nbrs_top["score"], color=c, alpha=0.85)
axes[1].set_yticks(range(len(nbrs_top))); axes[1].set_yticklabels(labels, fontsize=8)
axes[1].set_xlabel("Neighbor centrality (adj × weight)")
axes[1].set_title(f"Top 15 neighbors by own centrality", fontweight="bold")
axes[1].grid(axis="x", alpha=0.3)

plt.suptitle(f"#1 Physical Hub Drill-down", fontsize=13, fontweight="bold")
plt.tight_layout()
plt.savefig(FIG / "04_top_hub_drilldown.png")
plt.close()
print("  ✓ 04_top_hub_drilldown.png")

print(f"\n✅ Done. Files in {FIG}/ and {OUT_CSV}/")
