# Decisions

Every non-obvious choice, with reason and alternatives. Newest at the bottom.

## 2026-10-12 - Phase 0

- **Python 3.11.9 installed alongside 3.14.** The machine only had Python 3.14; TensorFlow wheels and the brief both target 3.11. Installed per-user with winget (`Python.Python.3.11`); the project venv `.venv` uses it. Alternative: try TensorFlow on 3.14 - rejected, not the documented environment.
- **LibreOffice installed with winget** (`TheDocumentFoundation.LibreOffice`) at the default path `C:\Program Files\LibreOffice\program\soffice.exe`, which `report/docx_format.py` already finds; no `SOFFICE` variable needed.
- **Repository folder stays `Seminar`** rather than the `water-electricity-forecasting` name suggested in START_HERE.md. Nothing depends on the folder name.
- **Root-level .docx files are git-ignored.** `Seminar Report Format 2526.docx` is byte-identical to `docs/reference/Seminar_Report_Format_2526.docx`; `Seminar_Synopsis_125M1H064_Manthan_Sankpal.docx` has the same text as `docs/reference/Approved_Synopsis_Manthan_Sankpal.docx` (whitespace only); `Seminar_Synopsis_Manthan_Sankpal.docx` is an earlier, longer draft. The canonical copies are in `docs/reference/`. Files left on disk untouched.
- **Model binaries in git.** Git cannot ignore by size, so `models/*.joblib` and `models/*.pkl` (Random Forest / XGBoost dumps, which can exceed 50 MB) are ignored; the small `.keras` files and `model_card.json` are tracked. All models are rebuilt by `python -m wef.cli all`.
- **CLI stage mapping.** Each stage is a module exposing `run(cfg) -> list[Path]` (input files read, checksummed into `results/run_manifest.json`): download -> `wef.data.download`, prepare -> `wef.features.build` (cleaning + features), train -> `wef.models.registry`, evaluate -> `wef.evaluation.backtest`, anomaly -> `wef.anomaly.evaluate`, optimise -> `wef.optimise.pump_schedule`, figures -> `wef.viz.figures`, export-powerbi -> `powerbi.export`. Stages not yet built exit with "not implemented yet (Phase N)". `run_manifest.json` is a JSON list, one record per stage run.
- **`set_seed` seeds TensorFlow only if it is already imported**, so non-deep stages do not pay TensorFlow's import time. `wef.models.dl` must call `set_seed` after `import tensorflow`.
- **requirements.txt pins direct dependencies only**, at the versions that installed here (pandas 3.0.6, TensorFlow 2.21.0, statsmodels 0.15.0, xgboost 3.2.0, ...). A full `pip freeze` would pull Windows-only transitive packages and break the Linux install. Added `pyarrow` (needed for the parquet files of Phase 2). Dropped `pulp`: the pump LP uses `scipy.optimize.linprog`, which the instructions allow, so one fewer dependency.
- **water-benchmark-hub[bwdf] 0.5.2 installs on Windows** (it brings epyt-flow, Hugging Face `datasets` and `wf4bwdf`). Whether its BWDF loader works is checked in Phase 1.
- **Provisional config values** (to be confirmed in the phase that uses them): degree-hour bases 15.5 C heating / 22 C cooling; water validation 10 weeks and test 12 weeks; outlier rule rolling 168 h median with k = 5 MAD; model grids in `config/config.yaml`.
