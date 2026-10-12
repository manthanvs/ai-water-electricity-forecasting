import numpy as np
import pytest

from wef.optimise.pump_schedule import plan, simulate


def toy():
    # 4 hours: cheap, cheap, expensive, expensive; tank 0..10 starting at 5; pump up to 6 per hour
    return {"L_min": 0.0, "L_max": 10.0, "L0": 5.0, "P_max": 6.0, "kwh_per_m3": 1.0,
            "price": np.array([1.0, 1.0, 3.0, 3.0]), "band": np.array(["off_peak"] * 2 + ["peak"] * 2)}


def test_lp_known_optimum_and_bounds():
    P, demand = toy(), np.array([2.0, 2.0, 4.0, 4.0])  # total 12
    r = plan(demand, P)
    assert r["feasible"]
    # Optimum: fill to the 10 cap in the cheap hours (pump 2 + 5 + ... ), buy the rest at peak: cheap volume is
    # limited by the tank: after hour 1 level <= 10 -> cheap pumping <= 10 - 5 + 4 = 9; peak pumping = 12 - 9 = 3.
    assert r["pumping"][:2].sum() == pytest.approx(9)
    assert r["pumping"][2:].sum() == pytest.approx(3)
    assert r["cost"] == pytest.approx(9 * 1 + 3 * 3)
    assert (r["level"] >= P["L_min"] - 1e-9).all() and (r["level"] <= P["L_max"] + 1e-9).all()
    assert r["level"][-1] >= P["L0"] - 1e-9  # end level at least the start level


def test_simulation_with_exact_demand_needs_no_correction():
    P, demand = toy(), np.array([2.0, 2.0, 4.0, 4.0])
    s = simulate(plan(demand, P)["pumping"], demand, P)
    assert s["corrective_m3"] == pytest.approx(0, abs=1e-6) and s["low_level_hours"] == 0
