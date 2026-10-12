"""Flask REST API (JSON only). Run: flask --app api.app run --port 5000

GET  /api/health                                      status, results version, selected and available models
GET  /api/metrics?resource=&horizon=                  test/validation metrics, selection, significance
POST /api/forecast   {resource, horizon, model?, history: [{timestamp, value}], weather?}
GET  /api/forecast/latest?resource=&horizon=&model=&origin=   forecast for a stored origin (default: last)
GET  /api/backtest?resource=&horizon=&start=&end=&model=      stored rolling-origin forecasts (dashboard)
GET  /api/anomalies?resource=&start=&end=&series=     detected events, labels, scores (+ series)
POST /api/schedule   {demand: [24 x m3/h], overrides?}  optimal pumping plan (ILLUSTRATIVE parameters)
GET  /api/optimisation                                pump-scheduling and peak-alert results
Errors: {"error": message} with 400 (bad input), 404 (unknown route or missing results), 405, 500.
"""
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from wef import service as S

app = Flask(__name__)


def _args(*names, required=()):
    missing = [n for n in required if not request.args.get(n)]
    if missing:
        raise S.BadRequest(f"missing query parameter(s): {', '.join(missing)}")
    return [request.args.get(n) or None for n in names]


def _body():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise S.BadRequest("request body must be a JSON object")
    return body


@app.errorhandler(S.BadRequest)
def _bad(e):
    return jsonify(error=str(e)), 400


@app.errorhandler(S.NotFound)
def _missing(e):
    return jsonify(error=str(e)), 404


@app.errorhandler(HTTPException)
def _http(e):
    return jsonify(error=e.description), e.code


@app.errorhandler(Exception)
def _crash(e):  # never leak a stack trace to the client
    app.logger.exception(e)
    return jsonify(error=f"internal error: {type(e).__name__}"), 500


@app.get("/api/health")
def health():
    return jsonify(S.health())


@app.get("/api/metrics")
def metrics():
    resource, horizon = _args("resource", "horizon", required=("resource", "horizon"))
    return jsonify(S.metrics(resource, horizon))


@app.post("/api/forecast")
def forecast():
    b = _body()
    for k in ("resource", "horizon", "history"):
        if k not in b:
            raise S.BadRequest(f"missing field '{k}'")
    return jsonify(S.forecast(b["resource"], b["horizon"], b["history"], b.get("model"), b.get("weather")))


@app.get("/api/forecast/latest")
def forecast_latest():
    resource, horizon, model, origin = _args("resource", "horizon", "model", "origin", required=("resource", "horizon"))
    return jsonify(S.latest(resource, horizon, model, origin))


@app.get("/api/backtest")
def backtest():
    resource, horizon, start, end, model = _args("resource", "horizon", "start", "end", "model", required=("resource", "horizon"))
    return jsonify(S.backtest(resource, horizon, start, end, model.split(",") if model else None))


@app.get("/api/anomalies")
def anomalies():
    resource, start, end, series = _args("resource", "start", "end", "series", required=("resource",))
    return jsonify(S.anomalies(resource, start, end, include_series=series in ("1", "true", "yes")))


@app.post("/api/schedule")
def schedule():
    b = _body()
    if "demand" not in b:
        raise S.BadRequest("missing field 'demand' (24 hourly values in m3/h)")
    if b.get("overrides") is not None and not isinstance(b["overrides"], dict):
        raise S.BadRequest("'overrides' must be an object")
    return jsonify(S.schedule(b["demand"], b.get("overrides")))


@app.get("/api/optimisation")
def optimisation():
    return jsonify(S.optimisation())
