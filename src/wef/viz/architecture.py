"""Diagrams drawn with matplotlib patches: fig_architecture (system) and fig_pipeline (six-stage methodology)."""
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from wef.viz import style

# slide tints per layer (light versions of the palette); the report is black on white
TINT = {"data": "#dceafa", "prep": "#e2f4ec", "model": "#fdebd9", "out": "#fbf0d2", "serve": "#ece9f8"}
EDGE = {"data": "#2a78d6", "prep": "#1baf7a", "model": "#eb6834", "out": "#c98500", "serve": "#4a3aa7"}


def _box(ax, mode, x, y, w, h, title, lines=(), layer="data", fs=None):
    fs = fs or plt.rcParams["font.size"]
    if mode == "report":
        kw = {"facecolor": "white", "edgecolor": "black", "linewidth": 0.8}
    else:
        kw = {"facecolor": TINT[layer], "edgecolor": EDGE[layer], "linewidth": 1.4}
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.008,rounding_size=0.015", **kw))
    ax.text(x + w / 2, y + h - 0.012, title, ha="center", va="top", fontsize=fs, fontweight="bold", color=style.INK)
    if lines:
        ax.text(x + w / 2, y + h / 2 - 0.018, "\n".join(lines), ha="center", va="center", fontsize=fs - 1,
                color="0.15" if mode == "report" else style.INK2, linespacing=1.25)
    return (x, y, w, h)


def _arrow(ax, mode, a, b, side_a="r", side_b="l"):
    def pt(box, side):
        x, y, w, h = box
        return {"r": (x + w, y + h / 2), "l": (x, y + h / 2), "t": (x + w / 2, y + h), "b": (x + w / 2, y)}[side]
    ax.add_patch(FancyArrowPatch(pt(a, side_a), pt(b, side_b), arrowstyle="-|>", mutation_scale=9,
                                 color="black" if mode == "report" else style.INK2, lw=0.8 if mode == "report" else 1.3,
                                 shrinkA=1, shrinkB=1))


def fig_architecture():
    """Five layers left to right; one arrow between layers, vertical arrows only for real dependencies."""
    def draw(mode, size):
        # report: drawn at the printed width (150 mm) so text prints at 7-8 pt
        fig = plt.figure(figsize=(size[0], size[0] * 0.46) if mode == "report" else (size[0], size[1] * 1.2))
        ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
        fs = 8 if mode == "report" else 10.5
        w, h, pad = 0.16, 0.23, 0.008
        xs = [0.02, 0.22, 0.42, 0.62, 0.82]
        ys = [0.64, 0.33, 0.02]
        heads = ["Data sources", "Data pipeline", "Forecasting models", "Analytics", "Delivery"]
        col = [[("Smart-meter data", ["household power", "(UCI); district", "water (BWDF)"]),
                ("Weather", ["Open-Meteo archive;", "BWDF weather"]),
                ("Leak labels", ["BattLeDIM 2018", "(L-Town)"])],
               [("Ingestion", ["checksummed", "downloads"]),
                ("Preprocessing", ["DST, gaps, outliers;", "hourly and daily"]),
                ("Feature store", ["lag rule, calendar,", "weather"])],
               [("Statistical", ["seasonal naive,", "SARIMA"]),
                ("Machine learning", ["Ridge, Random", "Forest, XGBoost"]),
                ("Deep learning", ["LSTM, GRU,", "CNN-LSTM"])],
               [("Forecasts", ["next day (hourly),", "next week (daily)"]),
                ("Anomaly detection", ["residual z-score,", "Isolation Forest"]),
                ("Optimisation", ["pump-schedule LP,", "peak alerts"])],
               [("Flask REST API", ["JSON endpoints"]),
                ("Dashboard", ["Streamlit,", "six pages"]),
                ("Power BI", ["star-schema", "CSV export"])]]
        layers = ["data", "prep", "model", "out", "serve"]
        groups, boxes = [], []
        for x, c, layer, head in zip(xs, col, layers, heads):
            gx, gy, gw, gh = x - pad, ys[-1] - pad, w + 2 * pad, ys[0] + h - ys[-1] + 2 * pad
            if mode == "report":
                ax.add_patch(FancyBboxPatch((gx, gy), gw, gh, boxstyle="round,pad=0,rounding_size=0.02",
                                            facecolor="0.94", edgecolor="0.5", linewidth=0.6, linestyle="--"))
            else:
                ax.add_patch(FancyBboxPatch((gx, gy), gw, gh, boxstyle="round,pad=0,rounding_size=0.02",
                                            facecolor="none", edgecolor=EDGE[layer], linewidth=1.0, linestyle="--"))
            ax.text(x + w / 2, gy + gh + 0.02, head, ha="center", va="bottom", fontsize=fs + 0.5, style="italic", color=style.INK)
            groups.append((gx, gy, gw, gh))
            boxes.append([_box(ax, mode, x, y, w, h, t, l, layer, fs) for (t, l), y in zip(c, ys)])
        for a, b in zip(groups, groups[1:]):
            _arrow(ax, mode, a, b)
        for i, j in [(1, 0), (1, 1), (3, 0), (3, 1), (4, 0)]:  # ingestion > preprocessing > features; forecasts > anomaly > optimisation; API > dashboard
            _arrow(ax, mode, boxes[i][j], boxes[i][j + 1], "b", "t")
        return fig
    style.save_both("fig_architecture", draw)


def fig_pipeline():
    stages = [("1  Data acquisition", ["four public", "datasets,", "checksums"]),
              ("2  Cleaning and EDA", ["DST, gaps,", "outliers,", "profiles"]),
              ("3  Features", ["lag rule,", "calendar,", "weather"]),
              ("4  Modelling", ["8 models,", "2 horizons,", "validation tuning"]),
              ("5  Evaluation", ["rolling origin,", "metrics,", "DM test"]),
              ("6  Applications", ["anomalies, pump", "LP, API,", "dashboard"])]
    layers = ["data", "prep", "prep", "model", "out", "serve"]

    def draw(mode, size):
        fig = plt.figure(figsize=(size[0], size[1] * 0.34))
        ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
        fs = 6.5 if mode == "report" else 11
        n, gap = len(stages), 0.04
        w = (1 - gap * (n + 1)) / n
        boxes = [_box(ax, mode, gap + i * (w + gap), 0.06, w, 0.88, t.replace("  ", "\n", 1), l, layer, fs)
                 for i, ((t, l), layer) in enumerate(zip(stages, layers))]
        for a, b in zip(boxes, boxes[1:]):
            _arrow(ax, mode, a, b)
        return fig
    style.save_both("fig_pipeline", draw)
