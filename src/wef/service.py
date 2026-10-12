"""Shared service layer for the Flask API and the Streamlit dashboard (the dashboard calls these functions directly
when the API is unreachable). Everything reads saved results and models; nothing here trains or downloads.
Invalid input raises BadRequest (HTTP 400), missing artefacts raise NotFound (HTTP 404).
"""
from functools import lru_cache

import numpy as np
import pandas as pd

from wef.data import clean
from wef.data.clean import PROCESSED
from wef.features import build
from wef.models.registry import MODEL_DIR, PRED_DIR, Data
from wef.utils.io import load_config, read_json
from wef.utils.paths import RESULTS

RESOURCES, HORIZONS = ("electricity", "water"), ("d1", "w1")
UNITS = {("electricity", "d1"): "kW", ("electricity", "w1"): "kWh/day", ("water", "d1"): "L/s", ("water", "w1"): "m3/day"}
MIN_HISTORY = {"d1": 336, "w1": 56}  # steps: longest lag (336 h) / longest deep-model window (56 days)
WEATHER_COLS = {"d1": ["temperature_c", "humidity_pct", "rain_mm"],
                "w1": ["temperature_mean", "temperature_max", "temperature_min", "humidity_mean", "rain_sum"]}


class BadRequest(ValueError):
    pass


class NotFound(LookupError):
    pass


def _check(resource, horizon=None):
    if resource not in RESOURCES:
        raise BadRequest(f"resource must be one of {list(RESOURCES)}")
    if horizon is not None and horizon not in HORIZONS:
        raise BadRequest(f"horizon must be one of {list(HORIZONS)}")


def _json(path):
    if not path.exists():
        raise NotFound(f"{path.name} not found - run the pipeline (python -m wef.cli all)")
    return read_json(path)


@lru_cache(maxsize=1)
def _cfg():
    return load_config()


@lru_cache(maxsize=1)
def _classes():
    from wef.models.registry import _deep_specs, specs
    return {cls.name: cls for cls, _ in specs(_cfg(), "d1") + _deep_specs(_cfg(), "d1")}


def models_available(resource, horizon) -> list[str]:
    return sorted(p.stem.removeprefix(f"{resource}_{horizon}_") for p in MODEL_DIR.glob(f"{resource}_{horizon}_*")
                  if p.suffix in (".joblib", ".keras"))


@lru_cache(maxsize=32)
def _model(resource, horizon, name):
    base = name.removesuffix("_no_weather")
    cls = _classes().get(base)
    if cls is None or name not in models_available(resource, horizon):
        raise BadRequest(f"model '{name}' not available; choose from {models_available(resource, horizon)}")
    return cls.load(MODEL_DIR / f"{resource}_{horizon}_{name}{cls.ext}")


@lru_cache(maxsize=4)
def _data(resource, horizon):
    return Data.load(resource, horizon, _cfg())


def selected(resource, horizon) -> str:
    return _json(RESULTS / "metrics.json")[resource][horizon]["selected"]["model"]


# ----------------------------------------------------------------------------------------------- read-only views
def health() -> dict:
    m = read_json(RESULTS / "metrics.json", default=None)
    out = {"status": "ok" if m else "degraded", "results_generated_at": m and m["generated_at"],
           "git_commit": m and m["git_commit"], "models": {}}
    for r in RESOURCES:
        for h in HORIZONS:
            out["models"][f"{r}.{h}"] = {"selected": m and m[r][h]["selected"]["model"],
                                         "available": models_available(r, h)}
    return out


def metrics(resource, horizon) -> dict:
    _check(resource, horizon)
    d = _json(RESULTS / "metrics.json")[resource][horizon]
    keep = ("split_dates", "n_test_origins", "n_val_origins", "test", "val", "selected", "significance",
            "significance_vs_naive", "ablation_no_weather")
    return {"resource": resource, "horizon": horizon, "unit": UNITS[(resource, horizon)], **{k: d[k] for k in keep if k in d}}


