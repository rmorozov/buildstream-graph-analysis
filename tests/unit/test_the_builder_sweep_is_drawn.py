"""UX-1274: the builder sweep runs past the host to the graph's width, its curve is drawn, and its top is no knee."""

import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import sweep_curve
from bga.correlate import compute_capacity_recommendation
from bga.findings import _capacity_step
from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
#: The round-164 review's page: 2,402 elements, both planes.
PAGE_SHAPE = ("--layers", "40", "--width", "60", "--workload", "binaries")
VIEWPORTS = [(1440, 900), (390, 844)]
REPLAYED = re.compile(r"the replay puts (\d+) builders at [\d.]+ (?:s|min|h) \(replayed, no contention\)")

_READ = r"""
(() => {
  const rec = document.querySelector('[data-section="capacity_recommendation"]');
  const series = rec?.querySelector('[data-role="series"]');
  return {
    points: series ? Number(series.dataset.points) : null,
    unit: series?.dataset.unit ?? null,
    marks: series ? series.querySelectorAll('svg[data-role="sparkline"] rect').length : null,
    step: document.querySelector('li.action [data-field="step"]')?.textContent ?? null,
    text: [rec, document.querySelector('[data-section="agent_sizing"]')].map((n) => n?.textContent ?? "").join(" "),
  };
})()
"""


@pytest.fixture(scope="module")
def page(tmp_path_factory):
    import tools.bga_view as view

    root = tmp_path_factory.mktemp("builder-sweep")
    run = pages.two_plane_run(root, PAGE_SHAPE, name="page")
    done = subprocess.run(
        [sys.executable, "-m", "bga.cli", "analyze", str(run), "--format", "json"],
        capture_output=True,
        text=True,
        cwd=REPO,
        timeout=300,
    )
    assert done.returncode == 0, done.stderr[-2000:]
    html = root / "page.html"
    view.export(str(run), str(html))
    yield json.loads(done.stdout), html.as_uri()
    shutil.rmtree(root, ignore_errors=True)


def test_the_sweep_reaches_past_the_host_to_sixteen(page):
    rec = page[0]["capacity_recommendation"]
    assert len(rec["sweep"]) >= 16, rec["sweep"]
    assert page[0]["agent_sizing"]["builders"]["swept_to"] == len(rec["sweep"])


def test_the_decision_names_a_replayed_wall_above_four_builders(page):
    step = page[0]["headline"]["top_actions"][0]["step"]
    said = REPLAYED.search(step)
    assert said and int(said.group(1)) > 4, step


@pytest.fixture(scope="module")
def read(page):
    with Browser(chrome) as browser:
        return {width: browser.measure(page[1], _READ, width, height) for width, height in VIEWPORTS}


@pytest.mark.skipif(chrome is None, reason=NO_BROWSER)
@pytest.mark.parametrize("width", [w for w, _ in VIEWPORTS])
def test_the_curve_is_drawn_one_mark_a_point(page, read, width):
    got = read[width]
    count = len(page[0]["capacity_recommendation"]["sweep"])
    assert (got["points"], got["marks"], got["unit"]) == (count, count, "builder"), got
    assert REPLAYED.search(got["step"] or ""), got["step"]
    assert not re.search(rf"knee is at {count} builders", got["text"]), got["text"]


def test_a_knee_at_the_range_top_is_no_knee():
    rec = compute_capacity_recommendation(
        {"cores_busy": 0.5, "host_cpu_count": 4}, {}, knee=8, knee_range_top=8, builders=4
    )
    said = " ".join([rec["verdict"], *(c["reason"] for c in rec["constraints"])])
    assert "knee is at 8" not in said and "allows 8" not in said, said
    assert "no knee within 8" in said, said


def test_the_step_quotes_the_wall_at_the_knee():
    rec = {
        "binding_constraint": "host_cores",
        "host_cpu_count": 4,
        "recommended_builders": 4,
        "constraints": [{"name": "graph", "allows": 6}, {"name": "host_cores", "allows": 4, "clamped_from": 18}],
        "sweep": [6e8, 3e8, 2e8, 1.5e8, 1.2e8, 1e8, 1e8],
    }
    assert sweep_curve.replayed_clause(rec) == "the replay puts 6 builders at 1.7 min (replayed, no contention)"
    run = type("Run", (), {"capacity_recommendation": rec})()
    assert all("the replay puts 6 builders at 1.7 min" in part for part in _capacity_step(run))


_PROBE = """
globalThis._installDocument ??= (await import(process.env.BGA_DOM_SHIM)).installDocument;
_installDocument();
const app = await import("./tests/viewer.mjs");
const text = (n) => !n ? "" : (n._text ?? "") + (n.children ?? []).map(text).join("");
console.log(JSON.stringify(text(app.renderSection("agent_sizing", JSON.parse(process.env.CARD), {}, undefined, null, {}, {}))));
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
@pytest.mark.parametrize("ceiling,said", [(8, "no knee within 8"), (6, "the graph allows 6")])
def test_the_sizing_card_says_no_knee_at_the_top(ceiling, said):
    card = {"builders": {"recommended": 4, "graph_ceiling": ceiling, "swept_to": 8, "observed": 4}}
    done = subprocess.run(
        [shutil.which("node"), "--input-type=module", "-e", _PROBE],
        capture_output=True,
        text=True,
        cwd=REPO,
        timeout=60,
        env=dict(os.environ, BGA_DOM_SHIM=str(REPO / "tests" / "dom_shim.mjs"), CARD=json.dumps(card)),
    )
    assert done.returncode == 0, done.stderr[-3000:]
    assert said in json.loads(done.stdout), done.stdout
