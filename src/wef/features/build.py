"""Feature engineering in the "origin" formulation.

Origin = 00:00 of day D; everything stamped before it is known (hourly values are hour-beginning, so the last
known hour is D-1 23:00). One row per (origin, step):
  D1: step s = 0..23, target hour D + s h.   Lags t-24, t-48, t-168, t-336 (all >= 24 h old), same-hour mean of
      the last 7 days and the mean of day D-1.
  W1: step s = 0..6, target day D + s.        Lags d-7, d-14, d-21, d-28 (all >= 7 days old), mean of the last
      28 days (D-28..D-1).
Weather and calendar are taken at the target time; weather is observed weather standing in for a forecast
("perfect weather forecast" assumption). `level` (mean of the last 168 h for D1, last 28 days for W1, at the
origin) is not a feature; models may use it to work relative to the recent level. Missing lags and targets (long gaps) stay NaN: training skips rows
with a missing target, and `eval_ok` marks origins whose full target window and seasonal-naive inputs are present.
"""
import holidays
import numpy as np
import pandas as pd

from wef.data.clean import PROCESSED, split_dates

FEATURES = PROCESSED / "features"
STEPS = {"d1": 24, "w1": 7}
WEATHER = {"d1": ["temperature_c", "humidity_pct", "rain_mm", "cdh", "hdh"],
           "w1": ["temperature_mean", "temperature_max", "temperature_min", "humidity_mean", "rain_sum", "cdd", "hdd"]}
CALENDAR = {"d1": ["hour_sin", "hour_cos", "dow_sin", "dow_cos", "month_sin", "month_cos",
                   "weekend", "holiday", "day_before_holiday", "day_after_holiday"],
            "w1": ["dow_sin", "dow_cos", "month_sin", "month_cos",
                   "weekend", "holiday", "day_before_holiday", "day_after_holiday"]}
LAGS = {"d1": ["lag_24", "lag_48", "lag_168", "lag_336", "same_hour_mean_7d", "prev_day_mean"],
        "w1": ["lag_7", "lag_14", "lag_21", "lag_28", "mean_28d"]}
NAIVE = {"d1": "lag_168", "w1": "lag_7"}  # seasonal naive = same hour / same weekday one week earlier


def feature_cols(horizon: str, weather: bool = True) -> list:
    return ["step", *CALENDAR[horizon], *LAGS[horizon], *(WEATHER[horizon] if weather else [])]


def _holiday_set(resource: str, cfg, years) -> set:
    country = cfg["holidays"].get(resource)
    days = set(holidays.country_holidays(country, years=years)) if country else set()
    if resource == "water":  # BWDF city's patron saint (wf4bwdf calendar), 3 November
        days |= {pd.Timestamp(y, 11, 3).date() for y in years}
    return days


def _calendar(t: pd.DatetimeIndex, hol: set) -> pd.DataFrame:
    day = t.normalize()
    is_hol = lambda d: np.array([x.date() in hol for x in d])  # noqa: E731
    return pd.DataFrame({
        "hour_sin": np.sin(2 * np.pi * t.hour / 24), "hour_cos": np.cos(2 * np.pi * t.hour / 24),
        "dow_sin": np.sin(2 * np.pi * t.dayofweek / 7), "dow_cos": np.cos(2 * np.pi * t.dayofweek / 7),
        "month_sin": np.sin(2 * np.pi * (t.month - 1) / 12), "month_cos": np.cos(2 * np.pi * (t.month - 1) / 12),
        "weekend": (t.dayofweek >= 5).astype(int), "holiday": is_hol(day).astype(int),
        "day_before_holiday": is_hol(day + pd.Timedelta(days=1)).astype(int),
        "day_after_holiday": is_hol(day - pd.Timedelta(days=1)).astype(int),
    }, index=t)


def _split_of(dates: pd.Series, sp: dict) -> pd.Series:
    out = pd.Series(None, index=dates.index, dtype="object")
    for name, (a, b) in sp.items():
        out[(dates >= a) & (dates <= b)] = name
    return out


