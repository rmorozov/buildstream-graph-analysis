"""UX-1273: the ready queue counts work ready with a builder free, so its
heading and gloss say so, and none of it reads as the backlog behind full builders."""

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
FREE = "builder free"
BACKLOG = ("capacity bound", "nowhere to run", "waiting to start")

_READ = r"""
(() => {
  const s = document.getElementById('ready_queue');
  if (!s) return null;
  const gloss = s.querySelector('[data-describes="nonzero_fraction"]');
  return { heading: s.querySelector('h1,h2,h3,h4')?.textContent ?? '',
           gloss: gloss?.textContent ?? '', text: s.textContent };
})()
"""


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
def test_the_ready_queue_names_a_free_builder(page, width):
    with Browser(chrome) as opened:
        read = opened.measure(page, _READ, width=width, height=900 if width > 400 else 844)
    assert read, "no #ready_queue on the page"
    assert FREE in read["heading"], read["heading"]
    assert "full builder" in read["gloss"] and "resource wait" in read["gloss"], read["gloss"]
    said = [phrase for phrase in BACKLOG if phrase in read["text"].lower()]
    assert not said, f"#ready_queue reads as the backlog behind full builders: {said}"
