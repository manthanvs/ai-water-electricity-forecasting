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
from wef.utils.io import read_json, write_json  # noqa: F401
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


MODELS = ["seasonal_naive", "sarima", "ridge", "random_forest", "xgboost", "lstm", "gru", "cnn_lstm"]
METRIC_KEYS = ["mae", "rmse", "mape", "smape", "r2", "peak_mae", "skill", "mape_excluded_points"]


def check_schema(m: dict) -> None:
    """Raise AssertionError if metrics.json does not follow section D of 01_PROJECT_BUILD.md."""
    for key in ("generated_at", "git_commit", "electricity", "water", "units"):
        assert key in m, key
    for r in ("electricity", "water"):
        for h in ("d1", "w1"):
            d = m[r][h]
            for key in ("split_dates", "n_test_origins", "test", "val", "ablation_no_weather", "selected", "significance"):
                assert key in d, f"{r}.{h}.{key}"
            assert set(d["split_dates"]) == {"train", "val", "test"}
            for split in ("test", "val"):
                for model in MODELS:
                    assert all(k in d[split][model] for k in METRIC_KEYS), f"{r}.{h}.{split}.{model}"
            assert len(d["ablation_no_weather"]["test"]) == 2
            assert d["selected"]["model"] in MODELS and "reason" in d["selected"]
            assert {"vs", "method", "p_value"} <= set(d["significance"])


def robustness(cfg) -> dict:
    """Water D1 on every DMA: XGBoost with the hyper-parameters selected on DMA 3, against seasonal naive."""
    from wef.data.clean import PROCESSED as P, daily
    from wef.models.ml import XGBoostModel
    from wef.models.registry import TUNING, Data
    params = read_json(TUNING)["water.d1"]["xgboost"]["selected_params"]
    dmas = pd.read_parquet(P / "water_all_dmas_hourly.parquet")
    weather = pd.read_parquet(P / "water_hourly.parquet")[["temperature_c", "humidity_pct", "rain_mm"]]
    out = {}
    for c in dmas.columns:
        hourly = weather.assign(value=dmas[c].reindex(weather.index))
        table = build.tabular("water", "d1", cfg, hourly, daily(hourly, 3.6))
        data = Data("water", "d1", table, hourly["value"], cfg)
        sel = XGBoostModel(**params).fit(data, ("train",))
        final = XGBoostModel(**params, **sel.refit_params()).fit(data, ("train", "val"))
        o = data.origins("test", eval_only=True)
        y, f, nv = data.matrix(o, "y").ravel(), final.predict(data, o).ravel(), data.matrix(o, "lag_168").ravel()
        out[c] = {"n_test_origins": len(o), "mae": mae(y, f), "naive_mae": mae(y, nv), "skill": 1 - mae(y, f) / mae(y, nv),
                  "mean_flow": float(np.nanmean(y)), "missing_share": float(dmas[c].isna().mean())}
        print(f"  robustness {c}: skill {out[c]['skill']:.3f} on {len(o)} origins")
    sk = [v["skill"] for v in out.values()]
    return {"model": "xgboost", "horizon": "d1", "params_from": "DMA 3 selection", "dmas": out,
            "n_dmas_beating_naive": int(sum(v > 0 for v in sk)), "median_skill": float(np.median(sk))}


NICE = {"seasonal_naive": "seasonal naive", "sarima": "SARIMA", "ridge": "Ridge regression", "random_forest": "Random Forest",
        "xgboost": "XGBoost", "lstm": "LSTM", "gru": "GRU", "cnn_lstm": "CNN-LSTM"}
TABULAR, DEEP = ("ridge", "random_forest", "xgboost"), ("lstm", "gru", "cnn_lstm")