def optimisation() -> dict:
    return _json(RESULTS / "optimisation.json")


def backtest(resource, horizon, start=None, end=None, models=None) -> dict:
    """Stored rolling-origin forecasts (validation and test) for origins in [start, end]."""
    _check(resource, horizon)
    path = PRED_DIR / f"{resource}_{horizon}.parquet"
    if not path.exists():
        raise NotFound("no backtest predictions - run python -m wef.cli train")
    p = pd.read_parquet(path).reset_index()
    cols = [c for c in p.columns if c not in ("origin", "step", "target_time", "split", "y", "eval_ok")]
    models = models or cols
    bad = [m for m in models if m not in cols]
    if bad:
        raise BadRequest(f"unknown model(s) {bad}; choose from {cols}")
    try:
        if start:
            p = p[p.origin >= pd.Timestamp(start)]
        if end:
            p = p[p.origin <= pd.Timestamp(end)]
    except ValueError as e:
        raise BadRequest(f"bad date: {e}")
    p = p.sort_values(["origin", "step"])
    return {"resource": resource, "horizon": horizon, "unit": UNITS[(resource, horizon)],
            "rows": [{"origin": str(r.origin), "timestamp": str(r.target_time), "split": r.split,
                      "actual": None if pd.isna(r.y) else float(r.y),
                      **{m: None if pd.isna(getattr(r, m)) else float(getattr(r, m)) for m in models}}
                     for r in p.itertuples()]}


def anomalies(resource, start=None, end=None, include_series=False) -> dict:
    _check(resource)
    ev = pd.read_csv(RESULTS / "anomaly_events.csv", parse_dates=["alarm", "start", "end"]) if (RESULTS / "anomaly_events.csv").exists() else None
    if ev is None:
        raise NotFound("no anomaly results - run python -m wef.cli anomaly")
    lab = pd.read_csv(PROCESSED / f"anomaly_{resource}_labels.csv", parse_dates=["start", "end", "window_end"])
    try:
        lo = pd.Timestamp(start) if start else pd.Timestamp.min
        hi = pd.Timestamp(end) + pd.Timedelta(hours=23) if end else pd.Timestamp.max
    except ValueError as e:
        raise BadRequest(f"bad date: {e}")
    if lo > hi:
        raise BadRequest("start must not be after end")
    ev = ev[(ev.resource == resource) & (ev.alarm >= lo) & (ev.alarm <= hi)]
    lab = lab[(lab.end >= lo) & (lab.start <= hi)]
    a = _json(RESULTS / "anomaly.json")[resource]
    out = {"resource": resource, "label_source": a["label_source"], "test_period": a["splits"]["test"],
           "events": [{"event_id": r.event_id, "method": r.method, "alarm": str(r.alarm), "start": str(r.start),
                       "end": str(r.end), "score": None if pd.isna(r.score) else float(r.score)} for r in ev.itertuples()],
           "labels": [{"event_id": r.event_id, "type": r.type, "start": str(r.start), "end": str(r.end)} for r in lab.itertuples()],
           "scores": {m: {k: a[m]["test"][k] for k in ("recall", "precision", "false_alarms_per_week", "median_delay_hours", "chance_precision")}
                      for m in ("residual_zscore", "isolation_forest")}}
    if include_series:
        s = pd.read_parquet(PROCESSED / f"anomaly_{resource}_test_series.parquet").loc[lo:hi]
        out["series"] = [{"timestamp": str(t), "actual": None if pd.isna(r.actual) else float(r.actual),
                          "forecast": float(r.forecast)} for t, r in s.iterrows()]
    return out


