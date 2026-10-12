"""`anomaly` stage: both methods on both resources, scored against labelled events -> results/anomaly.json.

Water, real labels: BattLeDIM 2018 network inflow (hourly). The forecaster is the model type and hyper-parameters
selected for water D1, trained on BattLeDIM January-March (no weather inputs); detection thresholds are tuned on
April-June and tested on July-December. A detection is correct if its alarm falls between a leak's start and
7 days after the leak's peak time (abrupt leaks peak at their start).
Electricity, INJECTED labels: anomalies are injected into copies of the validation and test periods (different
seeds); the selected D1 model forecasts the injected series; thresholds tuned on validation.
Both: Method A tuned over (k, m) and Method B over (contamination, minimum run) by event F1 on validation; the
Isolation Forest is fitted on validation-period features (out-of-sample residuals).
"""
import itertools

import numpy as np
import pandas as pd

from wef.anomaly import iforest, inject, residual
from wef.data import clean
from wef.data.clean import PROCESSED
from wef.features import build
from wef.models.registry import MODEL_DIR, TUNING, Data, _deep_specs, specs
from wef.utils.io import read_json, write_json
from wef.utils.paths import RESULTS

ANOMALY = RESULTS / "anomaly.json"
EVENTS = RESULTS / "anomaly_events.csv"


def _classes(cfg):
    return {cls.name: cls for cls, _ in specs(cfg, "d1") + _deep_specs(cfg, "d1")}


# ----------------------------------------------------------------------------------------------- scoring
def score(events: pd.DataFrame, labels: pd.DataFrame, start, end) -> dict:
    """Event-level recall, precision, false alarms per week and detection delay.
    labels: start, window_end; counted when the label starts inside [start, end]."""
    start, end = pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(hours=23)
    ev = events[(events.alarm >= start) & (events.alarm <= end)]
    lab = labels[(labels.window_end >= start) & (labels.start <= end)]
    hit = np.zeros(len(ev), bool)
    per_label = []
    for r in lab.itertuples():
        m = ((ev.alarm >= r.start) & (ev.alarm <= r.window_end)).to_numpy()
        hit |= m
        if start <= r.start <= end:
            first = ev.alarm[m].min() if m.any() else None
            per_label.append({"event_id": r.event_id, "type": r.type, "start": str(r.start), "detected": bool(m.any()),
                              "delay_hours": float((first - r.start) / pd.Timedelta(hours=1)) if m.any() else None})
    weeks = (end - start) / pd.Timedelta(days=7)
    hours = pd.date_range(start, end, freq="h")
    covered = np.zeros(len(hours), bool)
    for r in lab.itertuples():
        covered |= (hours >= r.start) & (hours <= r.window_end)
    n_det = sum(p["detected"] for p in per_label)
    recall = n_det / len(per_label) if per_label else float("nan")
    precision = hit.mean() if len(ev) else 0.0
    delays = [p["delay_hours"] for p in per_label if p["detected"]]
    return {"n_labels": len(per_label), "n_detected": int(n_det), "recall": recall, "n_events": int(len(ev)),
            "n_true_events": int(hit.sum()), "precision": float(precision),
            "false_alarms": int((~hit).sum()), "false_alarms_per_week": float((~hit).sum() / weeks),
            "median_delay_hours": float(np.median(delays)) if delays else None,
            "f1": float(2 * precision * recall / (precision + recall)) if precision + recall > 0 else 0.0,
            "chance_precision": float(covered.mean()),  # share of hours inside a label window = precision of random alarms
            "per_label": per_label}


# ----------------------------------------------------------------------------------------------- residuals
def residuals(model, data: Data, first_origin, last_origin) -> pd.DataFrame:
    origins = pd.date_range(first_origin, last_origin, freq="D")
    origins = origins[origins.isin(data.table["origin"])]
    f = model.predict(data, origins).ravel()
    t = (np.repeat(origins.to_numpy(), 24) + np.tile(np.arange(24), len(origins)) * np.timedelta64(1, "h"))
    out = pd.DataFrame({"forecast": f}, index=pd.DatetimeIndex(t, name="timestamp"))
    out["actual"] = data.series.reindex(out.index)
    out["residual"] = out["actual"] - out["forecast"]
    return out


