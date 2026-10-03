"""UX-1154: under print media every `details` is open, no control shows, and a next command wraps.

Paper has no click: a closed fold printed as its 24 px summary, 382 controls
printed as dead buttons, and a next command was cut at the right edge.
`.fold-more` stays - it is the count of the rows the page does not print.

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
WIDTHS = ((1440, 900), (390, 844))

_READ = r"""
(() => {
  const shown = (e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const name = (e) => `${e.tagName.toLowerCase()}.${e.className} ${(e.textContent || "").trim().slice(0, 30)}`;
  const closed = [...document.querySelectorAll("details:not([open])")].filter(shown);
  return {
    closed: closed.length,
    short: closed.filter((d) => d.getBoundingClientRect().height < 40).map((d) => name(d.querySelector("summary"))),
    controls: [...document.querySelectorAll("button:not(.fold-more), input, select")].filter(shown).map(name),
    commands: document.querySelectorAll("code.next-command").length,
    clipped: [...document.querySelectorAll("code.next-command")].filter((c) => shown(c) && c.scrollWidth > c.clientWidth + 1)
      .map((c) => `${c.scrollWidth}>${c.clientWidth} ${c.textContent.slice(0, 40)}`),
  };
})()
"""


@pytest.fixture(scope="module")
def printed(tmp_path_factory):
    root = tmp_path_factory.mktemp("print-folds")
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


@needs_browser
class TestPrintOpensEveryFoldAndDropsItsControls:
    @pytest.mark.parametrize("case", CASES, ids=[f"{label}-{w}" for label, w in CASES])
    def test_no_closed_fold_prints_as_its_summary_alone(self, printed, case):
        out = printed[case]
        assert not out["short"], (
            f"{case}: {len(out['short'])} of {out['closed']} closed details print under 40 px: {out['short'][:5]}"
        )

    @pytest.mark.parametrize("case", CASES, ids=[f"{label}-{w}" for label, w in CASES])
    def test_no_control_prints(self, printed, case):
        out = printed[case]
        assert not out["controls"], f"{case}: {len(out['controls'])} controls print: {out['controls'][:5]}"

    @pytest.mark.parametrize("case", CASES, ids=[f"{label}-{w}" for label, w in CASES])
    def test_a_next_command_wraps_rather_than_clips(self, printed, case):
        out = printed[case]
        assert not out["clipped"], f"{case}: next commands clipped in print: {out['clipped']}"

    def test_the_two_plane_page_has_what_the_claims_are_about(self, printed):
        """The three claims above are empty on a page with no fold and no command."""
        for w, _ in WIDTHS:
            out = printed[("two_plane", w)]
            assert out["closed"] >= 40 and out["commands"] >= 5, out
