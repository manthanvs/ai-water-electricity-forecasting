"""One interface for every forecaster, hyper-parameter selection on validation, and the `train` stage.

A model has `name`, `params`, `fit(data, splits)`, `predict(data, origins) -> array (n_origins, steps)`,
`save(path)` and `load(path)`; `predict_one(data, origin) -> array(steps)` is the single-origin form.
Hyper-parameters are chosen by validation MAE (SARIMA: by AIC) with a model fitted on train only; the chosen
model is then refitted on train + validation for the test backtest (deep models keep their early-stopped fit).
Val predictions come from the train-only fit, test predictions from the final fit; both are written to
results/predictions/<resource>_<horizon>.parquet (one column per model).
"""
import itertools
import time
from dataclasses import dataclass, field

import joblib
import numpy as np
import pandas as pd

from wef.evaluation.metrics import mae
from wef.features import build
from wef.utils.io import read_json, write_json
from wef.utils.paths import ROOT

PRED_DIR = ROOT / "results" / "predictions"
MODEL_DIR = ROOT / "models"
TUNING = ROOT / "results" / "tuning.json"


@dataclass
class Data:
    resource: str
    horizon: str
    table: pd.DataFrame
    series: pd.Series
    cfg: dict = field(repr=False)
    weather: bool = True

    @classmethod
    def load(cls, resource, horizon, cfg, weather=True):
        table = pd.read_parquet(build.FEATURES / f"{resource}_{horizon}.parquet")
        freq = "hourly" if horizon == "d1" else "daily"
        series = pd.read_parquet(build.PROCESSED / f"{resource}_{freq}.parquet")["value"]
        return cls(resource, horizon, table, series, cfg, weather)

    @property
    def steps(self):
        return build.STEPS[self.horizon]

    @property
    def unit(self):
        return pd.Timedelta(hours=1) if self.horizon == "d1" else pd.Timedelta(days=1)

    @property
    def features(self):
        return build.feature_cols(self.horizon, self.weather)

    def rows(self, splits, with_target=True) -> pd.DataFrame:
        r = self.table[self.table["split"].isin(splits)]
        return r[r["y"].notna()] if with_target else r

    def origins(self, split, eval_only=False) -> pd.DatetimeIndex:
        r = self.table[self.table["split"] == split]
        return pd.DatetimeIndex((r[r["eval_ok"]] if eval_only else r)["origin"].unique())

    def matrix(self, origins, col) -> np.ndarray:
        idx = pd.MultiIndex.from_product([pd.DatetimeIndex(origins), range(self.steps)], names=["origin", "step"])
        return self.table.set_index(["origin", "step"])[col].reindex(idx).to_numpy().reshape(len(origins), self.steps)

    def X(self, origins) -> pd.DataFrame:
        idx = pd.MultiIndex.from_product([pd.DatetimeIndex(origins), range(self.steps)], names=["origin", "step"])
        t = self.table.set_index(["origin", "step"]).reindex(idx).reset_index()
        return t[self.features + ["level"]]


class Model:
    name = "model"
    refit = True  # refit on train + val after selection
    ext = ".joblib"

    def __init__(self, **params):
        self.params = params

    def fit(self, data: Data, splits=("train",)):
        return self

    def refit_params(self) -> dict:
        """Extra parameters learned during selection that the refit must reuse (e.g. boosting rounds)."""
        return {}

    def fit_info(self) -> dict:
        return {}

    def predict(self, data: Data, origins) -> np.ndarray:
        raise NotImplementedError

    def predict_one(self, data: Data, origin) -> np.ndarray:
        return self.predict(data, [pd.Timestamp(origin)])[0]

    def save(self, path):
        joblib.dump(self, path)

    @staticmethod
    def load(path):
        return joblib.load(path)


def _val_mae(model, data: Data):
    origins = data.origins("val", eval_only=True)
    f = model.predict(data, origins)
    y = data.matrix(origins, "y")
    return mae(y.ravel(), f.ravel())


def grid(spec: dict) -> list[dict]:
    keys = list(spec)
    return [dict(zip(keys, v)) for v in itertools.product(*(spec[k] for k in keys))]


def tune(cls, data: Data, candidates: list[dict]):
    """Fit each candidate on train; pick by validation MAE, or by the model's own `select_key` (SARIMA: AIC),
    in which case only the chosen candidate is scored on validation (saves one backtest per candidate)."""
    by_key = getattr(cls, "select_key", None)
    log, best = [], None
    for params in candidates:
        t0 = time.time()
        m = cls(**params).fit(data, ("train",))
        score = {"fit_seconds": round(time.time() - t0, 1), **m.fit_info()}
        if not by_key:
            score["val_mae"] = _val_mae(m, data)
        log.append({"params": params, **score})
        key = score[by_key] if by_key else score["val_mae"]
        if best is None or key < best[0]:
            best = (key, m, params, log[-1])
        print(f"    {cls.name} {params} " + (f"{by_key} {key:.1f}" if by_key else f"val MAE {key:.4f}")
              + f" ({score['fit_seconds']} s)", flush=True)
    if by_key:
        best[3]["val_mae"] = _val_mae(best[1], data)
    return best[1], best[2], log


