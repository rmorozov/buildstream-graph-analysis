"""UX-1161: under print media nothing passes the sheet, no label or fold marker prints without its control, and nothing held back goes uncounted.

Every description prints (paper has no `?`), and every count of held-back rows
that the screen shows is still on paper.

Styleguide §2b.
"""

import functools
import pathlib
import shutil
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

_BUILD = {
    "two_plane": functools.partial(pages.two_plane_run, shape=("--layers", "8", "--width", "14"), name="two_plane"),
}
#: A4 at 96 dpi, and the compact viewport.
WIDTHS = ((794, 1123), (390, 844))

_READ = r"""
(() => {
  const W = document.documentElement.clientWidth;
  const shown = (e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const name = (e) => `${e.tagName.toLowerCase()}.${e.className} ${(e.textContent || "").trim().slice(0, 30)}`;
  const all = [...document.querySelectorAll("body *")].filter(shown);
  const over = all.filter((e) => e.getBoundingClientRect().right > W + 1);
  const clip = all.filter((e) => /auto|scroll|hidden|clip/.test(getComputedStyle(e).overflowX) && e.scrollWidth > e.clientWidth + 1);
  const summaries = [...document.querySelectorAll("summary")].filter(shown);
  const descriptions = [...document.querySelectorAll(".description")].filter((d) => shown(d.parentElement));
  const counts = [...document.querySelectorAll("[data-folded], .badge, [data-role=card-bound]")]
    .filter((e) => !e.closest("[hidden]:not([hidden=until-found])") && /\d/.test(e.getAttribute("data-folded") ?? e.textContent));
  return {
    over: over.filter((e) => !over.some((o) => o !== e && e.contains(o))).map((e) => `${Math.round(e.getBoundingClientRect().right)}>${W} ${name(e)}`),
    clipped: clip.map((e) => `${e.scrollWidth}>${e.clientWidth} ${name(e)}`),
    labels: [...document.querySelectorAll("label")].filter(shown).filter((l) => !l.control || !shown(l.control)).map(name),
    summaries: summaries.length,
    markers: summaries.filter((s) => /[▸▾]/.test(getComputedStyle(s, "::before").content)).map(name),
    descriptions: descriptions.length,
    unprinted: descriptions.filter((d) => !shown(d)).map(name),
    counts: counts.length,
    uncounted: counts.filter((e) => !shown(e)).map(name),
  };
})()
"""


@pytest.fixture(scope="module")
def printed(tmp_path_factory):
    root = tmp_path_factory.mktemp("print-residue")
    uris = {label: pages.export_uri(pages.FIXTURES[label], root / label, f"{label}.html") for label in pages.FIXTURES}
    for label, make in _BUILD.items():
        into = root / label
        uris[label] = pages.in_place_uri(make(into), into, f"{label}.html")
    with Browser(chrome) as browser:
        got = {
            (label, w): browser.measure(uri, _READ, w, h, media="print")
            for label, uri in uris.items()
            for w, h in WIDTHS
        }
    yield got
    shutil.rmtree(root, ignore_errors=True)


CASES = [(label, w) for label in (*pages.FIXTURES, *_BUILD) for w, _ in WIDTHS]
IDS = [f"{label}-{w}" for label, w in CASES]


@needs_browser
class TestPrintFitsTheSheetAndPrintsNoDeadApparatus:
    @pytest.mark.parametrize("case", CASES, ids=IDS)
    def test_nothing_passes_the_right_edge_of_the_sheet(self, printed, case):
        out = printed[case]
        assert not out["over"] and not out["clipped"], (
            f"{case}: {len(out['over'])} past the sheet {out['over'][:4]}, {len(out['clipped'])} clipped {out['clipped'][:3]}"
        )

    @pytest.mark.parametrize("case", CASES, ids=IDS)
    def test_no_label_prints_without_its_control(self, printed, case):
        out = printed[case]
        assert not out["labels"], f"{case}: {len(out['labels'])} labels print alone: {out['labels'][:5]}"

    @pytest.mark.parametrize("case", CASES, ids=IDS)
    def test_no_fold_marker_prints_over_open_content(self, printed, case):
        out = printed[case]
        assert not out["markers"], f"{case}: {len(out['markers'])} of {out['summaries']} summaries print a fold marker"

    @pytest.mark.parametrize("case", CASES, ids=IDS)
    def test_every_description_reaches_paper(self, printed, case):
        out = printed[case]
        assert not out["unprinted"], f"{case}: {len(out['unprinted'])} of {out['descriptions']} descriptions unprinted"

    @pytest.mark.parametrize("case", CASES, ids=IDS)
    def test_every_count_of_held_back_rows_prints(self, printed, case):
        out = printed[case]
        assert not out["uncounted"], f"{case}: held-back counts unprinted: {out['uncounted']}"

    def test_the_two_plane_page_has_what_the_claims_are_about(self, printed):
        """The five claims above are empty on a page with no summary, description or count."""
        for w, _ in WIDTHS:
            out = printed[("two_plane", w)]
            assert out["summaries"] >= 40 and out["descriptions"] >= 100 and out["counts"] >= 2, out
