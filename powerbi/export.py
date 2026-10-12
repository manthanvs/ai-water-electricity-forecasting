"""`export-powerbi` stage: a star schema of UTF-8 CSV files (ISO timestamps) in powerbi/exports/.

Facts: fact_consumption, fact_forecast, fact_anomaly, fact_metrics, fact_schedule.
Dimensions: dim_date (key: date), dim_resource (key: resource), dim_model (key: model).
Every fact carries `date` and `resource` (fact_schedule: water only); fact_forecast and fact_metrics carry `model`.
"""
import json

import pandas as pd

from wef.data.clean import PROCESSED
from wef.models.registry import PRED_DIR
from wef.utils.paths import RESULTS, ROOT

OUT = ROOT / "powerbi" / "exports"
FAMILY = {"seasonal_naive": "baseline", "sarima": "statistical", "ridge": "machine learning", "random_forest": "machine learning",
          "xgboost": "machine learning", "lstm": "deep learning", "gru": "deep learning", "cnn_lstm": "deep learning"}
DISPLAY = {"seasonal_naive": "Seasonal naive", "sarima": "SARIMA", "ridge": "Ridge", "random_forest": "Random Forest",
           "xgboost": "XGBoost", "lstm": "LSTM", "gru": "GRU", "cnn_lstm": "CNN-LSTM"}


def _iso(s):
    return pd.to_datetime(s).dt.strftime("%Y-%m-%dT%H:%M:%S")