def specs(cfg, horizon):
    from wef.models import baselines, classical, ml
    mc = cfg["models"]
    return [
        (baselines.SeasonalNaive, [{}]),
        (classical.Sarima, [dict(order=(p, 0, q), seasonal_order=(P, 1, Q)) for p, q in mc["sarima"]["pq"]
                            for P, Q in mc["sarima"]["PQ"]]),
        (ml.RidgeModel, grid(mc["ridge"])),
        (ml.RandomForestModel, grid(mc["random_forest"])),
        (ml.XGBoostModel, grid({k: v for k, v in mc["xgboost"].items() if isinstance(v, list)})),
    ]


def train_one(cls, candidates, data: Data, preds: pd.DataFrame, tuning: dict, suffix=""):
    name = cls.name + suffix
    print(f"  [{data.resource} {data.horizon}] {name}")
    t0 = time.time()
    model, params, log = tune(cls, data, candidates)
    val_o = data.origins("val")
    val_f = model.predict(data, val_o)
    final = cls(**params, **model.refit_params()).fit(data, ("train", "val")) if cls.refit else model
    test_o = data.origins("test")
    test_f = final.predict(data, test_o)
    for o, f in ((val_o, val_f), (test_o, test_f)):
        key = pd.MultiIndex.from_product([o, range(data.steps)], names=["origin", "step"])
        preds.loc[key, name] = f.ravel()
    MODEL_DIR.mkdir(exist_ok=True)
    final.save(MODEL_DIR / f"{data.resource}_{data.horizon}_{name}{final.ext}")
    tuning.setdefault(f"{data.resource}.{data.horizon}", {})[name] = {
        "selected_params": params, "candidates": log, "train_seconds": round(time.time() - t0, 1),
        "weather": data.weather, **final.fit_info()}
    return final


def prediction_frame(data: Data) -> pd.DataFrame:
    t = data.table[data.table["split"].isin(["val", "test"])]
    return t[["origin", "step", "target_time", "split", "y", "eval_ok"]].set_index(["origin", "step"]).sort_index()


def run(cfg, only=None) -> list:
    """Train every model for both resources and horizons, then the no-weather ablation."""
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    tuning = read_json(TUNING, default={})
    inputs = []
    for resource in ("electricity", "water"):
        for horizon in ("d1", "w1"):
            data = Data.load(resource, horizon, cfg)
            inputs.append(build.FEATURES / f"{resource}_{horizon}.parquet")
            path = PRED_DIR / f"{resource}_{horizon}.parquet"
            preds = pd.read_parquet(path) if path.exists() else prediction_frame(data)
            for cls, cands in specs(cfg, horizon) + _deep_specs(cfg, horizon):
                if only and cls.name not in only:
                    continue
                train_one(cls, cands, data, preds, tuning)
                preds.to_parquet(path)
                write_json(TUNING, tuning)
    if not only:
        ablation(cfg)
    return inputs


def _deep_specs(cfg, horizon):
    import importlib.util
    if importlib.util.find_spec("wef.models.dl") is None:  # Phase 5 not built yet
        return []
    from wef.models import dl
    return dl.specs(cfg, horizon)


TABULAR = ("ridge", "random_forest", "xgboost")
DEEP = ("lstm", "gru", "cnn_lstm")


def ablation(cfg) -> None:
    """No-weather ablation: refit the best tabular and the best deep model (by validation MAE) with their selected
    hyper-parameters but without weather inputs; columns '<model>_no_weather' in the prediction files."""
    from wef.evaluation.backtest import ABLATION_SUFFIX
    tuning = read_json(TUNING)
    classes = {cls.name: cls for h in ("d1", "w1") for cls, _ in specs(cfg, h) + _deep_specs(cfg, h)}
    for resource in ("electricity", "water"):
        for horizon in ("d1", "w1"):
            key = f"{resource}.{horizon}"
            val = {m: next(c["val_mae"] for c in t["candidates"] if c["params"] == t["selected_params"])
                   for m, t in tuning[key].items() if not m.endswith(ABLATION_SUFFIX)}
            path = PRED_DIR / f"{resource}_{horizon}.parquet"
            preds = pd.read_parquet(path)
            data = Data.load(resource, horizon, cfg, weather=False)
            for family in (TABULAR, DEEP):
                best = min((m for m in family if m in val), key=val.get)
                params = tuning[key][best]["selected_params"]
                train_one(classes[best], [params], data, preds, tuning, suffix=ABLATION_SUFFIX)
            preds.to_parquet(path)
            write_json(TUNING, tuning)
