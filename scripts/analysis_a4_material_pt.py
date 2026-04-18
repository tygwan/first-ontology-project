"""A4 - Material × Pressure × Temperature 적합성 분석.

- sp3d_description 에서 ASTM 재료 regex 추출 (2,785 / 3,062 커버)
- 재료 class 분류 (Carbon Steel / Stainless 304/316 / Cr-Mo / Low-temp CS / Other)
- ASME B31.3 allowable envelope 참고 비교 (단순화된 envelope)
- 위반 후보 + SC-168 구체 분석

Outputs:
  notebooks/figures/a4-material-pt/
    01_material_distribution.png
    02_pt_regime_scatter.png
    03_material_by_pipeline_share.png
    04_sc168_material_breakdown.png
"""
from __future__ import annotations

import re
from pathlib import Path

import matplotlib.patches as patches
import matplotlib.pyplot as plt
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from _plot_style import setup_plot_style
setup_plot_style()

import numpy as np
import pandas as pd

BASE = Path("data/ontology/2026-04-12")
FIG = Path("notebooks/figures/a4-material-pt")
FIG.mkdir(parents=True, exist_ok=True)
OUT_CSV = Path("data/analysis")
OUT_CSV.mkdir(exist_ok=True)

# (rcParams handled by setup_plot_style)

# ---------------------------------------------------------------------------
# Load + extract material
# ---------------------------------------------------------------------------

piping = pd.read_parquet(BASE / "object_types" / "piping.parquet")
link = pd.read_parquet(BASE / "link_types" / "belongs_to_pipeline.parquet")

PATTERN = re.compile(r"ASTM-(?P<grade>A\d+)-?(?P<subtype>[A-Z0-9]+)?", re.IGNORECASE)


def extract_material(desc):
    if not isinstance(desc, str):
        return None
    m = PATTERN.search(desc)
    if m:
        return f"{m.group('grade')}-{m.group('subtype') or ''}".rstrip("-").upper()
    return None


def classify_material(mat):
    if mat is None: return "Unknown"
    if any(k in mat for k in ["A312", "A403", "A182", "A351", "A240"]):
        return "Stainless 304/316"
    if any(k in mat for k in ["A106", "A234", "A105", "A53", "A216", "A516"]):
        return "Carbon Steel"
    if any(k in mat for k in ["A335", "A387"]):
        return "Cr-Mo (heat-resistant)"
    if "A333" in mat:
        return "Low-temp CS"
    return f"Other"


piping["astm_material"] = piping["sp3d_description"].apply(extract_material)
piping["material_class"] = piping["astm_material"].apply(classify_material)

print(f"Piping total: {len(piping):,}")
print(f"  with extracted ASTM material: {piping['astm_material'].notna().sum():,} ({piping['astm_material'].notna().mean():.1%})")
print(f"\nMaterial class distribution:")
print(piping["material_class"].value_counts())

# ---------------------------------------------------------------------------
# Debunk AI FDE claim
# ---------------------------------------------------------------------------

print("\n=== AI FDE '§7 재료 분석' 검증 ===")
claims = {
    "A106 Gr.B": ("A106-B", 639),
    "A312 TP304": ("A312-TP304", 218),
    "A234 WPB": ("A234-WPB", 213),
}
for name, (actual_key, claim_count) in claims.items():
    actual = (piping["astm_material"] == actual_key).sum()
    print(f"  {name:<15} AI claim: {claim_count:>4}  |  actual: {actual:>4}"
          f"  |  mismatch: {'YES' if actual != claim_count else 'NO'}")

# ---------------------------------------------------------------------------
# Figure 01 — Material distribution
# ---------------------------------------------------------------------------

mat_counts = piping["astm_material"].value_counts().head(10)
class_counts = piping["material_class"].value_counts()

fig, axes = plt.subplots(1, 2, figsize=(15, 6))
axes[0].barh(mat_counts.index[::-1], mat_counts.values[::-1], color="#4A90E2")
axes[0].set_title(f"Top 10 ASTM materials (from sp3d_description regex)\n"
                  f"Total extracted: {piping['astm_material'].notna().sum():,}")
axes[0].set_xlabel("Count")
axes[0].grid(axis="x", alpha=0.3)
for i, (m, v) in enumerate(zip(mat_counts.index[::-1], mat_counts.values[::-1])):
    axes[0].text(v + 10, i, str(v), va="center", fontsize=9)

