"""SARIMA (statsmodels SARIMAX, no exogenous inputs).

Parameters are estimated once: D1 on the most recent 8 weeks of the fitting data (seasonal period 24), W1 on all
fitting data (period 7). At each origin the state is updated by Kalman-filtering the history before the origin
with the fixed parameters (D1: the last 8 weeks; W1: everything), then the model forecasts the horizon.
No parameter is re-estimated during validation or test.

Speed: the seasonal difference is taken outside the state space (`simple_differencing=True`, about 6x faster
for period 24), so the model forecasts y_t - y_(t-s); since every horizon is at most one season, the forecast is
undone by adding the observed value one season earlier. If that value is missing (long gap), the origin is
forecast with the equivalent full state-space model instead (same parameter vector).
"""
import warnings

import numpy as np
from statsmodels.tsa.statespace.sarimax import SARIMAX

from wef.models.registry import Model


class Sarima(Model):
    name = "sarima"
    select_key = "aic"

    def _setup(self, data):
        sc = data.cfg["models"]["sarima"][data.horizon]
        self.period = sc["seasonal_period"]
        self.window = sc.get("window_weeks", 0) * 7 * (24 if data.horizon == "d1" else 1) or None

    def _model(self, endog, simple=True):
        return SARIMAX(endog.to_numpy(), order=self.params["order"],
                       seasonal_order=(*self.params["seasonal_order"], self.period), simple_differencing=simple)

    def fit(self, data, splits=("train",)):
        self._setup(data)
        last = max(data.table.loc[data.table["split"].isin(splits), "target_time"])
        hist = data.series.loc[:last]
        hist = hist.iloc[-self.window:] if self.window else hist.loc[data.table["target_time"].min():]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = self._model(hist).fit(disp=False, maxiter=50)
        self.coef, self.aic = res.params, float(res.aic)
        self.start = data.table["target_time"].min()
        return self

    def fit_info(self):
        return {"aic": self.aic}

    def predict(self, data, origins):
        out = np.full((len(origins), data.steps), np.nan)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            for i, o in enumerate(origins):
                hist = data.series.loc[:o - data.unit]
                hist = hist.iloc[-self.window:] if self.window else hist.loc[self.start:]
                last_season = hist.to_numpy()[-self.period:][:data.steps]
                if np.isnan(last_season).any():
                    out[i] = self._model(hist, simple=False).filter(self.coef).forecast(data.steps)
                else:
                    out[i] = self._model(hist).filter(self.coef).forecast(data.steps) + last_season
        return out