# ----------------------------------------------------------------------------------------------- forecasting
def latest(resource, horizon, model=None, origin=None) -> dict:
    """Forecast from a stored origin (default: the last origin in the processed data) with dataset weather."""
    _check(resource, horizon)
    data = _data(resource, horizon)
    origins = pd.DatetimeIndex(data.table["origin"].unique())
    o = origins[-1] if origin is None else pd.Timestamp(origin)
    if o not in origins:
        raise BadRequest(f"origin must be a date between {origins[0].date()} and {origins[-1].date()}")
    name = model or selected(resource, horizon)
    f = _model(resource, horizon, name).predict_one(
        Data(resource, horizon, data.table, data.series, data.cfg, weather=not name.endswith("_no_weather")), o)
    t = pd.date_range(o, periods=data.steps, freq=data.unit)
    y = data.matrix([o], "y")[0]
    return {"resource": resource, "horizon": horizon, "model": name, "origin": str(o), "unit": UNITS[(resource, horizon)],
            "forecast": [{"timestamp": str(ts), "value": float(v), "actual": None if np.isnan(a) else float(a)}
                         for ts, v, a in zip(t, f, y)]}


def _parse_history(history, horizon) -> pd.Series:
    if not isinstance(history, list) or not history:
        raise BadRequest("history must be a non-empty list of {timestamp, value}")
    try:
        s = pd.Series({pd.Timestamp(h["timestamp"]): float(h["value"]) for h in history}).sort_index()
    except (KeyError, TypeError, ValueError):
        raise BadRequest("every history item needs a parseable 'timestamp' and a numeric 'value'")
    if s.index.tz is not None:
        s.index = s.index.tz_localize(None)
    if (s < 0).any() or not np.isfinite(s).all():
        raise BadRequest("values must be finite and non-negative")
    freq = "h" if horizon == "d1" else "D"
    full = pd.date_range(s.index[0], s.index[-1], freq=freq)
    if len(full) != len(s):
        raise BadRequest(f"history must be regular {'hourly' if horizon == 'd1' else 'daily'} data without duplicates "
                         f"(expected {len(full)} points between first and last timestamp, got {len(s)})")
    if len(s) < MIN_HISTORY[horizon]:
        raise BadRequest(f"history needs at least {MIN_HISTORY[horizon]} {'hours' if horizon == 'd1' else 'days'}")
    if horizon == "d1" and s.index[-1].hour != 23:
        raise BadRequest("D1 history must end at 23:00 (the forecast origin is the next 00:00)")
    if horizon == "w1" and (s.index != s.index.normalize()).any():
        raise BadRequest("W1 history must be daily values stamped at 00:00")
    return s.asfreq(freq)


def forecast(resource, horizon, history, model=None, weather=None) -> dict:
    """Forecast the next day (24 hourly values) or week (7 daily totals) after the end of `history`.
    Weather for the target period comes from `weather` (list of {timestamp, <weather columns>}), else from the
    processed dataset if it covers the dates, else a no-weather model is used."""
    _check(resource, horizon)
    s = _parse_history(history, horizon)
    unit = pd.Timedelta(hours=1) if horizon == "d1" else pd.Timedelta(days=1)
    steps = build.STEPS[horizon]
    origin = s.index[-1] + unit
    targets = pd.date_range(origin, periods=steps, freq=unit)
    idx = s.index.append(targets)
    cols = WEATHER_COLS[horizon]
    w = pd.DataFrame(np.nan, index=idx, columns=cols)
    source = "none"
    if weather:
        try:
            wr = pd.DataFrame(weather)
            ts = pd.DatetimeIndex(pd.to_datetime(wr.pop("timestamp")))
            wr.index = ts.tz_localize(None) if ts.tz is not None else ts
            w.update(wr[cols].astype(float))
        except (KeyError, TypeError, ValueError) as e:
            raise BadRequest(f"weather must be a list of objects with 'timestamp' and {cols} ({e})")
        source = "request"
    else:
        ds = pd.read_parquet(PROCESSED / f"{resource}_{'hourly' if horizon == 'd1' else 'daily'}.parquet")
        if targets.isin(ds.index).all():
            w.update(ds.loc[ds.index.isin(idx), cols])
            source = "dataset"
    use_weather = source != "none" and not w.loc[targets].isna().any().any()
    name = model or selected(resource, horizon)
    if not use_weather and not name.endswith("_no_weather"):
        options = [m for m in models_available(resource, horizon) if m.endswith("_no_weather")]
        if model:
            raise BadRequest(f"no weather for the target period; model '{model}' needs it - use one of {options} or send 'weather'")
        abl = _json(RESULTS / "metrics.json")[resource][horizon]["ablation_no_weather"]["val"]
        name = min(options, key=lambda m: abl[m.removesuffix("_no_weather")]["mae"])
    if horizon == "d1":
        hourly = w.assign(value=s.reindex(idx), long_gap=False)
        table = build.tabular(resource, horizon, _cfg(), hourly, clean.daily(hourly, 1.0), inference=True)
        series = hourly["value"]
    else:
        daily = w.assign(value=s.reindex(idx))
        table = build.tabular(resource, horizon, _cfg(), pd.DataFrame(), daily, inference=True)
        series = daily["value"]
    data = Data(resource, horizon, table, series, _cfg(), weather=not name.endswith("_no_weather"))
    f = _model(resource, horizon, name).predict_one(data, origin)
    return {"resource": resource, "horizon": horizon, "model": name, "origin": str(origin), "weather_source": source,
            "unit": UNITS[(resource, horizon)], "forecast": [{"timestamp": str(t), "value": float(v)} for t, v in zip(targets, f)]}