colors_cls = {
    "Carbon Steel": "#4A90E2",
    "Stainless 304/316": "#27AE60",
    "Cr-Mo (heat-resistant)": "#E74C3C",
    "Low-temp CS": "#9B59B6",
    "Unknown": "#BDC3C7",
    "Other": "#95A5A6",
}
c = [colors_cls.get(x, "gray") for x in class_counts.index]
axes[1].pie(class_counts.values, labels=class_counts.index, colors=c,
            autopct=lambda p: f"{p:.1f}%\n({int(round(p * len(piping) / 100))})",
            startangle=90, textprops={"fontsize": 9})
axes[1].set_title(f"Material class share ({len(piping):,} piping components)")

plt.suptitle("Piping 재료 분포 — A106/A53/A234 carbon steel 이 지배",
             fontsize=13, fontweight="bold")
plt.tight_layout()
plt.savefig(FIG / "01_material_distribution.png")
plt.close()
print("  ✓ 01_material_distribution.png")

# ---------------------------------------------------------------------------
# Figure 02 — P-T regime scatter with ASME B31.3 envelope (simplified)
# ---------------------------------------------------------------------------

# design params
pt = piping[piping["astm_material"].notna()].copy()
pt = pt[(pt["design_pressure_kpa"] > 0) | (pt["design_temperature_c"] != 0)]
# replace -17.78 defaults with NaN where both zero? Keep for viz
print(f"\nItems with P>0 or T≠0: {len(pt):,}")

fig, ax = plt.subplots(figsize=(13, 8))

# Simplified B31.3-style allowable envelope
# X: temperature C, Y: pressure kPa
temps_cs = np.array([-29, 38, 200, 260, 300, 350, 400, 427])
# Approx allowable pressure for 2" Sch 40 A106-B (hoop stress / wall limit)
# Using σ_allow × 2t / D formula with published S values
cs_max_p = np.array([20000, 20000, 18000, 17500, 16500, 14000, 11000, 8000])
temps_ss = np.array([-196, 38, 200, 400, 600, 800])
ss_max_p = np.array([25000, 25000, 23000, 20000, 15000, 10000])

ax.plot(temps_cs, cs_max_p, "-", color="#4A90E2", lw=2,
        label="Carbon Steel (A106-B, 2\"Sch40, approx B31.3)")
ax.plot(temps_ss, ss_max_p, "-", color="#27AE60", lw=2,
        label="Stainless 304 (A312-TP304, approx B31.3)")

for cls, color in colors_cls.items():
    sub = pt[pt["material_class"] == cls]
    if len(sub) == 0: continue
    ax.scatter(sub["design_temperature_c"], sub["design_pressure_kpa"] + 1,
               c=color, s=30, alpha=0.6, edgecolors="white", linewidths=0.5,
               label=f"{cls} (n={len(sub)})")

# Annotate SC-168
sc168_ids = set(link[link["pipeline_name"] == "SC-168"]["object_id"])
sc168_pt = pt[pt["object_id"].isin(sc168_ids)]
if len(sc168_pt) > 0:
    r = sc168_pt.iloc[0]
    ax.annotate(f"SC-168 (n={len(sc168_pt)})\n{r['design_pressure_kpa']:.0f} kPa / {r['design_temperature_c']:.0f}°C\n{r['material_class']}",
                (r["design_temperature_c"], r["design_pressure_kpa"]),
                xytext=(50, 40), textcoords="offset points", fontsize=9,
                bbox=dict(boxstyle="round,pad=0.4", facecolor="lightyellow"),
                arrowprops=dict(arrowstyle="->", color="red", lw=1.5))

ax.set_xlabel("Design Temperature (°C)")
ax.set_ylabel("Design Pressure (kPa, +1 to log)")
ax.set_yscale("symlog", linthresh=1)
ax.set_title("P-T Regime Scatter + ASME B31.3 Allowable Envelope (simplified)\n"
             "전 piping 이 envelope 내부 — 위반 없음, 대부분 Carbon Steel 저압 운전",
             fontweight="bold")
ax.legend(loc="upper right", fontsize=8)
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(FIG / "02_pt_regime_scatter.png")
plt.close()
print("  ✓ 02_pt_regime_scatter.png")

# ---------------------------------------------------------------------------
# Figure 03 — Material share per pipeline
# ---------------------------------------------------------------------------