def summary(m: dict) -> str:
    """Plain-language findings generated from metrics.json (the report paraphrases this file)."""
    unit = {("electricity", "d1"): "kW", ("electricity", "w1"): "kWh/day", ("water", "d1"): "L/s", ("water", "w1"): "m3/day"}
    hname = {"d1": "next-day hourly (D1)", "w1": "next-week daily (W1)"}
    out = ["# Summary of findings", "", f"Generated from results/metrics.json ({m['generated_at']}). Test-period numbers; "
           "every model is scored on the same forecast origins.", ""]
    for r in ("electricity", "water"):
        for h in ("d1", "w1"):
            d, u = m[r][h], unit[(r, h)]
            t, sel = d["test"], d["selected"]["model"]
            ranked = sorted(t, key=lambda k: t[k]["mae"])
            bt = min(TABULAR, key=lambda k: t[k]["mae"]); bd = min(DEEP, key=lambda k: t[k]["mae"])
            sig = d["significance"]
            beat = [k for k in t if k != "seasonal_naive" and t[k]["mae"] < t["seasonal_naive"]["mae"]]
            out += [f"## {r.capitalize()}, {hname[h]}", "",
                    f"- Selected model (lowest validation MAE): {NICE[sel]}. Test MAE {t[sel]['mae']:.3f} {u}, "
                    f"RMSE {t[sel]['rmse']:.3f} {u}, MAPE {t[sel]['mape']:.1f} percent, sMAPE {t[sel]['smape']:.1f} percent, "
                    f"R2 {t[sel]['r2']:.3f}, skill versus seasonal naive {t[sel]['skill']:.3f}.",
                    f"- Seasonal naive: test MAE {t['seasonal_naive']['mae']:.3f} {u}. {len(beat)} of {len(t) - 1} models beat it on test"
                    + ("" if len(beat) == len(t) - 1 else f"; not beating it: {', '.join(NICE[k] for k in t if k != 'seasonal_naive' and k not in beat)}") + ".",
                    f"- Lowest test MAE overall: {NICE[ranked[0]]} ({t[ranked[0]]['mae']:.3f} {u}); "
                    f"{'the selected model' if ranked[0] == sel else 'the selected model ranks ' + str(ranked.index(sel) + 1) + ' of ' + str(len(ranked)) + ' on test'}.",
                    f"- Best tabular model {NICE[bt]} ({t[bt]['mae']:.3f}) versus best deep model {NICE[bd]} ({t[bd]['mae']:.3f}): "
                    + ("the deep model is better." if t[bd]["mae"] < t[bt]["mae"] else "the deep model does not beat the tabular model."),
                    f"- Diebold-Mariano test, {NICE[sel]} versus {NICE[sig['vs']]} (per-origin MAE): p = {sig['p_value']:.3f}"
                    + (" - the difference is statistically significant at the 5 percent level." if sig["p_value"] < 0.05 else " - the difference is not statistically significant at the 5 percent level."),
                    ]
            ab = d["ablation_no_weather"]["test"]
            for k, v in ab.items():
                full = t[k]["mae"]
                out.append(f"- Without weather inputs, {NICE[k]} test MAE is {v['mae']:.3f} {u} (with weather {full:.3f}; change {100 * (v['mae'] - full) / full:+.1f} percent).")
            out.append("")
    rb = m["water"].get("robustness")
    if rb:
        out += ["## Robustness across water areas", "",
                f"- XGBoost with the DMA 3 hyper-parameters beats seasonal naive on {rb['n_dmas_beating_naive']} of {len(rb['dmas'])} DMAs "
                f"(D1, test period); median skill {rb['median_skill']:.3f}.", ""]
    return "\n".join(out)


def run(cfg) -> list:
    res = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "git_commit": _git_commit()}
    for resource in ("electricity", "water"):
        res[resource] = {h: score(resource, h, cfg) for h in ("d1", "w1")}
    res["water"]["robustness"] = robustness(cfg)
    res["units"] = {"electricity": "kW (hourly mean) for D1; kWh per day for W1",
                    "water": "L/s (hourly mean inflow, DMA 3) for D1; m3 per day for W1",
                    "detail": UNITS}
    check_schema(res)
    write_json(METRICS, res)
    (RESULTS / "summary.md").write_text(summary(res), encoding="utf-8")
    return sorted(PRED_DIR.glob("*.parquet"))
