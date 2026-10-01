"""UX-1257: the compare chapter leads with the wall delta and its band verdict.

`compare/v2` publishes `total_duration_delta_share`; `compareLead` in
`chapters.js` is the one sentence, drawn as the chapter's lead and in the
decision panel. A single snapshot has no chapter and one absence sentence.
"""

import pathlib
import re
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

ABSENT = "No earlier run to compare against."
LEAD = re.compile(r"^[+-]?\d+\.\d% \([^)]+ (faster|slower)\) than the run before, (inside|outside) the noise band")

_MEASURE = r"""
(() => {
  const text = (q) => [...document.querySelectorAll(q)].map((n) => n.textContent.trim());
  return {
    chapter: !!document.querySelector("#chapter-compare"),
    lead: text('[data-chapter-answer="compare"]'),
    panel: text('#decision [data-role="compare-lead"]'),
    absent: document.body.innerText.split(%r).length - 1,
  };
})()
""".replace("%r", repr(ABSENT))


def _page(tmp_path_factory, runs):
    into = tmp_path_factory.mktemp(f"u1257-{runs}")
    import tools.bga_view as view

    run = pages.two_plane_run(into, ("--layers", "8", "--width", "14"), runs=runs)
    # In place, not `export_uri`: its copy leaves the store behind, and with it the run before.
    view.export(str(run), str(into / "report.html"))
    with Browser(chrome) as opened:
        return opened.measure((into / "report.html").as_uri(), _MEASURE)


@needs_browser
def test_the_lead_is_the_delta_and_the_panel_says_it_too(tmp_path_factory):
    page = _page(tmp_path_factory, 2)
    assert page["chapter"] and len(page["lead"]) == 1, page
    assert LEAD.match(page["lead"][0]), page
    assert page["panel"] == page["lead"] and page["absent"] == 0, page


@needs_browser
def test_one_snapshot_reads_one_absence_sentence(tmp_path_factory):
    page = _page(tmp_path_factory, 1)
    assert page == {"chapter": False, "lead": [], "panel": [ABSENT], "absent": 1}, page


def test_compare_publishes_the_delta_as_a_share_of_the_baseline():
    from bga.compare import _delta_share

    assert _delta_share({"total_duration_us": 2_000_000}, {"total_duration_us": -50_000}) == -0.025
    assert _delta_share({"total_duration_us": None}, {"total_duration_us": -50_000}) is None
