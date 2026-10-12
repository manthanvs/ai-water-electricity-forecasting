"""Streamlit dashboard. Run: streamlit run dashboard/app.py   (API at WEF_API_URL, default http://127.0.0.1:5000)

Every page calls the Flask API; if the API is unreachable a banner says so and the page calls the same functions
(wef.service) directly, so the dashboard still works offline.
"""
import io
import os

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

API = os.environ.get("WEF_API_URL", "http://127.0.0.1:5000").rstrip("/")
COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
NAMES = {"seasonal_naive": "Seasonal naive", "sarima": "SARIMA", "ridge": "Ridge", "random_forest": "Random Forest",
         "xgboost": "XGBoost", "lstm": "LSTM", "gru": "GRU", "cnn_lstm": "CNN-LSTM"}
HNAME = {"d1": "Next day, hourly (D1)", "w1": "Next week, daily (W1)"}
PAGES = ["Overview", "Forecast", "Anomalies", "Optimisation", "Model comparison", "Upload"]


class ApiError(Exception):
    pass


# ----------------------------------------------------------------------------------------------- data access
def _local(path, params, body):
    from wef import service as S
    p, b = params or {}, body or {}
    fn = {
        "/api/health": lambda: S.health(),
        "/api/metrics": lambda: S.metrics(p.get("resource"), p.get("horizon")),
        "/api/forecast/latest": lambda: S.latest(p.get("resource"), p.get("horizon"), p.get("model"), p.get("origin")),
        "/api/backtest": lambda: S.backtest(p.get("resource"), p.get("horizon"), p.get("start"), p.get("end"),
                                            p["model"].split(",") if p.get("model") else None),
        "/api/anomalies": lambda: S.anomalies(p.get("resource"), p.get("start"), p.get("end"), p.get("series") == "1"),
        "/api/optimisation": lambda: S.optimisation(),
        "/api/forecast": lambda: S.forecast(b.get("resource"), b.get("horizon"), b.get("history"), b.get("model"), b.get("weather")),
        "/api/schedule": lambda: S.schedule(b.get("demand"), b.get("overrides")),
    }[path]
    try:
        return fn()
    except (S.BadRequest, S.NotFound) as e:
        raise ApiError(str(e))


@st.cache_data(show_spinner=False, ttl=300)
def call(api, path, params=None, body=None):
    """(response, source) where source is 'api' or 'local'. `api` is part of the cache key."""
    try:
        r = requests.request("POST" if body is not None else "GET", api + path, params=params, json=body, timeout=60)
    except requests.RequestException:
        return _local(path, params, body), "local"
    if r.status_code >= 400:
        raise ApiError(r.json().get("error", r.text) if r.headers.get("content-type", "").startswith("application/json") else r.text)
    return r.json(), "api"


def get(path, params=None, body=None):
    data, source = call(API, path, params, body)
    if source == "local":
        st.session_state["offline"] = True
    return data


# ----------------------------------------------------------------------------------------------- helpers
def fig_base(height=380, ytitle=""):
    f = go.Figure()
    f.update_layout(template="simple_white", height=height, margin=dict(l=10, r=10, t=30, b=10), hovermode="x unified",
                    font=dict(color=INK), legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0), yaxis_title=ytitle)
    f.update_xaxes(showgrid=False, linecolor="#b5b4ae")
    f.update_yaxes(gridcolor=GRID, showgrid=True, linecolor="#b5b4ae")
    return f


def pick_resource(key, horizon=True):
    c1, c2 = st.columns(2)
    r = c1.selectbox("Resource", ["electricity", "water"], key=key + "_r", format_func=str.capitalize)
    h = c2.selectbox("Horizon", ["d1", "w1"], key=key + "_h", format_func=HNAME.get) if horizon else None
    return r, h


def guard(fn):
    try:
        fn()
    except ApiError as e:
        st.error(f"Request failed: {e}")


