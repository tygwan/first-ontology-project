"""Generate matplotlib mockups of Power BI dashboard pages.

Produces preview PNGs that show what each dashboard page should look
like when built in Power BI Desktop. The user can use these as a
"North Star" reference while replicating in Power BI.

Output location::

    docs/analysis/powerbi-dashboard-preview/figures/
        page1-overview.png
        page2-classification-confidence.png
        page3-spatial-distribution.png
        page4-pipelines.png
        page5-mesh-quality.png
        page6-connected-groups.png
        page7-physical-properties.png

Run::

    .venv/bin/python scripts/powerbi_mockup.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from bimkg import config  # noqa: E402

FIG_DIR = config.PROJECT_ROOT / "docs" / "analysis" / "powerbi-dashboard-preview" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

# Consistent color scheme for classes
CLASS_COLORS: dict[str, str] = {
    "Structure": "#ff7f0e",
    "Piping": "#1f77b4",
    "Equipment": "#2ca02c",
    "Other": "#7f7f7f",
    "Electrical": "#d62728",
    "HVAC": "#9467bd",
}

CONFIDENCE_COLORS: dict[str, str] = {
    "HIGH": "#2ca02c",
    "LOW": "#ff7f0e",
    "LIKELY_BUG": "#8b0000",
}

plt.rcParams["figure.dpi"] = 110
plt.rcParams["font.family"] = "DejaVu Sans"


def load_data() -> dict:
    """Load all PowerBI CSV files we need for mockups."""
    return {
        "fact_objects": pd.read_csv(config.POWERBI_DIR / "fact_objects.csv"),
        "dim_class": pd.read_csv(config.POWERBI_DIR / "dim_class.csv"),
        "dim_level": pd.read_csv(config.POWERBI_DIR / "dim_level.csv"),
        "dim_pipeline": pd.read_csv(config.POWERBI_DIR / "dim_pipeline.csv"),
        "dim_meshq": pd.read_csv(config.POWERBI_DIR / "dim_meshq.csv"),
        "dim_verdict": pd.read_csv(config.POWERBI_DIR / "dim_verdict.csv"),
        "dim_group": pd.read_csv(config.POWERBI_DIR / "dim_group.csv"),
    }


def format_count(n: int) -> str:
    return f"{n:,}"


def page1_overview(data: dict) -> None:
    fo = data["fact_objects"]
    dim_class = data["dim_class"]

    fig = plt.figure(figsize=(14, 9), constrained_layout=True)
    gs = fig.add_gridspec(3, 4, height_ratios=[0.8, 1.5, 1.5])

    fig.suptitle("Page 1 — Overview", fontsize=16, fontweight="bold", y=1.02)

    # Row 1: KPI cards
    total = len(fo)
    giant = int(fo["in_giant_group"].sum())
    with_mesh = int(fo["has_own_geometry"].sum())
    classes = fo["refined_class"].nunique()

    kpis = [
        ("Total Objects", format_count(total), "#1f77b4"),
        ("Classes", str(classes), "#2ca02c"),
        ("In Giant Group", format_count(giant), "#ff7f0e"),
        ("With Real Mesh", format_count(with_mesh), "#9467bd"),
    ]
    for i, (label, value, color) in enumerate(kpis):
        ax = fig.add_subplot(gs[0, i])
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.text(0.5, 0.35, value, ha="center", va="center",
                fontsize=28, fontweight="bold", color=color)
        ax.text(0.5, 0.82, label, ha="center", va="center",
                fontsize=11, color="#555")
        ax.axis("off")
        for spine in ax.spines.values():
            spine.set_visible(False)
        rect = plt.Rectangle((0.05, 0.05), 0.9, 0.9, fill=False,
                             edgecolor=color, linewidth=2)
        ax.add_patch(rect)

    # Row 2: class distribution donut + level bar
    ax_donut = fig.add_subplot(gs[1, :2])
    class_counts = fo["refined_class"].value_counts()
    colors = [CLASS_COLORS.get(c, "#cccccc") for c in class_counts.index]
    wedges, texts, autotexts = ax_donut.pie(
        class_counts.values,
        labels=class_counts.index,
        colors=colors,
        autopct="%1.1f%%",
        startangle=90,
        wedgeprops=dict(width=0.45, edgecolor="white"),
        textprops=dict(fontsize=9),
    )
    ax_donut.set_title("Class distribution (refined_class)",
                       fontsize=12, pad=10)

    ax_level = fig.add_subplot(gs[1, 2:])
    level_counts = fo["level"].value_counts().sort_index()
    bars = ax_level.bar(level_counts.index, level_counts.values,
                        color="#1f77b4", edgecolor="black")
    for bar, val in zip(bars, level_counts.values):
        if val > 50:
            ax_level.text(bar.get_x() + bar.get_width() / 2,
                          bar.get_height() + 20, str(val),
                          ha="center", fontsize=9)
    ax_level.set_xlabel("Hierarchy Level")
    ax_level.set_ylabel("Object Count")
    ax_level.set_title("Objects by hierarchy level", fontsize=12, pad=10)
    ax_level.set_xticks(range(10))
    ax_level.grid(axis="y", linestyle="--", alpha=0.4)

    # Row 3: mesh quality + container fraction
    ax_mesh = fig.add_subplot(gs[2, :2])
    mq_counts = fo["mesh_quality"].value_counts()
    ax_mesh.barh(mq_counts.index, mq_counts.values,
                 color=["#2ca02c" if "full" in x else
                        "#ff7f0e" if "fbx" in x or "line" in x else "#8b0000"
                        for x in mq_counts.index])
    for i, v in enumerate(mq_counts.values):
        ax_mesh.text(v + 50, i, str(v), va="center", fontsize=9)
    ax_mesh.set_xlabel("Count")
    ax_mesh.set_title("Mesh quality breakdown", fontsize=12, pad=10)
    ax_mesh.grid(axis="x", linestyle="--", alpha=0.4)

    ax_flags = fig.add_subplot(gs[2, 2:])
    flags = ["is_container", "is_bbox_placeholder", "is_analysis_volume",
             "has_own_geometry", "graph_participant"]
    flag_counts = [int(fo[f].sum()) for f in flags]
    flag_labels = [f.replace("is_", "").replace("_", " ").title() for f in flags]
    colors_flag = ["#8b0000", "#d62728", "#ff7f0e", "#2ca02c", "#1f77b4"]
    bars = ax_flags.barh(flag_labels, flag_counts,
                          color=colors_flag, edgecolor="black")
    for bar, val in zip(bars, flag_counts):
        pct = val / total * 100
        ax_flags.text(val + 100, bar.get_y() + bar.get_height() / 2,
                      f"{val:,} ({pct:.1f}%)", va="center", fontsize=9)
    ax_flags.set_xlabel("Count")
    ax_flags.set_xlim(0, total * 1.1)
    ax_flags.set_title("Flag counts", fontsize=12, pad=10)
    ax_flags.grid(axis="x", linestyle="--", alpha=0.4)

    plt.savefig(FIG_DIR / "page1-overview.png", bbox_inches="tight")
    plt.close()
    print("  wrote page1-overview.png")


def page2_classification_confidence(data: dict) -> None:
    fo = data["fact_objects"]

    fig = plt.figure(figsize=(14, 9), constrained_layout=True)
    gs = fig.add_gridspec(2, 2)
    fig.suptitle("Page 2 — Classification Confidence (Phase 1e)",
                 fontsize=16, fontweight="bold", y=1.02)

    # 2a: stacked bar - confidence per class
    ax = fig.add_subplot(gs[0, :])
    classes = ["Piping", "Structure", "Equipment", "Electrical", "HVAC", "Other"]
    high_counts = []
    low_counts = []
    bug_counts = []
    for c in classes:
        cls_rows = fo[fo["refined_class"] == c]
        high_counts.append((cls_rows["classification_confidence"] == "HIGH").sum())
        low_counts.append((cls_rows["classification_confidence"] == "LOW").sum())
        bug_counts.append((cls_rows["classification_confidence"] == "LIKELY_BUG").sum())

    x = np.arange(len(classes))
    width = 0.6
    p1 = ax.bar(x, high_counts, width, label="HIGH", color=CONFIDENCE_COLORS["HIGH"])
    p2 = ax.bar(x, low_counts, width, bottom=high_counts,
                label="LOW", color=CONFIDENCE_COLORS["LOW"])
    bottoms = [h + l for h, l in zip(high_counts, low_counts)]
    p3 = ax.bar(x, bug_counts, width, bottom=bottoms,
                label="LIKELY_BUG", color=CONFIDENCE_COLORS["LIKELY_BUG"])

    for i, (h, l, b) in enumerate(zip(high_counts, low_counts, bug_counts)):
        total_cls = h + l + b
        if total_cls > 0:
            ax.text(i, total_cls + 50, str(total_cls),
                    ha="center", fontsize=9, fontweight="bold")
        if b > 100:
            ax.text(i, h + l + b / 2, str(b),
                    ha="center", fontsize=9, color="white", fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(classes)
    ax.set_ylabel("Object Count")
    ax.set_title("Confidence breakdown by class", fontsize=12, pad=10)
    ax.legend(loc="upper right")
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    # 2b: bug reasons pie
    ax = fig.add_subplot(gs[1, 0])
    bug_rows = fo[fo["classification_confidence"] == "LIKELY_BUG"]
    reasons = bug_rows["classification_confidence_reason"].value_counts()
    reason_labels = [r.replace("piping_no_metadata_", "").replace("_", " ")
                     for r in reasons.index]
    colors_bug = plt.cm.Reds(np.linspace(0.3, 0.9, len(reasons)))
    ax.pie(reasons.values, labels=reason_labels,
           autopct="%1.0f%%", colors=colors_bug, startangle=90,
           textprops=dict(fontsize=8))
    ax.set_title(f"LIKELY_BUG root causes (n={len(bug_rows)})",
                 fontsize=12, pad=10)

    # 2c: M1 impact summary
    ax = fig.add_subplot(gs[1, 1])
    ax.axis("off")
    total_piping = (fo["refined_class"] == "Piping").sum()
    high_piping = ((fo["refined_class"] == "Piping") &
                   (fo["classification_confidence"] == "HIGH")).sum()
    bug_piping = ((fo["refined_class"] == "Piping") &
                  (fo["classification_confidence"] == "LIKELY_BUG")).sum()
    summary = (
        f"M1 Finding — Piping Class Inflation\n\n"
        f"XLSX says Piping = {total_piping:,}\n"
        f"HIGH confidence = {high_piping:,}\n"
        f"LIKELY_BUG      = {bug_piping:,}\n\n"
        f"Inflation: +{bug_piping / high_piping * 100:.1f}%\n\n"
        f"Root cause: substring keyword matching\n"
        f"  - 'tee' matches 'steel'\n"
        f"  - 'pipe' matches 'Pipe Rack'\n\n"
        f"Resolution: classification_confidence\n"
        f"column (Phase 1e). Filter HIGH for\n"
        f"Phase 2 ontology instances.\n\n"
        f"Upstream fix: DXTnavis Issue #2"
    )
    ax.text(0.5, 0.5, summary, ha="center", va="center",
            fontsize=11, family="monospace",
            bbox=dict(boxstyle="round,pad=1", facecolor="#fff3e0",
                      edgecolor="#d62728"))

    plt.savefig(FIG_DIR / "page2-classification-confidence.png",
                bbox_inches="tight")
    plt.close()
    print("  wrote page2-classification-confidence.png")


def page3_spatial_distribution(data: dict) -> None:
    fo = data["fact_objects"]
    fig = plt.figure(figsize=(14, 10), constrained_layout=True)
    gs = fig.add_gridspec(2, 2)
    fig.suptitle("Page 3 — Spatial Distribution",
                 fontsize=16, fontweight="bold", y=1.02)

    # 3a: XY scatter with class color
    ax = fig.add_subplot(gs[0, 0])
    sub = fo[fo["centroid_x"].notna()]
    for cls in ["Structure", "Piping", "Equipment", "Electrical", "HVAC", "Other"]:
        m = sub[sub["refined_class"] == cls]
        if len(m):
            ax.scatter(m["centroid_x"], m["centroid_y"],
                       c=CLASS_COLORS[cls], label=cls, s=4, alpha=0.6)
    ax.set_xlabel("Centroid X (m)")
    ax.set_ylabel("Centroid Y (m)")
    ax.set_title("Plan view (X-Y) colored by class", fontsize=12, pad=10)
    ax.legend(loc="upper right", fontsize=8, markerscale=2)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, linestyle="--", alpha=0.3)

    # 3b: density heatmap
    ax = fig.add_subplot(gs[0, 1])
    hb = ax.hexbin(sub["centroid_x"], sub["centroid_y"],
                   gridsize=40, cmap="hot_r", mincnt=1)
    ax.set_xlabel("Centroid X (m)")
    ax.set_ylabel("Centroid Y (m)")
    ax.set_title("Object density heatmap (hexbin)",
                 fontsize=12, pad=10)
    ax.set_aspect("equal", adjustable="box")
    fig.colorbar(hb, ax=ax, label="Count")

    # 3c: Z elevation distribution
    ax = fig.add_subplot(gs[1, 0])
    sub_z = fo[fo["centroid_z"].notna()]
    ax.hist(sub_z["centroid_z"], bins=40, color="#1f77b4",
            edgecolor="black", alpha=0.8)
    ax.set_xlabel("Centroid Z (m) — elevation")
    ax.set_ylabel("Object count")
    ax.set_title("Elevation distribution", fontsize=12, pad=10)
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    # 3d: level vs Z correlation
    ax = fig.add_subplot(gs[1, 1])
    lvl_z = fo[["level", "centroid_z"]].dropna()
    avg_by_level = lvl_z.groupby("level")["centroid_z"].agg(["mean", "std", "count"])
    ax.errorbar(avg_by_level.index, avg_by_level["mean"],
                yerr=avg_by_level["std"], fmt="o-", color="#ff7f0e",
                capsize=4, markersize=8, linewidth=2)
    for lvl in avg_by_level.index:
        ax.text(lvl, avg_by_level.loc[lvl, "mean"] + 2,
                f"n={int(avg_by_level.loc[lvl, 'count'])}",
                ha="center", fontsize=8)
    ax.set_xlabel("Hierarchy level")
    ax.set_ylabel("Mean Z (m) ± std")
    ax.set_title("Elevation vs hierarchy level",
                 fontsize=12, pad=10)
    ax.grid(True, linestyle="--", alpha=0.4)

    plt.savefig(FIG_DIR / "page3-spatial-distribution.png",
                bbox_inches="tight")
    plt.close()
    print("  wrote page3-spatial-distribution.png")


def page4_pipelines(data: dict) -> None:
    fo = data["fact_objects"]
    dim_pipeline = data["dim_pipeline"]

    fig = plt.figure(figsize=(14, 9), constrained_layout=True)
    gs = fig.add_gridspec(2, 2)
    fig.suptitle("Page 4 — Pipelines", fontsize=16, fontweight="bold", y=1.02)

    # 4a: Top 20 pipelines by object count
    ax = fig.add_subplot(gs[0, :])
    top20 = dim_pipeline.nlargest(20, "object_count")
    bars = ax.barh(range(len(top20)), top20["object_count"],
                   color="#1f77b4", edgecolor="black")
    ax.set_yticks(range(len(top20)))
    ax.set_yticklabels(top20["pipeline_name"], fontsize=8)
    for i, v in enumerate(top20["object_count"]):
        ax.text(v + 1, i, str(v), va="center", fontsize=8)
    ax.set_xlabel("Object count")
    ax.set_title("Top 20 pipelines by object count", fontsize=12, pad=10)
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    ax.invert_yaxis()

    # 4b: NPD distribution (from sp3d_npd)
    ax = fig.add_subplot(gs[1, 0])
    npd_counts = fo["sp3d_npd"].value_counts().head(15)
    bars = ax.bar(range(len(npd_counts)), npd_counts.values,
                  color="#2ca02c", edgecolor="black")
    ax.set_xticks(range(len(npd_counts)))
    ax.set_xticklabels(npd_counts.index, rotation=45, ha="right", fontsize=7)
    ax.set_ylabel("Object count")
    ax.set_title("Top 15 NPD values", fontsize=12, pad=10)
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    # 4c: pipe_run_count vs object_count scatter
    ax = fig.add_subplot(gs[1, 1])
    ax.scatter(dim_pipeline["pipe_run_count"],
               dim_pipeline["object_count"],
               s=40, alpha=0.5, c="#ff7f0e", edgecolors="black")
    ax.set_xlabel("Pipe run count")
    ax.set_ylabel("Object count")
    ax.set_title("Pipelines: pipe runs vs objects",
                 fontsize=12, pad=10)
    ax.grid(True, linestyle="--", alpha=0.4)

    plt.savefig(FIG_DIR / "page4-pipelines.png", bbox_inches="tight")
    plt.close()
    print("  wrote page4-pipelines.png")


def page5_mesh_quality(data: dict) -> None:
    fo = data["fact_objects"]
    fig = plt.figure(figsize=(14, 9), constrained_layout=True)
    gs = fig.add_gridspec(2, 2)
    fig.suptitle("Page 5 — Mesh Quality", fontsize=16, fontweight="bold", y=1.02)

    # 5a: mesh_quality x verdict crosstab heatmap
    ax = fig.add_subplot(gs[0, 0])
    ct = pd.crosstab(fo["mesh_quality"], fo["verdict"])
    im = ax.imshow(ct.values, cmap="Blues", aspect="auto")
    ax.set_xticks(range(len(ct.columns)))
    ax.set_xticklabels(ct.columns, rotation=45, ha="right", fontsize=9)
    ax.set_yticks(range(len(ct.index)))
    ax.set_yticklabels(ct.index, fontsize=9)
    for i in range(len(ct.index)):
        for j in range(len(ct.columns)):
            ax.text(j, i, ct.values[i, j], ha="center", va="center",
                    color="white" if ct.values[i, j] > 3000 else "black",
                    fontsize=8)
    ax.set_title("Mesh quality × Verdict", fontsize=12, pad=10)
    fig.colorbar(im, ax=ax, label="Count")

    # 5b: vertex count distribution (log)
    ax = fig.add_subplot(gs[0, 1])
    vc = fo[fo["vertex_count"] > 0]["vertex_count"]
    ax.hist(vc, bins=50, color="#9467bd", edgecolor="black")
    ax.set_xscale("log")
    ax.set_xlabel("Vertex count (log)")
    ax.set_ylabel("Frequency")
    ax.set_title(f"Vertex count distribution (n={len(vc):,})",
                 fontsize=12, pad=10)
    ax.grid(True, linestyle="--", alpha=0.4)

    # 5c: has_real_mesh by class
    ax = fig.add_subplot(gs[1, 0])
    classes = ["Structure", "Piping", "Equipment", "Electrical", "HVAC", "Other"]
    mesh_yes = []
    mesh_no = []
    for c in classes:
        m = fo[fo["refined_class"] == c]
        mesh_yes.append(m["has_real_mesh"].sum())
        mesh_no.append(len(m) - m["has_real_mesh"].sum())
    x = np.arange(len(classes))
    width = 0.6
    ax.bar(x, mesh_yes, width, label="has real mesh",
           color="#2ca02c", edgecolor="black")
    ax.bar(x, mesh_no, width, bottom=mesh_yes, label="no mesh",
           color="#d62728", edgecolor="black")
    ax.set_xticks(x)
    ax.set_xticklabels(classes, rotation=30, ha="right")
    ax.set_ylabel("Object count")
    ax.set_title("Mesh presence by class",
                 fontsize=12, pad=10)
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    # 5d: triangle count summary (text)
    ax = fig.add_subplot(gs[1, 1])
    ax.axis("off")
    tc = fo["triangle_count"]
    summary = (
        f"Mesh Statistics\n\n"
        f"Total objects:     {len(fo):,}\n"
        f"With real mesh:    {int(fo['has_real_mesh'].sum()):,}\n"
        f"Zero vertices:     {int((fo['vertex_count']==0).sum()):,}\n\n"
        f"Triangle count:\n"
        f"  Total:   {int(tc.sum()):,}\n"
        f"  Mean:    {tc.mean():.0f}\n"
        f"  Median:  {tc.median():.0f}\n"
        f"  Max:     {int(tc.max()):,}\n\n"
        f"Mesh quality tiers:\n"
        f"  full_mesh:          {int((fo['mesh_quality']=='full_mesh').sum()):,}\n"
        f"  fbx_supplemented:   {int((fo['mesh_quality']=='fbx_supplemented').sum()):,}\n"
        f"  box_placeholder:    {int((fo['mesh_quality']=='box_placeholder').sum()):,}\n"
        f"  skipped_container:  {int((fo['mesh_quality']=='skipped_container').sum()):,}"
    )
    ax.text(0.5, 0.5, summary, ha="center", va="center",
            fontsize=11, family="monospace",
            bbox=dict(boxstyle="round,pad=1", facecolor="#e8f5e9",
                      edgecolor="#2ca02c"))

    plt.savefig(FIG_DIR / "page5-mesh-quality.png", bbox_inches="tight")
    plt.close()
    print("  wrote page5-mesh-quality.png")


def page6_connected_groups(data: dict) -> None:
    fo = data["fact_objects"]
    dim_group = data["dim_group"]

    fig = plt.figure(figsize=(14, 9), constrained_layout=True)
    gs = fig.add_gridspec(2, 2)
    fig.suptitle("Page 6 — Connected Groups",
                 fontsize=16, fontweight="bold", y=1.02)

    # 6a: group size distribution (log)
    ax = fig.add_subplot(gs[0, 0])
    sizes = dim_group["group_size"]
    ax.hist(sizes, bins=np.logspace(0, 4, 50),
            color="#1f77b4", edgecolor="black")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Group size (log)")
    ax.set_ylabel("Number of groups (log)")
    ax.set_title(f"Group size distribution (n={len(dim_group):,})",
                 fontsize=12, pad=10)
    ax.grid(True, linestyle="--", alpha=0.4)

    # 6b: giant group vs rest
    ax = fig.add_subplot(gs[0, 1])
    giant_size = sizes.max()
    in_giant = int(fo["in_giant_group"].sum())
    not_in_giant = len(fo) - in_giant
    labels = [f"Giant group\nn={in_giant:,}",
              f"Other groups\nn={not_in_giant:,}"]
    ax.pie([in_giant, not_in_giant], labels=labels,
           colors=["#2ca02c", "#d62728"],
           autopct="%1.1f%%", startangle=90,
           wedgeprops=dict(edgecolor="white", linewidth=2))
    ax.set_title(f"Giant group coverage (size {giant_size:,})",
                 fontsize=12, pad=10)

    # 6c: singletons per class
    ax = fig.add_subplot(gs[1, 0])
    singleton_ids = dim_group[dim_group["group_size"] == 1]["group_id"].tolist()
    singletons = fo[fo["group_id"].isin(singleton_ids)]
    classes_order = ["Structure", "Piping", "Equipment",
                     "Electrical", "HVAC", "Other"]
    counts = [int((singletons["refined_class"] == c).sum())
              for c in classes_order]
    colors_s = [CLASS_COLORS[c] for c in classes_order]
    bars = ax.bar(classes_order, counts, color=colors_s, edgecolor="black")
    for bar, val in zip(bars, counts):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 20, str(val),
                    ha="center", fontsize=9)
    ax.set_ylabel("Singleton count")
    ax.set_xticklabels(classes_order, rotation=30, ha="right")
    ax.set_title("Singleton groups by class",
                 fontsize=12, pad=10)
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    # 6d: top 10 largest groups
    ax = fig.add_subplot(gs[1, 1])
    top10 = dim_group.nlargest(10, "group_size")
    labels10 = [f"{g[:8]}" for g in top10["group_id"]]
    bars = ax.barh(range(len(top10)), top10["group_size"],
                   color="#ff7f0e", edgecolor="black")
    ax.set_yticks(range(len(top10)))
    ax.set_yticklabels(labels10, fontsize=8, family="monospace")
    ax.set_xscale("log")
    ax.set_xlabel("Members (log)")
    ax.set_title("Top 10 groups by size",
                 fontsize=12, pad=10)
    ax.invert_yaxis()
    for i, v in enumerate(top10["group_size"]):
        ax.text(v * 1.1, i, str(v), va="center", fontsize=8)
    ax.grid(axis="x", linestyle="--", alpha=0.4)

    plt.savefig(FIG_DIR / "page6-connected-groups.png",
                bbox_inches="tight")
    plt.close()
    print("  wrote page6-connected-groups.png")


def page7_physical_properties(data: dict) -> None:
    fo = data["fact_objects"]
    fig = plt.figure(figsize=(14, 9), constrained_layout=True)
    gs = fig.add_gridspec(2, 2)
    fig.suptitle("Page 7 — Physical Properties (SI units)",
                 fontsize=16, fontweight="bold", y=1.02)

    # 7a: dry weight distribution (log)
    ax = fig.add_subplot(gs[0, 0])
    dw = fo[fo["dry_weight_kg"] > 0]["dry_weight_kg"]
    if len(dw):
        ax.hist(dw, bins=np.logspace(-1, 6, 50),
                color="#2ca02c", edgecolor="black")
        ax.set_xscale("log")
    ax.set_xlabel("Dry weight (kg, log)")
    ax.set_ylabel("Count")
    ax.set_title(f"Dry weight distribution (n={len(dw):,})",
                 fontsize=12, pad=10)
    ax.grid(True, linestyle="--", alpha=0.4)

    # 7b: length distribution
    ax = fig.add_subplot(gs[0, 1])
    lm = fo[fo["length_m"] > 0]["length_m"]
    if len(lm):
        ax.hist(lm, bins=40, color="#1f77b4", edgecolor="black")
    ax.set_xlabel("Length (m)")
    ax.set_ylabel("Count")
    ax.set_title(f"Length distribution (n={len(lm):,})",
                 fontsize=12, pad=10)
    ax.grid(True, linestyle="--", alpha=0.4)

    # 7c: design pressure vs temperature scatter
    ax = fig.add_subplot(gs[1, 0])
    pt = fo[(fo["design_pressure_kpa"].notna()) &
             (fo["design_temperature_c"].notna())]
    if len(pt):
        ax.scatter(pt["design_pressure_kpa"], pt["design_temperature_c"],
                   s=15, alpha=0.5, c="#d62728", edgecolors="black")
    ax.set_xlabel("Design pressure (kPa)")
    ax.set_ylabel("Design temperature (°C)")
    ax.set_title(f"Design conditions (n={len(pt):,})",
                 fontsize=12, pad=10)
    ax.grid(True, linestyle="--", alpha=0.4)

    # 7d: NPD distribution (end1)
    ax = fig.add_subplot(gs[1, 1])
    npd = fo[fo["npd_end1_m"] > 0]["npd_end1_m"]
    if len(npd):
        # Convert meters back to inches for readability
        npd_in = npd * 39.3701
        ax.hist(npd_in, bins=20, color="#9467bd", edgecolor="black")
    ax.set_xlabel("NPD end1 (inches)")
    ax.set_ylabel("Count")
    ax.set_title(f"NPD distribution (n={len(npd):,})",
                 fontsize=12, pad=10)
    ax.grid(True, linestyle="--", alpha=0.4)

    plt.savefig(FIG_DIR / "page7-physical-properties.png",
                bbox_inches="tight")
    plt.close()
    print("  wrote page7-physical-properties.png")


def main() -> int:
    print(f"Output directory: {FIG_DIR.relative_to(config.PROJECT_ROOT)}")
    print("Loading data...")
    data = load_data()
    print(f"  fact_objects: {data['fact_objects'].shape}")

    print("\nGenerating mockups...")
    page1_overview(data)
    page2_classification_confidence(data)
    page3_spatial_distribution(data)
    page4_pipelines(data)
    page5_mesh_quality(data)
    page6_connected_groups(data)
    page7_physical_properties(data)

    print("\nDone. Open the PNG files to preview each dashboard page.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
