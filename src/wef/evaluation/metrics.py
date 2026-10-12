"""Point-forecast metrics. Inputs are flat arrays of actuals and forecasts."""
import numpy as np


def mae(y, f):
    return float(np.mean(np.abs(y - f)))


def rmse(y, f):
    return float(np.sqrt(np.mean((y - f) ** 2)))


def mape(y, f, min_actual: float):
    """MAPE in percent over points with actual >= min_actual. Returns (mape, n_excluded)."""
    keep = y >= min_actual
    return float(100 * np.mean(np.abs((y[keep] - f[keep]) / y[keep]))), int((~keep).sum())


def smape(y, f):
    """Symmetric MAPE in percent (0-200 scale)."""
    den = np.abs(y) + np.abs(f)
    return float(100 * np.mean(np.where(den == 0, 0.0, 2 * np.abs(y - f) / np.where(den == 0, 1, den))))


def r2(y, f):
    return float(1 - np.sum((y - f) ** 2) / np.sum((y - np.mean(y)) ** 2))


def peak_mae(y, f, threshold: float):
    """MAE over points whose actual exceeds the threshold (90th percentile of training demand)."""
    keep = y > threshold
    return float(np.mean(np.abs(y[keep] - f[keep]))) if keep.any() else float("nan")


def all_metrics(y, f, train_mean: float, peak_threshold: float, naive_mae: float = None, min_frac: float = 0.05) -> dict:
    y, f = np.asarray(y, float), np.asarray(f, float)
    m, excl = mape(y, f, min_frac * train_mean)
    out = {"mae": mae(y, f), "rmse": rmse(y, f), "mape": m, "smape": smape(y, f), "r2": r2(y, f),
           "peak_mae": peak_mae(y, f, peak_threshold), "mape_excluded_points": excl, "n_points": int(len(y))}
    out["skill"] = 1 - out["mae"] / naive_mae if naive_mae else 0.0
    return out
