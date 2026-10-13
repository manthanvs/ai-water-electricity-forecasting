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
        ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter("%a %d" if mode == "report" else "%a %d %b"))
        ax.legend(frameon=False, ncol=3, loc="lower left", bbox_to_anchor=(0, 1.0))
        fig.tight_layout()
        return fig
    style.save_both(f"fig_forecast_{resource}", draw, compact=True)


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


# --------------------------------------------------------------------------- anomaly detection (Phase 7)
def fig_anomaly_water():
    """BattLeDIM test period: daily mean network inflow, leaks that start in the period shaded, alarms marked."""
    s = pd.read_parquet(PROCESSED / "anomaly_water_test_series.parquet")
    a = json.loads((RESULTS / "anomaly.json").read_text())["water"]
    lab = pd.read_csv(PROCESSED / "anomaly_water_labels.csv", parse_dates=["start", "end", "peak", "window_end"])
    ev = pd.read_csv(RESULTS / "anomaly_events.csv", parse_dates=["alarm", "start", "end"])
    ev = ev[ev.resource == "water"]
    t0, t1 = pd.Timestamp(a["splits"]["test"][0]), pd.Timestamp(a["splits"]["test"][1]) + pd.Timedelta(hours=23)
    s = s.loc[t0:t1]
    lab = lab[(lab.start >= t0) & (lab.start <= t1)]

    def draw(mode, size):
        fig, ax = plt.subplots(figsize=(size[0], size[1] * 1.1))
        daily = s["actual"].resample("D").mean()
        ax.plot(daily.index, daily.values, label="Network inflow (daily mean)", **style.line(mode, 0))
        for i, r in enumerate(lab.itertuples()):
            ax.axvline(r.start, color="0.3" if mode == "report" else style.SLIDE_COLORS[3], lw=1.0 if mode == "report" else 2,
                       ls="--", label="Leak start (labelled)" if i == 0 else None)
            ax.annotate(f"{r.link} ({r.type})", (r.start, 1.0), xycoords=("data", "axes fraction"), rotation=90,
                        va="top", ha="right", fontsize=plt.rcParams["legend.fontsize"] - 1, color=style.INK2 if mode == "slides" else "0.2")
        lo, hi = ax.get_ylim()
        for j, (meth, lab_m, mk) in enumerate([("residual_zscore", "Alarm: residual z-score", "v"), ("isolation_forest", "Alarm: Isolation Forest", "x")]):
            e = ev[ev.method == meth]
            ax.scatter(e.alarm, np.full(len(e), lo - (0.04 + 0.05 * j) * (hi - lo)), marker=mk, s=18 if mode == "report" else 40,
                       clip_on=False, color=style.colour(mode, 0) if mode == "report" else style.SLIDE_COLORS[[2, 4][j]], label=lab_m, zorder=3)
        ax.set_ylim(lo - 0.12 * (hi - lo), hi)
        ax.set_ylabel("Inflow (m$^3$/h)"); ax.set_xlabel("2018 (test period)")
        ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter("%b"))
        ax.legend(frameon=False, ncol=2, loc="upper left", bbox_to_anchor=(0, -0.18))
        fig.tight_layout()
        return fig
    style.save_both("fig_anomaly_water", draw, compact=True)


