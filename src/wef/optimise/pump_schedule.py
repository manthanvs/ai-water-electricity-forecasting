"""Water pump scheduling as a linear programme (scipy linprog / HiGHS), evaluated against actual demand.

For each test day: choose hourly pumped volume p_h (0 <= p_h <= P_max) minimising sum tariff_h x kWh/m3 x p_h,
subject to the tank balance L_h = L_(h-1) + p_h - demand_h with L_min <= L_h <= L_max and L_23 >= L_0.
The plan made from a demand forecast is then simulated with the actual demand: whenever the level would fall
below L_min, corrective pumping at that hour's tariff (within the pump's spare capacity) restores it; level
above L_max is spilled and counted; any end-of-day shortfall against L_0 is topped up in the last hour. Every
day starts at L_0, so days are independent. All parameters: config/optimisation.yaml (ILLUSTRATIVE ASSUMPTIONS).
"""
import numpy as np
import pandas as pd
import yaml
from scipy.optimize import linprog

from wef.models.registry import PRED_DIR
from wef.utils.io import read_json, write_json
from wef.utils.paths import ROOT, RESULTS

OPT_CFG = ROOT / "config" / "optimisation.yaml"
OPTIMISATION = RESULTS / "optimisation.json"


def load_params(path=OPT_CFG) -> dict:
    return params_from(yaml.safe_load(open(path, encoding="utf-8")))


def params_from(c: dict) -> dict:
    t = c["tariff"]
    mult = np.full(24, t["multipliers"]["normal"])
    mult[t["off_peak_hours"]] = t["multipliers"]["off_peak"]
    mult[t["peak_hours"]] = t["multipliers"]["peak"]
    cap = c["tank"]["capacity_m3"]
    return {"label": c["label"], "L_min": cap * c["tank"]["min_fraction"], "L_max": cap * c["tank"]["max_fraction"],
            "L0": cap * c["tank"]["start_fraction"], "P_max": c["pump"]["max_m3_per_h"], "kwh_per_m3": c["pump"]["kwh_per_m3"],
            "price": t["base_rate"] * mult, "band": np.where(mult < 1, "off_peak", np.where(mult > 1, "peak", "normal")),
            "trigger": (cap * c["level_trigger"]["on_below_fraction"], cap * c["level_trigger"]["off_above_fraction"]),
            "raw": c}


def plan(demand: np.ndarray, P: dict) -> dict:
    """Optimal 24-hour pumping plan for the given demand (m3/h). Returns status, pumping, levels, cost."""
    n = len(demand)
    lower = np.tril(np.ones((n, n)))  # L_h - L0 = cumsum(p - d)
    cum_d = np.cumsum(demand)
    A = np.vstack([lower, -lower, -lower[-1:]])
    b = np.concatenate([P["L_max"] - P["L0"] + cum_d, P["L0"] - P["L_min"] - cum_d, [-cum_d[-1]]])  # last: sum p >= sum d
    cost = P["price"][:n] * P["kwh_per_m3"]
    r = linprog(cost, A_ub=A, b_ub=b, bounds=[(0, P["P_max"])] * n, method="highs")
    if not r.success:
        return {"feasible": False, "message": r.message}
    p = r.x
    return {"feasible": True, "pumping": p, "level": P["L0"] + np.cumsum(p - demand), "cost": float(cost @ p)}


def simulate(pumping: np.ndarray, actual: np.ndarray, P: dict) -> dict:
    """Run a pumping schedule against actual demand with corrective pumping (see module docstring)."""
    L, levels, extra, spill, low_hours, unmet = P["L0"], [], np.zeros(len(actual)), 0.0, 0, 0.0
    pump = np.asarray(pumping, float).copy()
    for h in range(len(actual)):
        L += pump[h] - actual[h]
        if L < P["L_min"] - 1e-6:  # tolerance: a plan sitting exactly at L_min is not a violation
            low_hours += 1
            add = min(P["L_min"] - L, P["P_max"] - pump[h])
            extra[h] += add
            L += add
            unmet += max(0.0, P["L_min"] - L)
        if L > P["L_max"] + 1e-6:
            spill += L - P["L_max"]
            L = P["L_max"]
        levels.append(L)
    if L < P["L0"] - 1e-6:  # restore the start level for the next day, at the last hour's tariff
        extra[-1] += P["L0"] - L
        levels[-1] = P["L0"]
    total = pump + extra
    energy = total * P["kwh_per_m3"]
    return {"cost": float(P["price"] @ energy), "energy_kwh": float(energy.sum()),
            "offpeak_kwh": float(energy[P["band"] == "off_peak"].sum()), "peak_kwh": float(energy[P["band"] == "peak"].sum()),
            "corrective_m3": float(extra.sum()), "low_level_hours": int(low_hours), "spill_m3": float(spill),
            "unmet_m3": float(unmet), "pumping": total, "level": np.array(levels)}


def level_trigger(actual: np.ndarray, P: dict) -> np.ndarray:
    """Baseline on/off controller: pump at P_max when the level is below the 'on' threshold until it passes 'off'."""
    on_below, off_above = P["trigger"]
    L, on, out = P["L0"], False, []
    for d in actual:
        on = (L < on_below) or (on and L < off_above)
        p = min(P["P_max"], max(0.0, P["L_max"] - L + d)) if on else 0.0
        L += p - d
        out.append(p)
    return np.array(out)


