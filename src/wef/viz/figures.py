"""Every figure of the project, drawn in both styles via wef.viz.style.save_both. EDA uses training data only."""
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from wef.data.clean import PROCESSED
from wef.utils.paths import RESULTS
from wef.viz import style

LABEL = {"electricity": "Electricity (kW)", "water": "Water, DMA 3 (L/s)"}
DAILY_LABEL = {"electricity": "Daily energy (kWh)", "water": "Daily volume (m$^3$)"}
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _train(resource: str, freq: str = "hourly") -> pd.DataFrame:
    sp = json.loads((RESULTS / "eda_summary.json").read_text())[resource]["splits"]["train"]
    df = pd.read_parquet(PROCESSED / f"{resource}_{freq}.parquet")
    return df.loc[sp[0]:sp[1] + (" 23:00" if freq == "hourly" else "")]


def _panel(ax, letter, text):
    ax.set_title(f"({letter}) {text}", loc="left", fontsize=plt.rcParams["axes.labelsize"])


def fig_eda_profiles():
    def draw(mode, size):
        fig, axes = plt.subplots(1, 2, figsize=size)
        for ax, letter, res in zip(axes, "ab", ["electricity", "water"]):
            h = _train(res)["value"]
            weekend = h.index.dayofweek >= 5
            for i, (mask, lab) in enumerate([(~weekend, "Weekday"), (weekend, "Weekend")]):
                prof = h[mask].groupby(h.index[mask].hour).mean()
                ax.plot(prof.index, prof.values, label=lab, marker="o" if mode == "report" else None,
                        markersize=2.5, **style.line(mode, i))
            ax.set_xticks(range(0, 24, 3)); ax.set_xlim(0, 23)
            ax.set_xlabel("Hour of day"); ax.set_ylabel(LABEL[res]); _panel(ax, letter, res.capitalize())
        axes[0].legend(frameon=False)
        fig.tight_layout()
        return fig
    style.save_both("fig_eda_profiles", draw)


def fig_eda_weekly_heatmap():
    def draw(mode, size):
        fig, axes = plt.subplots(1, 2, figsize=size)
        for ax, letter, res in zip(axes, "ab", ["electricity", "water"]):
            h = _train(res)["value"]
            grid = h.groupby([h.index.dayofweek, h.index.hour]).mean().unstack()
            im = ax.imshow(grid.values, aspect="auto", cmap=style.cmap(mode), origin="upper")
            ax.set_yticks(range(7), DAYS); ax.set_xticks(range(0, 24, 3)); ax.grid(False)
            ax.set_xlabel("Hour of day"); _panel(ax, letter, res.capitalize())
            fig.colorbar(im, ax=ax, label=LABEL[res], fraction=0.05, pad=0.02)
        fig.tight_layout()
        return fig
    style.save_both("fig_eda_weekly_heatmap", draw)


def fig_eda_temperature():
    from statsmodels.nonparametric.smoothers_lowess import lowess

    def draw(mode, size):
        fig, axes = plt.subplots(1, 2, figsize=size)
        for ax, letter, res in zip(axes, "ab", ["electricity", "water"]):
            d = _train(res, "daily").dropna(subset=["value"])
            ax.scatter(d["temperature_mean"], d["value"], s=4 if mode == "report" else 10, alpha=0.5,
                       color=style.colour(mode, 2 if mode == "report" else 0), linewidths=0, label="Day")
            fit = lowess(d["value"], d["temperature_mean"], frac=0.3)
            ax.plot(fit[:, 0], fit[:, 1], label="LOWESS", **style.line(mode, 0 if mode == "report" else 1))
            ax.set_xlabel("Daily mean temperature ($^\\circ$C)"); ax.set_ylabel(DAILY_LABEL[res])
            _panel(ax, letter, res.capitalize())
        axes[0].legend(frameon=False)
        fig.tight_layout()
        return fig
    style.save_both("fig_eda_temperature", draw)


def fig_eda_missing():
    """Share of missing hours per day before short-gap filling (all data: a data-quality view, not a value view)."""
    e = pd.read_parquet(PROCESSED / "electricity_hourly.parquet")
    e_miss = (e["interpolated"] | e["long_gap"]).resample("D").mean()
    dmas = pd.read_parquet(PROCESSED / "water_all_dmas_hourly.parquet").isna().resample("D").mean()

    def draw(mode, size):
        fig, axes = plt.subplots(2, 1, figsize=(size[0], size[1] * 1.4), height_ratios=[1, 2], layout="constrained")
        years = sorted(set(e_miss.index.year))
        grid = np.full((len(years), 366), np.nan)
        for t, v in e_miss.items():
            grid[years.index(t.year), t.dayofyear - 1] = v
        cm = plt.get_cmap(style.cmap(mode)).copy(); cm.set_bad("white")
        axes[0].imshow(grid, aspect="auto", cmap=cm, vmin=0, vmax=1, interpolation="nearest")
        axes[0].set_yticks(range(len(years)), years); axes[0].set_xlabel("Day of year"); axes[0].grid(False)
        _panel(axes[0], "a", "Electricity")
        im = axes[1].imshow(dmas.T.values, aspect="auto", cmap=cm, vmin=0, vmax=1, interpolation="nearest",
                            extent=[0, len(dmas), len(dmas.columns) - 0.5, -0.5])
        ticks = [i for i, t in enumerate(dmas.index) if t.day == 1 and t.month in (1, 7)]
        axes[1].set_xticks(ticks, [dmas.index[i].strftime("%b %Y") for i in ticks])
        axes[1].set_yticks(range(len(dmas.columns)), dmas.columns); axes[1].grid(False)
        _panel(axes[1], "b", "Water, all DMAs")
        fig.colorbar(im, ax=axes, label="Share of hours missing", fraction=0.03, pad=0.02)
        return fig
    style.save_both("fig_eda_missing", draw)


EDA = [fig_eda_profiles, fig_eda_weekly_heatmap, fig_eda_temperature, fig_eda_missing]
FIGURES = EDA  # later phases append their figures here


def run(cfg) -> list:
    for f in FIGURES:
        f()
        print(f"  {f.__name__}")
    return []