def _tune_and_test(res_val, res_test, lab, sp, ac, seed):
    """Tune both methods on validation, apply to test. Returns (results dict, test events DataFrame)."""
    w, gap = ac["rolling_window_hours"], ac["merge_gap_hours"]
    out, events = {}, []
    # Method A
    grid = []
    for k, m in itertools.product(ac["k"], ac["m"]):
        ev, _ = residual.detect(res_val["residual"], k, m, w, gap)
        s = score(ev, lab, *sp["val"])
        grid.append({"k": k, "m": m, "f1": s["f1"], "recall": s["recall"], "false_alarms_per_week": s["false_alarms_per_week"]})
    best = max(grid, key=lambda g: (g["f1"], -g["false_alarms_per_week"]))
    ev_val, _ = residual.detect(res_val["residual"], best["k"], best["m"], w, gap)
    ev_test, z = residual.detect(res_test["residual"], best["k"], best["m"], w, gap)
    out["residual_zscore"] = {"params": {"k": best["k"], "m": best["m"], "window_hours": w, "merge_gap_hours": gap},
                              "val": score(ev_val, lab, *sp["val"]), "test": score(ev_test, lab, *sp["test"]), "grid": grid}
    events.append(ev_test.assign(method="residual_zscore"))
    # Method B
    Xv = iforest.features(res_val["actual"], res_val["residual"]).loc[sp["val"][0]:sp["val"][1] + " 23:00"]
    Xt = iforest.features(res_test["actual"], res_test["residual"]).loc[sp["test"][0]:sp["test"][1] + " 23:00"]
    grid = []
    for c, m in itertools.product(ac["contamination"], ac["iforest_min_run"]):
        f, sc = iforest.flags(iforest.fit(Xv, c, seed), Xv)
        s = score(residual.events_from_flags(f, m, gap, sc), lab, *sp["val"])
        grid.append({"contamination": c, "min_run": m, "f1": s["f1"], "recall": s["recall"],
                     "false_alarms_per_week": s["false_alarms_per_week"]})
    best = max(grid, key=lambda g: (g["f1"], -g["false_alarms_per_week"]))
    forest = iforest.fit(Xv, best["contamination"], seed)
    fv, sv = iforest.flags(forest, Xv)
    ft, st = iforest.flags(forest, Xt)
    ev_test_b = residual.events_from_flags(ft, best["min_run"], gap, st)
    out["isolation_forest"] = {"params": {"contamination": best["contamination"], "min_run": best["min_run"],
                                          "fitted_on": "validation-period features"},
                               "val": score(residual.events_from_flags(fv, best["min_run"], gap, sv), lab, *sp["val"]),
                               "test": score(ev_test_b, lab, *sp["test"]), "grid": grid}
    events.append(ev_test_b.assign(method="isolation_forest"))
    series = res_test.assign(z=z, iforest_flag=ft.reindex(res_test.index, fill_value=False))
    ev = pd.concat(events, ignore_index=True)
    in_test = (ev.alarm >= sp["test"][0]) & (ev.alarm <= pd.Timestamp(sp["test"][1]) + pd.Timedelta(hours=23))
    return out, ev[in_test].reset_index(drop=True), series.loc[sp["test"][0]:]


# ----------------------------------------------------------------------------------------------- resources
def water(cfg, ac):
    sel = read_json(RESULTS / "metrics.json")["water"]["d1"]["selected"]["model"]
    cls = _classes(cfg)[sel]
    params = read_json(TUNING)["water.d1"][sel]["selected_params"]
    inflow = pd.read_parquet(PROCESSED / "battledim_inflow_hourly.parquet")["inflow_m3h"]
    hourly = pd.DataFrame({"value": inflow, "long_gap": False, "temperature_c": np.nan,
                           "humidity_pct": np.nan, "rain_mm": np.nan})
    table = build.tabular("battledim", "d1", cfg, hourly, clean.daily(hourly, 1.0))
    data = Data("battledim", "d1", table, hourly["value"], cfg, weather=False)
    model = cls(**params).fit(data, ("train",))  # trained on January-March only, used for both periods
    sp = cfg["splits"]["battledim"]
    leaks = pd.read_csv(PROCESSED / "battledim_leaks.csv", parse_dates=["start", "end", "peak"])
    cap = pd.Timedelta(days=ac["leak_window_after_peak_days"])
    lab = leaks.assign(event_id=leaks["link"], window_end=np.minimum(leaks["end"], leaks["peak"] + cap))
    lab = lab[lab.start.dt.year == 2018].reset_index(drop=True)
    warm = pd.Timedelta(days=14)
    res_val = residuals(model, data, pd.Timestamp(sp["val"][0]) - warm, sp["val"][1])
    res_test = residuals(model, data, pd.Timestamp(sp["test"][0]) - warm, sp["test"][1])
    out, events, series = _tune_and_test(res_val, res_test, lab, sp, ac, cfg["seed"])
    # Secondary, stricter rule: onset detection within 72 h of the leak start (chance precision is much lower)
    onset = lab.assign(window_end=lab["start"] + pd.Timedelta(hours=72))
    for meth in ("residual_zscore", "isolation_forest"):
        e = events[events.method == meth]
        out[meth]["test_onset_72h"] = score(e, onset, *sp["test"])
    out.update({"label_source": "BattLeDIM 2018 leak list (dataset_configuration.yaml)",
                "series": "L-Town network inflow p227 + p235, hourly mean, m3/h (simulated hydraulics)",
                "forecaster": {"model": sel, "params": params, "trained_on": sp["train"], "weather": False},
                "splits": sp, "match_rule": f"alarm between leak start and min(end, peak + {cap.days} days)",
                "leaks_by_period": {k: int(((lab.start >= v[0]) & (lab.start <= v[1] + " 23:59")).sum()) for k, v in sp.items()}})
    return out, events.assign(resource="water"), lab, series


