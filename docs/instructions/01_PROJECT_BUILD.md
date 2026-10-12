# 01 - Project Build Instructions

Read `CLAUDE.md` first. This file defines the complete project, in twelve gated phases. Execute one phase per session prompt, run its gate checks, update the phase status in `CLAUDE.md`, summarise, and stop.

## A. Definition of done

The project is complete when all of the following are true.

1. `python -m wef.cli all` runs end to end on a CPU-only laptop in under about 60 minutes and regenerates every file in `results/`, `figures/`, `models/` and `powerbi/exports/`.
2. For both resources (electricity and water) and both horizons (next day, next week), the test-set metrics of the seasonal-naive baseline, SARIMA, Ridge regression, Random Forest, XGBoost, LSTM, GRU and CNN-LSTM are in `results/metrics.json`.
3. Anomaly detection is evaluated against labelled events (real leak labels for water, clearly labelled injected anomalies for electricity) and the scores are in `results/anomaly.json`.
4. The pump-scheduling optimiser reports cost and energy shift against a baseline in `results/optimisation.json`.
5. The Flask API and the Streamlit dashboard run locally against the saved models, with no internet connection required.
6. Every figure listed in section E exists in `figures/report/` (greyscale) and `figures/slides/` (colour).
7. `pytest -q` passes, including the leakage tests in section F.

## B. Fixed scope decisions

These follow from the approved synopsis. Change them only with the user's agreement, and log any change in `docs/DECISIONS.md`.

Resources and datasets

