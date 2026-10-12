"""Method B: Isolation Forest on residual, absolute residual, hour, weekday and the trailing 24-hour mean and
standard deviation of consumption. Fitted on the training period; contamination tuned on validation."""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


def features(actual: pd.Series, residual: pd.Series) -> pd.DataFrame:
    past = actual.shift(1)
    X = pd.DataFrame({"residual": residual, "abs_residual": residual.abs(),
                      "hour": actual.index.hour, "weekday": actual.index.dayofweek,
                      "mean_24h": past.rolling(24, min_periods=12).mean(),
                      "std_24h": past.rolling(24, min_periods=12).std()}, index=actual.index)
    return X


def fit(X_train: pd.DataFrame, contamination: float, seed: int) -> IsolationForest:
    return IsolationForest(n_estimators=200, contamination=contamination, random_state=seed).fit(X_train.dropna())


def flags(model: IsolationForest, X: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    ok = X.notna().all(axis=1)
    flag = pd.Series(False, index=X.index)
    score = pd.Series(np.nan, index=X.index)
    flag[ok] = model.predict(X[ok]) == -1
    score[ok] = -model.score_samples(X[ok])
    return flag, score
