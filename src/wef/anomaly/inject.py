"""INJECTED (synthetic) anomalies for electricity, on a copy of one period. Never applied to the real data files.

Types, each multiplying the real reading:
  spike        2 to 4 times the value for 1 to 3 hours
  level_shift  +30 to +60 percent for 1 to 3 days (an appliance left running)
  drift        linear ramp from 0 to +40 to +60 percent over 3 to 5 days (slow degradation), then back to normal
Events do not overlap, avoid long gaps, and leave a 2-day margin between them.
"""
import numpy as np
import pandas as pd


def inject(hourly: pd.DataFrame, start, end, n: dict, seed: int):
    """Return (copy of hourly with injected anomalies in [start, end], labels DataFrame)."""
    rng = np.random.default_rng(seed)
    out = hourly.copy()
    idx = out.loc[start:end].index
    busy = np.zeros(len(idx), bool) | out.loc[start:end, "long_gap"].to_numpy()
    labels = []
    for kind, count in n.items():
        for _ in range(count):
            for _attempt in range(500):
                if kind == "spike":
                    length, factor = int(rng.integers(1, 4)), float(rng.uniform(2, 4))
                elif kind == "level_shift":
                    length, factor = 24 * int(rng.integers(1, 4)), float(rng.uniform(0.3, 0.6))
                else:
                    length, factor = 24 * int(rng.integers(3, 6)), float(rng.uniform(0.4, 0.6))
                i = int(rng.integers(0, len(idx) - length))
                lo, hi = max(0, i - 48), min(len(idx), i + length + 48)
                if not busy[lo:hi].any():
                    break
            else:
                raise RuntimeError(f"no room to inject {kind}")
            busy[i:i + length] = True
            t = idx[i:i + length]
            ramp = np.linspace(1 / length, 1, length)
            mult = {"spike": factor, "level_shift": 1 + factor, "drift": 1 + factor * ramp}[kind]
            out.loc[t, "value"] = out.loc[t, "value"] * mult
            labels.append({"start": t[0], "end": t[-1], "type": kind, "factor": round(factor, 3), "hours": length})
    lab = pd.DataFrame(labels).sort_values("start").reset_index(drop=True)
    lab.insert(0, "event_id", [f"injected_{i + 1:02d}" for i in range(len(lab))])
    lab["label_source"] = "injected"
    out["injected"] = False
    for r in lab.itertuples():
        out.loc[r.start:r.end, "injected"] = True
    return out, lab
