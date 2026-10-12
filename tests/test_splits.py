import pandas as pd
import pytest

from wef.features.build import FEATURES


@pytest.mark.parametrize("name", ["electricity_d1", "electricity_w1", "water_d1", "water_w1"])
def test_splits_disjoint_and_chronological(name):
    path = FEATURES / f"{name}.parquet"
    if not path.exists():
        pytest.skip("feature tables missing; run python -m wef.cli prepare")
    t = pd.read_parquet(path)
    span = t.groupby("split")["target_time"].agg(["min", "max"])
    assert span.loc["train", "max"] < span.loc["val", "min"]
    assert span.loc["val", "max"] < span.loc["test", "min"]
    origins = t.groupby("split")["origin"].apply(set)
    assert not (origins["train"] & origins["val"] or origins["val"] & origins["test"] or origins["train"] & origins["test"])