def tables() -> dict:
    m = json.loads((RESULTS / "metrics.json").read_text())
    t = {}
    # consumption (hourly actuals of the cleaned series)
    rows = []
    for res in ("electricity", "water"):
        h = pd.read_parquet(PROCESSED / f"{res}_hourly.parquet")["value"].dropna()
        rows.append(pd.DataFrame({"timestamp": h.index, "resource": res, "actual": h.to_numpy(),
                                  "unit": "kW" if res == "electricity" else "L/s"}))
    c = pd.concat(rows, ignore_index=True)
    t["fact_consumption"] = c
    # forecasts (validation and test backtest, long format)
    rows = []
    for res in ("electricity", "water"):
        for hz in ("d1", "w1"):
            p = pd.read_parquet(PRED_DIR / f"{res}_{hz}.parquet").reset_index()
            models = [k for k in p.columns if k not in ("origin", "step", "target_time", "split", "y", "eval_ok")]
            long = p.melt(id_vars=["origin", "step", "target_time", "split", "y", "eval_ok"], value_vars=models,
                          var_name="model", value_name="forecast")
            rows.append(long.assign(resource=res, horizon=hz).rename(columns={"target_time": "timestamp", "y": "actual"}))
    f = pd.concat(rows, ignore_index=True)
    t["fact_forecast"] = f[["origin", "timestamp", "resource", "horizon", "model", "step", "split", "eval_ok", "actual", "forecast"]]
    # anomalies: detections and the labels they are scored against
    a = json.loads((RESULTS / "anomaly.json").read_text())
    ev = pd.read_csv(RESULTS / "anomaly_events.csv")
    ev = ev.assign(kind="detection", label_source=ev.resource.map({r: a[r]["label_source"] for r in ("electricity", "water")}),
                   type=None)
    labs = []
    for res in ("electricity", "water"):
        lab = pd.read_csv(PROCESSED / f"anomaly_{res}_labels.csv")
        labs.append(pd.DataFrame({"event_id": res + "_label_" + lab["event_id"].astype(str), "resource": res, "method": "label",
                                  "alarm": None, "start": lab["start"], "end": lab["end"], "score": None, "kind": "label",
                                  "label_source": a[res]["label_source"], "type": lab["type"]}))
    an = pd.concat([ev[["event_id", "resource", "method", "alarm", "start", "end", "score", "kind", "label_source", "type"]], *labs],
                   ignore_index=True)
    t["fact_anomaly"] = an
    # metrics (long)
    rows = []
    for res in ("electricity", "water"):
        for hz in ("d1", "w1"):
            d = m[res][hz]
            for split in ("val", "test"):
                for model, vals in d[split].items():
                    for k, v in vals.items():
                        rows.append({"resource": res, "horizon": hz, "split": split, "model": model, "metric": k,
                                     "value": v, "is_selected": model == d["selected"]["model"]})
    t["fact_metrics"] = pd.DataFrame(rows)
    # pump schedule: per test day and plan (ILLUSTRATIVE ASSUMPTIONS)
    s = pd.read_csv(RESULTS / "pump_schedule_days.csv")
    t["fact_schedule"] = s.assign(resource="water", note="ILLUSTRATIVE ASSUMPTIONS")
    # dimensions
    t["dim_resource"] = pd.DataFrame([
        {"resource": "electricity", "unit_hourly": "kW", "unit_daily": "kWh/day", "description": "One household, Sceaux (France), 2006-2010",
         "source": "UCI Machine Learning Repository, dataset 235 (CC BY 4.0)"},
        {"resource": "water", "unit_hourly": "L/s", "unit_daily": "m3/day", "description": "District metered area DMA 3, north-east Italy, 2021-2023",
         "source": "Battle of the Water Demand Forecasting, WDSA-CCWI 2024 (CC BY 4.0)"}])
    sel = {f"selected_{r}_{h}": m[r][h]["selected"]["model"] for r in ("electricity", "water") for h in ("d1", "w1")}
    models = sorted(set(f["model"]) | set(t["fact_metrics"]["model"]))
    t["dim_model"] = pd.DataFrame([{"model": k, "display_name": DISPLAY.get(k.removesuffix("_no_weather"), k) + (" (no weather)" if k.endswith("_no_weather") else ""),
                                    "family": FAMILY.get(k.removesuffix("_no_weather"), "other"), "uses_weather": not k.endswith("_no_weather") and k not in ("seasonal_naive", "sarima"),
                                    **{key: v == k for key, v in sel.items()}} for k in models])
    # date keys for every fact
    for name in ("fact_consumption", "fact_forecast"):
        t[name]["date"] = pd.to_datetime(t[name]["timestamp"]).dt.strftime("%Y-%m-%d")
    t["fact_anomaly"]["date"] = pd.to_datetime(t["fact_anomaly"]["start"]).dt.strftime("%Y-%m-%d")
    t["fact_schedule"]["date"] = pd.to_datetime(t["fact_schedule"]["date"]).dt.strftime("%Y-%m-%d")
    dates = pd.to_datetime(pd.concat([t[n]["date"] for n in ("fact_consumption", "fact_forecast", "fact_anomaly", "fact_schedule")]).unique())
    dd = pd.DataFrame({"date": pd.date_range(dates.min(), dates.max(), freq="D")})
    t["dim_date"] = dd.assign(year=dd.date.dt.year, month=dd.date.dt.month, month_name=dd.date.dt.strftime("%b"),
                              day=dd.date.dt.day, weekday=dd.date.dt.dayofweek + 1, weekday_name=dd.date.dt.strftime("%a"),
                              is_weekend=dd.date.dt.dayofweek >= 5, date=dd.date.dt.strftime("%Y-%m-%d"))
    for name, df in t.items():
        for col in ("timestamp", "origin", "alarm", "start", "end"):
            if col in df:
                df[col] = _iso(df[col]).where(df[col].notna(), None)
    return t


def run(cfg) -> list:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, df in tables().items():
        df.to_csv(OUT / f"{name}.csv", index=False, encoding="utf-8")
        print(f"  {name}.csv: {len(df):,} rows")
    return [RESULTS / "metrics.json", RESULTS / "anomaly.json", RESULTS / "anomaly_events.csv", RESULTS / "pump_schedule_days.csv"]
