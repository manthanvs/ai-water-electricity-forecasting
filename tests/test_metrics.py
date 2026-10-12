import numpy as np
import pytest

from wef.evaluation import metrics as m

Y = np.array([1.0, 2.0, 4.0, 0.01])
F = np.array([2.0, 2.0, 3.0, 0.02])


def test_against_hand_computed_values():
    assert m.mae(Y, F) == pytest.approx((1 + 0 + 1 + 0.01) / 4)
    assert m.rmse(Y, F) == pytest.approx(np.sqrt((1 + 0 + 1 + 0.0001) / 4))
    # MAPE excludes the 0.01 actual when the floor is 5% of a training mean of 2 (= 0.1)
    mape, excl = m.mape(Y, F, 0.05 * 2)
    assert mape == pytest.approx(100 * (1 / 1 + 0 / 2 + 1 / 4) / 3) and excl == 1
    assert m.smape(Y, F) == pytest.approx(100 * np.mean([2 * 1 / 3, 0, 2 * 1 / 7, 2 * 0.01 / 0.03]))
    ybar = Y.mean()
    assert m.r2(Y, F) == pytest.approx(1 - 2.0001 / np.sum((Y - ybar) ** 2))
    assert m.peak_mae(Y, F, 1.5) == pytest.approx(0.5)


def test_skill_is_relative_to_naive():
    out = m.all_metrics(Y, F, train_mean=2, peak_threshold=1.5, naive_mae=2 * m.mae(Y, F))
    assert out["skill"] == pytest.approx(0.5)


def test_peak_mae_is_none_without_peak_points():
    out = m.all_metrics(Y, F, train_mean=2, peak_threshold=100)
    assert out["peak_mae"] is None and out["n_peak_points"] == 0


def test_metrics_json_follows_schema():
    from wef.evaluation.backtest import METRICS, check_schema
    from wef.utils.io import read_json
    if not METRICS.exists():
        pytest.skip("results/metrics.json missing; run python -m wef.cli evaluate")
    check_schema(read_json(METRICS))