def tabular(resource: str, horizon: str, cfg, hourly: pd.DataFrame = None, daily: pd.DataFrame = None) -> pd.DataFrame:
    """Origin-formulated table: origin, step, target_time, y, split, eval_ok, features."""
    hourly = pd.read_parquet(PROCESSED / f"{resource}_hourly.parquet") if hourly is None else hourly
    daily = pd.read_parquet(PROCESSED / f"{resource}_daily.parquet") if daily is None else daily
    sp = split_dates(resource, daily.index, cfg)
    fc = cfg["features"]
    n = STEPS[horizon]
    if horizon == "d1":
        y, unit = hourly["value"], pd.Timedelta(hours=1)
        origins = pd.date_range(y.index[0].normalize() + pd.Timedelta(days=1), y.index[-1].normalize(), freq="D")
    else:
        y, unit = daily["value"], pd.Timedelta(days=1)
        origins = daily.index[1:]
    o = np.repeat(origins, n)
    step = np.tile(np.arange(n), len(origins))
    t = pd.DatetimeIndex(o) + step * unit
    df = pd.DataFrame({"origin": o, "step": step, "target_time": t, "y": y.reindex(t).to_numpy()})
    at = lambda times: y.reindex(times).to_numpy()  # noqa: E731
    if horizon == "d1":
        for k in (24, 48, 168, 336):
            df[f"lag_{k}"] = at(t - pd.Timedelta(hours=k))
        df["same_hour_mean_7d"] = np.nanmean(np.stack([at(t - pd.Timedelta(hours=24 * k)) for k in range(1, 8)]), 0)
        df["prev_day_mean"] = y.resample("D").mean().shift(1).reindex(pd.DatetimeIndex(o)).to_numpy()
        df["level"] = y.rolling(168, min_periods=24).mean().shift(1).reindex(pd.DatetimeIndex(o)).to_numpy()
        w = hourly.reindex(t)
        df["temperature_c"], df["humidity_pct"], df["rain_mm"] = (w[c].to_numpy() for c in ["temperature_c", "humidity_pct", "rain_mm"])
        df["cdh"] = np.maximum(0, df["temperature_c"] - fc["cooling_base_c"])
        df["hdh"] = np.maximum(0, fc["heating_base_c"] - df["temperature_c"])
    else:
        for k in (7, 14, 21, 28):
            df[f"lag_{k}"] = at(t - pd.Timedelta(days=k))
        df["mean_28d"] = y.rolling(28, min_periods=21).mean().shift(1).reindex(pd.DatetimeIndex(o)).to_numpy()
        df["level"] = y.rolling(28, min_periods=7).mean().shift(1).reindex(pd.DatetimeIndex(o)).to_numpy()
        w = daily.reindex(t)
        for c in ["temperature_mean", "temperature_max", "temperature_min"]:
            df[c] = w[c].to_numpy()
        df["humidity_mean"], df["rain_sum"] = w["humidity_mean"].to_numpy(), w["rain_sum"].to_numpy()
        df["cdd"] = np.maximum(0, df["temperature_mean"] - fc["cooling_base_c"])
        df["hdd"] = np.maximum(0, fc["heating_base_c"] - df["temperature_mean"])
    hol = _holiday_set(resource, cfg, range(t.year.min() - 1, t.year.max() + 2))
    cal = _calendar(t, hol)
    df[CALENDAR[horizon]] = cal[CALENDAR[horizon]].to_numpy()
    # split by origin; the whole target window must lie in the same split
    df["split"] = _split_of(df["origin"], sp)
    last_t = df.groupby("origin")["target_time"].transform("max").dt.normalize()
    df.loc[_split_of(last_t, sp) != df["split"], "split"] = None
    complete = df.groupby("origin")[["y", NAIVE[horizon]]].transform(lambda c: c.notna().all()).all(axis=1)
    df["eval_ok"] = complete
    return df[df["split"].notna()].reset_index(drop=True)


def windows(table: pd.DataFrame, series: pd.Series, horizon: str, window: int, weather: bool = True) -> dict:
    """Deep-model tensors for every origin in `table`:
    seq (n, window, 5): past values and their hour/day-of-week encodings, ending at origin - 1 step;
    fut (n, steps, k): calendar (+ weather) of the target steps; lags (n, steps, m): the lag-rule features of each
    target step (all known at the origin); y (n, steps), NaN where missing."""
    n = STEPS[horizon]
    t = table.sort_values(["origin", "step"])
    origins = pd.DatetimeIndex(t["origin"].unique())
    unit = pd.Timedelta(hours=1) if horizon == "d1" else pd.Timedelta(days=1)
    rel = np.arange(-window, 0)
    times = origins.to_numpy()[:, None] + rel[None, :] * unit.to_timedelta64()
    flat = pd.DatetimeIndex(times.ravel())
    vals = series.reindex(flat).to_numpy().reshape(len(origins), window)
    period = 24 if horizon == "d1" else 7
    pos = (flat.hour if horizon == "d1" else flat.dayofweek).to_numpy().reshape(len(origins), window)
    dow = flat.dayofweek.to_numpy().reshape(len(origins), window)
    seq = np.stack([vals, np.sin(2 * np.pi * pos / period), np.cos(2 * np.pi * pos / period),
                    np.sin(2 * np.pi * dow / 7), np.cos(2 * np.pi * dow / 7)], axis=-1)
    fut_cols = CALENDAR[horizon] + (WEATHER[horizon] if weather else [])
    fut = t[fut_cols].to_numpy(dtype="float64").reshape(len(origins), n, len(fut_cols))
    lags = t[LAGS[horizon]].to_numpy(dtype="float64").reshape(len(origins), n, len(LAGS[horizon]))
    return {"origins": origins, "seq": seq, "fut": fut, "lags": lags, "y": t["y"].to_numpy().reshape(len(origins), n),
            "split": t.groupby("origin")["split"].first().to_numpy(),
            "eval_ok": t.groupby("origin")["eval_ok"].first().to_numpy()}


def run(cfg) -> list:
    from wef.data import clean
    inputs = clean.run(cfg)
    FEATURES.mkdir(parents=True, exist_ok=True)
    for resource in ("electricity", "water"):
        for horizon in ("d1", "w1"):
            tab = tabular(resource, horizon, cfg)
            tab.to_parquet(FEATURES / f"{resource}_{horizon}.parquet")
            print(f"  {resource} {horizon}: {len(tab):,} rows, {tab['origin'].nunique()} origins, "
                  f"eval origins by split {tab[tab.eval_ok].groupby('split')['origin'].nunique().to_dict()}")
    return inputs
