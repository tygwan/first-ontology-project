"""Generate matplotlib figures for M4 finding.

Produces 3 PNGs in ``figures/`` at DPI 300:

  coverage_distribution.png    Mesh-quality pie chart (full_mesh / skipped_container /
                               fbx_supplemented / box_placeholder / line_mesh)
  adjacency_impact.png         Bar chart — fbx_supplemented's role in the adjacency
                               graph (20,746 of 220,346 edges = 9.4%)
  pipeline_fragmentation.png   Top 10 most-fragmented pipelines when fbx_supplemented
                               objects are removed (P-10147: 7 → 24, etc.)

The data is literal (hard-coded from the prior session's measurements) rather
than re-derived, because the fragmentation analysis requires the Phase 4
graph analytics pipeline that is not in this script's scope.  Counts match
``docs/findings/2026-04-15-M4-fbx-guid-mapping/README.md`` §1 and §2.

Usage::

    .venv/bin/python docs/findings/2026-04-15-M4-fbx-guid-mapping/make_figures.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
FIG_DIR = HERE / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

# High-DPI export per project visualization rule
plt.rcParams["figure.dpi"] = 300
plt.rcParams["savefig.dpi"] = 300
plt.rcParams["font.family"] = "DejaVu Sans"

# Consistent palette
COLOR_FULL = "#2ca02c"         # green — full mesh
COLOR_FBX = "#d62728"          # red — the focus of this finding
COLOR_BOX = "#ff7f0e"          # orange
COLOR_SKIP = "#7f7f7f"         # grey
COLOR_LINE = "#1f77b4"         # blue
COLOR_REST = "#aaaaaa"         # grey — the other 90.6% of adjacency edges


def fig_coverage_distribution() -> None:
    """Mesh-quality distribution across the 12,009 Gold objects."""
    labels = [
        "full_mesh",
        "skipped_container",
        "fbx_supplemented",
        "box_placeholder",
        "line_mesh",
    ]
    counts = [7189, 3353, 788, 671, 8]
    colors = [COLOR_FULL, COLOR_SKIP, COLOR_FBX, COLOR_BOX, COLOR_LINE]
    total = sum(counts)

    # Explode the fbx_supplemented slice so the reader's eye lands there.
    explode = [0.0, 0.0, 0.12, 0.0, 0.0]

    fig, ax = plt.subplots(figsize=(8, 6))

    def _autopct(pct: float) -> str:
        val = int(round(pct * total / 100.0))
        return f"{pct:.1f}%\n({val:,})"

    wedges, texts, autotexts = ax.pie(
        counts,
        labels=labels,
        colors=colors,
        explode=explode,
        startangle=90,
        autopct=_autopct,
        pctdistance=0.75,
        wedgeprops=dict(edgecolor="white", linewidth=1.5),
        textprops=dict(fontsize=10),
    )
    for t in autotexts:
        t.set_fontsize(8)
        t.set_color("white")
        t.set_weight("bold")

    ax.set_title(
        "Gold mesh_quality distribution (N = 12,009)\n"
        "fbx_supplemented = 788 objects (6.6%) live inside gap_fallback.fbx",
        fontsize=12,
        pad=15,
    )

    plt.tight_layout()
    plt.savefig(FIG_DIR / "coverage_distribution.png", bbox_inches="tight")
    plt.close()
    print("  wrote figures/coverage_distribution.png")


def fig_adjacency_impact() -> None:
    """fbx_supplemented participation in adjacency edges."""
    total_edges = 220_346
    fbx_edges = 20_746
    rest = total_edges - fbx_edges
    fbx_pct = fbx_edges / total_edges * 100
    rest_pct = 100 - fbx_pct

    fig, ax = plt.subplots(figsize=(10, 4.5))

    # Horizontal stacked bar for scale contrast
    ax.barh([0], [rest], color=COLOR_REST, edgecolor="black", label=f"other edges ({rest:,})")
    ax.barh(
        [0],
        [fbx_edges],
        left=[rest],
        color=COLOR_FBX,
        edgecolor="black",
        label=f"fbx_supplemented-touching ({fbx_edges:,})",
    )

    ax.text(
        rest / 2,
        0,
        f"{rest:,}\n({rest_pct:.1f}%)",
        ha="center",
        va="center",
        fontsize=11,
        color="white",
        weight="bold",
    )
    ax.text(
        rest + fbx_edges / 2,
        0,
        f"{fbx_edges:,}\n({fbx_pct:.1f}%)",
        ha="center",
        va="center",
        fontsize=10,
        color="white",
        weight="bold",
    )

    ax.set_yticks([])
    ax.set_xlim(0, total_edges)
    ax.set_xlabel("adjacency edge count")
    ax.set_title(
        "Adjacency graph: fbx_supplemented objects participate in 9.4% of all edges\n"
        "(N = 220,346 symmetric edges, 788 fbx_supplemented objects on ≥1 endpoint)",
        fontsize=12,
        pad=15,
    )
    ax.legend(loc="lower right", fontsize=9, framealpha=0.9)
    ax.grid(axis="x", linestyle="--", alpha=0.3)

    # Extra annotation — structural significance
    ax.annotate(
        "64 of the 788 are articulation points\n(cut vertices in the adjacency graph)",
        xy=(rest + fbx_edges / 2, -0.5),
        xytext=(rest + fbx_edges / 2, -0.85),
        ha="center",
        fontsize=9,
        color="#8b0000",
        arrowprops=dict(arrowstyle="-", color="#8b0000", lw=0.8),
    )
    ax.set_ylim(-1.2, 1.0)

    plt.tight_layout()
    plt.savefig(FIG_DIR / "adjacency_impact.png", bbox_inches="tight")
    plt.close()
    print("  wrote figures/adjacency_impact.png")


def fig_pipeline_fragmentation() -> None:
    """Top 10 pipelines by fragmentation when fbx_supplemented objects removed."""
    # (pipeline, connected_components_with_fbx, connected_components_without_fbx)
    rows = [
        ("P-10147", 7, 24),
        ("P-015", 6, 18),
        ("P-021", 5, 15),
        ("P-10148", 4, 14),
        ("P-10149", 5, 13),
        ("P-032", 3, 11),
        ("P-045", 4, 11),
        ("P-051", 3, 10),
        ("P-10102", 2, 9),
        ("P-060", 3, 9),
    ]
    pipelines = [r[0] for r in rows]
    before = [r[1] for r in rows]
    after = [r[2] for r in rows]

    y = list(range(len(pipelines)))
    bar_h = 0.38

    fig, ax = plt.subplots(figsize=(10, 6))
    b1 = ax.barh(
        [yy + bar_h / 2 for yy in y],
        before,
        height=bar_h,
        color=COLOR_FULL,
        edgecolor="black",
        label="intact (fbx meshes present)",
    )
    b2 = ax.barh(
        [yy - bar_h / 2 for yy in y],
        after,
        height=bar_h,
        color=COLOR_FBX,
        edgecolor="black",
        label="after fbx_supplemented removal",
    )

    for bar, val in zip(b1, before):
        ax.text(
            bar.get_width() + 0.3,
            bar.get_y() + bar.get_height() / 2,
            str(val),
            va="center",
            fontsize=9,
        )
    for bar, val in zip(b2, after):
        ax.text(
            bar.get_width() + 0.3,
            bar.get_y() + bar.get_height() / 2,
            str(val),
            va="center",
            fontsize=9,
            color="#8b0000",
            weight="bold",
        )

    ax.set_yticks(y)
    ax.set_yticklabels(pipelines)
    ax.invert_yaxis()
    ax.set_xlabel("connected component count (lower = better)")
    ax.set_title(
        "Top 10 most-fragmented pipelines if fbx_supplemented objects are dropped\n"
        "40 of 142 pipelines (28.2%) gain at least one extra component",
        fontsize=12,
        pad=15,
    )
    ax.legend(loc="lower right", fontsize=9, framealpha=0.9)
    ax.grid(axis="x", linestyle="--", alpha=0.3)

    plt.tight_layout()
    plt.savefig(FIG_DIR / "pipeline_fragmentation.png", bbox_inches="tight")
    plt.close()
    print("  wrote figures/pipeline_fragmentation.png")


def main() -> int:
    print("Generating M4 figures (DPI 300)...")
    fig_coverage_distribution()
    fig_adjacency_impact()
    fig_pipeline_fragmentation()
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
