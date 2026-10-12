"""Electricity peak-day alerts from the selected D1 forecast.

A test day gets an alert when its forecast daily peak (highest forecast hourly kW) exceeds the 90th percentile of
training-period daily peaks; it is a true peak day when its actual daily peak does. The energy that could be
moved out of peak-tariff hours is estimated from the household's own sub-meters for shiftable appliances
(laundry; electric water heater and air conditioner) - an upper bound that assumes all of it could be moved.
Tariff bands come from config/optimisation.yaml (ILLUSTRATIVE ASSUMPTIONS).
"""
import numpy as np
import pandas as pd

from wef.data import load
from wef.data.clean import PROCESSED
from wef.models.registry import PRED_DIR
from wef.utils.io import read_json
from wef.utils.paths import RESULTS


def _alerts(fc_peak, act_peak, alert_thr, peak_thr):
    alert, peak = fc_peak > alert_thr, act_peak > peak_thr
    hits = int((alert & peak).sum())
    return {"alert_threshold_kw": float(alert_thr), "peak_threshold_kw": float(peak_thr),
            "alert_days": int(alert.sum()), "actual_peak_days": int(peak.sum()), "hits": hits,
            "hit_rate": hits / int(peak.sum()) if peak.any() else None,
            "precision": hits / int(alert.sum()) if alert.any() else None,
            "false_alarms": int((alert & ~peak).sum()), "missed_peak_days": int((~alert & peak).sum())}


def run(cfg) -> dict:
    from wef.optimise.pump_schedule import load_params
    P = load_params()
    pa = P["raw"]["peak_alerts"]
    m = read_json(RESULTS / "metrics.json")["electricity"]["d1"]
    sel, sp = m["selected"]["model"], m["split_dates"]
    hourly = pd.read_parquet(PROCESSED / "electricity_hourly.parquet")["value"]
    train_peaks = hourly.loc[sp["train"][0]:sp["train"][1] + " 23:00"].resample("D").max().dropna()
    thr = float(train_peaks.quantile(pa["quantile"]))
    preds = pd.read_parquet(PRED_DIR / "electricity_d1.parquet").reset_index()
    out = {"selected_model": sel, "rule": f"forecast daily peak > {pa['quantile']:.0%} quantile of training daily peaks"}
    peaks = {s: preds[(preds.split == s) & preds.eval_ok].groupby("origin")[[sel, "y"]].max() for s in ("val", "test")}
    for split, pk in peaks.items():
        out[split] = _alerts(pk[sel], pk["y"], thr, thr)
    # Forecasts are smoother than actuals, so their daily peaks rarely reach the actual-peak threshold. Calibrated
    # variant: alert when the forecast peak exceeds the same quantile of the model's own validation forecast peaks.
    thr_cal = float(peaks["val"][sel].quantile(pa["quantile"]))
    out["test_calibrated"] = {**_alerts(peaks["test"][sel], peaks["test"]["y"], thr_cal, thr),
                              "note": "alert threshold = 90th percentile of validation forecast peaks (tuned on validation)"}
    fc = peaks["test"][sel]
    alert = fc > thr_cal
    # shiftable energy in peak-tariff hours on alert days (calibrated alerts), from the sub-meters (Wh per minute)
    minute = load.uci_minute()[pa["shiftable_submeters"]]
    sub_kwh = minute.sum(axis=1).resample("h").sum(min_count=1) / 1000
    peak_hours = [h for h in range(24) if P["band"][h] == "peak"]
    alert_days = fc.index[alert]
    in_peak = sub_kwh[sub_kwh.index.normalize().isin(alert_days) & sub_kwh.index.hour.isin(peak_hours)]
    all_peak = hourly[hourly.index.normalize().isin(alert_days) & hourly.index.hour.isin(peak_hours)]
    out["shiftable_energy"] = {"alert_days": int(len(alert_days)), "submeters": pa["shiftable_submeters"],
                               "shiftable_kwh_in_peak_hours": float(in_peak.sum()),
                               "total_kwh_in_peak_hours": float(all_peak.sum()),
                               "shiftable_share": float(in_peak.sum() / all_peak.sum()) if all_peak.sum() else None,
                               "cost_saving_if_moved_to_off_peak_units": float(in_peak.sum() * P["raw"]["tariff"]["base_rate"]
                                   * (P["raw"]["tariff"]["multipliers"]["peak"] - P["raw"]["tariff"]["multipliers"]["off_peak"])),
                               "note": "upper bound: assumes all sub-metered laundry, water-heater and air-conditioner energy in peak hours can move to off-peak"}
    t = out["test"]
    print(f"  peak alerts (test): {t['alert_days']} alerts, {t['hits']}/{t['actual_peak_days']} peak days hit; "
          f"calibrated: {out['test_calibrated']['alert_days']} alerts, {out['test_calibrated']['hits']} hits")
    return out
