"""Common matplotlib style setup for analysis scripts — Korean font support.

Usage:
    from _plot_style import setup_plot_style
    setup_plot_style()

Locally registers Noto Sans CJK KR from ~/.fonts/ and sets matplotlib rcParams
so that Korean text renders correctly in saved figures.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt


FONT_PATH = Path.home() / ".fonts" / "NanumGothic.ttf"


def setup_plot_style() -> None:
    """Register Korean font and apply common rcParams."""
    if FONT_PATH.exists():
        fm.fontManager.addfont(str(FONT_PATH))
        prop = fm.FontProperties(fname=str(FONT_PATH))
        family = prop.get_name()
    else:
        family = "DejaVu Sans"
    plt.rcParams.update({
        "font.family": family,
        "axes.unicode_minus": False,
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "figure.dpi": 100,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
    })