def electricity(cfg, ac):
    m = read_json(RESULTS / "metrics.json")
    sel = m["electricity"]["d1"]["selected"]["model"]
    sp = m["electricity"]["d1"]["split_dates"]
    cls = _classes(cfg)[sel]
    params = read_json(TUNING)["electricity.d1"][sel]["selected_params"]
    hourly = pd.read_parquet(PROCESSED / "electricity_hourly.parquet")
    clean_data = Data.load("electricity", "d1", cfg)
    final = cls.load(MODEL_DIR / f"electricity_d1_{sel}{cls.ext}")
    val_model = cls(**params).fit(clean_data, ("train",)) if cls.refit else final
    ic = ac["inject"]
    labs, res = [], {}
    for split, seed, model in (("val", ic["seed_val"], val_model), ("test", ic["seed_test"], final)):
        inj, lab = inject.inject(hourly, sp[split][0], sp[split][1] + " 23:00", ic["n"], seed)
        lab["event_id"] = [f"{split}_{e}" for e in lab["event_id"]]
        lab.to_csv(PROCESSED / f"electricity_{split}_injected_labels.csv", index=False)
        labs.append(lab)
        data = Data("electricity", "d1", build.tabular("electricity", "d1", cfg, inj, clean.daily(inj, 1.0)),
                    inj["value"], cfg)
        res[split] = residuals(model, data, pd.Timestamp(sp[split][0]) - pd.Timedelta(days=14), sp[split][1])
        res[split]["injected"] = inj["injected"].reindex(res[split].index, fill_value=False)
    lab = pd.concat(labs, ignore_index=True).assign(window_end=lambda d: d["end"])
    out, events, series = _tune_and_test(res["val"], res["test"], lab, sp, ac, cfg["seed"])
    out.update({"label_source": "INJECTED (synthetic) anomalies on copies of the validation and test periods",
                "injection": {"types": ic["n"], "seed_val": ic["seed_val"], "seed_test": ic["seed_test"],
                              "test_labels_file": "data/processed/electricity_test_injected_labels.csv"},
                "forecaster": {"model": sel, "params": params}, "splits": {k: sp[k] for k in ("val", "test")},
                "match_rule": "alarm between injected anomaly start and end",
                "recall_by_type_test": {
                    meth: {t: float(np.mean([p["detected"] for p in out[meth]["test"]["per_label"] if p["type"] == t]))
                           for t in ic["n"]} for meth in ("residual_zscore", "isolation_forest")}})
    return out, events.assign(resource="electricity"), lab, series


def run(cfg) -> list:
    ac = cfg["anomaly"]
    res, all_events = {"units": {"electricity": "kW", "water": "m3/h"}}, []
    for name, fn in (("water", water), ("electricity", electricity)):
        out, events, lab, series = fn(cfg, ac)
        res[name] = out
        all_events.append(events)
        series.to_parquet(PROCESSED / f"anomaly_{name}_test_series.parquet")
        lab.to_csv(PROCESSED / f"anomaly_{name}_labels.csv", index=False)
        for meth in ("residual_zscore", "isolation_forest"):
            t = out[meth]["test"]
            print(f"  {name} {meth}: recall {t['recall']:.2f} ({t['n_detected']}/{t['n_labels']}), precision "
                  f"{t['precision']:.2f}, false alarms/week {t['false_alarms_per_week']:.2f}, median delay {t['median_delay_hours']} h")
    ev = pd.concat(all_events, ignore_index=True)
    ev.insert(0, "event_id", [f"{r}_{m}_{i:03d}" for i, (r, m) in enumerate(zip(ev.resource, ev.method))])
    ev.to_csv(EVENTS, index=False)
    write_json(ANOMALY, res)
    return [PROCESSED / "battledim_inflow_hourly.parquet", PROCESSED / "electricity_hourly.parquet"]