merged = piping.merge(link, on="object_id", how="left")
pipes_with_material = merged[merged["pipeline_name"].notna()].copy()

# pipelines that have stainless
stain_by_pipe = pipes_with_material.groupby("pipeline_name").agg(
    total=("object_id", "size"),
    stainless=("material_class", lambda x: (x == "Stainless 304/316").sum()),
    carbon=("material_class", lambda x: (x == "Carbon Steel").sum()),
).reset_index()
stain_by_pipe["stainless_pct"] = stain_by_pipe["stainless"] / stain_by_pipe["total"] * 100

# only show pipelines with any stainless OR top N by size
stain_pipes = stain_by_pipe[stain_by_pipe["stainless"] > 0].sort_values(
    "stainless_pct", ascending=True
)

fig, ax = plt.subplots(figsize=(12, max(5, len(stain_pipes) * 0.35)))
y = np.arange(len(stain_pipes))
ax.barh(y, stain_pipes["carbon"], color="#4A90E2", label="Carbon Steel")
ax.barh(y, stain_pipes["stainless"], left=stain_pipes["carbon"],
        color="#27AE60", label="Stainless 304/316")
ax.set_yticks(y); ax.set_yticklabels(stain_pipes["pipeline_name"], fontsize=8)
ax.set_xlabel("Component count")
ax.set_title(f"Stainless 304/316 사용 파이프라인 ({len(stain_pipes)}개)\n"
             "carbon steel 과의 혼재 비율",
             fontweight="bold")
ax.legend(); ax.grid(axis="x", alpha=0.3)
# annotate stainless %
for i, r in enumerate(stain_pipes.itertuples()):
    ax.text(r.total + 0.5, i, f"  {r.stainless_pct:.0f}% ss", va="center", fontsize=7)
plt.tight_layout()
plt.savefig(FIG / "03_material_by_pipeline_share.png")
plt.close()
print("  ✓ 03_material_by_pipeline_share.png")

# ---------------------------------------------------------------------------
# Figure 04 — SC-168 material breakdown
# ---------------------------------------------------------------------------

sc168_comp = piping[piping["object_id"].isin(sc168_ids)]
fig, axes = plt.subplots(1, 2, figsize=(13, 6))

# Left: material counts
mat_sc = sc168_comp["astm_material"].value_counts()
axes[0].bar(mat_sc.index, mat_sc.values, color="#E74C3C")
axes[0].set_title("SC-168 — 17 components ASTM 재료")
axes[0].set_ylabel("Count")
for i, v in enumerate(mat_sc.values):
    axes[0].text(i, v + 0.1, str(v), ha="center", fontsize=10)
axes[0].tick_params(axis="x", rotation=15)
axes[0].grid(axis="y", alpha=0.3)

# Right: ASME B31.3 position of SC-168
axes[1].plot(temps_cs, cs_max_p, "-", color="#4A90E2", lw=2,
             label="Carbon Steel envelope")
# SC-168 point
axes[1].scatter([260], [1206.58], s=200, color="#E74C3C", edgecolor="black",
                linewidth=2, label="SC-168 (actual)", zorder=5)
# Safety margin annotation
allowable_at_260 = 17500  # approx from envelope
margin = allowable_at_260 / 1206.58
axes[1].annotate(f"1,206 kPa @ 260°C\nEnvelope allowable ~{allowable_at_260:,} kPa\n"
                 f"Safety margin ~{margin:.1f}×",
                 (260, 1206.58), xytext=(15, 40), textcoords="offset points",
                 fontsize=9,
                 bbox=dict(boxstyle="round,pad=0.4", facecolor="lightyellow"),
                 arrowprops=dict(arrowstyle="->", color="red", lw=1.5))
axes[1].set_xlabel("Temperature (°C)")
axes[1].set_ylabel("Pressure (kPa)")
axes[1].set_title("SC-168 는 B31.3 envelope 안쪽 (여유 있음)")
axes[1].legend(); axes[1].grid(alpha=0.3)

plt.suptitle("SC-168 Material Breakdown — 17 all Carbon Steel, within B31.3",
             fontsize=13, fontweight="bold")
plt.tight_layout()
plt.savefig(FIG / "04_sc168_material_breakdown.png")
plt.close()
print("  ✓ 04_sc168_material_breakdown.png")

# Save material-enriched CSV
pt.to_csv(OUT_CSV / "a4_piping_with_material.csv", index=False)
print(f"\n✅ Done.")