def fig_anomaly_electricity():
    """Injected anomalies (labelled INJECTED) and detections on the test fortnight with the most injected events."""
    s = pd.read_parquet(PROCESSED / "anomaly_electricity_test_series.parquet")
    lab = pd.read_csv(PROCESSED / "electricity_test_injected_labels.csv", parse_dates=["start", "end"])
    ev = pd.read_csv(RESULTS / "anomaly_events.csv", parse_dates=["alarm", "start", "end"])
    ev = ev[ev.resource == "electricity"]
    starts = pd.date_range(lab.start.min().normalize(), lab.end.max().normalize(), freq="D")
    best = max(starts, key=lambda d: ((lab.start >= d) & (lab.start < d + pd.Timedelta(days=14))).sum())
    t0, t1 = best, best + pd.Timedelta(days=14)
    s, lab = s.loc[t0:t1], lab[(lab.end >= t0) & (lab.start <= t1)]

    def draw(mode, size):
        fig, ax = plt.subplots(figsize=size)
        ax.plot(s.index, s["actual"], label="Actual with INJECTED anomalies", lw=0.8 if mode == "report" else 1.4, **{k: v for k, v in style.line(mode, 0).items()})
        ax.plot(s.index, s["forecast"], label="Forecast (selected model)", lw=0.8 if mode == "report" else 1.4, **style.line(mode, 1))
        for i, r in enumerate(lab.itertuples()):
            kw = {"facecolor": "none", "edgecolor": "0.4", "hatch": "///", "lw": 0} if mode == "report" else {"color": style.SLIDE_COLORS[3], "alpha": 0.22, "lw": 0}
            ax.axvspan(max(r.start, t0), min(r.end + pd.Timedelta(hours=1), t1), label="Injected anomaly" if i == 0 else None, **kw)
            ax.annotate(r.type.replace("_", " "), (max(r.start, t0), 1.0), xycoords=("data", "axes fraction"), va="top",
                        fontsize=plt.rcParams["legend.fontsize"] - 1, color=style.INK2 if mode == "slides" else "0.2")
        lo, hi = ax.get_ylim()
        for j, (meth, lab_m, mk) in enumerate([("residual_zscore", "Alarm: residual z-score", "v"), ("isolation_forest", "Alarm: Isolation Forest", "x")]):
            e = ev[(ev.method == meth) & (ev.alarm >= t0) & (ev.alarm <= t1)]
            ax.scatter(e.alarm, np.full(len(e), lo - (0.04 + 0.05 * j) * (hi - lo)), marker=mk, s=18 if mode == "report" else 40, clip_on=False,
                       color=style.colour(mode, 0) if mode == "report" else style.SLIDE_COLORS[[2, 4][j]], label=lab_m, zorder=3)
        ax.set_ylim(lo - 0.12 * (hi - lo), hi)
        ax.set_ylabel(LABEL["electricity"]); ax.set_xlabel("Test period (2010)")
        ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter("%d %b"))
        ax.legend(frameon=False, ncol=3, loc="upper left", bbox_to_anchor=(0, -0.16))
        fig.tight_layout()
        return fig
    style.save_both("fig_anomaly_electricity", draw, compact=True)


# --------------------------------------------------------------------------- optimisation (Phase 8)
def fig_pump_schedule():
    """The median-saving test day: forecast and actual demand, optimised pumping, tank level, tariff bands."""
    d = pd.read_csv(RESULTS / "pump_schedule_example.csv")
    o = json.loads((RESULTS / "optimisation.json").read_text())["assumptions"]
    cap = o["tank"]["capacity_m3"]
    lmin, lmax = cap * o["tank"]["min_fraction"], cap * o["tank"]["max_fraction"]

    def draw(mode, size):
        fig, (a1, a2) = plt.subplots(2, 1, figsize=(size[0], size[1] * (1.3 if mode == "report" else 1.45)), sharex=True, height_ratios=[1.2, 1])
        h = d["hour"].to_numpy()
        for ax in (a1, a2):
            for hr, band in zip(h, d["band"]):
                if band != "normal":
                    kw = ({"facecolor": "0.88" if band == "peak" else "white", "hatch": "..." if band == "off_peak" else None,
                           "edgecolor": "0.7", "lw": 0} if mode == "report" else
                          {"color": style.SLIDE_COLORS[7] if band == "peak" else style.SLIDE_COLORS[2], "alpha": 0.12, "lw": 0})
                    ax.axvspan(hr - 0.5, hr + 0.5, zorder=0, **kw)
        a1.bar(h, d["planned_pumping_m3h"], 0.7, label="Optimised pumping (plan)", zorder=2, **style.bar(mode, 1 if mode == "report" else 0))
        a1.plot(h, d["forecast_m3h"], label="Forecast demand", marker="o" if mode == "report" else None, ms=2.5, zorder=3, **style.line(mode, 0 if mode == "report" else 1))
        a1.plot(h, d["actual_m3h"], label="Actual demand", zorder=3, **(style.line(mode, 2) if mode == "report" else {"color": style.INK, "ls": ":"}))
        a1.set_ylabel("m$^3$/h")
        a1.legend(frameon=False, ncol=3, loc="upper left", bbox_to_anchor=(0, 1.22))
        a2.plot(h, d["planned_level_m3"], label="Tank level, plan", **style.line(mode, 0 if mode == "report" else 0))
        a2.plot(h, d["simulated_level_m3"], label="Tank level, actual demand", **(style.line(mode, 1) if mode == "report" else {"color": style.SLIDE_COLORS[1], "ls": "--"}))
        for v in (lmin, lmax):
            a2.axhline(v, color="0.3" if mode == "report" else style.INK2, lw=0.8, ls=":")
        a2.text(23.4, lmax, "max", va="top", ha="right", fontsize=plt.rcParams["legend.fontsize"] - 1)
        a2.text(23.4, lmin, "min", va="bottom", ha="right", fontsize=plt.rcParams["legend.fontsize"] - 1)
        a2.set_ylabel("Tank level (m$^3$)")
        a2.set_xlabel("Hour of day (grey: peak tariff; dotted: off-peak)" if mode == "report"
                      else "Hour of day (red: peak tariff; green: off-peak)")
        a2.set_xticks(range(0, 24, 3)); a2.set_xlim(-0.5, 23.5)
        if mode == "slides":  # report: the caption legend explains solid (plan) and dashed (actual demand)
            a2.legend(frameon=False, ncol=2, loc="lower left")
        fig.tight_layout()
        return fig
    style.save_both("fig_pump_schedule", draw, compact=True)


