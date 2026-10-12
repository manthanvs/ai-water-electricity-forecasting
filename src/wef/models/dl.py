"""LSTM, GRU and CNN-LSTM (TensorFlow/Keras) with identical inputs.

Inputs per origin (from wef.features.build.windows): a past window (168 h for D1, 56 days for W1) of the value and
its hour-or-weekday and weekday sine/cosine channels, plus a future block with the calendar, weather and lag
features of each target step (the same lag-rule features the tabular models use, all known at the origin). The
recurrent (or convolutional-recurrent) encoder summarises the window; its output is joined with the flattened
future block and a dense head emits all 24 or 7 steps at once (direct multi-output). With `residual=True` the
head's output is added to the seasonal-naive forecast (lag 168 h / 7 days, scaled), so the network learns a
correction to it. The output layer is zero-initialised, so training starts exactly at seasonal naive (residual)
or at the training mean / recent level (plain); with only about 650-1,100 training windows a random start can
sit far from the target and not recover within the epoch cap. `residual` and `relative` are chosen on validation. The recurrent (or convolutional-recurrent) encoder summarises the window; its output is joined with
the flattened future block and a dense head emits all 24 or 7 steps at once (direct multi-output).

Scaling is fitted on training data only: future covariates are standardised with training means and standard
deviations; the value channel, the lag features and the target are either standardised with the training target
mean and deviation (absolute) or divided by the recent level known at the origin and centred at 1 (relative, the
same option as the tabular models, chosen on validation).
Missing inputs inside a window (long gaps) become 0 after scaling, i.e. the training mean or the recent level.
Early stopping on validation loss; the early-stopped model is kept (no refit on train + validation).
"""
import json
import time

import numpy as np

from wef.features import build
from wef.models.registry import MODEL_DIR, Model
from wef.utils.io import read_json, write_json
from wef.utils.paths import RESULTS

CARD = MODEL_DIR / "model_card.json"
CURVES = RESULTS / "training_curves.json"


def _tf():
    import os
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")  # hide TensorFlow's C++ info/warning lines
    import tensorflow as tf
    from wef.utils.seed import set_seed
    tf.get_logger().setLevel("ERROR")
    return tf, set_seed


