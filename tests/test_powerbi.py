import pandas as pd
import pytest

from powerbi.export import OUT

FILES = ["fact_consumption", "fact_forecast", "fact_anomaly", "fact_metrics", "fact_schedule", "dim_date", "dim_resource", "dim_model"]
pytestmark = pytest.mark.skipif(not (OUT / "dim_date.csv").exists(), reason="run python -m wef.cli export-powerbi")


def load(name):
    return pd.read_csv(OUT / f"{name}.csv", encoding="utf-8")


def test_every_csv_loads():
    for name in FILES:
        assert len(load(name)) > 0, name


def test_dimension_keys_unique_and_cover_facts():
    dims = {"date": load("dim_date"), "resource": load("dim_resource"), "model": load("dim_model")}
    for key, d in dims.items():
        assert d[key].is_unique, key
    for fact in FILES[:5]:
        f = load(fact)
        for key, d in dims.items():
            if key in f:
                missing = set(f[key].dropna()) - set(d[key])
                assert not missing, (fact, key, list(missing)[:3])


def test_timestamps_are_iso():
    f = load("fact_forecast")
    assert f["timestamp"].str.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$").all()
