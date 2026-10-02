"""UX-1273: the ready queue says which ready work it counted - with a builder free
when builder slots were recorded, every dependency-ready task when not - and none
of it reads as the backlog behind full builders."""

import dataclasses
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

#: The 2,402-element two-plane page the walk read 1.0% queued beside 43.7 min of resource wait.
PAGE_SHAPE = ("--layers", "40", "--width", "60", "--workload", "binaries")
BACKLOG = ("capacity bound", "nowhere to run", "waiting to start")
GOLDEN = REPO / "tests/fixtures/golden/mixed_task_kinds"

_READ = r"""
(() => {
  const s = document.getElementById('ready_queue');
  if (!s) return null;
  const dd = s.querySelector('dt[data-key="counts"] + dd');
  return { heading: s.querySelector('h1,h2,h3,h4')?.textContent ?? '',
           counts: dd?.querySelector('[data-raw]')?.textContent ?? '',
           gloss: dd?.querySelector('[data-describes="counts"]')?.textContent ?? '',
           text: s.textContent };
})()
"""


def _ready_queue(capacities):
    from bga.analyzer import BuildEfficiencyAnalyzer
    from bga.report.json import build_document

    analyzer = BuildEfficiencyAnalyzer()
    analyzer.load(GOLDEN)
    if capacities is not None:
        analyzer.run_context = dataclasses.replace(analyzer.run_context, resource_capacities=capacities)
    return build_document(analyzer.analyze())["ready_queue"]


def test_the_payload_says_which_ready_work_it_counted():
    assert _ready_queue(None)["counts"] == "builder_free"
    assert _ready_queue({})["counts"] == "dependency_ready"


@pytest.fixture(scope="module")
def page(tmp_path_factory):
    import tools.bga_view as view

    tmp = tmp_path_factory.mktemp("ready-queue")
    run = pages.two_plane_run(tmp, shape=PAGE_SHAPE, runs=2)
    out = tmp / "report.html"
    view.export(str(run), str(out))
    return out.as_uri()


@needs_browser
@pytest.mark.parametrize("width", [1440, 390])
def test_the_ready_queue_names_what_it_counted(page, width):
    with Browser(chrome) as opened:
        read = opened.measure(page, _READ, width=width, height=900 if width > 400 else 844)
    assert read, "no #ready_queue on the page"
    assert "builder free" not in read["heading"], f"the heading claims one path: {read['heading']}"
    assert read["counts"] == "Ready with a builder free", read["counts"]
    for path in ("builder free", "full builder", "dependency-ready"):
        assert path in read["gloss"], (path, read["gloss"])
    said = [phrase for phrase in BACKLOG if phrase in read["text"].lower()]
    assert not said, f"#ready_queue reads as the backlog behind full builders: {said}"
