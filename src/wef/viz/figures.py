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


# --------------------------------------------------------------------------- results (Phase 6)
MODEL_LABEL = {"seasonal_naive": "Seasonal\nnaive", "sarima": "SARIMA", "ridge": "Ridge", "random_forest": "Random\nforest",
               "xgboost": "XGBoost", "lstm": "LSTM", "gru": "GRU", "cnn_lstm": "CNN-\nLSTM"}
SHORT = {k: v.replace("-\n", "-").replace("\n", " ") for k, v in MODEL_LABEL.items()}


def _metrics():
    return json.loads((RESULTS / "metrics.json").read_text())


def fig_model_comparison():
    """Test MAE of every model relative to seasonal naive (1 = naive; shorter is better), D1 and W1 panels."""
    m = _metrics()
    models = list(MODEL_LABEL)

    def draw(mode, size):
        fig, axes = plt.subplots(1, 2, figsize=(size[0], size[1] * 1.15), sharey=True)
        y = np.arange(len(models))[::-1]
        for ax, letter, h in zip(axes, "ab", ["d1", "w1"]):
            for i, res in enumerate(["electricity", "water"]):
                t = m[res][h]["test"]
                rel = [t[k]["mae"] / t["seasonal_naive"]["mae"] for k in models]
                ax.barh(y + (0.5 - i) * 0.38, rel, 0.38, label=res.capitalize(), **style.bar(mode, i))
            ax.axvline(1, color=style.INK if mode == "slides" else "0", lw=0.8, ls="--")
            ax.set_yticks(y, [SHORT[k] for k in models])
            ax.set_xlabel("Test MAE / seasonal-naive MAE")
            ax.grid(axis="y", visible=False)
            _panel(ax, letter, "Next day, hourly (D1)" if h == "d1" else "Next week, daily (W1)")
        axes[1].legend(frameon=False, loc="lower right")
        fig.tight_layout()
        return fig
    style.save_both("fig_model_comparison", draw)


def _representative_week(resource):
    """The test week (7 consecutive evaluable origins starting on a Monday) whose selected-model MAE is closest
    to the median weekly MAE - a typical week, not a best case."""
    sel = _metrics()[resource]["d1"]["selected"]["model"]
    p = pd.read_parquet(RESULTS / "predictions" / f"{resource}_d1.parquet").reset_index()
    p = p[(p.split == "test") & p.eval_ok]
    ok = set(p.origin)
    weeks = []
    for o in sorted(ok):
        days = [o + pd.Timedelta(days=k) for k in range(7)]
        if o.dayofweek == 0 and all(d in ok for d in days):
            w = p[p.origin.isin(days)]
            weeks.append((float(np.mean(np.abs(w[sel] - w.y))), o))
    med = np.median([e for e, _ in weeks])
    start = min(weeks, key=lambda t: abs(t[0] - med))[1]
    return sel, p[p.origin.isin([start + pd.Timedelta(days=k) for k in range(7)])].sort_values("target_time")


def _fig_forecast(resource):
    sel, w = _representative_week(resource)

    def draw(mode, size):
        fig, ax = plt.subplots(figsize=size)
        series = [("y", "Actual"), ("seasonal_naive", "Seasonal naive"), (sel, f"{SHORT[sel]} (selected)")]
        for i, (col, lab) in enumerate(series):
            kw = style.line(mode, [0, 2, 1][i]) if mode == "report" else {"color": [style.INK, "#b5b4ae", style.SLIDE_COLORS[0]][i]}
            ax.plot(w.target_time, w[col], label=lab, lw=[1.2, 0.9, 1.1][i] if mode == "report" else [2.2, 1.6, 2.0][i], **kw)
        ax.set_ylabel(LABEL[resource]); ax.set_xlabel("Day (test period)")
        ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter("%a %d %b"))
        ax.legend(frameon=False, ncol=3, loc="upper left", bbox_to_anchor=(0, 1.12))
        fig.tight_layout()
        return fig
    style.save_both(f"fig_forecast_{resource}", draw)


def fig_forecast_electricity():
    _fig_forecast("electricity")


def fig_forecast_water():
    _fig_forecast("water")


def fig_error_by_hour():
    m = _metrics()

    def draw(mode, size):
        fig, axes = plt.subplots(1, 2, figsize=size)
        for ax, letter, res in zip(axes, "ab", ["electricity", "water"]):
            e = m[res]["d1"]["error_by_hour"]
            sel = SHORT[m[res]["d1"]["selected"]["model"]]
            ax.plot(range(24), e["seasonal_naive"], label="Seasonal naive", marker="o" if mode == "report" else None, ms=2.5, **style.line(mode, 1 if mode == "slides" else 2))
            ax.plot(range(24), e["selected"], label=f"{sel} (selected)", marker="s" if mode == "report" else None, ms=2.5, **style.line(mode, 0))
            ax.set_xticks(range(0, 24, 3)); ax.set_xlabel("Hour of day"); ax.set_ylabel("Test MAE (" + LABEL[res].split("(")[1])
            _panel(ax, letter, res.capitalize())
            ax.legend(frameon=False)
        fig.tight_layout()
        return fig
    style.save_both("fig_error_by_hour", draw)


def fig_training_curves():
    """Training and validation loss of each resource-horizon's best deep model (viva appendix)."""
    curves = json.loads((RESULTS / "training_curves.json").read_text())
    tuning = json.loads((RESULTS / "tuning.json").read_text())
    picks = []
    for res in ("electricity", "water"):
        for h in ("d1", "w1"):
            t = tuning[f"{res}.{h}"]
            best = min(("lstm", "gru", "cnn_lstm"), key=lambda k: next(c["val_mae"] for c in t[k]["candidates"] if c["params"] == t[k]["selected_params"]))
            picks.append((f"{res}_{h}_{best}", f"{res.capitalize()} {h.upper()}, {SHORT[best]}"))

    def draw(mode, size):
        fig, axes = plt.subplots(2, 2, figsize=(size[0], size[1] * 1.5))
        for ax, letter, (key, title) in zip(axes.ravel(), "abcd", picks):
            c = curves[key]
            ax.plot(range(1, len(c["loss"]) + 1), c["loss"], label="Training", **style.line(mode, 0))
            ax.plot(range(1, len(c["val_loss"]) + 1), c["val_loss"], label="Validation", **style.line(mode, 1))
            ax.set_xlabel("Epoch"); ax.set_ylabel("MSE (scaled)"); _panel(ax, letter, title)
        axes[0, 0].legend(frameon=False)
        fig.tight_layout()
        return fig
    style.save_both("fig_training_curves", draw)


EDA = [fig_eda_profiles, fig_eda_weekly_heatmap, fig_eda_temperature, fig_eda_missing]
RESULT_FIGS = [fig_model_comparison, fig_forecast_electricity, fig_forecast_water, fig_error_by_hour, fig_training_curves]
FIGURES = EDA + RESULT_FIGS  # later phases append their figures here


def run(cfg) -> list:
    for f in FIGURES:
        f()
        print(f"  {f.__name__}")
    return []