class Deep(Model):
    refit = False
    ext = ".keras"
    arch = "lstm"

    # ------------------------------------------------------------------ data
    def _arrays(self, data, origins):
        rows = data.table[data.table["origin"].isin(origins)]
        w = build.windows(rows, data.series, data.horizon, self.window, weather=data.weather)
        level = rows.groupby("origin")["level"].first().reindex(w["origins"]).to_numpy()
        return w, level

    def _scale(self, w, level):
        seq, cov = w["seq"].copy(), (w["fut"] - self.fut_mean) / self.fut_std
        if self.params["relative"]:
            value = lambda a: a / level.reshape(-1, *[1] * (a.ndim - 1)) - 1  # noqa: E731
        else:
            value = lambda a: (a - self.y_mean) / self.y_std  # noqa: E731
        seq[..., 0] = value(seq[..., 0])
        lags = value(w["lags"])
        fut = np.concatenate([cov, lags], axis=-1)
        naive = lags[..., build.LAGS[self.horizon].index(build.NAIVE[self.horizon])]
        x = [np.nan_to_num(a).astype("float32") for a in (seq, fut, naive)]
        return x if self.params["residual"] else x[:2], value(w["y"])

    def _unscale(self, out, level):
        return (out + 1) * level[:, None] if self.params["relative"] else out * self.y_std + self.y_mean

    # ------------------------------------------------------------------ network
    def _net(self, tf, seq_shape, fut_shape, steps):
        units, layers = self.params["units"], self.params["layers"]
        rnn = tf.keras.layers.GRU if self.arch == "gru" else tf.keras.layers.LSTM
        seq_in = tf.keras.Input(seq_shape, name="history")
        fut_in = tf.keras.Input(fut_shape, name="future_covariates")
        naive_in = tf.keras.Input((steps,), name="seasonal_naive") if self.params["residual"] else None
        h = seq_in
        if self.arch == "cnn_lstm":
            h = tf.keras.layers.Conv1D(32, 3, padding="causal", activation="relu")(h)
            h = tf.keras.layers.MaxPooling1D(2)(h)
        for i in range(layers):
            h = rnn(units, return_sequences=i < layers - 1)(h)
        z = tf.keras.layers.Concatenate()([h, tf.keras.layers.Flatten()(fut_in)])
        z = tf.keras.layers.Dense(64, activation="relu")(z)
        out = tf.keras.layers.Dense(steps, kernel_initializer="zeros")(z)
        if naive_in is not None:
            out = tf.keras.layers.Add()([out, naive_in])
        net = tf.keras.Model([seq_in, fut_in] + ([naive_in] if naive_in is not None else []), out)
        net.compile(optimizer=tf.keras.optimizers.Adam(1e-3), loss="mse")
        return net

    # ------------------------------------------------------------------ interface
    def fit(self, data, splits=("train",)):
        tf, set_seed = _tf()
        dc = data.cfg["models"]["deep"]
        set_seed(data.cfg["seed"])
        self.window, self.horizon = dc["window"][data.horizon], data.horizon
        tr, lv_tr = self._arrays(data, data.origins("train"))
        va, lv_va = self._arrays(data, data.origins("val"))
        ok_tr = ~np.isnan(tr["y"]).any(1) & (~np.isnan(lv_tr) if self.params["relative"] else True)
        ok_va = ~np.isnan(va["y"]).any(1) & (~np.isnan(lv_va) if self.params["relative"] else True)
        self.fut_mean = np.nanmean(tr["fut"][ok_tr], axis=(0, 1))
        self.fut_std = np.nanstd(tr["fut"][ok_tr], axis=(0, 1)) + 1e-6
        self.y_mean, self.y_std = float(np.nanmean(tr["y"][ok_tr])), float(np.nanstd(tr["y"][ok_tr]))
        x_tr, y_tr = self._scale(tr, lv_tr)
        x_va, y_va = self._scale(va, lv_va)
        self.net = self._net(tf, x_tr[0].shape[1:], x_tr[1].shape[1:], data.steps)
        stop = tf.keras.callbacks.EarlyStopping("val_loss", patience=dc["patience"], restore_best_weights=True)
        t0 = time.time()
        hist = self.net.fit([a[ok_tr] for a in x_tr], y_tr[ok_tr], validation_data=([a[ok_va] for a in x_va], y_va[ok_va]),
                            epochs=dc["epochs"], batch_size=dc["batch_size"], callbacks=[stop], verbose=0, shuffle=True)
        self.history = {k: [round(float(v), 5) for v in vals] for k, vals in hist.history.items()}
        self.info = {"epochs_run": len(self.history["loss"]), "best_epoch": int(np.argmin(self.history["val_loss"])) + 1,
                     "val_loss": min(self.history["val_loss"]), "train_seconds": round(time.time() - t0, 1),
                     "n_train_windows": int(ok_tr.sum()), "n_val_windows": int(ok_va.sum())}
        return self

    def fit_info(self):
        return self.info

    def predict(self, data, origins):
        w, level = self._arrays(data, origins)
        x, _ = self._scale(w, level)
        out = self.net.predict(x, verbose=0, batch_size=256)
        pred = self._unscale(out, level)
        order = {o: i for i, o in enumerate(w["origins"])}
        return pred[[order[o] for o in origins]]

    def save(self, path):
        self.net.save(path)
        card = read_json(CARD, default={})
        card[path.stem] = {
            "architecture": self.arch, "params": self.params, "window": self.window, "horizon": self.horizon,
            "inputs": {"history_channels": ["value", "position_sin", "position_cos", "dow_sin", "dow_cos"],
                       "residual_on": build.NAIVE[self.horizon],
                       "future_covariates": int(len(self.fut_mean)), "future_lag_features": build.LAGS[self.horizon]},
            "scaler": {"y_mean": self.y_mean, "y_std": self.y_std, "fut_mean": self.fut_mean.tolist(),
                       "fut_std": self.fut_std.tolist(), "relative_to_level": bool(self.params["relative"])},
            **self.info}
        write_json(CARD, card)
        curves = read_json(CURVES, default={})
        curves[path.stem] = self.history
        write_json(CURVES, curves)

    @classmethod
    def load(cls, path):
        tf, _ = _tf()
        meta = read_json(CARD)[path.stem]
        m = cls(**meta["params"])
        m.net = tf.keras.models.load_model(path)
        m.window, m.horizon, sc = meta["window"], meta["horizon"], meta["scaler"]
        m.y_mean, m.y_std = sc["y_mean"], sc["y_std"]
        m.fut_mean, m.fut_std = np.array(sc["fut_mean"]), np.array(sc["fut_std"])
        m.info = {k: meta[k] for k in ("epochs_run", "best_epoch", "val_loss", "train_seconds")}
        return m


class LSTMModel(Deep):
    name, arch = "lstm", "lstm"


class GRUModel(Deep):
    name, arch = "gru", "gru"


class CNNLSTMModel(Deep):
    name, arch = "cnn_lstm", "cnn_lstm"


def specs(cfg, horizon):
    from wef.models.registry import grid
    dc = cfg["models"]["deep"]
    cands = grid({k: dc[k] for k in ("units", "layers", "relative", "residual")})
    return [(LSTMModel, cands), (GRUModel, cands), (CNNLSTMModel, cands)]


if __name__ == "__main__":  # quick smoke run: python -m wef.models.dl
    from wef.models.registry import Data
    from wef.utils.io import load_config
    cfg = load_config()
    d = Data.load("water", "w1", cfg)
    m = LSTMModel(units=32, layers=1, relative=True, residual=True).fit(d)
    print(json.dumps(m.info), m.predict_one(d, d.origins("test")[0]))
