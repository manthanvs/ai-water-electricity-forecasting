# AI-Based Prediction of Water Demand and Electricity Consumption

MCA Seminar project (Course MCA33AE01), Pimpri Chinchwad College of Engineering, Pune. Student: Mr. Manthan Sankpal (PRN 125M1H064). Guide: Prof. Dr. Anjana Arakerimath.

The project forecasts household electricity consumption and district water demand with statistical, machine-learning and deep-learning models, detects anomalies (leaks; injected electricity anomalies), turns water forecasts into a cost-optimal pumping schedule, and serves everything through a Flask REST API, a Streamlit dashboard and a Power BI dataset. Every number in the seminar report and slides is read from the `results/` files that this pipeline writes.

## What it does

- **Forecasting.** Two tasks for each resource: next-day hourly profile (D1, 24 values from each midnight) and next-week daily totals (W1, 7 values). Eight models, scored on the same forecast origins: seasonal naive, SARIMA, Ridge regression, Random Forest, XGBoost, LSTM, GRU and CNN-LSTM. Chronological train, validation and test splits; hyper-parameters chosen on validation only; every lag at least one horizon old (checked by a perturbation test).
- **Evaluation.** MAE, RMSE, MAPE, sMAPE, R², peak-period MAE and skill versus seasonal naive; model selection by validation MAE; Diebold-Mariano tests; a no-weather ablation; a robustness check across all ten water districts. Plain-language findings: `results/summary.md`.
- **Anomaly detection.** Residual robust z-score and Isolation Forest, tuned on validation, scored on real BattLeDIM leak labels (water) and on clearly labelled INJECTED anomalies (electricity): `results/anomaly.json`.
- **Optimisation.** A linear programme schedules water pumping into a tank against a time-of-day tariff and is evaluated against the actual demand, two baselines and a perfect-forecast bound; electricity peak-day alerts estimate shiftable energy from the household's sub-meters: `results/optimisation.json`. Tank, pump and tariff parameters are ILLUSTRATIVE ASSUMPTIONS (`config/optimisation.yaml`).

## Datasets and licences

All four sources are public and licensed CC BY 4.0. Full data cards: `docs/DATA.md`.

- **UCI Individual Household Electric Power Consumption** (dataset 235): one household in Sceaux, France, one-minute readings, December 2006 to November 2010. G. Hebrail and A. Berard, UCI Machine Learning Repository, DOI 10.24432/C58K54.
- **Battle of the Water Demand Forecasting (BWDF)**, WDSA-CCWI 2024: hourly inflows of ten district metered areas in north-east Italy with weather, January 2021 to March 2023 (bundled in the `wf4bwdf` package). Alvisi et al., Journal of Water Resources Planning and Management 151(10), 2025, DOI 10.1061/JWRMD5.WRENG-6887.
- **BattLeDIM 2020** (L-Town benchmark, KIOS Research Centre): 2018 SCADA flows and the leak list, Zenodo DOI 10.5281/zenodo.4017659. L-Town is a realistic benchmark network with simulated hydraulics, not a live utility.
- **Open-Meteo historical weather API** (ERA5 reanalysis) for the household's location. Zippenfenig, Zenodo DOI 10.5281/zenodo.7970649.

Raw data is downloaded into `data/` (git-ignored) and never committed.

## Setup

Requirements: Python 3.11, Git; Node.js 20+ and LibreOffice only for building the report and the slides; Power BI Desktop (Windows) only for the Power BI report.

Windows (PowerShell):

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e . --no-deps
```

Linux:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e . --no-deps
```

The dashboard screenshot uses an installed Microsoft Edge or Google Chrome; if neither is present run `playwright install chromium` once.

## Run

Everything, from download to Power BI export (about 30 minutes on a CPU-only laptop):

```bash
python -m wef.cli all
```

Or stage by stage: `download`, `prepare` (cleaning and features), `train`, `evaluate`, `anomaly`, `optimise`, `figures`, `export-powerbi`, e.g. `python -m wef.cli evaluate`. Each stage appends a record (time, git commit, config hash, input checksums) to `results/run_manifest.json`.