# ----------------------------------------------------------------------------------------------- optimisation
OVERRIDES = {"capacity_m3": ("tank", "capacity_m3"), "max_m3_per_h": ("pump", "max_m3_per_h"),
             "kwh_per_m3": ("pump", "kwh_per_m3"), "start_fraction": ("tank", "start_fraction")}


def schedule(demand, overrides=None) -> dict:
    """Optimal pumping plan for a 24-hour demand forecast (m3/h); optional parameter overrides."""
    import copy

    import yaml

    from wef.optimise import pump_schedule as ps
    if not isinstance(demand, list) or len(demand) != 24:
        raise BadRequest("demand must be a list of 24 hourly values in m3/h")
    try:
        d = np.array(demand, dtype=float)
    except (TypeError, ValueError):
        raise BadRequest("demand values must be numbers")
    if (d < 0).any() or not np.isfinite(d).all():
        raise BadRequest("demand values must be finite and non-negative")
    raw = yaml.safe_load(open(ps.OPT_CFG, encoding="utf-8"))
    cfg = copy.deepcopy(raw)
    for k, v in (overrides or {}).items():
        if k not in OVERRIDES:
            raise BadRequest(f"unknown override '{k}'; allowed: {list(OVERRIDES)}")
        if not isinstance(v, (int, float)) or v <= 0 or (k == "start_fraction" and not 0 < v < 1):
            raise BadRequest(f"override '{k}' must be a positive number" + (" below 1" if k == "start_fraction" else ""))
        sec, key = OVERRIDES[k]
        cfg[sec][key] = float(v)
    P = ps.params_from(cfg)
    r = ps.plan(d, P)
    if not r["feasible"]:
        raise BadRequest(f"infeasible with these parameters: {r['message']}")
    follow = float(P["price"] @ (d * P["kwh_per_m3"]))
    return {"label": P["label"], "unit": {"volume": "m3", "flow": "m3/h", "cost": "cost units"},
            "hours": list(range(24)), "pumping_m3h": r["pumping"].round(3).tolist(), "level_m3": r["level"].round(3).tolist(),
            "tariff_multiplier": (P["price"] / raw["tariff"]["base_rate"]).tolist(), "band": P["band"].tolist(),
            "limits": {"min_m3": P["L_min"], "max_m3": P["L_max"], "start_m3": P["L0"], "pump_max_m3h": P["P_max"]},
            "cost": r["cost"], "demand_following_cost": follow, "saving_pct": 100 * (1 - r["cost"] / follow) if follow else 0.0}
