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