- Electricity, primary: UCI "Individual Household Electric Power Consumption" (UCI dataset id 235). One household in Sceaux, France, one-minute readings, December 2006 to November 2010, about 2.07 million rows, about 1.25 percent missing values marked with "?". Target: `Global_active_power` (kW), aggregated to hourly mean kW (equivalently kWh per hour). Download with the `ucimlrepo` package or from the dataset page https://archive.ics.uci.edu/dataset/235.
- Electricity, optional extension only if time permits: UCI "ElectricityLoadDiagrams20112014" (id 321, 370 clients, 15-minute). Do not start this without the user's go-ahead.
- Water demand, primary: the Battle of the Water Demand Forecasting (BWDF) dataset from WDSA-CCWI 2024 (hourly inflows of several district metered areas, with weather variables). Try `pip install "water-benchmark-hub[bwdf]"` and read the package documentation (https://waterbenchmarkhub.readthedocs.io) for the loader; otherwise use the official BWDF release. Inspect the data and record the real structure (number of areas, period, units, weather columns, licence) in the data card. Choose one area as the primary series (the one with the fewest gaps; log the choice) and keep the others for a robustness check.
- Water leakage labels: BattLeDIM 2020 dataset (L-Town benchmark network, KIOS Research Centre), Zenodo record https://zenodo.org/record/4017659. It is expected to contain 2018 and 2019 SCADA data (flows, pressures, tank level, AMR household demands at five-minute resolution), the 2018 leakage list with start and end times, and the network model. Confirm the actual file list on download. Note in the report that L-Town is a realistic benchmark network with simulated hydraulics, not a live utility.
- Weather for electricity: Open-Meteo historical archive API, `https://archive-api.open-meteo.com/v1/archive`, latitude 48.78, longitude 2.29, timezone Europe/Paris, hourly `temperature_2m`, `relative_humidity_2m`, `precipitation`, for the full UCI period. Cache the response in `data/raw/`.
- Holidays: the `holidays` Python package (France for electricity; the BWDF country for water).
- Fallback rule: if any source cannot be downloaded or its licence forbids academic use, stop and ask the user. Never substitute synthetic data silently.

Forecast tasks

- D1, next-day hourly profile: at each forecast origin (00:00 local time) predict the 24 hourly values of the next day.
- W1, next-week daily totals: at each origin (00:00 on each day of the test period) predict the next 7 daily totals.
- Lag rule that removes leakage by construction: for D1 every lag feature is at least 24 hours older than the target hour; for W1 every lag is at least 7 days older than the target day. Rolling statistics are computed only from data up to the origin.
- Weather at the target time uses observed values as a stand-in for a weather forecast. State this "perfect weather forecast" assumption in the report, and report one ablation without weather features.

Splits (chronological; confirm against the real date coverage and log the final dates)

- Electricity: train 2007-01-01 to 2009-12-31, validation 2010-01-01 to 2010-06-30, test 2010-07-01 to the end of the data.
- Water: last 12 or more weeks are test, the 8 to 12 weeks before that are validation, the rest is train.

Models (the same feature sets and splits for both resources)

1. Seasonal naive: D1 uses the same hour seven days earlier; W1 uses the same weekday one week earlier.
2. SARIMA (statsmodels SARIMAX): W1 on daily totals with seasonal period 7; D1 on hourly data with seasonal period 24, fitted on a rolling window of the most recent 8 weeks to keep run time low. Small AIC grid search on the validation period only.
3. Ridge regression on the engineered features.
4. Random Forest (scikit-learn).
5. XGBoost (`xgboost`), early stopping on validation.
6. LSTM, 7. GRU, 8. CNN-LSTM (TensorFlow/Keras): input window of 168 hours for D1 and 56 days for W1, direct multi-output dense head (24 or 7 outputs), early stopping on validation loss, at most about 60 epochs, small networks (1 to 2 layers, 32 to 64 units) so that CPU training stays short.

For the tabular models (3 to 5), use the "origin" formulation: one row per (origin, target step), with the step index as a feature and only lag-rule-compliant features. This gives one model per resource and horizon, not 24 separate models.

Metrics: MAE, RMSE, MAPE, R squared, plus peak-period MAE (hours above the 90th percentile of training demand) and skill versus seasonal naive (`1 - MAE_model / MAE_naive`). MAPE is computed only where the actual value is at least 5 percent of the training mean (log how many points were excluded); also report sMAPE.

## C. Phases

Each phase lists tasks, outputs and gate checks. Do not move on until the gate checks pass.

### Phase 0 - Scaffold and environment

Tasks
- Create the layout in `CLAUDE.md` section 5, `pyproject.toml` (package `wef`, src layout, Python 3.11), `.gitignore` (data/, .venv/, models/*.keras over 50 MB, report/out/, presentation/out/, .env), `config/config.yaml`, `docs/DECISIONS.md`, `docs/CHANGELOG.md`.
- `requirements.txt` with versions pinned to what actually installs: pandas, numpy, scipy, scikit-learn, xgboost, statsmodels, tensorflow, matplotlib, pyyaml, holidays, requests, ucimlrepo, water-benchmark-hub (with the bwdf extra), flask, streamlit, plotly, python-docx, pdfplumber, pytest, pillow, playwright (for the dashboard screenshot; use an already installed Chromium if one exists), pulp (or use scipy.optimize.linprog only).
- `src/wef/utils/seed.py` with a `set_seed(42)` used by every entry point.
- `src/wef/cli.py` with the sub-commands listed in `CLAUDE.md`; each stage writes a line to `results/run_manifest.json` (stage, timestamp, git commit, config hash, input file checksums).
- Run `python report/docx_format.py --selftest` to prove python-docx and LibreOffice work on this machine.

Gate checks
- `pip install -r requirements.txt` succeeds in a fresh virtual environment; `python -c "import tensorflow, xgboost, statsmodels"` works.
- `python -m wef.cli --help` lists all stages.
- Format self-test prints `SELFTEST OK`.

### Phase 1 - Data acquisition and data cards

Tasks
- `wef.data.download`: idempotent downloads into `data/raw/<source>/`, SHA-256 checksums stored in `data/raw/checksums.json`, polite retry, no re-download when the checksum matches.
- One data card per source in `data/cards/<source>.md` and summarised in `docs/DATA.md`: origin URL, licence and citation, period, resolution, units, columns, missing-value rate, known caveats, and how it is used in this project.
- Add each dataset's citation to `report/references.yaml` (status `seed` until verified in report phase R1).

Gate checks
- All four sources present (UCI 235, BWDF, BattLeDIM, Open-Meteo); checksums recorded; data cards complete; any deviation from section B logged.

### Phase 2 - Cleaning and exploratory analysis

Tasks
- Parse timestamps, handle daylight-saving duplicates and gaps explicitly (document the rule), resample to hourly and daily.
- Missing data: interpolate gaps of up to 3 hours; mark longer gaps and exclude affected origins from training and evaluation (never fill long gaps with fabricated values). Report the counts.
- Outliers: flag with a rolling median and MAD rule; keep genuine peaks; do not delete test-period values.
- EDA figures (section E): average daily profile by weekday and weekend, weekly hour-by-day pattern, consumption versus temperature, missing-data map.
- Save `data/processed/<resource>_hourly.parquet` and `<resource>_daily.parquet`.

Gate checks
- No duplicated timestamps; regular frequency; summary statistics written to `results/eda_summary.json`.

### Phase 3 - Feature engineering

Tasks
- Calendar: hour, day of week, month as sine and cosine pairs; weekend flag; public-holiday flag; day before and after a holiday.
- Lags honouring the lag rule: D1 uses t-24, t-48, t-168, t-336 and same-hour means of the last 7 days computed at the origin; W1 uses d-7, d-14, d-21, d-28 and the mean of the last 28 days at the origin.
- Weather at the target time: temperature, humidity, precipitation, plus cooling and heating degree hours (base temperatures in config).
- Build the origin-formulated datasets for the tabular models and the windowed tensors for the deep models from the same cleaned series.

Gate checks
- Leakage test (see section F) passes: for every row, the newest timestamp used by any feature is not later than the origin.

### Phase 4 - Baselines, statistical and machine learning models

Tasks
- Implement models 1 to 5 behind one interface in `wef.models.registry` (`fit`, `predict(origin) -> array(h)`, `save`, `load`, `name`).
- Hyper-parameter selection uses the validation period only (small grids, logged). Refit on train plus validation before the final test evaluation.
- Rolling-origin backtest over the whole test period (`wef.evaluation.backtest`): one forecast per origin, no refitting during the test period, except that SARIMA may update its state with new observations without re-estimating parameters.

Gate checks
- Every model beats or is honestly compared to seasonal naive on validation; results written to `results/metrics.json` (schema in section D).

### Phase 5 - Deep learning models

Tasks
- LSTM, GRU and CNN-LSTM in `wef.models.dl` with identical inputs; scaler fit on training data only; fixed seeds; early stopping; save the best model per resource and horizon as `.keras` with a `model_card.json` (inputs, window, scaler, epochs run, validation loss, training time).
- Training curves saved for the appendix of the viva notes (not for the report unless it is useful).

Gate checks
- Training time per model logged; total under the run-time budget; metrics added to `results/metrics.json`.

### Phase 6 - Evaluation and model selection

Tasks
- Test-set metrics for all models, both resources, both horizons. Also: peak-period MAE, skill versus naive, the no-weather ablation for the best tabular and the best deep model, and error by hour of day.
- Select the operational model per resource and horizon by validation MAE (not by test); record the choice and the reason in `results/metrics.json` under `selected`.
- Diebold-Mariano test (or a simple paired bootstrap of daily MAE) between the selected model and the best alternative, so the report can say whether the difference is meaningful.

Gate checks
- `results/metrics.json` validates against the schema; comparison figures generated; a short plain-language summary of findings in `results/summary.md` that the report will paraphrase.

### Phase 7 - Anomaly detection

Tasks
- Method A, residual-based: residual = actual - forecast of the selected D1 model; robust z-score on a rolling 7-day window using median and MAD; flag when the absolute z exceeds k for at least m consecutive hours; merge flags into events. Tune k and m on validation.
- Method B, Isolation Forest on residual, absolute residual, hour, weekday, and rolling mean and standard deviation of consumption; contamination tuned on validation.
- Water, real labels: run both methods on BattLeDIM 2018 network inflow (aggregate to hourly; also try 15-minute if useful) and compare with the 2018 leakage list. Report event recall, precision, false alarms per week and median detection delay in hours. Expect small leaks to be missed; report this honestly.
- Electricity, injected labels: on a copy of the test period, inject three anomaly types with a fixed seed and save the labels to `data/processed/electricity_test_injected_labels.csv`: spikes (2 to 4 times the expected value for 1 to 3 hours), level shifts (plus 30 to 60 percent for 1 to 3 days, imitating an appliance left running) and slow drift. Report the same event metrics, labelled "injected" everywhere.
- Results in `results/anomaly.json`.

Gate checks
- Both methods evaluated on both resources; precision, recall and delay present; all injected data labelled.

### Phase 8 - Resource optimisation

Tasks
- Water pump scheduling as a linear programme (`wef.optimise.pump_schedule`, scipy `linprog` or PuLP). Decision: pumped volume p_h for each hour of the next day. Constraints: 0 <= p_h <= P_max; tank balance L_h = L_(h-1) + p_h - forecast demand_h; L_min <= L_h <= L_max; end-of-day level at least the start level. Objective: minimise the sum over hours of tariff_h x energy_per_m3 x p_h.
- Baseline: demand-following pumping (p_h equals actual demand) and a level-triggered on/off rule.
- Evaluate each forecast-based plan against the actual demand of that day: simulate the tank with actual demand, count bound violations, and add corrective pumping at the tariff of the hour when needed. This shows how forecast error affects savings.
- All parameters in `config/optimisation.yaml` and labelled ILLUSTRATIVE ASSUMPTIONS: tank size, pump capacity, kWh per m3, and a time-of-day tariff with off-peak, normal and peak bands expressed as multipliers of a base rate. If the user later supplies a real tariff schedule, use it and cite it.
- Electricity peak alerts (`wef.optimise.peak_alerts`): flag days whose forecast daily peak exceeds the 90th percentile of training-period daily peaks; report hit rate and false alarms; estimate the energy in peak-tariff hours that could be shifted.
- Results in `results/optimisation.json`: cost saving percentage, kWh shifted to off-peak, violations, and the same numbers under a perfect-forecast upper bound.

Gate checks
- The LP is feasible for every test day or the infeasible days are explained; savings reported against both baselines and against perfect foresight.

### Phase 9 - Flask API and Streamlit dashboard

Flask API (`api/app.py`), JSON only, input validated, errors returned as `{"error": ...}` with proper status codes:
- `GET /api/health` - status and loaded model versions
- `GET /api/metrics?resource=electricity|water&horizon=d1|w1`
- `POST /api/forecast` - body `{"resource", "horizon", "model" (optional), "history": [{"timestamp","value"}...]}`; returns forecast values with timestamps
- `GET /api/forecast/latest?resource=...&horizon=...` - forecast for the last available origin in the processed data
- `GET /api/anomalies?resource=...&start=...&end=...`
- `POST /api/schedule` - body with a 24-hour demand forecast (optional parameter overrides); returns pumping plan, tank levels and cost

Streamlit dashboard (`dashboard/app.py`, multi-page), calling the API at `WEF_API_URL`; if the API is unreachable, show a clear banner and fall back to importing `wef` directly:
1. Overview - key numbers for both resources (latest forecast, selected model and its test MAPE, anomalies in the last 7 days, estimated saving)
2. Forecast - choose resource, horizon and model; actual versus forecast chart; download as CSV
3. Anomalies - timeline with flagged events; table of events; for water, labelled leaks overlaid
4. Optimisation - pumping plan, tank level and tariff bands for a chosen day; cost comparison
5. Model comparison - metrics by model, horizon and resource
6. Upload - upload a CSV of recent readings and get a forecast (validates columns and frequency)

Keep a consistent, clean visual design; it will be shown live in the presentation and captured for the report.

Gate checks
- API tests with the Flask test client cover every endpoint, including invalid input; the dashboard starts with `streamlit run` and every page renders without errors with the API running and with it stopped.

### Phase 10 - Power BI dataset and build guide

Claude Code cannot author `.pbix` files. Instead:
- `powerbi/export.py` writes a star schema to `powerbi/exports/`: `fact_consumption` (timestamp, resource, actual), `fact_forecast` (origin, timestamp, resource, horizon, model, forecast), `fact_anomaly` (event id, resource, start, end, method, score, label source), `fact_metrics`, `fact_schedule`, `dim_date`, `dim_resource`, `dim_model`. UTF-8 CSV with ISO timestamps.
- `powerbi/POWERBI_BUILD_GUIDE.md` for the student: import steps, relationships, DAX measures (Total Consumption, Forecast Error, MAPE, Anomaly Count, Estimated Saving), and a three-page layout (Overview, Forecast versus Actual, Anomalies and Savings) with exact visuals and fields. Include where to take the screenshots needed for the report and slides.

Gate checks
- Every CSV loads with pandas and the relationships in the guide are valid (keys unique in dimension tables).

### Phase 11 - Figure freeze, tests, README, release

Tasks
- Generate all figures in section E in both styles.
- Capture `fig_dashboard` automatically: start the API and the dashboard, open the Forecast page with Playwright (headless Chromium, 1600 x 900 window), save the screenshot, and derive the greyscale report version. If Manthan has saved Power BI screenshots in `figures/raw_screenshots/`, convert them the same way and register them as optional figures.
- `README.md`: purpose, datasets and licences, setup on Windows and Linux, how to run each part, how to reproduce results, project structure, limitations.
- Tag the release `v1.0-results-frozen`. From this point the report and deck read only frozen results; any re-run requires a new tag and a rebuild of both documents.

Gate checks
- `pytest -q` passes; a clean re-run of `python -m wef.cli all` reproduces `results/metrics.json` within numerical tolerance (deep learning results may differ slightly on different hardware; document the tolerance).

## D. Results schema (`results/metrics.json`)

```json
{
  "generated_at": "ISO-8601",
  "git_commit": "abc123",
  "electricity": {
    "d1": {
      "split_dates": {"train": ["2007-01-01", "2009-12-31"], "val": ["...", "..."], "test": ["...", "..."]},
      "n_test_origins": 0,
      "test": {
        "seasonal_naive": {"mae": 0.0, "rmse": 0.0, "mape": 0.0, "smape": 0.0, "r2": 0.0, "peak_mae": 0.0, "skill": 0.0, "mape_excluded_points": 0},
        "sarima": {}, "ridge": {}, "random_forest": {}, "xgboost": {}, "lstm": {}, "gru": {}, "cnn_lstm": {}
      },
      "val": {},
      "ablation_no_weather": {"xgboost": {}, "lstm": {}},
      "selected": {"model": "lstm", "reason": "lowest validation MAE"},
      "significance": {"vs": "xgboost", "method": "diebold_mariano", "p_value": 0.0}
    },
    "w1": {}
  },
  "water": {"d1": {}, "w1": {}},
  "units": {"electricity": "kW (hourly mean)", "water": "as in source, see data card"}
}
```

`results/anomaly.json` and `results/optimisation.json` follow the same idea: nested by resource and method, every number with its unit. The report token `{{m:electricity.d1.test.lstm.mape|.1f}}` reads this file by dotted path.

## E. Figure specification

Every figure has an id, is produced by `wef.viz.figures`, and is written twice: `figures/report/<id>.png` (greyscale, 300 dpi, serif font) and `figures/slides/<id>.png` (colour, 200 dpi, sans font). Do not put titles inside report images; the report caption carries the title.

- fig_architecture - system architecture: smart meter and weather data, ingestion, preprocessing, feature store, models, forecasts, anomaly detection, optimisation, Flask API, Streamlit and Power BI. Drawn with matplotlib patches and arrows (or Graphviz rendered to PNG), black and white. Report chapter 5, slide 8.
- fig_pipeline - the six-stage methodology as a left-to-right flow. Chapter 5 (optional if space is short), slide 10.
- fig_eda_profiles - average hourly profile, weekday versus weekend, for both resources (two panels). Chapter 5, slide 9.
- fig_eda_temperature - consumption versus temperature scatter with a smoothed line. Optional.
- fig_forecast_electricity - one representative test week, actual versus seasonal naive versus selected model, D1. Chapter 6, slide 11.
- fig_forecast_water - same for water. Chapter 6, slide 12.
- fig_model_comparison - grouped bars of test MAE (or MAPE) for all models, both resources, D1 and W1 panels; hatched bars in the report version. Chapter 6, slide 11 or 12.
- fig_anomaly_water - BattLeDIM inflow with labelled leak periods shaded and detected events marked. Chapter 6, slide 13.
- fig_anomaly_electricity - injected anomalies versus detections on a test fortnight. Optional in the report, slide 13.
- fig_pump_schedule - one test day: forecast demand, optimised pumping, tank level and tariff bands. Chapter 6, slide 14.
- fig_dashboard - screenshot of the Streamlit Forecast page (and optionally the Power BI overview), captured from this project and converted to greyscale for the report. Chapter 6, slide 15.

Report style (`wef.viz.style.report()`):

```python
import matplotlib as mpl
from cycler import cycler
mpl.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Liberation Serif", "DejaVu Serif"],
    "font.size": 9, "axes.labelsize": 9, "legend.fontsize": 8,
    "axes.prop_cycle": cycler(color=["0.0", "0.35", "0.6", "0.0", "0.35"]) +
                       cycler(linestyle=["-", "--", ":", "-.", (0, (5, 1, 1, 1))]),
    "axes.grid": True, "grid.color": "0.85", "grid.linewidth": 0.5,
    "savefig.dpi": 300, "figure.dpi": 100, "savefig.bbox": "tight",
})
# width 150 mm max (5.9 in) for full width, about 3.0 in tall; legends outside data or frameless;
# bars use white fill with hatches ("", "//", "..", "xx", "\\\\") and black edges.
```

After saving, verify each report PNG is greyscale (convert with Pillow to `L` and back, or assert that the RGB channels are equal).

## F. Tests (minimum set)

- `test_no_leakage.py` - for random rows of every training and test table, the latest timestamp used by any feature is not later than the forecast origin.
- `test_splits.py` - train, validation and test are disjoint and in chronological order.
- `test_metrics.py` - MAE, RMSE, MAPE (with exclusion), sMAPE and R squared against hand-computed values.
- `test_lp.py` - the optimiser respects tank bounds and the end-level constraint on a toy case with a known optimum.
- `test_api.py` - every endpoint, valid and invalid input.
- `test_figures.py` - every figure id exists in both folders; report versions are greyscale.

## G. Run-time and hardware budget

Target a CPU-only laptop with 8 to 16 GB RAM. Keep deep models small, cap epochs, use early stopping and `tf.data` batching. If the full run exceeds about 60 minutes, reduce SARIMA's window or the number of test origins for SARIMA only, and log it.
