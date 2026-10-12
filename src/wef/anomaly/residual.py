"""Method A: residual-based detection.

residual = actual - forecast of the selected D1 model; robust z = (residual - trailing median) / (1.4826 x trailing
MAD) over the previous `window` hours (causal); an alarm is raised when |z| > k for m consecutive hours; alarms
closer than `merge_gap` hours form one event.
"""
import numpy as np
import pandas as pd


def robust_z(residual: pd.Series, window: int) -> pd.Series:
    past = residual.shift(1)  # strictly earlier hours
    med = past.rolling(window, min_periods=window // 4).median()
    mad = (past - med).abs().rolling(window, min_periods=window // 4).median()
    return (residual - med) / (1.4826 * mad.replace(0, np.nan))


def events_from_flags(flags: pd.Series, m: int, merge_gap: int, score: pd.Series = None) -> pd.DataFrame:
    """Runs of >= m consecutive flagged hours; alarm time = the m-th hour of the run (when it can be raised).
    Alarms within merge_gap hours of the previous event's end extend it."""
    f = flags.fillna(False).astype(bool)
    run_id = (f != f.shift()).cumsum()
    rows = []
    for _, g in f[f].groupby(run_id[f]):
        if len(g) >= m:
            rows.append([g.index[m - 1], g.index[0], g.index[-1]])
    events = []
    for alarm, start, end in rows:
        if events and (start - events[-1]["end"]) <= pd.Timedelta(hours=merge_gap):
            events[-1]["end"] = end
        else:
            events.append({"alarm": alarm, "start": start, "end": end})
    ev = pd.DataFrame(events, columns=["alarm", "start", "end"])
    if score is not None and len(ev):
        ev["score"] = [float(score.loc[r.start:r.end].abs().max()) for r in ev.itertuples()]
    return ev


def detect(residual: pd.Series, k: float, m: int, window: int, merge_gap: int):
    z = robust_z(residual, window)
    return events_from_flags(z.abs() > k, m, merge_gap, z), z