# ----------------------------------------------------------------------------------------------- pages
def overview():
    st.caption("Key numbers for both resources. Every figure is read from the project's results files.")
    opt = get("/api/optimisation")
    cols = st.columns(2)
    for col, res in zip(cols, ["electricity", "water"]):
        with col:
            st.subheader(res.capitalize())
            m = get("/api/metrics", {"resource": res, "horizon": "d1"})
            sel = m["selected"]["model"]
            t = m["test"][sel]
            lt = get("/api/forecast/latest", {"resource": res, "horizon": "d1"})
            vals = [x["value"] for x in lt["forecast"]]
            total = sum(vals) * (1.0 if res == "electricity" else 3.6)
            an = get("/api/anomalies", {"resource": res})
            end = pd.Timestamp(an["test_period"][1]) + pd.Timedelta(hours=23)
            recent = [e for e in an["events"] if pd.Timestamp(e["alarm"]) > end - pd.Timedelta(days=7)]
            a, b = st.columns(2)
            a.metric("Selected D1 model", NAMES[sel], f"skill {t['skill']:.2f} vs naive", delta_color="off")
            b.metric("Test MAPE", f"{t['mape']:.1f} %", f"MAE {t['mae']:.3f} {m['unit']}", delta_color="off")
            a.metric(f"Forecast for {lt['origin'][:10]}", f"{total:,.0f} {'kWh' if res == 'electricity' else 'm³'}",
                     f"peak {max(vals):.2f} {m['unit']}", delta_color="off")
            b.metric("Alarms, last 7 days of test", len(recent), an["label_source"].split(" (")[0][:40], delta_color="off")
            if res == "water":
                s = opt["water_pump"]["summary"]["selected_forecast"]
                st.metric("Pump cost saving vs demand-following", f"{s['saving_pct_vs_demand_following']:.1f} %",
                          "illustrative tank and tariff", delta_color="off")
            else:
                e = opt["electricity_peak_alerts"]["shiftable_energy"]
                st.metric("Shiftable energy on alert days", f"{e['shiftable_kwh_in_peak_hours']:.1f} kWh",
                          f"{e['alert_days']} alert days, upper bound", delta_color="off")
    st.info("Water forecasts: BWDF district DMA 3 (2021-2023). Water anomalies: BattLeDIM L-Town (simulated network, 2018). "
            "Electricity: one household, Sceaux, 2006-2010; electricity anomalies are INJECTED for evaluation. "
            "Tank, pump and tariff parameters are ILLUSTRATIVE ASSUMPTIONS.")


def forecast_page():
    res, hz = pick_resource("fc")
    h = get("/api/health")["models"][f"{res}.{hz}"]
    m = get("/api/metrics", {"resource": res, "horizon": hz})
    names = [n for n in NAMES if n != "seasonal_naive"]
    model = st.selectbox("Model", names, index=names.index(h["selected"]), format_func=lambda n: NAMES[n] + (" (selected)" if n == h["selected"] else ""))
    t0, t1 = pd.Timestamp(m["split_dates"]["test"][0]), pd.Timestamp(m["split_dates"]["test"][1])
    span = 7 if hz == "d1" else 28
    d = st.date_input("Test-period window", (t0, t0 + pd.Timedelta(days=span - 1)), min_value=t0, max_value=t1)
    if not isinstance(d, tuple) or len(d) != 2:
        st.stop()
    rows = get("/api/backtest", {"resource": res, "horizon": hz, "start": str(d[0]), "end": str(d[1]), "model": f"{model},seasonal_naive"})["rows"]
    df = pd.DataFrame(rows)
    if df.empty:
        st.warning("No forecasts in that window.")
        return
    if hz == "w1":  # one line per horizon is unreadable; show the one-day-ahead and seven-day-ahead forecasts
        df["step"] = df.groupby("origin").cumcount()
        st.caption("Weekly forecasts overlap; shown: the forecast made 1 day ahead and 7 days ahead for each day.")
    f = fig_base(420, m["unit"])
    first = df if hz == "d1" else df[df.step == 0]
    f.add_scatter(x=first.timestamp, y=first.actual, name="Actual", line=dict(color=INK, width=2))
    f.add_scatter(x=first.timestamp, y=first.seasonal_naive, name="Seasonal naive", line=dict(color="#b5b4ae", width=1.5))
    f.add_scatter(x=first.timestamp, y=first[model], name=NAMES[model] + (" (1 day ahead)" if hz == "w1" else ""), line=dict(color=COLORS[0], width=2.2))
    if hz == "w1":
        last = df[df.step == 6]
        f.add_scatter(x=last.timestamp, y=last[model], name=NAMES[model] + " (7 days ahead)", line=dict(color=COLORS[1], width=2, dash="dash"))
    st.plotly_chart(f, use_container_width=True)
    ok = df.dropna(subset=["actual"])
    c = st.columns(3)
    c[0].metric("MAE in window", f"{(ok[model] - ok.actual).abs().mean():.3f} {m['unit']}")
    c[1].metric("Seasonal-naive MAE", f"{(ok.seasonal_naive - ok.actual).abs().mean():.3f} {m['unit']}")
    c[2].metric("Full test-period MAE", f"{m['test'][model]['mae']:.3f} {m['unit']}")
    st.download_button("Download CSV", df.to_csv(index=False).encode(), f"forecast_{res}_{hz}_{model}.csv", "text/csv")


