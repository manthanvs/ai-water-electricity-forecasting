"""`evaluate` stage: metrics for every model from the rolling-origin backtest predictions.

The backtest itself (one forecast per origin over validation and test, no refitting inside a period) is run by
`wef.models.registry` and stored in results/predictions/. Here every model is scored on the same origins
(`eval_ok`), the operational model is selected by validation MAE, and the selected model is compared with the
best alternative by a Diebold-Mariano test on per-origin MAE.
"""
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from scipy import stats

from wef.cli import _git_commit
from wef.data.clean import UNITS, split_dates
from wef.evaluation.metrics import all_metrics, mae
from wef.features import build
from wef.models.registry import PRED_DIR
from wef.utils.io import read_json, write_json
from wef.utils.paths import RESULTS

METRICS = RESULTS / "metrics.json"
NAIVE = "seasonal_naive"
ABLATION_SUFFIX = "_no_weather"


def diebold_mariano(loss_a, loss_b, h: int) -> dict:
    """Two-sided DM test of equal mean loss (a - b) with the Harvey et al. small-sample correction.
    h = forecast-overlap lag: 1 for D1 (origins one day apart, non-overlapping), 7 for W1."""
    d = np.asarray(loss_a) - np.asarray(loss_b)
    n, dbar = len(d), d.mean()
    gamma = [np.mean((d[k:] - dbar) * (d[:n - k] - dbar)) for k in range(h)]
    var = (gamma[0] + 2 * sum(gamma[1:])) / n
    if var <= 0:
        return {"statistic": float("nan"), "p_value": float("nan"), "n": n}
    dm = dbar / np.sqrt(var)
    dm *= np.sqrt((n + 1 - 2 * h + h * (h - 1) / n) / n)
    return {"statistic": float(dm), "p_value": float(2 * stats.t.sf(abs(dm), df=n - 1)), "n": n,
            "mean_loss_difference": float(dbar)}


def score(resource: str, horizon: str, cfg) -> dict:
    preds = pd.read_parquet(PRED_DIR / f"{resource}_{horizon}.parquet")
    table = pd.read_parquet(build.FEATURES / f"{resource}_{horizon}.parquet")
    train_y = table.loc[(table.split == "train") & table.y.notna(), "y"]
    train_mean, peak = float(train_y.mean()), float(train_y.quantile(cfg["metrics"]["peak_quantile"]))
    models = [c for c in preds.columns if c not in ("target_time", "split", "y", "eval_ok")]
    base = [m for m in models if not m.endswith(ABLATION_SUFFIX)]
    daily = pd.read_parquet(build.PROCESSED / f"{resource}_daily.parquet")
    out = {"split_dates": split_dates(resource, daily.index, cfg),
           "train_mean": train_mean, "peak_threshold": peak,
           "mape_min_actual": cfg["metrics"]["mape_min_fraction_of_train_mean"] * train_mean}
    per_origin = {}
    for split in ("val", "test"):
        p = preds[(preds.split == split) & preds.eval_ok]
        out[f"n_{split}_origins"] = int(p.index.get_level_values("origin").nunique())
        naive_mae = mae(p.y.to_numpy(), p[NAIVE].to_numpy())
        out[split] = {m: all_metrics(p.y, p[m], train_mean, peak, naive_mae,
                                     cfg["metrics"]["mape_min_fraction_of_train_mean"]) for m in base}
        abl = [m for m in models if m.endswith(ABLATION_SUFFIX)]
        if abl:
            out.setdefault("ablation_no_weather", {})[split] = {
                m.removesuffix(ABLATION_SUFFIX): all_metrics(p.y, p[m], train_mean, peak, naive_mae) for m in abl}
        per_origin[split] = p.assign(**{m: (p[m] - p.y).abs() for m in models}).groupby(level="origin")[models].mean()
    sel = min((m for m in base if m != NAIVE), key=lambda m: out["val"][m]["mae"])
    out["selected"] = {"model": sel, "reason": "lowest validation MAE",
                       "val_mae": out["val"][sel]["mae"]}
    alt = min((m for m in base if m not in (sel, NAIVE)), key=lambda m: out["test"][m]["mae"])
    t = per_origin["test"]
    out["significance"] = {"vs": alt, "method": "diebold_mariano", "loss": "per-origin MAE on test",
                           **diebold_mariano(t[sel], t[alt], 1 if horizon == "d1" else 7)}
    out["significance_vs_naive"] = {"vs": NAIVE, "method": "diebold_mariano",
                                    **diebold_mariano(t[sel], t[NAIVE], 1 if horizon == "d1" else 7)}
    p = preds[(preds.split == "test") & preds.eval_ok]
    step_err = p.assign(err_sel=(p[sel] - p.y).abs(), err_naive=(p[NAIVE] - p.y).abs()).groupby(level="step")
    key = "error_by_hour" if horizon == "d1" else "error_by_step"
    out[key] = {"selected": step_err["err_sel"].mean().round(5).tolist(),
                "seasonal_naive": step_err["err_naive"].mean().round(5).tolist()}
    return out


def run(cfg) -> list:
    res = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "git_commit": _git_commit()}
    old = read_json(METRICS, default={})
    for resource in ("electricity", "water"):
        res[resource] = {h: score(resource, h, cfg) for h in ("d1", "w1")}
        if resource in old and "robustness" in old[resource]:
            res[resource]["robustness"] = old[resource]["robustness"]
    res["units"] = {"electricity": "kW (hourly mean) for D1; kWh per day for W1",
                    "water": "L/s (hourly mean inflow, DMA 3) for D1; m3 per day for W1",
                    "detail": UNITS}
    write_json(METRICS, res)
    return sorted(PRED_DIR.glob("*.parquet"))
