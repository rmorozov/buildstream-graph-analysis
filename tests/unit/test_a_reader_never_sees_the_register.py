"""UX-824 (styleguide §4g): a reader never sees the register.

Boots the golden export and the 1,202-element scale export
(`tests.pages.scale_run`), every `.description[hidden]` door,
`data-collapsed` section and `data-open` chapter forced open and
`content-visibility` lifted first - the expression `UX-826`'s track
left in its scratchpad, reused here so the fold state a real reader
never sees stops hiding a citation from `innerText` too. Covers items
1-4 of §4g's list; item 5 is `UX-823`'s (an offset's origin) and item
6 is guarded by the superlative and label sections - both skipped
here, not silently narrowed.

Measured on both exports before this guard existed: 0 task ids, 0
`span.section-key`, 0 pipe-delimited cells, one `dt` reading
"Schema?" - the document's own `bga:version` field name, labelling
itself rather than the producer's jargon leaking into a sentence, so
item 4 narrows around that one `data-key="schema"` term rather than
the word `schema` outright.
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

#: Every real UI door forced open - never the JSON door, never a
#: `<script>`, which `innerText` never shows a reader anyway.
_OPEN_AND_READ = r"""
(() => {
  document.querySelectorAll('.description[hidden]').forEach(n => { n.hidden = false; });
  document.querySelectorAll('section[data-section][data-collapsed]').forEach(
    n => n.setAttribute('data-collapsed', 'false'));
  document.querySelectorAll('section.chapter[data-open]').forEach(
    n => n.setAttribute('data-open', 'true'));
  document.querySelectorAll('section.chapter > section[data-section]')
    .forEach(n => { n.style.contentVisibility = 'visible'; });
  const strip = (el) => {
    const clone = el.cloneNode(true);
    clone.querySelectorAll('code').forEach(c => c.remove());
    return clone.textContent;
  };
  return {
    innerText: document.body.innerText,
    sectionKeySpans: document.querySelectorAll('span.section-key').length,
    headings: [...document.querySelectorAll('h2, h3')].map((h) => h.textContent.trim()),
    cells: [...document.querySelectorAll('p, li, td, dt, dd, h2')].map((el) => ({
      tag: el.tagName, key: el.getAttribute('data-key'), text: strip(el).trim(),
    })),
    sectionsCount: document.querySelectorAll('section[data-section]').length,
    headingsCount: document.querySelectorAll('h2, h3').length,
    cellsCount: document.querySelectorAll('td').length,
  };
})()
"""

_TASK_ID = re.compile(r"\bUX-\d+\b")
_SNAKE_HEADING = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)+$")
_PIPE_KEY = re.compile(r"\|(FETCH|BUILD|PULL|PUSH|TRACK)\|")
_REGISTER_WORD = re.compile(r"\b(payload|contract|schema)\b|Part \d", re.IGNORECASE)


def _run(into, label):
    if label == "golden":
        return pages.export_uri(pages.FIXTURES["golden"], into)
    return pages.export_uri(pages.scale_run(into / "run"), into)


@pytest.fixture(scope="module", params=["golden", "scale"])
def measured(request, tmp_path_factory):
    tmp = tmp_path_factory.mktemp(f"reader-facing-{request.param}")
    uri = _run(tmp, request.param)
    with Browser(chrome) as opened:
        result = opened.measure(uri, _OPEN_AND_READ)
    result["label"] = request.param
    return result


@needs_browser
class TestAReaderNeverSeesTheRegister:
    def test_the_page_has_sections_headings_and_cells(self, measured):
        assert measured["sectionsCount"] > 0, measured["label"]
        assert measured["headingsCount"] > 0, measured["label"]
        assert measured["cellsCount"] > 0, measured["label"]

    def test_item_1_no_task_id(self, measured):
        ids = _TASK_ID.findall(measured["innerText"])
        assert ids == [], (measured["label"], ids)

    def test_item_2_no_section_key_and_no_snake_case_heading(self, measured):
        assert measured["sectionKeySpans"] == 0, measured["label"]
        headings = measured["headings"]
        assert headings, measured["label"]
        bad = [h for h in headings if _SNAKE_HEADING.match(h)]
        assert bad == [], (measured["label"], bad)

    def test_item_3_no_pipe_delimited_task_key_in_a_cell(self, measured):
        # Widened from `td` alone: `duration_resolution.tasks`
        # (`KEYED_BY_TASK_UID`) renders as a `<dd><span>` list, not a
        # table, so a `td`-only scan passed with the join key intact
        # (verifier finding). Item 4's cell set catches both shapes.
        cells = measured["cells"]
        assert cells, measured["label"]
        bad = [c["text"] for c in cells if _PIPE_KEY.search(c["text"])]
        assert bad == [], (measured["label"], bad)

    def test_item_4_no_register_word_outside_the_schema_version_term(self, measured):
        cells = measured["cells"]
        assert cells, measured["label"]
        bad = [c for c in cells
              if _REGISTER_WORD.search(c["text"])
              and not (c["tag"] == "DT" and c["key"] == "schema")]
        assert bad == [], (measured["label"], bad)