def run_days(demand_by_plan: dict, actual: pd.DataFrame, P: dict) -> dict:
    """demand_by_plan: {plan name: DataFrame (days x 24) of the demand used for planning}."""
    out, schedules = {}, {}
    days = actual.index
    for name, dem in demand_by_plan.items():
        rows, infeasible = [], []
        for day in days:
            pl = plan(dem.loc[day].to_numpy(), P)
            if not pl["feasible"]:
                infeasible.append(str(day.date()))
                continue
            sim = simulate(pl["pumping"], actual.loc[day].to_numpy(), P)
            rows.append({"day": day, **{k: v for k, v in sim.items() if k not in ("pumping", "level")}})
            schedules[(name, day)] = (pl, sim)
        df = pd.DataFrame(rows)
        out[name] = {"days": int(len(df)), "infeasible_days": infeasible,
                     **{k: float(df[k].sum()) for k in ("cost", "energy_kwh", "offpeak_kwh", "peak_kwh", "corrective_m3", "spill_m3", "unmet_m3")},
                     "low_level_hours": int(df["low_level_hours"].sum()),
                     "days_with_corrective_pumping": int((df["corrective_m3"] > 1e-6).sum())}
    for name, fn in (("demand_following", lambda a: a), ("level_trigger", lambda a: level_trigger(a, P))):
        rows = []
        for day in days:
            a = actual.loc[day].to_numpy()
            sim = simulate(fn(a), a, P)
            rows.append({k: v for k, v in sim.items() if k not in ("pumping", "level")})
            schedules[(name, day)] = (None, sim)
        df = pd.DataFrame(rows)
        out[name] = {"days": len(df), **{k: float(df[k].sum()) for k in ("cost", "energy_kwh", "offpeak_kwh", "peak_kwh", "corrective_m3", "spill_m3", "unmet_m3")},
                     "low_level_hours": int(df["low_level_hours"].sum()),
                     "days_with_corrective_pumping": int((df["corrective_m3"] > 1e-6).sum())}
    return out, schedules


def run(cfg) -> list:
    P = load_params()
    m = read_json(RESULTS / "metrics.json")["water"]["d1"]
    sel = m["selected"]["model"]
    preds = pd.read_parquet(PRED_DIR / "water_d1.parquet").reset_index()
    test = preds[(preds.split == "test") & preds.eval_ok]
    wide = lambda col: test.pivot(index="origin", columns="step", values=col) * 3.6  # noqa: E731  L/s -> m3/h
    actual = wide("y")
    plans = {"selected_forecast": wide(sel), "seasonal_naive_forecast": wide("seasonal_naive"), "perfect_forecast": actual}
    res, schedules = run_days(plans, actual, P)
    per_day = pd.DataFrame([{"date": day.date(), "plan": name, **{k: sim[k] for k in ("cost", "energy_kwh", "offpeak_kwh", "peak_kwh", "corrective_m3", "spill_m3")}}
                            for (name, day), (_, sim) in schedules.items()])
    per_day.sort_values(["date", "plan"]).to_csv(RESULTS / "pump_schedule_days.csv", index=False)
    base = {k: res[k]["cost"] for k in ("demand_following", "level_trigger")}
    summary = {}
    for name in plans:
        r = res[name]
        summary[name] = {
            "saving_pct_vs_demand_following": 100 * (1 - r["cost"] / base["demand_following"]),
            "saving_pct_vs_level_trigger": 100 * (1 - r["cost"] / base["level_trigger"]),
            "offpeak_kwh_shift_vs_demand_following": r["offpeak_kwh"] - res["demand_following"]["offpeak_kwh"],
            "peak_kwh_avoided_vs_demand_following": res["demand_following"]["peak_kwh"] - r["peak_kwh"]}
    from wef.optimise import peak_alerts
    out = {"label": "ILLUSTRATIVE ASSUMPTIONS - tank, pump and tariff parameters are not from a real utility",
           "assumptions": P["raw"], "units": {"cost": "cost units (base rate 1 per kWh)", "energy": "kWh", "volume": "m3"},
           "water_pump": {"series": "water DMA 3 test days with complete data", "forecast_model": sel,
                          "n_days": int(len(actual)), "results": res, "summary": summary},
           "electricity_peak_alerts": peak_alerts.run(cfg)}
    write_json(OPTIMISATION, out)
    # one representative day for the figure and the API example: the median-saving day of the selected plan
    day_save = {d: 1 - schedules[("selected_forecast", d)][1]["cost"] / schedules[("demand_following", d)][1]["cost"]
                for d in actual.index if ("selected_forecast", d) in schedules}
    med = float(np.median(list(day_save.values())))
    day = min(day_save, key=lambda d: abs(day_save[d] - med))
    pl, sim = schedules[("selected_forecast", day)]
    pd.DataFrame({"hour": range(24), "forecast_m3h": plans["selected_forecast"].loc[day].to_numpy(),
                  "actual_m3h": actual.loc[day].to_numpy(), "planned_pumping_m3h": pl["pumping"],
                  "planned_level_m3": pl["level"], "simulated_pumping_m3h": sim["pumping"], "simulated_level_m3": sim["level"],
                  "tariff_multiplier": P["price"] / P["raw"]["tariff"]["base_rate"], "band": P["band"]}).assign(
        day=day.date()).to_csv(RESULTS / "pump_schedule_example.csv", index=False)
    for name, s in summary.items():
        print(f"  {name}: saving {s['saving_pct_vs_demand_following']:.1f}% vs demand-following, "
              f"{s['saving_pct_vs_level_trigger']:.1f}% vs level trigger; corrective {res[name]['corrective_m3']:.1f} m3")
    return [PRED_DIR / "water_d1.parquet", PRED_DIR / "electricity_d1.parquet", OPT_CFG]
