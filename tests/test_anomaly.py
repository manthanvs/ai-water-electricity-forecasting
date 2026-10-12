import pandas as pd

from wef.anomaly.evaluate import score
from wef.anomaly.residual import events_from_flags


def test_events_need_m_hours_and_merge_close_alarms():
    t = pd.date_range("2020-01-01", periods=30, freq="h")
    f = pd.Series(False, index=t)
    f.iloc[2:4] = True    # 2-hour run -> alarm at hour 3 when m = 2
    f.iloc[6] = True      # 1-hour run -> ignored when m = 2
    f.iloc[7:10] = True   # 3-hour run, starts 4 h after the first ended -> merged (gap 6)
    f.iloc[25:27] = True  # far away -> separate event
    ev = events_from_flags(f, m=2, merge_gap=6)
    assert list(ev.alarm) == [t[3], t[26]]
    assert ev.end.iloc[0] == t[9]


def test_score_counts_hits_false_alarms_and_delay():
    ev = pd.DataFrame({"alarm": pd.to_datetime(["2020-01-02 05:00", "2020-01-05 00:00"])})
    lab = pd.DataFrame({"event_id": ["a", "b"], "type": ["spike", "spike"],
                        "start": pd.to_datetime(["2020-01-02 02:00", "2020-01-04 00:00"]),
                        "window_end": pd.to_datetime(["2020-01-02 10:00", "2020-01-04 03:00"])})
    s = score(ev, lab, "2020-01-01", "2020-01-07")
    assert s["recall"] == 0.5 and s["precision"] == 0.5 and s["false_alarms"] == 1
    assert s["median_delay_hours"] == 3.0
