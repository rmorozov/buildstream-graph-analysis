"""UX-1025 (styleguide §6e.13): one disclosure glyph pair.

Measured on `main` at `98ab850`, booted: `▾` on the boxed section-fold
button (`nav.js`), the browser's own `▶`/`▼` marker on every `<details>`
- two glyphs for one idea. `style.css` now draws `▸`/`▾` on `summary`
too, matching state; `renderProvenance`'s unlabeled folds (`decision.js`)
said "1 level, N rows" alone, which `test_the_fold_says_how_deep_it_goes.py`
already guards at the data level (`data-levels`/`data-rows`) - this
file is the rendered-label half.
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

_DEPTH_COUNT_ALONE = re.compile(r"^\d+ levels?, \d+ rows?$")

#: Force every `<details>` open once, so the guard sees both glyphs -
#: never the JSON door, which is not this rule's disclosure.
_MEASURE = r"""
(() => {
  const rows = [];
  for (const d of document.querySelectorAll("details:not(.raw-json)")) {
    const summary = d.querySelector(":scope > summary");
    if (!summary) continue;
    const before = getComputedStyle(summary, "::before").content;
    rows.push({ open: d.open, before,
                text: (summary.textContent || "").replace(/\s+/g, " ").trim() });
    d.open = !d.open;
    const after = getComputedStyle(summary, "::before").content;
    rows[rows.length - 1].beforeToggled = after;
  }
  return rows;
})()
"""


@pytest.fixture(scope="module", params=["golden", "macro_micro"])
def measured(request, tmp_path_factory):
    uri = pages.export_uri(pages.FIXTURES[request.param], tmp_path_factory.mktemp(f"u1025-{request.param}"))
    with Browser(chrome) as opened:
        rows = opened.measure(uri, _MEASURE)
    return {"label": request.param, "rows": rows}


@needs_browser
class TestOneDisclosureGlyphPair:
    def test_every_disclosure_starts_with_the_matching_glyph(self, measured):
        rows = measured["rows"]
        assert rows, measured["label"]
        for row in rows:
            closed_glyph, open_glyph = row["before"], row["beforeToggled"]
            if row["open"]:
                open_glyph, closed_glyph = closed_glyph, open_glyph
            assert "25b8" in closed_glyph.encode("unicode_escape").decode() or "▸" in closed_glyph, (
                measured["label"],
                row,
            )
            assert "25be" in open_glyph.encode("unicode_escape").decode() or "▾" in open_glyph, (measured["label"], row)

    def test_no_label_is_depth_and_count_alone(self, measured):
        bad = [row["text"] for row in measured["rows"] if _DEPTH_COUNT_ALONE.match(row["text"])]
        assert bad == [], (measured["label"], bad)
