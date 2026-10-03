"""UX-1150: a boolean group reads as one verdict sentence, and absence has one word.

`#capacity_verdict` answered "Was the capacity right?" with "Oversubscribed
false / Undersubscribed false / Checks ran true"; other pairs read "true" or
"false", and absence read "—" in some places and "none" in others.

Styleguide §6e rule 12.
"""

import functools
import pathlib
import shutil
import sys
from types import SimpleNamespace

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga.analyzer import BuildEfficiencyAnalyzer
from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

_BUILD = {
    "two_plane": functools.partial(pages.two_plane_run, shape=("--layers", "8", "--width", "14"), name="two_plane"),
}
#: The words a value cell may not be on its own.
REFUSED = ("true", "false", "—")

_READ = r"""
(() => {
  document.querySelectorAll("article.finding").forEach((a) => a._hydrate?.());
  const value = (cell) => {
    const c = cell.cloneNode(true);
    c.querySelectorAll('button, [data-role="description"], .run-advice').forEach((n) => n.remove());
    return c.textContent.trim();
  };
  const where = (cell) => cell.closest("article[id]")?.id ?? cell.closest("[data-section]")?.dataset.section;
  const cells = [...document.querySelectorAll("dd, td")].map((cell) => [where(cell), cell.tagName, value(cell)]);
  const verdict = document.querySelector('[data-section="capacity_verdict"]');
  const label = (dt) => { const c = dt.cloneNode(true); c.querySelectorAll("button").forEach((b) => b.remove()); return c.textContent.trim(); };
  return {
    cells,
    lead: verdict?.children[1]?.matches("p.section-lead") ? verdict.children[1].textContent : null,
    terms: verdict ? [...verdict.querySelectorAll("dt")].map(label) : null,
  };
})()
"""


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module")
def read(browser, tmp_path_factory):
    root = tmp_path_factory.mktemp("boolean-verdict")
    uris = {label: pages.export_uri(pages.FIXTURES[label], root / label, f"{label}.html") for label in pages.FIXTURES}
    for label, make in _BUILD.items():
        into = root / label
        uris[label] = pages.in_place_uri(make(into), into, f"{label}.html")
    got = {(label, 1440): browser.measure(uri, _READ, 1440, 900) for label, uri in uris.items()}
    got[("two_plane", 390)] = browser.measure(uris["two_plane"], _READ, 390, 844)
    yield got
    shutil.rmtree(root, ignore_errors=True)


PAGES = [("two_plane", 1440), ("two_plane", 390), ("golden", 1440), ("macro_micro", 1440)]


@needs_browser
@pytest.mark.parametrize("label,width", PAGES)
def test_no_value_cell_reads_a_boolean_or_a_dash(read, label, width):
    cells = read[(label, width)]["cells"]
    assert len(cells) > 50, f"{label}: only {len(cells)} cells - the read is measuring nothing"
    raw = [tuple(cell) for cell in cells if cell[2] in REFUSED]
    bad = sorted(set(raw))
    assert bad == [], f"{label} @{width}: {len(raw)} cells, {len(bad)} distinct: {bad[:12]}"


@needs_browser
@pytest.mark.parametrize("label,width", PAGES)
def test_the_capacity_verdict_is_a_sentence(read, label, width):
    got = read[(label, width)]
    assert got["lead"], f"{label} @{width}: #capacity_verdict does not open with a sentence"
    drawn = {"Oversubscribed", "Undersubscribed", "Checks ran"} & set(got["terms"])
    assert drawn == set(), f"{label} @{width}: the booleans the sentence answers are drawn again: {drawn}"


def _verdict(violations=(), skipped=()):
    holder = SimpleNamespace(
        violations=[{"type": kind} for kind in violations], capacity_check_skipped_inputs=list(skipped)
    )
    return BuildEfficiencyAnalyzer._build_capacity_verdict(holder)["verdict"]


def test_each_state_has_its_own_sentence():
    matched = _verdict()
    assert matched.startswith("Capacity matched demand"), matched
    over = _verdict(["resource_oversubscription"])
    assert over.startswith("Oversubscribed"), over
    under = _verdict(["resource_undersubscription"])
    assert under.startswith("Undersubscribed"), under
    skipped = _verdict(skipped=["native_max_jobs"])
    assert "did not run" in skipped and "--max-jobs value" in skipped, skipped
    assert len({matched, over, under, skipped}) == 4
