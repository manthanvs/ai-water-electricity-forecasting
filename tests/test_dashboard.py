"""Every dashboard page renders without an exception, with the API stopped and with it running."""
import socket
import threading

import pytest

from wef.utils.paths import RESULTS, ROOT

pytestmark = pytest.mark.skipif(not (RESULTS / "metrics.json").exists(), reason="run the pipeline first")
APP = str(ROOT / "dashboard" / "app.py")
PAGES = ["Overview", "Forecast", "Anomalies", "Optimisation", "Model comparison", "Upload"]


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _render(monkeypatch, url):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv("WEF_API_URL", url)
    for page in PAGES:
        at = AppTest.from_file(APP, default_timeout=180)
        at.run()
        at.sidebar.radio[0].set_value(page).run()
        assert not at.exception, (page, at.exception)
        assert not at.error, (page, [e.value for e in at.error])
        yield page, at


def test_pages_render_without_api(monkeypatch):
    for page, at in _render(monkeypatch, f"http://127.0.0.1:{_free_port()}"):
        assert any("unreachable" in w.value for w in at.warning), page


def test_pages_render_with_api(monkeypatch):
    from werkzeug.serving import make_server

    from api.app import app
    port = _free_port()
    server = make_server("127.0.0.1", port, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        for page, at in _render(monkeypatch, f"http://127.0.0.1:{port}"):
            assert not any("unreachable" in w.value for w in at.warning), page
    finally:
        server.shutdown()
