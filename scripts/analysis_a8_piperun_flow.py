"""A8 - BimPipeRun Flow Analysis.

핵심 발견:
1. valve_count BUG: bim_piperuns aggregate 는 전부 0 인데 실제 472 valves / 159 runs 존재
2. 378 runs / 147 pipelines: 평균 2.57 runs/pipeline (median 2)
3. Top valve-density runs: S-175 (12 valves), P-204 (9 v + 11 f = 28 중 71%)
4. NPD: 4in (531) + 8in (506) + 6in (376) + 2in (355) 이 주류
5. "Pipelines" 메타의 U12-2-MZ 시리즈 11 runs = 명명 실패 sample

Outputs:
  notebooks/figures/a8-piperun-flow/
    01_run_size_and_per_pipeline.png
    02_valve_count_bug.png
    03_fitting_density_outliers.png
    04_npd_distribution.png
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE = Path("data/ontology/2026-04-12")
FIG = Path("notebooks/figures/a8-piperun-flow")
FIG.mkdir(parents=True, exist_ok=True)
OUT_CSV = Path("data/analysis")

plt.rcParams.update({
    "font.size": 10, "axes.titlesize": 12,
    "figure.dpi": 100, "savefig.dpi": 300, "savefig.bbox": "tight",
})

run = pd.read_parquet(BASE / "bim_piperuns.parquet")
pipe = pd.read_parquet(BASE / "bim_pipelines.parquet")
piping = pd.read_parquet(BASE / "object_types" / "piping.parquet")
print(f"Runs: {len(run)} | Pipelines: {len(pipe)} | Piping comps: {len(piping)}")

# ---------------------------------------------------------------------------
# Compute actual valve count per run (bug workaround)
# ---------------------------------------------------------------------------

valve_mask = piping["sp3d_short_code"].fillna("").str.contains("valve", case=False)
print(f"\nActual valves in piping: {valve_mask.sum()}")

piping_w = piping[piping["sp3d_pipe_run"].notna() & piping["sp3d_pipeline"].notna()].copy()
piping_w["piperun_id"] = piping_w["sp3d_pipeline"] + "::" + piping_w["sp3d_pipe_run"]
actual_valves = piping_w[valve_mask.loc[piping_w.index]].groupby("piperun_id").size().rename(
    "actual_valve_count"
)

run["piperun_id_match"] = run["pipeline_name"] + "::" + run["pipe_run_name"]
run = run.merge(actual_valves, left_on="piperun_id_match", right_index=True, how="left")
run["actual_valve_count"] = run["actual_valve_count"].fillna(0).astype(int)

print(f"Runs with valves (actual): {(run['actual_valve_count'] > 0).sum()}")
print(f"Total valves summed over runs (actual): {run['actual_valve_count'].sum()}")

# fitting density 재계산 (valve_count bug 교체)
run["fitting_total_real"] = (
    run["actual_valve_count"]
    + run["flange_count"]
    + run["elbow_count"]
    + run["tee_count"]
)
run["fitting_density"] = run["fitting_total_real"] / run["component_count"].replace(0, 1)

# ---------------------------------------------------------------------------
# Figure 01 — Run size distribution + runs-per-pipeline distribution
# ---------------------------------------------------------------------------

fig, axes = plt.subplots(1, 2, figsize=(14, 6))
axes[0].hist(run["component_count"], bins=30, color="#4A90E2", edgecolor="white")
axes[0].axvline(run["component_count"].median(), color="#E74C3C", lw=2,
                label=f"median = {run['component_count'].median():.0f}")
axes[0].set_xlabel("Components per pipe run")
axes[0].set_ylabel("# runs")
axes[0].set_title(f"Run size distribution (n={len(run)})\n"
                  f"median 5, max 38")
axes[0].legend(); axes[0].grid(alpha=0.3)

runs_per_pipe = run.groupby("pipeline_name").size().sort_values(ascending=False)
axes[1].hist(runs_per_pipe, bins=range(1, int(runs_per_pipe.max()) + 2),
             color="#27AE60", edgecolor="white", align="left")
axes[1].axvline(runs_per_pipe.median(), color="#E74C3C", lw=2,
                label=f"median = {runs_per_pipe.median():.0f}")
axes[1].set_xlabel("Pipe runs per pipeline")
axes[1].set_ylabel("# pipelines")
axes[1].set_title(f"Runs per pipeline (n={len(runs_per_pipe)})\n"
                  f"median 2, top P-10147=17 / P-10148=15 / Pipelines=11")
axes[1].legend(); axes[1].grid(alpha=0.3)

plt.suptitle("378 Pipe Runs / 147 Pipelines — 분포 기본",
             fontsize=13, fontweight="bold")
plt.tight_layout()
plt.savefig(FIG / "01_run_size_and_per_pipeline.png")
plt.close()
print("  ✓ 01_run_size_and_per_pipeline.png")

# ---------------------------------------------------------------------------
# Figure 02 — Valve count bug visualization
# ---------------------------------------------------------------------------

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# left: claim vs reality
axes[0].bar(["bim_piperuns\n.valve_count\n(aggregated)", "Actual\n(counted from piping)"],
            [run["valve_count"].sum(), run["actual_valve_count"].sum()],
            color=["#E74C3C", "#27AE60"],
            edgecolor="black", linewidth=1.5)
axes[0].set_ylabel("Total valves")
axes[0].set_title("valve_count BUG — aggregate 0 vs actual 472",
                  fontweight="bold")
for i, v in enumerate([run["valve_count"].sum(), run["actual_valve_count"].sum()]):
    axes[0].text(i, v + 10, str(v), ha="center", fontsize=12, fontweight="bold")
axes[0].grid(axis="y", alpha=0.3)

# right: top 10 valve-rich runs
top_v = run.nlargest(10, "actual_valve_count")[::-1]
labels = [f"{r['pipeline_name'][:15]} / {r['pipe_run_name'][:30]}"
          for _, r in top_v.iterrows()]
axes[1].barh(range(len(top_v)), top_v["actual_valve_count"], color="#F39C12")
axes[1].set_yticks(range(len(top_v))); axes[1].set_yticklabels(labels, fontsize=7)
axes[1].set_xlabel("Actual valve count")
axes[1].set_title("Top 10 valve-rich runs (from piping join)",
                  fontweight="bold")
axes[1].grid(axis="x", alpha=0.3)
for i, v in enumerate(top_v["actual_valve_count"]):
    axes[1].text(v + 0.2, i, str(v), va="center", fontsize=9)

plt.suptitle("A8 Bug Finding — Aggregate valve_count 누락",
             fontsize=13, fontweight="bold")
plt.tight_layout()
plt.savefig(FIG / "02_valve_count_bug.png")
plt.close()
print("  ✓ 02_valve_count_bug.png")

# ---------------------------------------------------------------------------
# Figure 03 — Fitting density outliers
# ---------------------------------------------------------------------------

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# left: density distribution
axes[0].hist(run["fitting_density"].clip(0, 1), bins=30, color="#9B59B6",
             edgecolor="white")
axes[0].set_xlabel("Fitting density (fittings / component)")
axes[0].set_ylabel("# runs")
axes[0].set_title(f"Fitting density (actual valve + flange + elbow + tee / total)\n"
                  f"median={run['fitting_density'].median():.2f}, "
                  f"p75={run['fitting_density'].quantile(.75):.2f}")
axes[0].grid(alpha=0.3)

# right: runs with highest fitting density (with decent size)
dense = run[run["component_count"] >= 10].nlargest(10, "fitting_density")[::-1]
labels = [f"{r['pipeline_name'][:12]} / {r['pipe_run_name'][:30]}"
          for _, r in dense.iterrows()]
axes[1].barh(range(len(dense)), dense["fitting_density"], color="#1ABC9C")
axes[1].set_yticks(range(len(dense))); axes[1].set_yticklabels(labels, fontsize=7)
axes[1].set_xlabel("Fitting density")
axes[1].set_title("Top 10 dense runs (size ≥ 10)\n"
                  "(높은 density = 많은 valve/flange — 복잡 구간)",
                  fontweight="bold")
axes[1].grid(axis="x", alpha=0.3)
for i, (_, r) in enumerate(dense.iterrows()):
    axes[1].text(r["fitting_density"] + 0.01, i,
                 f"{r['fitting_total_real']:.0f}/{r['component_count']:.0f}",
                 va="center", fontsize=8)

plt.suptitle("Run Complexity — Fitting Density Outliers",
             fontsize=13, fontweight="bold")
plt.tight_layout()
plt.savefig(FIG / "03_fitting_density_outliers.png")
plt.close()
print("  ✓ 03_fitting_density_outliers.png")

# ---------------------------------------------------------------------------
# Figure 04 — NPD distribution + pipe-run NPD (per pipeline, heterogeneity)
# ---------------------------------------------------------------------------

# Parse NPD into size (first number)
import re
def extract_inch(npd):
    if not isinstance(npd, str): return None
    m = re.match(r"(\d+(?:\.\d+)?)\s*in", npd)
    if m: return float(m.group(1))
    m = re.match(r"(\d+(?:\.\d+)?)\s*mm", npd)
    if m: return float(m.group(1)) / 25.4
    return None

piping["npd_inch"] = piping["sp3d_npd"].apply(extract_inch)
print(f'\nNPD 파싱 성공: {piping["npd_inch"].notna().sum()} / {piping["sp3d_npd"].notna().sum()}')

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

npd_counts = piping["npd_inch"].value_counts().sort_index()
axes[0].bar(npd_counts.index.astype(str), npd_counts.values, color="#4A90E2")
axes[0].set_xlabel("Nominal Pipe Diameter (inch)")
axes[0].set_ylabel("# components")
axes[0].set_title(f"NPD 분포 (n={piping['npd_inch'].notna().sum()})\n"
                  "4in + 8in + 6in + 2in 이 주류")
axes[0].tick_params(axis="x", rotation=45)
axes[0].grid(axis="y", alpha=0.3)

# Heterogeneity: pipelines with mixed NPDs
piping_valid = piping.dropna(subset=["sp3d_pipeline", "npd_inch"])
npd_div = piping_valid.groupby("sp3d_pipeline")["npd_inch"].agg(
    [("unique_npd", "nunique"), ("range_inch", lambda x: x.max() - x.min())]
).reset_index()
div_top = npd_div.nlargest(10, "unique_npd")[::-1]
labels = div_top["sp3d_pipeline"].values
axes[1].barh(range(len(div_top)), div_top["unique_npd"], color="#F39C12")
axes[1].set_yticks(range(len(div_top))); axes[1].set_yticklabels(labels, fontsize=9)
axes[1].set_xlabel("# distinct NPD sizes")
axes[1].set_title("가장 NPD heterogeneous pipelines\n"
                  "(여러 size 혼합 = size transition 이 많은 라인)",
                  fontweight="bold")
axes[1].grid(axis="x", alpha=0.3)
for i, v in enumerate(div_top["unique_npd"]):
    axes[1].text(v + 0.1, i, str(v), va="center")

plt.suptitle("NPD — 전체 분포 + 다양성 outlier",
             fontsize=13, fontweight="bold")
plt.tight_layout()
plt.savefig(FIG / "04_npd_distribution.png")
plt.close()
print("  ✓ 04_npd_distribution.png")

# Save enriched piperuns
run.to_csv(OUT_CSV / "a8_piperun_enriched.csv", index=False)
print("\n✅ Done.")
