import numpy as np
import pytest
from PIL import Image

from wef.utils.paths import ROOT
from wef.viz.figures import REQUIRED

REPORT, SLIDES = ROOT / "figures" / "report", ROOT / "figures" / "slides"
pytestmark = pytest.mark.skipif(not REPORT.exists(), reason="run python -m wef.cli figures")


@pytest.mark.parametrize("fig_id", REQUIRED)
def test_figure_exists_in_both_styles(fig_id):
    assert (REPORT / f"{fig_id}.png").exists(), fig_id
    assert (SLIDES / f"{fig_id}.png").exists(), fig_id


@pytest.mark.parametrize("path", sorted(REPORT.glob("*.png")) if REPORT.exists() else [], ids=lambda p: p.stem)
def test_report_figures_are_greyscale(path):
    img = Image.open(path)
    if img.mode in ("L", "LA", "1"):
        return
    a = np.asarray(img.convert("RGB")).astype(int)
    assert (a[..., 0] == a[..., 1]).all() and (a[..., 1] == a[..., 2]).all(), path.name
