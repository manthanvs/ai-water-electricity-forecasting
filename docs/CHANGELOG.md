# Changelog

## Phase 0 - scaffold and environment (2026-10-12)

- Added `pyproject.toml` (package `wef`, src layout, Python 3.11), pinned `requirements.txt`, `.gitignore`, `config/config.yaml`.
- Added `src/wef/cli.py` (stages download, prepare, train, evaluate, anomaly, optimise, figures, export-powerbi, all; run manifest) and `src/wef/utils/` (`seed.py`, `io.py`, `paths.py`).
- Added `docs/DECISIONS.md`, `docs/CHANGELOG.md`, `tests/test_cli.py`, `figures/raw_screenshots/.gitkeep`.
- Environment: Python 3.11.9 venv in `.venv`, LibreOffice installed; format self-test passes.

## Phase 1 - data acquisition and data cards (2026-10-12)

- Added `wef.data.download` (idempotent, checksummed, retrying), `wef.data.load` (raw readers) and `wef.data.cards` (generated data cards and `docs/DATA.md`).
- Downloaded UCI 235, BWDF (from wf4bwdf), BattLeDIM 2018 files and Open-Meteo weather; checksums in `data/raw/checksums.json`.
- Added `report/references.yaml` with the five dataset citations (status seed).
- Config: Open-Meteo timezone GMT, water holidays IT, primary DMA 3, BattLeDIM inflow links.

## Phase 2 - cleaning and exploratory analysis (2026-10-12)

- Added `wef.data.clean` (DST rule, minute-to-hour aggregation, short-gap interpolation, MAD outlier flags, daily totals, split dates, `results/eda_summary.json`).
- Added `wef.viz.style` (report and slide styles, `save_both`) and `wef.viz.figures` with `fig_eda_profiles`, `fig_eda_weekly_heatmap`, `fig_eda_temperature`, `fig_eda_missing`.
- Processed files: `electricity_hourly/daily`, `water_hourly/daily`, `water_all_dmas_hourly`, `battledim_inflow_15min/hourly` (parquet), `battledim_leaks.csv`.
- Added `tests/test_clean.py`.

## Phase 3 - feature engineering (2026-10-12)

- Added `wef.features.build` (origin-formulated tables in `data/processed/features/`, deep-model windows, eval mask); `prepare` stage now runs cleaning + features.
- Added `tests/test_no_leakage.py` (perturbation test) and `tests/test_splits.py`.

## Phase 4 - baselines, statistical and machine learning models (2026-10-12)

- Added `wef.models.registry` (Data, Model interface, tuning, `train` stage), `baselines.py` (seasonal naive), `classical.py` (SARIMA), `ml.py` (Ridge, Random Forest, XGBoost with the relative-to-level option).
- Added `wef.evaluation.metrics` (MAE, RMSE, MAPE with exclusion, sMAPE, R2, peak MAE, skill) and `wef.evaluation.backtest` (`evaluate` stage: `results/metrics.json`, selection by validation MAE, Diebold-Mariano test, error by hour).
- Feature tables now keep rows with a missing target and carry a `level` column; tests updated (`tests/test_metrics.py`).

## Phase 5 - deep learning models (2026-10-12)

- Added `wef.models.dl` (LSTM, GRU, CNN-LSTM; relative and residual options; zero-initialised head; model card and training curves). `build.windows` now also returns per-step lag features.
- Config: deep grid units x relative x residual, 1 layer, batch 32.

## Phase 6 - evaluation and model selection (2026-10-12)

- `wef.evaluation.backtest`: schema check, no-weather ablation scoring, DMA robustness check, generated `results/summary.md`; `registry.ablation`.
- Metrics: `peak_mae` is null when no point exceeds the training 90th percentile (`n_peak_points`); `write_json` refuses NaN.
- Figures: `fig_model_comparison`, `fig_forecast_electricity`, `fig_forecast_water`, `fig_error_by_hour`, `fig_training_curves`.
- Tests: metrics.json schema test.

## Phase 7 - anomaly detection (2026-10-12)

- Added `wef.anomaly` (`inject.py`, `residual.py`, `iforest.py`, `evaluate.py`; `anomaly` stage), `results/anomaly.json`, `results/anomaly_events.csv`, figures `fig_anomaly_water` and `fig_anomaly_electricity`, `tests/test_anomaly.py`.
- Config: BattLeDIM splits, anomaly grids and injection settings; `split_dates` and holiday helper generalised.
