"""Pipeline entry point: python -m wef.cli <stage>.

Each stage is a `run(cfg) -> list[Path]` function (the input files it read); after it succeeds a record
is appended to results/run_manifest.json.
"""
import argparse
import hashlib
import importlib
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from wef.utils.io import load_config, read_json, sha256, write_json
from wef.utils.paths import RESULTS, ROOT
from wef.utils.seed import set_seed

# stage -> (module, phase that implements it)
STAGES = {
    "download": ("wef.data.download", 1),
    "prepare": ("wef.features.build", 3),
    "train": ("wef.models.registry", 4),
    "evaluate": ("wef.evaluation.backtest", 6),
    "anomaly": ("wef.anomaly.evaluate", 7),
    "optimise": ("wef.optimise.pump_schedule", 8),
    "figures": ("wef.viz.figures", 11),
    "export-powerbi": ("powerbi.export", 10),
}
MANIFEST = RESULTS / "run_manifest.json"


def _git_commit():
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _config_hash():
    h = hashlib.sha256()
    for p in sorted((ROOT / "config").glob("*.yaml")):
        h.update(p.read_bytes())
    return h.hexdigest()


def run_stage(name: str, cfg: dict) -> None:
    module, phase = STAGES[name]
    try:
        mod = importlib.import_module(module)
    except ModuleNotFoundError as e:
        if e.name and module.startswith(e.name):
            sys.exit(f"stage '{name}' is not implemented yet (Phase {phase})")
        raise
    set_seed(cfg["seed"])
    inputs = mod.run(cfg) or []
    manifest = read_json(MANIFEST, default=[])
    manifest.append({
        "stage": name,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_commit": _git_commit(),
        "config_hash": _config_hash(),
        "inputs": {str(Path(p).resolve().relative_to(ROOT)): sha256(p) for p in inputs},
    })
    write_json(MANIFEST, manifest)
    print(f"[{name}] done")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m wef.cli", description=__doc__.splitlines()[0])
    ap.add_argument("stage", choices=[*STAGES, "all"], help="pipeline stage to run ('all' runs every stage in order)")
    args = ap.parse_args(argv)
    cfg = load_config()
    for name in (STAGES if args.stage == "all" else [args.stage]):
        run_stage(name, cfg)


if __name__ == "__main__":
    main()
