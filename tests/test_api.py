import pandas as pd
import pytest

from wef.utils.paths import RESULTS

pytestmark = pytest.mark.skipif(not (RESULTS / "metrics.json").exists(), reason="run the pipeline first")


@pytest.fixture(scope="module")
def client():
    from api.app import app
    return app.test_client()


def _hourly_history(start, end):
    s = pd.read_parquet("data/processed/electricity_hourly.parquet")["value"].loc[start:end]
    return [{"timestamp": str(t), "value": float(v)} for t, v in s.items()]


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json["status"] == "ok"
    assert r.json["models"]["water.d1"]["selected"] in r.json["models"]["water.d1"]["available"]


def test_metrics_valid_and_invalid(client):
    r = client.get("/api/metrics?resource=electricity&horizon=d1")
    assert r.status_code == 200 and "seasonal_naive" in r.json["test"]
    assert client.get("/api/metrics?resource=gas&horizon=d1").status_code == 400
    r = client.get("/api/metrics?resource=water")
    assert r.status_code == 400 and "horizon" in r.json["error"]


def test_forecast_latest(client):
    r = client.get("/api/forecast/latest?resource=water&horizon=w1")
    assert r.status_code == 200 and len(r.json["forecast"]) == 7
    assert client.get("/api/forecast/latest?resource=water&horizon=d1&origin=1999-01-01").status_code == 400
    assert client.get("/api/forecast/latest?resource=water&horizon=d1&model=nope").status_code == 400


def test_forecast_post(client):
    hist = _hourly_history("2010-10-01", "2010-10-20 23:00")
    r = client.post("/api/forecast", json={"resource": "electricity", "horizon": "d1", "history": hist})
    assert r.status_code == 200, r.json
    assert len(r.json["forecast"]) == 24 and r.json["weather_source"] == "dataset"
    # dates outside the data: falls back to a model without weather inputs
    shifted = [{"timestamp": str(pd.Timestamp(h["timestamp"]) + pd.Timedelta(days=700)), "value": h["value"]} for h in hist]
    r = client.post("/api/forecast", json={"resource": "electricity", "horizon": "d1", "history": shifted})
    assert r.status_code == 200 and r.json["model"].endswith("_no_weather")


@pytest.mark.parametrize("body,needle", [
    ("not json", "JSON object"),
    ({"resource": "electricity", "horizon": "d1"}, "history"),
    ({"resource": "electricity", "horizon": "d1", "history": []}, "non-empty"),
    ({"resource": "electricity", "horizon": "d1", "history": [{"timestamp": "x", "value": 1}]}, "parseable"),
    ({"resource": "electricity", "horizon": "d1", "history": [{"timestamp": "2010-01-01 00:00", "value": 1}]}, "at least"),
])
def test_forecast_post_invalid(client, body, needle):
    r = client.post("/api/forecast", json=body) if isinstance(body, dict) else client.post("/api/forecast", data=body)
    assert r.status_code == 400 and needle in r.json["error"]


def test_forecast_post_irregular_and_negative(client):
    hist = _hourly_history("2010-10-01", "2010-10-20 23:00")
    gap = hist[:100] + hist[101:]
    r = client.post("/api/forecast", json={"resource": "electricity", "horizon": "d1", "history": gap})
    assert r.status_code == 400 and "regular" in r.json["error"]
    neg = [dict(h, value=-1.0) if i == 5 else h for i, h in enumerate(hist)]
    assert client.post("/api/forecast", json={"resource": "electricity", "horizon": "d1", "history": neg}).status_code == 400


def test_backtest(client):
    r = client.get("/api/backtest?resource=water&horizon=w1&start=2023-03-01&end=2023-03-03&model=xgboost")
    assert r.status_code == 200 and len(r.json["rows"]) == 21
    assert client.get("/api/backtest?resource=water&horizon=w1&model=nope").status_code == 400
    assert client.get("/api/backtest?resource=water&horizon=w1&start=notadate").status_code == 400


def test_anomalies(client):
    r = client.get("/api/anomalies?resource=water&start=2018-10-01&end=2018-10-31&series=1")
    assert r.status_code == 200 and r.json["series"] and "residual_zscore" in r.json["scores"]
    assert client.get("/api/anomalies").status_code == 400
    assert client.get("/api/anomalies?resource=water&start=2018-12-01&end=2018-01-01").status_code == 400


def test_schedule(client):
    r = client.post("/api/schedule", json={"demand": [10] * 24})
    assert r.status_code == 200 and len(r.json["pumping_m3h"]) == 24
    lim = r.json["limits"]
    assert min(r.json["level_m3"]) >= lim["min_m3"] - 1e-6 and max(r.json["level_m3"]) <= lim["max_m3"] + 1e-6
    assert r.json["cost"] <= r.json["demand_following_cost"] + 1e-9
    assert client.post("/api/schedule", json={"demand": [10] * 23}).status_code == 400
    assert client.post("/api/schedule", json={"demand": [-1] * 24}).status_code == 400
    assert client.post("/api/schedule", json={"demand": [10] * 24, "overrides": {"colour": 1}}).status_code == 400
    r = client.post("/api/schedule", json={"demand": [100] * 24})  # beyond pump capacity
    assert r.status_code == 400 and "infeasible" in r.json["error"]


def test_optimisation_and_unknown_route(client):
    assert client.get("/api/optimisation").status_code == 200
    r = client.get("/api/nothing")
    assert r.status_code == 404 and "error" in r.json
    assert client.post("/api/health").status_code == 405