# --------------------------------------------------------------------------- screenshots (Phase 11)
def _free_port(preferred=0):
    """The preferred port if it is free (so screenshots show the documented port), else any free port."""
    import socket
    for port in (preferred, 0):
        with socket.socket() as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return sock.getsockname()[1]
            except OSError:
                continue


def _wait_http(url, timeout=120):
    import time

    import requests
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            if requests.get(url, timeout=2).ok:
                return
        except requests.RequestException:
            pass
        time.sleep(1)
    raise TimeoutError(url)


def fig_dashboard():
    """Start the API and the dashboard, open the Forecast page in headless Chromium/Edge (1600 x 900), save the
    colour screenshot for the slides and a greyscale copy for the report. Skips with a warning if no browser works."""
    import os
    import subprocess
    import sys

    from PIL import Image
    from wef.utils.paths import ROOT
    api_port, ui_port = _free_port(5000), _free_port(8501)
    env = {**os.environ, "WEF_API_URL": f"http://127.0.0.1:{api_port}"}
    procs = [subprocess.Popen([sys.executable, "-m", "flask", "--app", "api.app", "run", "--port", str(api_port)], cwd=ROOT,
                              env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL),
             subprocess.Popen([sys.executable, "-m", "streamlit", "run", "dashboard/app.py", "--server.port", str(ui_port),
                               "--server.headless", "true", "--browser.gatherUsageStats", "false"], cwd=ROOT, env=env,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)]
    out = {m: ROOT / "figures" / m / "fig_dashboard.png" for m in ("slides", "report")}
    try:
        _wait_http(f"http://127.0.0.1:{api_port}/api/health")
        _wait_http(f"http://127.0.0.1:{ui_port}/_stcore/health")
        from playwright.sync_api import Error, sync_playwright
        with sync_playwright() as pw:
            browser = None
            for kw in ({"channel": "msedge"}, {"channel": "chrome"}, {}):
                try:
                    browser = pw.chromium.launch(**kw)
                    break
                except Error:
                    continue
            if browser is None:
                print("  WARNING fig_dashboard skipped: no Chromium/Edge/Chrome found (run: playwright install chromium)")
                return
            page = browser.new_page(viewport={"width": 1600, "height": 900})
            page.goto(f"http://127.0.0.1:{ui_port}", wait_until="networkidle")
            page.get_by_text("Forecast", exact=True).first.click()
            page.wait_for_selector(".js-plotly-plot", timeout=120000)
            page.wait_for_timeout(4000)
            out["slides"].parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(out["slides"]))
            browser.close()
        out["report"].parent.mkdir(parents=True, exist_ok=True)
        # report copy: crop the sidebar so the chart stays legible at print width
        Image.open(out["slides"]).convert("L").crop((300, 90, 1600, 900)).save(out["report"])
    finally:
        for proc in procs:
            proc.terminate()


def convert_raw_screenshots():
    """Power BI screenshots saved by hand in figures/raw_screenshots/*.png -> slide copy and greyscale report copy."""
    from PIL import Image
    from wef.utils.paths import ROOT
    for src in sorted((ROOT / "figures" / "raw_screenshots").glob("*.png")):
        img = Image.open(src).convert("RGB")
        for mode in ("slides", "report"):
            dst = ROOT / "figures" / mode / src.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            (img if mode == "slides" else img.convert("L")).save(dst)
        print(f"  converted {src.name}")


EDA = [fig_eda_profiles, fig_eda_weekly_heatmap, fig_eda_temperature, fig_eda_missing]
RESULT_FIGS = [fig_model_comparison, fig_forecast_electricity, fig_forecast_water, fig_error_by_hour, fig_training_curves]
ANOMALY_FIGS = [fig_anomaly_water, fig_anomaly_electricity]
def _diagrams():
    from wef.viz.architecture import fig_architecture, fig_pipeline
    return [fig_architecture, fig_pipeline]


FIGURES = EDA + RESULT_FIGS + ANOMALY_FIGS + [fig_pump_schedule]
# ids required by section E of 01_PROJECT_BUILD.md (tests check both versions exist; report versions greyscale)
REQUIRED = ["fig_architecture", "fig_pipeline", "fig_eda_profiles", "fig_eda_temperature", "fig_forecast_electricity",
            "fig_forecast_water", "fig_model_comparison", "fig_anomaly_water", "fig_anomaly_electricity", "fig_pump_schedule",
            "fig_dashboard"]


def run(cfg) -> list:
    for f in _diagrams() + FIGURES + [fig_dashboard]:
        f()
        print(f"  {f.__name__}")
    convert_raw_screenshots()
    return []
