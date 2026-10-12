"""Leakage: features of every row with origin <= o must not change when all values at or after o are changed.

Weather columns are excluded by design (observed weather at the target time stands in for a forecast).
"""
import numpy as np
import pandas as pd
import pytest

from wef.data.clean import PROCESSED
from wef.features import build
from wef.utils.io import load_config

CASES = [(r, h) for r in ("electricity", "water") for h in ("d1", "w1")]


def _data(resource):
    hp, dp = PROCESSED / f"{resource}_hourly.parquet", PROCESSED / f"{resource}_daily.parquet"
    if not hp.exists():
        pytest.skip("processed data missing; run python -m wef.cli prepare")
    return pd.read_parquet(hp), pd.read_parquet(dp)


@pytest.mark.parametrize("resource,horizon", CASES)
def test_features_use_only_data_before_origin(resource, horizon):
    cfg = load_config()
    hourly, daily = _data(resource)
    base = build.tabular(resource, horizon, cfg, hourly, daily)
    rng = np.random.default_rng(0)
    for split in ("train", "test"):
        o = rng.choice(base.loc[base.split == split, "origin"].unique())
        h2, d2 = hourly.copy(), daily.copy()
        h2.loc[h2.index >= o, "value"] = rng.uniform(0, 100, (h2.index >= o).sum())
        d2.loc[d2.index >= o, "value"] = rng.uniform(0, 1e4, (d2.index >= o).sum())
        pert = build.tabular(resource, horizon, cfg, h2, d2)
        cols = ["step", *build.LAGS[horizon], *build.CALENDAR[horizon]]
        a = base.loc[base.origin <= o].set_index(["origin", "step"])[cols[1:]]
        b = pert.set_index(["origin", "step"]).reindex(a.index)[cols[1:]]
        pd.testing.assert_frame_equal(a, b)
        assert len(a) > 100
        # the deep-model input windows obey the same rule
        series = hourly["value"] if horizon == "d1" else daily["value"]
        series2 = h2["value"] if horizon == "d1" else d2["value"]
        keep = base[base.origin <= o]
        w1 = build.windows(keep, series, horizon, 24)
        w2 = build.windows(keep, series2, horizon, 24)
        np.testing.assert_array_equal(w1["seq"], w2["seq"])


@pytest.mark.parametrize("horizon", ["d1", "w1"])
def test_lags_are_older_than_horizon(horizon):
    # lags are in the series' own unit (hours for D1, days for W1), as are the steps
    lags = [int(c.split("_")[1]) for c in build.LAGS[horizon] if c.startswith("lag_")]
    assert min(lags) >= build.STEPS[horizon]