API and dashboard (two terminals, from the repository root):

```bash
flask --app api.app run --port 5000
streamlit run dashboard/app.py
```

The dashboard reads `WEF_API_URL` (default `http://127.0.0.1:5000`). If the API is not running it shows a banner and computes the same answers locally. API endpoints (all JSON): `GET /api/health`, `GET /api/metrics`, `POST /api/forecast`, `GET /api/forecast/latest`, `GET /api/backtest`, `GET /api/anomalies`, `POST /api/schedule`, `GET /api/optimisation`; see the docstring of `api/app.py`.

Power BI: run `python -m wef.cli export-powerbi`, then follow `powerbi/POWERBI_BUILD_GUIDE.md`.

Tests:

```bash
pytest -q
```

## Report, slides and submission

These read the frozen results; every number in them is a token resolved at build time.

```bash
python report/build_report.py --final --check
python presentation/make_deck_json.py
npm install --prefix presentation
node presentation/build_deck.js
python presentation/render_deck.py
python presentation/record_demo.py
python make_submission.py
```

1. The report command writes `report/out/Seminar_Report_Manthan_Sankpal.docx` and `.pdf` and the checks to `check_report.txt`.
2. `make_deck_json.py` resolves the slide text and writes `SPEAKER_SCRIPT.md`, `DEMO_SCRIPT.md` and `VIVA_PREP.md` to `presentation/out/`.
3. `build_deck.js` writes the `.pptx`. Run `npm install` only the first time.
4. `render_deck.py` makes the PDF and slide images and checks fonts and notes.
5. `record_demo.py` records the backup demo video. MP4 output needs ffmpeg on PATH, imageio-ffmpeg, or `--ffmpeg PATH`.
6. `make_submission.py` assembles `submission/` and the zip. It runs only after a passing final-mode report build.

## Reproducing the results

`python -m wef.cli all` rebuilds every file in `results/`, `figures/`, `models/` and `powerbi/exports/` from the raw data, with seed 42 for Python, NumPy and TensorFlow (TensorFlow op determinism on). Downloads are checksummed (`data/raw/checksums.json`) and are skipped when the files are already present. On the machine that produced the frozen results a clean re-run reproduced `results/metrics.json` exactly; on other hardware the deep-learning metrics can differ slightly (floating-point order), within the tolerance stated in `docs/DECISIONS.md`. The other models are deterministic.

## Project structure

```
config/            config.yaml (paths, splits, horizons, grids), optimisation.yaml (ILLUSTRATIVE parameters)
src/wef/           the package: cli.py, data/, features/, models/, evaluation/, anomaly/, optimise/, viz/, service.py
api/app.py         Flask REST API          dashboard/app.py   Streamlit dashboard
powerbi/           export.py, POWERBI_BUILD_GUIDE.md, exports/ (generated)
results/           metrics.json, anomaly.json, optimisation.json, summary.md, predictions/, run manifest
figures/report/    greyscale 300 dpi figures for the report    figures/slides/  colour figures for the deck
models/            deep models (.keras) and model_card.json; tree models (.joblib, git-ignored)
tests/             pytest suite (leakage, splits, metrics, LP, API, dashboard, figures, Power BI)
report/, presentation/   seminar report and slides (built from results/)
docs/              DATA.md, DECISIONS.md (every judgement call), CHANGELOG.md, instructions/, reference/
```

## Limitations

- One household is a noisy, appliance-driven series; its percentage errors are high because night loads are small. District water demand is much smoother.
- The water test period follows a drop in demand in late 2022; models had to work relative to the recent level, and SARIMA did not adapt.
- Observed weather stands in for a weather forecast ("perfect weather forecast"); a no-weather ablation shows how much weather contributes.
- BattLeDIM leaks overlap heavily, so event precision must be read against its chance level (reported); incipient leaks are hard to detect from inflow alone. L-Town is simulated.
- Electricity anomalies are injected, not observed.
- Tank, pump and tariff values are illustrative; savings are in percent of a notional cost, not money.
- Deep models were trained once per configuration on about 650 to 1,100 daily windows; with more data they may do better.
