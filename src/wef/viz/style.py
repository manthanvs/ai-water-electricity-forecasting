"""Two figure styles: 'report' (greyscale, serif, 300 dpi) and 'slides' (colour, sans, 200 dpi).

Every figure is drawn once per style by `save_both`; report PNGs are forced to greyscale after saving.
"""
from contextlib import contextmanager

import matplotlib

matplotlib.use("Agg")
import matplotlib as mpl  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from cycler import cycler  # noqa: E402
from PIL import Image  # noqa: E402

from wef.utils.paths import ROOT  # noqa: E402

# Slides: validated categorical palette (fixed order, never cycled past 8); text stays neutral ink.
SLIDE_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
INK, INK2 = "#0b0b0b", "#52514e"
REPORT_GREYS = ["0.0", "0.35", "0.6", "0.0", "0.35"]
REPORT_LINES = ["-", "--", ":", "-.", (0, (5, 1, 1, 1))]
HATCHES = ["", "//", "..", "xx", "\\\\", "--", "++", "oo"]

REPORT = {
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Liberation Serif", "DejaVu Serif"],
    "font.size": 9, "axes.labelsize": 9, "legend.fontsize": 8, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "axes.prop_cycle": cycler(color=REPORT_GREYS) + cycler(linestyle=REPORT_LINES),
    "axes.grid": True, "grid.color": "0.85", "grid.linewidth": 0.5,
    "lines.linewidth": 1.0,
    "savefig.dpi": 300, "figure.dpi": 100, "savefig.bbox": "tight",
}
SLIDES = {
    "font.family": "sans-serif",
    "font.sans-serif": ["Segoe UI", "Arial", "Liberation Sans", "DejaVu Sans"],
    "font.size": 14, "axes.labelsize": 14, "legend.fontsize": 13, "xtick.labelsize": 13, "ytick.labelsize": 13,
    "axes.prop_cycle": cycler(color=SLIDE_COLORS),
    "axes.grid": True, "grid.color": "#e4e3df", "grid.linewidth": 0.6,
    "axes.edgecolor": "#b5b4ae", "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "axes.spines.top": False, "axes.spines.right": False,
    "lines.linewidth": 2.0,
    "savefig.dpi": 200, "figure.dpi": 100, "savefig.bbox": "tight",
}
SIZE = {"report": (5.9, 3.0), "slides": (11.0, 5.2)}
# Single-panel report figures are drawn at their printed width (about 117 mm) so that axis text stays
# at 8-9 pt in the report instead of being scaled down from the full text width.
COMPACT_REPORT = (4.6, 2.1)


def report():
    mpl.rcParams.update(REPORT)


def slides():
    mpl.rcParams.update(SLIDES)


def colour(mode: str, i: int):
    return REPORT_GREYS[i % len(REPORT_GREYS)] if mode == "report" else SLIDE_COLORS[i]


def line(mode: str, i: int) -> dict:
    """Line kwargs for series i: grey + line style in the report, palette colour on slides."""
    if mode == "report":
        return {"color": REPORT_GREYS[i % 5], "linestyle": REPORT_LINES[i % 5]}
    return {"color": SLIDE_COLORS[i], "linestyle": "-"}


def bar(mode: str, i: int) -> dict:
    if mode == "report":
        return {"facecolor": "white", "edgecolor": "black", "hatch": HATCHES[i], "linewidth": 0.6}
    return {"color": SLIDE_COLORS[i], "edgecolor": "white", "linewidth": 1.0}


def cmap(mode: str) -> str:
    return "Greys" if mode == "report" else "Blues"


@contextmanager
def _style(mode):
    with mpl.rc_context(REPORT if mode == "report" else SLIDES):
        yield


def save_both(fig_id: str, draw, compact: bool = False) -> None:
    """draw(mode, figsize) -> Figure. Writes figures/report/<id>.png (greyscale) and figures/slides/<id>.png."""
    for mode in ("report", "slides"):
        out = ROOT / "figures" / mode / f"{fig_id}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        with _style(mode):
            fig = draw(mode, COMPACT_REPORT if compact and mode == "report" else SIZE[mode])
            fig.savefig(out)
            plt.close(fig)
        if mode == "report":
            Image.open(out).convert("L").save(out)
