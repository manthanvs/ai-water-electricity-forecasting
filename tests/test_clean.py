import numpy as np
import pandas as pd

from wef.data.clean import _local_regular, fill_short_gaps


def test_fill_short_gaps_only_fills_runs_up_to_limit():
    s = pd.Series([np.nan, 1, np.nan, np.nan, 4, np.nan, np.nan, np.nan, np.nan, 9.0])
    filled, interp, long_gap = fill_short_gaps(s, max_len=3)
    assert filled[2:4].tolist() == [2.0, 3.0]  # 2-hour gap interpolated
    assert filled[5:9].isna().all()  # 4-hour gap kept missing
    assert np.isnan(filled[0])  # edge gap cannot be interpolated
    assert interp.sum() == 2 and long_gap.sum() == 5


def test_local_regular_handles_dst():
    autumn = pd.date_range("2021-10-31 00:00", periods=5, freq="h", tz="Europe/Rome")  # 02:00 occurs twice
    df = _local_regular(pd.DataFrame({"v": [0.0, 1, 2, 4, 5]}, index=autumn))
    assert not df.index.duplicated().any() and df.index.freq == "h"
    assert df.loc["2021-10-31 02:00", "v"] == 3.0  # the two 02:00 readings averaged
    spring = pd.date_range("2021-03-28 00:00", periods=3, freq="h", tz="Europe/Rome")  # 02:00 absent
    df = _local_regular(pd.DataFrame({"v": [1.0, 2, 3]}, index=spring))
    assert len(df) == 4 and np.isnan(df.loc["2021-03-28 02:00", "v"])