def anomalies_page():
    res, _ = pick_resource("an", horizon=False)
    base = get("/api/anomalies", {"resource": res})
    t0, t1 = pd.Timestamp(base["test_period"][0]), pd.Timestamp(base["test_period"][1])
    d = st.date_input("Window (test period)", (t0, min(t1, t0 + pd.Timedelta(days=30))), min_value=t0, max_value=t1)
    if not isinstance(d, tuple) or len(d) != 2:
        st.stop()
    a = get("/api/anomalies", {"resource": res, "start": str(d[0]), "end": str(d[1]), "series": "1"})
    st.caption(f"Labels: {a['label_source']}.")
    s = pd.DataFrame(a["series"])
    unit = "kW" if res == "electricity" else "m³/h"
    f = fig_base(420, unit)
    for i, lab in enumerate(a["labels"]):
        f.add_vrect(x0=max(pd.Timestamp(lab["start"]), pd.Timestamp(d[0])), x1=min(pd.Timestamp(lab["end"]), pd.Timestamp(d[1]) + pd.Timedelta(days=1)),
                    fillcolor=COLORS[3], opacity=0.15, line_width=0, annotation_text=f"{lab['event_id']} ({lab['type']})",
                    annotation_position="top left", annotation_font_size=10)
    if not s.empty:
        f.add_scatter(x=s.timestamp, y=s.actual, name="Actual" + (" with INJECTED anomalies" if res == "electricity" else ""), line=dict(color=COLORS[0], width=1.5))
        f.add_scatter(x=s.timestamp, y=s.forecast, name="Forecast", line=dict(color=COLORS[1], width=1.2))
        lo = s.actual.min()
        for j, (meth, sym, name) in enumerate([("residual_zscore", "triangle-down", "Alarm: residual z-score"), ("isolation_forest", "x", "Alarm: Isolation Forest")]):
            ev = [e for e in a["events"] if e["method"] == meth]
            f.add_scatter(x=[e["alarm"] for e in ev], y=[lo * (0.97 - 0.03 * j)] * len(ev), mode="markers", name=name,
                          marker=dict(symbol=sym, size=10, color=COLORS[[2, 4][j]]))
    st.plotly_chart(f, use_container_width=True)
    c = st.columns(2)
    for col, (meth, title) in zip(c, [("residual_zscore", "Residual z-score"), ("isolation_forest", "Isolation Forest")]):
        sc = a["scores"][meth]
        col.markdown(f"**{title}** (whole test period): recall {sc['recall']:.2f}, precision {sc['precision']:.2f} "
                     f"(random alarms: {sc['chance_precision']:.2f}), false alarms per week {sc['false_alarms_per_week']:.2f}, "
                     f"median delay {sc['median_delay_hours'] if sc['median_delay_hours'] is not None else '-'} h")
    st.dataframe(pd.DataFrame(a["events"]), use_container_width=True, hide_index=True)


