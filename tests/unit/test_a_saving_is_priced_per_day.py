"""UX-1276: with a declared build rate, a saving reads in agent-hours a day and names where the rate came from."""

import json
import os
import pathlib
import shutil
import subprocess
import sys
import threading

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import build_rate, run_store
from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
RATE = 300
SOURCE = "300 builds/day, declared in .bga/config"

_READ = r"""
(async () => {
  for (let i = 0; i < 100 && !document.querySelector('[data-section="decision"] li.action'); i++) {
    await new Promise((r) => setTimeout(r, 100));
  }
  const decision = document.querySelector('[data-section="decision"]');
  return [...(decision?.querySelectorAll("li.action") ?? [])].map((row) => ({
    saving: row.querySelector('[data-field="saving_us"]')?.dataset.raw ?? null,
    hours: row.querySelector('[data-field="saving_us.agent_hours"]')?.dataset.raw ?? null,
    said: row.querySelector('[data-field="saving_us.agent_hours"]')?.textContent ?? null,
    text: row.textContent,
  }));
})()
"""


def _declare(project, config):
    run_store.write_config(str(project), {**run_store.read_config(str(project)), **config})


def test_a_declared_rate_is_read_with_its_source(tmp_path):
    assert build_rate.build_rate(str(tmp_path)) is None
    for bad in (True, "300", 0, -5):
        _declare(tmp_path, {"builds_per_day": bad})
        assert build_rate.build_rate(str(tmp_path)) is None, bad
    _declare(tmp_path, {"builds_per_day": RATE})
    assert build_rate.build_rate(str(tmp_path)) == {"per_day": RATE, "source": "declared in .bga/config"}
    assert build_rate.agent_hours_per_day(12_000_000, RATE) == 1.0


@pytest.fixture(scope="module")
def served(tmp_path_factory):
    """`{declared: rows}` read off one served two-plane store, first without the key, then with it."""
    from tools.bga_snapshot import store_listing, write_element_slice
    from tools.bga_view import serve

    root = tmp_path_factory.mktemp("priced")
    newest = pages.two_plane_run(root, name="store", runs=2)
    project = root / "store"
    for snapshot in run_store.list_runs(str(project)):
        write_element_slice(str(snapshot), str(pathlib.Path(snapshot) / run_store.RUN_SUBDIR))
    got = {}
    with Browser(chrome) as browser:
        for declared in (False, True):
            if declared:
                _declare(project, {"builds_per_day": RATE})
            httpd, url = serve(str(newest), port=0)
            threading.Thread(target=httpd.serve_forever, daemon=True).start()
            try:
                got[declared] = (store_listing(str(project)), browser.measure(url, _READ, 1440, 900))
            finally:
                httpd.shutdown()
                httpd.server_close()
    shutil.rmtree(root, ignore_errors=True)
    return got


@pytest.mark.skipif(chrome is None, reason=NO_BROWSER)
def test_a_saving_shows_its_agent_hours_and_their_source(served):
    listing, rows = served[True]
    assert listing["build_rate"] == {"per_day": RATE, "source": "declared in .bga/config"}, listing.get("build_rate")
    priced = [row for row in rows if row["saving"] is not None]
    assert priced, rows
    for row in priced:
        assert float(row["hours"]) == pytest.approx(float(row["saving"]) / 1e6 * RATE / 3600), row
        assert row["said"].startswith("≈ ") and row["said"].endswith(f"agent-hours/day ({SOURCE})"), row


@pytest.mark.skipif(chrome is None, reason=NO_BROWSER)
def test_no_rate_no_agent_hours(served):
    listing, rows = served[False]
    assert "build_rate" not in listing, listing
    assert rows and not any("agent-hours" in row["text"] for row in rows), rows


_PROBE = """
globalThis._installDocument ??= (await import(process.env.BGA_DOM_SHIM)).installDocument;
_installDocument();
const app = await import("./tests/viewer.mjs");
const text = (n) => !n ? "" : (n._text ?? "") + (n.children ?? []).map(text).join("");
const payload = { headline: { diagnosis: "capacity-bound", sentence: "s", top_actions: [
  { step: "Measure builders above the host's 4-core cap with bga sweep", finding_id: "capacity-recommendation",
    replayed_delta_us: 2435300000 }] } };
const rate = JSON.parse(process.env.RATE);
const section = app.renderDecision(payload, null, null, rate ? { store: { build_rate: rate } } : {});
console.log(JSON.stringify(text(section)));
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
@pytest.mark.parametrize("rate", [{"per_day": RATE, "source": "declared in .bga/config"}, None])
def test_the_replayed_delta_is_priced_beside_the_builders_step(rate):
    """The 2,402-element page's step: 4 builders replay 47.0 min, 30 replay 6.4 min, 40.6 min apart."""
    done = subprocess.run(
        [shutil.which("node"), "--input-type=module", "-e", _PROBE],
        capture_output=True,
        text=True,
        cwd=REPO,
        timeout=60,
        env=dict(os.environ, BGA_DOM_SHIM=str(REPO / "tests" / "dom_shim.mjs"), RATE=json.dumps(rate)),
    )
    assert done.returncode == 0, done.stderr[-3000:]
    said = json.loads(done.stdout)
    assert "replays 40.6 min shorter" in said, said
    # 2,435.3 s x 300 / 3600 = 202.9 hours: a count, rounded.
    assert ("≈ 203 agent-hours/day (" + SOURCE + ")" in said) == bool(rate), said
