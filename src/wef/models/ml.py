"""Tabular models in the origin formulation: one model per resource and horizon, step index as a feature.

With `relative=True` the target and the lag features are divided by the recent level (table column `level`,
known at the origin) and predictions are multiplied back; this lets trees follow level shifts they cannot
extrapolate. Whether to use it is a hyper-parameter chosen on validation.
"""
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

from wef.features.build import LAGS
from wef.models.registry import Model


class Tabular(Model):
    def make(self, data):
        raise NotImplementedError

    def _xy(self, data, rows):
        """Model inputs, target and the multiplier that maps model output back to the original units."""
        X, y, scale = rows[self.features].copy(), rows.get("y"), 1.0
        if self.params.get("relative"):
            scale = rows["level"].to_numpy()
            lags = [c for c in LAGS[data.horizon] if c in self.features]
            X[lags] = X[lags].div(scale, axis=0)
            y = None if y is None else y / scale
        return X, y, scale

    def _train_rows(self, data, splits):
        rows = data.rows(splits)
        return rows[rows["level"].notna()] if self.params.get("relative") else rows

    def _est_params(self):
        return {k: v for k, v in self.params.items() if k not in ("relative", "n_estimators")}

    def fit(self, data, splits=("train",)):
        self.features = data.features
        X, y, _ = self._xy(data, self._train_rows(data, splits))
        self.est = self.make(data)
        self.est.fit(X, y)
        return self

    def predict(self, data, origins):
        X, _, scale = self._xy(data, data.X(origins))
        return (self.est.predict(X) * scale).reshape(len(origins), data.steps)


class RidgeModel(Tabular):
    """Missing lags (long gaps) are replaced by the training mean; features standardised on training data."""
    name = "ridge"

    def make(self, data):
        return make_pipeline(SimpleImputer(strategy="mean"), StandardScaler(), Ridge(**self._est_params()))


class RandomForestModel(Tabular):
    name = "random_forest"  # scikit-learn forests accept NaN inputs natively

    def make(self, data):
        return RandomForestRegressor(random_state=data.cfg["seed"], n_jobs=-1, **self._est_params())


class XGBoostModel(Tabular):
    """Early stopping on the validation rows during selection; the refit reuses the best number of rounds."""
    name = "xgboost"

    def make(self, data):
        xc = data.cfg["models"]["xgboost"]
        return XGBRegressor(n_estimators=self.params.get("n_estimators", xc["n_estimators"]),
                            subsample=0.8, colsample_bytree=0.8, random_state=data.cfg["seed"], n_jobs=-1,
                            early_stopping_rounds=None if "n_estimators" in self.params else xc["early_stopping_rounds"],
                            **self._est_params())

    def fit(self, data, splits=("train",)):
        self.features = data.features
        X, y, _ = self._xy(data, self._train_rows(data, splits))
        self.est = self.make(data)
        fit_kw = {}
        if "n_estimators" not in self.params:  # selection fit: stop on validation
            Xv, yv, _ = self._xy(data, self._train_rows(data, ["val"]))
            fit_kw = {"eval_set": [(Xv, yv)], "verbose": False}
        self.est.fit(X, y, **fit_kw)
        return self

    def refit_params(self):
        return {"n_estimators": int(self.est.best_iteration) + 1}

    def fit_info(self):
        return {"n_estimators": int(self.params.get("n_estimators") or self.est.best_iteration + 1)}
