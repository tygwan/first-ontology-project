"""Generate matplotlib figures for M1 finding.

Produces 4 charts in figures/:
  01_piping_confidence.png       - HIGH / MED / LOW / LIKELY_BUG bar chart
  02_substring_bug_causes.png    - Which substring bugs cause the misclassification
  03_likely_misclassified.png    - Top display_name prefixes in LIKELY_BUG
  04_class_distribution.png      - XLSX Piping total vs high-confidence subset

Reads from data/*.csv produced by audit.py.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).parent
DATA_DIR = HERE / "data"
FIG_DIR = HERE / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

# Consistent color palette
COLOR_HIGH = "#2ca02c"    # green
COLOR_MED = "#ff7f0e"     # orange
COLOR_LOW = "#d62728"     # red
COLOR_BUG = "#8b0000"     # dark red
COLOR_OK = "#2ca02c"
COLOR_BAD = "#d62728"

plt.rcParams["figure.dpi"] = 110
plt.rcParams["font.family"] = "DejaVu Sans"


def fig_01_confidence() -> None:
    df = pd.read_csv(DATA_DIR / "piping_confidence_breakdown.csv")
    order = ["HIGH", "MED", "LOW", "LIKELY_BUG"]
    df = df.set_index("confidence").loc[order].reset_index()
    colors = [COLOR_HIGH, COLOR_MED, COLOR_LOW, COLOR_BUG]

    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.bar(df["confidence"], df["count"], color=colors, edgecolor="black")

    for bar, val in zip(bars, df["count"]):
        pct = val / df["count"].sum() * 100
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 50,
            f"{val:,}\n({pct:.1f}%)",
            ha="center",
            va="bottom",
            fontsize=10,
        )

    ax.set_title(
        "Piping class — classification confidence breakdown\n"
        "(4,014 objects labeled 'Piping' by RefinedXlsxExporter)",
        fontsize=12,
        pad=15,
    )
    ax.set_ylabel("Object count")
    ax.set_ylim(0, max(df["count"]) * 1.2)
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    # Legend
    for label, criterion in zip(df["confidence"], df["criterion"]):
        ax.plot([], [], " ", label=f"{label}: {criterion}")
    ax.legend(loc="upper right", fontsize=9, framealpha=0.9)

    plt.tight_layout()
    plt.savefig(FIG_DIR / "01_piping_confidence.png", bbox_inches="tight")
    plt.close()
    print("  wrote figures/01_piping_confidence.png")


def fig_02_substring_bugs() -> None:
    df = pd.read_csv(DATA_DIR / "substring_bug_causes.csv")
    df = df.sort_values("count", ascending=True)

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(
        df["cause"],
        df["count"],
        color=[COLOR_BAD if c > 100 else COLOR_MED for c in df["count"]],
        edgecolor="black",
    )

    for bar, kw, corr in zip(bars, df["keyword_triggered"], df["correct_class_would_be"]):
        ax.text(
            bar.get_width() + 5,
            bar.get_y() + bar.get_height() / 2,
            f"keyword '{kw}' → should be {corr}",
            va="center",
            fontsize=8,
        )

    ax.set_title(
        "Substring matching bugs in RefinedXlsxExporter.InferClass\n"
        "(causes among 997 LIKELY_BUG Piping objects)",
        fontsize=12,
        pad=15,
    )
    ax.set_xlabel("Object count affected")
    ax.set_xlim(0, df["count"].max() * 2.0)
    ax.grid(axis="x", linestyle="--", alpha=0.4)

    plt.tight_layout()
    plt.savefig(FIG_DIR / "02_substring_bug_causes.png", bbox_inches="tight")
    plt.close()
    print("  wrote figures/02_substring_bug_causes.png")


def fig_03_likely_misclassified() -> None:
    df = pd.read_csv(DATA_DIR / "likely_misclassified_sample.csv").head(15)
    df = df.sort_values("count", ascending=True)

    fig, ax = plt.subplots(figsize=(9, 6))
    colors = ["#cc3333" if c >= 50 else "#ff9966" for c in df["count"]]
    bars = ax.barh(df["display_name_prefix"], df["count"], color=colors, edgecolor="black")

    for bar, val in zip(bars, df["count"]):
        ax.text(
            bar.get_width() + 2,
            bar.get_y() + bar.get_height() / 2,
            str(val),
            va="center",
            fontsize=9,
        )

    ax.set_title(
        "Top 15 display_name prefixes in LIKELY_BUG Piping (n=997)\n"
        "These are classified as Piping but are actually Structure / Electrical / etc.",
        fontsize=11,
        pad=15,
    )
    ax.set_xlabel("Object count")
    ax.set_xlim(0, df["count"].max() * 1.2)
    ax.grid(axis="x", linestyle="--", alpha=0.4)

    plt.tight_layout()
    plt.savefig(FIG_DIR / "03_likely_misclassified.png", bbox_inches="tight")
    plt.close()
    print("  wrote figures/03_likely_misclassified.png")


def fig_04_class_distribution() -> None:
    """Before/after style comparison: XLSX Piping=4014 vs HIGH-confidence only=2926."""
    labels = ["XLSX Class\n= Piping", "Actual Piping\n(HIGH confidence)"]
    values = [4014, 2926]
    diff = 4014 - 2926  # = 1088 (includes the 997 LIKELY_BUG + 91 LOW)

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(
        labels,
        values,
        color=[COLOR_BAD, COLOR_OK],
        edgecolor="black",
        width=0.55,
    )

    for bar, val in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 50,
            f"{val:,}",
            ha="center",
            va="bottom",
            fontsize=13,
            fontweight="bold",
        )

    # Arrow showing the delta
    ax.annotate(
        f"- {diff:,} questionable",
        xy=(1, 2926),
        xytext=(0.5, 3500),
        fontsize=11,
        ha="center",
        color="#cc0000",
        arrowprops=dict(arrowstyle="->", color="#cc0000", lw=1.5),
    )

    ax.set_title(
        "Piping class inflation due to classifier bugs\n"
        "(XLSX reports 4,014; high-confidence subset is 2,926)",
        fontsize=12,
        pad=15,
    )
    ax.set_ylabel("Object count")
    ax.set_ylim(0, 4500)
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    plt.tight_layout()
    plt.savefig(FIG_DIR / "04_class_distribution.png", bbox_inches="tight")
    plt.close()
    print("  wrote figures/04_class_distribution.png")


def main() -> int:
    print("Generating M1 figures...")
    fig_01_confidence()
    fig_02_substring_bugs()
    fig_03_likely_misclassified()
    fig_04_class_distribution()
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
