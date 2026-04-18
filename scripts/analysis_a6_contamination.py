"""A6 - Hierarchy Contamination Detection (M3 연장).

주요 발견:
1. 12,009 중 98.8% 가 TRAINING 경로 — 전체 dataset 이 튜토리얼 데이터
2. M3 에서 식별된 448 parent_box 외 추가 30 unflagged contamination 후보
3. "Pipelines" 메타-이름 = L5 에서 유일한 발견 (153 components 오분류)
4. 메타-이름 27개 전수 — 정상 L4 aggregator 26개 + 비정상 L5 "Pipelines" 1개

Outputs:
  notebooks/figures/a6-contamination/
    01_training_vs_production.png
    02_flag_matrix.png
    03_level_contamination.png
    04_meta_names_drill.png
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
FIG = Path("notebooks/figures/a6-contamination")
FIG.mkdir(parents=True, exist_ok=True)
OUT_CSV = Path("data/analysis")
OUT_CSV.mkdir(exist_ok=True)

# (rcParams handled by setup_plot_style)

keep = ["object_id", "display_name", "refined_class", "original_class",
        "dry_weight_kg", "bbox_volume_m3", "is_parent_box", "is_bbox_placeholder",
        "is_container", "adjacency_count", "level_val", "parent_id",
        "has_real_mesh", "verdict", "system_path"]
all_obj = pd.concat([
    pd.read_parquet(BASE / "object_types" / f"{t}.parquet", columns=keep)
    for t in ["piping", "structural", "equipment", "electrical", "hvac", "other"]
])
print(f"Total: {len(all_obj):,}")

# Training flag
all_obj["in_training"] = all_obj["system_path"].fillna("").str.contains("TRAINING", case=False)
print(f"TRAINING 경로: {all_obj['in_training'].sum():,} ({all_obj['in_training'].mean():.1%})")
print(f"Non-TRAINING: {(~all_obj['in_training']).sum():,}")

# ---------------------------------------------------------------------------
# Figure 01 — TRAINING vs non-TRAINING breakdown
# ---------------------------------------------------------------------------

fig, axes = plt.subplots(1, 2, figsize=(14, 6))
# left: overall pie
cts = all_obj["in_training"].value_counts()
axes[0].pie(cts.values, labels=["TRAINING", "non-TRAINING"],
            colors=["#F39C12", "#27AE60"],
            autopct=lambda p: f"{p:.1f}%\n({int(round(p*len(all_obj)/100))})",
            startangle=90, textprops={"fontsize": 11})
axes[0].set_title("전체 12,009 objects — 98.8% TRAINING", fontweight="bold")

# right: non-TRAINING 149 breakdown
non = all_obj[~all_obj["in_training"]]
counts = non.groupby("path_second" if "path_second" in non.columns else non["system_path"].str.split(" > ").str[1]).size().sort_values(ascending=False)
if len(counts) > 0:
    axes[1].barh(counts.index[::-1], counts.values[::-1], color="#27AE60")
    axes[1].set_title(f"non-TRAINING 149개 내역 — 2번째 토큰", fontweight="bold")
    axes[1].set_xlabel("Count")
    for i, v in enumerate(counts.values[::-1]):
        axes[1].text(v + 2, i, str(v), va="center")
axes[1].grid(axis="x", alpha=0.3)

plt.suptitle("데이터셋 성격 재정의 — 거의 전부 TRAINING 데이터", fontsize=13, fontweight="bold")
plt.tight_layout()
plt.savefig(FIG / "01_training_vs_production.png")
plt.close()
print("  ✓ 01_training_vs_production.png")

# ---------------------------------------------------------------------------
# Figure 02 — Flag combination matrix
# ---------------------------------------------------------------------------

pb = all_obj["is_parent_box"].fillna(False)
bp = all_obj["is_bbox_placeholder"].fillna(False)
ic = all_obj["is_container"].fillna(False)
# 8 combos
combos = []
for p in [True, False]:
    for b in [True, False]:
        for c in [True, False]:
            n = ((pb == p) & (bp == b) & (ic == c)).sum()
            if n > 0:
                combos.append({"parent_box": p, "bbox_placeholder": b,
                               "is_container": c, "count": n})
combos_df = pd.DataFrame(combos).sort_values("count", ascending=False)
print("\n=== Flag 조합 ===")
print(combos_df.to_string(index=False))

fig, ax = plt.subplots(figsize=(12, 6))
labels = [f"pb={r['parent_box']}, bp={r['bbox_placeholder']}, ic={r['is_container']}"
          for _, r in combos_df.iterrows()]
colors_c = ["#E74C3C" if r["parent_box"] or r["bbox_placeholder"]
            else "#F39C12" if r["is_container"] else "#27AE60"
            for _, r in combos_df.iterrows()]
ax.barh(range(len(labels)), combos_df["count"].values, color=colors_c)
ax.set_yticks(range(len(labels))); ax.set_yticklabels(labels, fontsize=9)
ax.set_xlabel("Object count")
ax.set_title(f"Object 분류 by Flag 조합 (총 {len(all_obj):,})\n"
             "[RED] = 이미 필터 대상 (parent_box or bbox_placeholder)\n"
             "[ORANGE] = 애매 (is_container 만)\n"
             "[GREEN] = 실체 물리 객체",
             fontweight="bold")
for i, v in enumerate(combos_df["count"].values):
    ax.text(v + 50, i, f"{v:,}", va="center", fontsize=9)
ax.grid(axis="x", alpha=0.3)
plt.tight_layout()
plt.savefig(FIG / "02_flag_matrix.png")
plt.close()
print("  ✓ 02_flag_matrix.png")

# ---------------------------------------------------------------------------
# Figure 03 — Level × contamination
# ---------------------------------------------------------------------------

lvl = all_obj.groupby("level_val").agg(
    total=("object_id", "size"),
    parent_box=("is_parent_box", lambda x: x.fillna(False).sum()),
    placeholder=("is_bbox_placeholder", lambda x: x.fillna(False).sum()),
    container_only=("is_container", lambda x: (x.fillna(False)
                    & ~all_obj.loc[x.index, "is_parent_box"].fillna(False)).sum()),
).reset_index()
lvl["real"] = lvl["total"] - lvl["parent_box"] - lvl["placeholder"] - lvl["container_only"]
lvl = lvl[lvl["total"] > 0]

fig, ax = plt.subplots(figsize=(13, 7))
x = lvl["level_val"]
ax.bar(x, lvl["real"], color="#27AE60", label="Real (physical)")
ax.bar(x, lvl["container_only"], bottom=lvl["real"], color="#F39C12", label="Container only")
ax.bar(x, lvl["placeholder"], bottom=lvl["real"] + lvl["container_only"],
       color="#9B59B6", label="BBox placeholder")
ax.bar(x, lvl["parent_box"],
       bottom=lvl["real"] + lvl["container_only"] + lvl["placeholder"],
       color="#E74C3C", label="Parent box (M3)")
ax.set_xlabel("Level (hierarchy depth)")
ax.set_ylabel("Object count")
ax.set_title("Level × Flag 조합 — L3-L5 에 parent_box 집중 / L6-L7 이 physical peak",
             fontweight="bold")
ax.legend(loc="upper right")
for _, r in lvl.iterrows():
    ax.text(r["level_val"], r["total"] + 30,
            f"{int(r['total']):,}", ha="center", fontsize=8)
ax.grid(axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig(FIG / "03_level_contamination.png")
plt.close()
print("  ✓ 03_level_contamination.png")

# ---------------------------------------------------------------------------
# Figure 04 — Meta-name drill-down
# ---------------------------------------------------------------------------

meta_names = ["Pipelines", "Piping", "Equipment", "Structure", "Electrical",
              "HVAC", "Process", "Module", "Plant", "Space", "System"]
meta = all_obj[all_obj["display_name"].isin(meta_names)].copy()
print(f"\n=== Meta-name objects: {len(meta)} ===")

# pipeline_name="Pipelines" 로 링크된 piping component
link = pd.read_parquet(BASE / "link_types" / "belongs_to_pipeline.parquet")
pipelines_linked = (link["pipeline_name"] == "Pipelines").sum()
print(f'"Pipelines" 를 pipeline 으로 가진 piping: {pipelines_linked}')

fig, axes = plt.subplots(1, 2, figsize=(15, 7))

# left: meta objects by level
meta_lvl = meta.groupby(["display_name", "level_val"]).size().unstack(fill_value=0)
meta_lvl.plot(kind="barh", stacked=True, ax=axes[0],
              color=["#3498DB", "#9B59B6", "#E74C3C"])
axes[0].set_title(f"Meta-name 객체 {len(meta)}개 — 대부분 L4\n"
                  '"Pipelines" 만 L5 (이상)',
                  fontweight="bold")
axes[0].set_xlabel("Count")
axes[0].legend(title="Level", fontsize=8)
axes[0].grid(axis="x", alpha=0.3)

# right: 30 unflagged contamination candidates scatter
p95_bbox = all_obj["bbox_volume_m3"].quantile(.95)
cand = all_obj[
    (all_obj["bbox_volume_m3"] > p95_bbox)
    & (~all_obj["has_real_mesh"].fillna(False))
    & (~all_obj["is_parent_box"].fillna(False))
    & (~all_obj["is_bbox_placeholder"].fillna(False))
]
# group by refined_class for the bar
cand_cls = cand["refined_class"].value_counts()
axes[1].barh(cand_cls.index[::-1], cand_cls.values[::-1],
             color=["#F39C12", "#95A5A6", "#27AE60", "#4A90E2"][:len(cand_cls)])
axes[1].set_title(f"Unflagged contamination 후보 ({len(cand)}개)\n"
                  "bbox > p95 + no_mesh + not parent_box / placeholder",
                  fontweight="bold")
axes[1].set_xlabel("Count")
for i, v in enumerate(cand_cls.values[::-1]):
    axes[1].text(v + 0.2, i, str(v), va="center")
axes[1].grid(axis="x", alpha=0.3)

plt.suptitle("A6 Extension Findings — M3 추가 오염 + Meta-name 이상", fontsize=13, fontweight="bold")
plt.tight_layout()
plt.savefig(FIG / "04_meta_names_drill.png")
plt.close()
print("  ✓ 04_meta_names_drill.png")

# Save candidates
cand.to_csv(OUT_CSV / "a6_unflagged_contamination_candidates.csv", index=False)
meta.to_csv(OUT_CSV / "a6_meta_name_objects.csv", index=False)

print(f"\n✅ Done.")