def optimisation_page():
    m = get("/api/metrics", {"resource": "water", "horizon": "d1"})
    sel = m["selected"]["model"]
    t0, t1 = pd.Timestamp(m["split_dates"]["test"][0]), pd.Timestamp(m["split_dates"]["test"][1])
    day = st.date_input("Test day (water, DMA 3)", t0 + pd.Timedelta(days=60), min_value=t0, max_value=t1)
    c = st.columns(2)
    cap = c[0].slider("Tank capacity (m³)", 80, 300, 150, 10)
    pmax = c[1].slider("Pump capacity (m³/h)", 20, 60, 30, 2)
    rows = get("/api/backtest", {"resource": "water", "horizon": "d1", "start": str(day), "end": str(day), "model": sel})["rows"]
    if len(rows) != 24:
        st.warning("No complete forecast for that day; pick another.")
        return
    demand = [r[sel] * 3.6 for r in rows]
    actual = [None if r["actual"] is None else r["actual"] * 3.6 for r in rows]
    p = get("/api/schedule", body={"demand": demand, "overrides": {"capacity_m3": cap, "max_m3_per_h": pmax}})
    f = fig_base(300, "m³/h")
    for h, band in zip(p["hours"], p["band"]):
        if band != "normal":
            f.add_vrect(x0=h - 0.5, x1=h + 0.5, fillcolor=COLORS[7] if band == "peak" else COLORS[2], opacity=0.10, line_width=0)
    f.add_bar(x=p["hours"], y=p["pumping_m3h"], name="Optimised pumping", marker_color=COLORS[0])
    f.add_scatter(x=p["hours"], y=demand, name=f"Forecast demand ({NAMES[sel]})", line=dict(color=COLORS[1], width=2))
    f.add_scatter(x=p["hours"], y=actual, name="Actual demand", line=dict(color=INK, width=1.5, dash="dot"))
    st.plotly_chart(f, use_container_width=True)
    g = fig_base(260, "Tank level (m³)")
    g.add_scatter(x=p["hours"], y=p["level_m3"], name="Planned level", line=dict(color=COLORS[0], width=2))
    for v, name in ((p["limits"]["min_m3"], "min"), (p["limits"]["max_m3"], "max")):
        g.add_hline(y=v, line_dash="dot", line_color=INK2, annotation_text=name)
    st.plotly_chart(g, use_container_width=True)
    st.caption("Shaded red: peak tariff; green: off-peak. Parameters are ILLUSTRATIVE ASSUMPTIONS; costs are in cost units.")
    c = st.columns(3)
    c[0].metric("Plan cost", f"{p['cost']:.1f}")
    c[1].metric("Demand-following cost", f"{p['demand_following_cost']:.1f}")
    c[2].metric("Saving", f"{p['saving_pct']:.1f} %")
    st.subheader("Whole test period (default parameters)")
    o = get("/api/optimisation")["water_pump"]
    tab = pd.DataFrame({k: {"cost": v["cost"], "corrective m³": v["corrective_m3"], "peak-tariff kWh": v["peak_kwh"]}
                        for k, v in o["results"].items()}).T
    st.dataframe(tab.style.format("{:,.1f}"), use_container_width=True)


def comparison_page():
    res, hz = pick_resource("cmp")
    m = get("/api/metrics", {"resource": res, "horizon": hz})
    t = pd.DataFrame(m["test"]).T.loc[list(NAMES)]
    sel = m["selected"]["model"]
    f = fig_base(380, f"Test MAE ({m['unit']})")
    f.add_bar(x=[NAMES[k] for k in t.index], y=t["mae"], marker_color=[COLORS[1] if k == sel else COLORS[0] for k in t.index],
              text=[f"{v:.3f}" for v in t["mae"]], textposition="outside", showlegend=False)
    f.add_hline(y=t.loc["seasonal_naive", "mae"], line_dash="dash", line_color=INK2, annotation_text="seasonal naive")
    st.plotly_chart(f, use_container_width=True)
    st.caption(f"Orange: selected model ({NAMES[sel]}, {m['selected']['reason']}). Diebold-Mariano versus "
               f"{NAMES[m['significance']['vs']]}: p = {m['significance']['p_value']:.3f}. Test origins: {m['n_test_origins']}.")
    show = t[["mae", "rmse", "mape", "smape", "r2", "skill"]].rename(index=NAMES)
    show.columns = ["MAE", "RMSE", "MAPE %", "sMAPE %", "R²", "Skill vs naive"]
    st.dataframe(show.style.format("{:.3f}"), use_container_width=True)


