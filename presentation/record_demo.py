"""Record the backup demo video: the DEMO_SCRIPT.md click path through the real dashboard, with step captions.

    python presentation/record_demo.py [--ffmpeg PATH]

Starts the API and the dashboard on free ports, drives Chromium/Edge with Playwright (video recording), and writes
submission/Demo_Backup_Manthan_Sankpal.mp4. MP4 needs a full ffmpeg (found on PATH, through imageio-ffmpeg, or given
with --ffmpeg); without one the WebM recording is kept instead. Manthan may replace it with his own narrated recording.
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import Error, sync_playwright

from wef.utils.paths import ROOT
from wef.viz.figures import _free_port, _wait_http

OUT = ROOT / "submission" / "Demo_Backup_Manthan_Sankpal.mp4"
SIZE = {"width": 1440, "height": 810}
BANNER = """(t) => { let b = document.getElementById('demo-banner');
  if (!b) { b = document.createElement('div'); b.id = 'demo-banner'; document.body.appendChild(b);
    Object.assign(b.style, {position: 'fixed', right: '24px', bottom: '24px', zIndex: 99999, padding: '10px 18px',
      background: '#0B2545', color: '#fff', font: '600 20px Calibri, Segoe UI, sans-serif', borderRadius: '8px'}); }
  b.textContent = t; }"""


def ffmpeg_path(argv):
    if "--ffmpeg" in argv:
        return argv[argv.index("--ffmpeg") + 1]
    if shutil.which("ffmpeg"):
        return shutil.which("ffmpeg")
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return None


def record(ui: str, video_dir: str) -> Path:
    with sync_playwright() as pw:
        browser = None
        for kw in ({"channel": "msedge"}, {"channel": "chrome"}, {}):
            try:
                browser = pw.chromium.launch(**kw)
                break
            except Error:
                continue
        if browser is None:
            sys.exit("no Chromium/Edge/Chrome found (run: playwright install chromium)")
        page = None

        def caption(text, wait_ms=0):
            page.evaluate(BANNER, text)
            page.wait_for_timeout(wait_ms)

        def plot():
            page.wait_for_selector(".js-plotly-plot", timeout=120000)
            page.wait_for_timeout(2500)

        def scroll(dy):
            page.mouse.move(900, 500)  # over the main area, not the sidebar
            page.mouse.wheel(0, dy)
            page.wait_for_timeout(800)

        def goto(name):  # wait for the new page's title and chart, so no stale widget of the old page is clicked
            scroll(-5000)  # Streamlit keeps the scroll position across pages
            page.locator('[data-testid="stSidebar"]').get_by_text(name, exact=True).click()
            page.get_by_role("heading", name=name, exact=True).wait_for(timeout=60000)
            plot()

        def choose(label, option):  # keyboard is reliable with Streamlit's combobox; mouse picks are not
            box = page.get_by_role("combobox", name=label).first
            box.click()
            box.fill(option)
            page.keyboard.press("Enter")
            page.wait_for_timeout(1000)
            if box.input_value() != option:
                page.screenshot(path=str(ROOT / "submission" / "record_demo_failure.png"))
                sys.exit(f"could not select {option} in {label} (screenshot in submission/)")
            plot()

        def click_path(record: bool):
            hold = 1 if record else 0  # the unrecorded warm-up pass does not pause
            page.goto(ui, wait_until="networkidle")
            page.get_by_text("Selected D1 model").first.wait_for(timeout=180000)
            caption("1  Overview: selected models and test errors", 13000 * hold)
            caption("2  Forecast: water, actual vs forecast (test week)")
            goto("Forecast"); choose("Resource", "Water")
            page.wait_for_timeout(9000 * hold)
            scroll(500); caption("2  Forecast: error in window vs seasonal naive", 6000 * hold)
            caption("3  Anomalies: labelled BattLeDIM leaks and detector alarms")
            goto("Anomalies"); choose("Resource", "Water")
            page.wait_for_timeout(9000 * hold)
            scroll(450); caption("3  Anomalies: recall, precision vs chance, delay", 7000 * hold)
            caption("4  Optimisation: pumping moves into off-peak hours")
            goto("Optimisation")
            page.wait_for_timeout(10000 * hold)
            scroll(700); caption("4  Optimisation: cost vs demand-following (illustrative tariff)", 8000 * hold)
            scroll(-5000); caption("Back to the slides", 3000 * hold)

        warm = browser.new_context(viewport=SIZE)  # first load is slow (models, caches): keep it out of the video
        page = warm.new_page()
        click_path(record=False)
        warm.close()
        ctx = browser.new_context(viewport=SIZE, record_video_dir=video_dir, record_video_size=SIZE)
        page = ctx.new_page()
        click_path(record=True)
        video = Path(page.video.path())
        ctx.close()
        browser.close()
    return video


def main():
    api_port, ui_port = _free_port(5000), _free_port(8501)
    env = {**os.environ, "WEF_API_URL": f"http://127.0.0.1:{api_port}"}
    procs = [subprocess.Popen([sys.executable, "-m", "flask", "--app", "api.app", "run", "--port", str(api_port)], cwd=ROOT,
                              env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL),
             subprocess.Popen([sys.executable, "-m", "streamlit", "run", "dashboard/app.py", "--server.port", str(ui_port),
                               "--server.headless", "true", "--browser.gatherUsageStats", "false"], cwd=ROOT, env=env,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)]
    try:
        _wait_http(f"http://127.0.0.1:{api_port}/api/health")
        _wait_http(f"http://127.0.0.1:{ui_port}/_stcore/health")
        with tempfile.TemporaryDirectory() as tmp:
            webm = record(f"http://127.0.0.1:{ui_port}", tmp)
            OUT.parent.mkdir(exist_ok=True)
            ff = ffmpeg_path(sys.argv)
            if ff:
                subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(webm), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                                "-crf", "23", "-movflags", "+faststart", str(OUT)], check=True)
                print(f"wrote {OUT}")
            else:
                shutil.copy2(webm, OUT.with_suffix(".webm"))
                print(f"no ffmpeg for MP4: wrote {OUT.with_suffix('.webm')}")
    finally:
        for p in procs:
            p.terminate()


if __name__ == "__main__":
    main()
