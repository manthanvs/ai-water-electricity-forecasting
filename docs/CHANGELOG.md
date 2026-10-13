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

## Phase 8 - resource optimisation (2026-10-12)

- Added `config/optimisation.yaml` (ILLUSTRATIVE ASSUMPTIONS), `wef.optimise.pump_schedule` (LP, simulation with corrective pumping, baselines; `optimise` stage) and `wef.optimise.peak_alerts`.
- Outputs: `results/optimisation.json`, `results/pump_schedule_example.csv`, figure `fig_pump_schedule`; `tests/test_lp.py`.

## Phase 9 - Flask API and Streamlit dashboard (2026-10-13)

- Added `wef.service`, `api/app.py`, `dashboard/app.py`, `.streamlit/config.toml`; `build.tabular(inference=True)`; `pump_schedule.params_from`.
- Tests: `tests/test_api.py`, `tests/test_dashboard.py`.

## Phase 10 - Power BI dataset and build guide (2026-10-13)

- Added `powerbi/export.py` (`export-powerbi` stage, eight CSV tables) and `powerbi/POWERBI_BUILD_GUIDE.md`; optimise stage writes `results/pump_schedule_days.csv`; `tests/test_powerbi.py`.

## Phase 11 - figure freeze, tests, README (2026-10-13)

- Added `wef.viz.architecture` (`fig_architecture`, `fig_pipeline`), automatic `fig_dashboard` capture and Power BI screenshot conversion in the `figures` stage, `tests/test_figures.py`, `README.md`.
- Clean end-to-end re-run (17 min) reproduced every results number exactly. Full test suite: 67 passed.
- Release tag pending confirmation.

## Report R1 - bibliography verified (2026-10-13)

- `report/references.yaml`: 21 verified entries with `verified_on`, `verified_via` and `used_for`; verification log and raw evidence in `report/out/` (git-ignored).
- Release tag `v1.0-results-frozen` created before R1.

## Report R2 - chapter drafts (2026-10-13)

- Added `report/build_report.py`, `report/content/ch0_front.md` ... `ch7_conclusion.md`, `report/figures.yaml`, `report/equations.yaml`, `report/facts.yaml`.
- Extended `report/docx_format.py` (subscripts in body text, italic reference segments, `term_line`, table grid widths).
- Draft builds with every token and citation resolved (21 of 21 references cited); one CONFIRM marker (Director's name).

## Report R3 - build, page budget, checks (2026-10-13)

- `build_report.py --check` with the 12 checks; draft build passes with 0 failures (warnings: pages above 15, Director CONFIRM marker, chapter budgets).
- Body trimmed from 26 to 20 pages; Tables 6.1 and 6.2 merged; figure placement and widths adjusted.
- `wef.viz.style.COMPACT_REPORT` and `save_both(compact=True)` for single-panel report figures; dashboard report copy cropped; figures regenerated.
- `docx_format.py`: `new_page` on title functions, caption kept with legend.

## Report R4 - visual review and student handover (2026-10-13)

- `report/docx_format.py`: table rows cannot split across pages and the header row repeats; new `group_heading()`. Self-test passes.
- `report/build_report.py`: `p` filter returns "p < 0.001" or "p = x.xxx"; nomenclature groups use `group_heading()`; Table 6.2 column widths.
- `report/figures.yaml`: Table 5.1 column widths; Figure 5.1 at 150 mm.
- `src/wef/viz/architecture.py`: report version drawn at the printed width with larger text. `src/wef/viz/figures.py`: BattLeDIM anomaly figure legend above the axes, short leak labels.
- `report/content/ch5_methodology.md`, `ch6_results.md`: equation reference and p-value wording.
- Report rebuilt: 30 pages, 20 body pages, `--check` 0 failures (draft mode). `report/out/STUDENT_REVIEW.md` written. 67 tests pass.

## Presentation P1 - deck content (2026-10-13)

- Added `presentation/slides.yaml` (18 slides plus backups B1-B5: text, notes, figure ids, tokens) and `presentation/make_deck_json.py` (resolves through the report's resolver, checks text rules, writes `presentation/deck.json`, renders `presentation/*.md.tmpl` into `presentation/out/`).
- `report/build_report.py`: `year` filter. `report/facts.yaml`: `nrw_ibnet_pct`.