def upload_page():
    res, hz = pick_resource("up")
    unit = "hourly" if hz == "d1" else "daily"
    st.caption(f"Upload a CSV with columns `timestamp,value` of {unit} readings (at least {336 if hz == 'd1' else 56} "
               f"{'hours' if hz == 'd1' else 'days'}, regular, ending {'at 23:00' if hz == 'd1' else 'on the day before the forecast'}).")
    from wef.data.clean import PROCESSED
    sample = pd.read_parquet(PROCESSED / f"{res}_{'hourly' if hz == 'd1' else 'daily'}.parquet")["value"].dropna()
    sample = sample.iloc[-(15 * 24 if hz == "d1" else 70) - (24 if hz == "d1" else 7):-(24 if hz == "d1" else 7)]
    st.download_button("Download a sample CSV", sample.rename_axis("timestamp").reset_index().to_csv(index=False).encode(),
                       f"sample_{res}_{hz}.csv", "text/csv")
    up = st.file_uploader("CSV file", type="csv")
    if up is None:
        return
    try:
        df = pd.read_csv(io.BytesIO(up.getvalue()))
    except Exception as e:  # noqa: BLE001 - show any parse error to the user
        st.error(f"Could not read the CSV: {e}")
        return
    if not {"timestamp", "value"} <= set(df.columns):
        st.error(f"The CSV needs columns 'timestamp' and 'value'; found {list(df.columns)}.")
        return
    hist = [{"timestamp": str(t), "value": v} for t, v in zip(df.timestamp, df.value)]
    try:
        r = get("/api/forecast", body={"resource": res, "horizon": hz, "history": hist})
    except ApiError as e:
        st.error(str(e))
        return
    fc = pd.DataFrame(r["forecast"])
    f = fig_base(380, r["unit"])
    tail = df.tail(7 * 24 if hz == "d1" else 28)
    f.add_scatter(x=pd.to_datetime(tail.timestamp), y=tail.value, name="Uploaded history", line=dict(color=INK, width=1.5))
    f.add_scatter(x=pd.to_datetime(fc.timestamp), y=fc.value, name=f"Forecast ({NAMES.get(r['model'].removesuffix('_no_weather'), r['model'])})",
                  line=dict(color=COLORS[0], width=2.2))
    st.plotly_chart(f, use_container_width=True)
    st.caption(f"Model: {r['model']}; weather for the forecast period: {r['weather_source']}.")
    st.download_button("Download forecast CSV", fc.to_csv(index=False).encode(), "forecast.csv", "text/csv")


def main():
    st.set_page_config(page_title="Water & Electricity Forecasting", layout="wide")
    st.session_state["offline"] = False
    with st.sidebar:
        st.markdown("### AI-Based Prediction of Water Demand and Electricity Consumption")
        page = st.radio("Page", PAGES, label_visibility="collapsed")
        st.caption(f"API: {API}")
    st.title(page)
    banner = st.empty()
    guard(lambda: get("/api/health"))  # every page knows whether the API is up
    guard({"Overview": overview, "Forecast": forecast_page, "Anomalies": anomalies_page, "Optimisation": optimisation_page,
           "Model comparison": comparison_page, "Upload": upload_page}[page])
    if st.session_state.get("offline"):
        banner.warning(f"The API at {API} is unreachable - showing results computed locally from the project files. "
                       "Start it with: flask --app api.app run --port 5000")


main()
