"""UX-1153: the view review's L1-L6, each measured absent on the booted page.

L1 the h1 is not cut while the header has room; L2 the rail's key hint is
keys, not a checkbox, and a disabled "Sections" wears no control's border;
L3 no numeric header or description is monospace; L4 a command is one line;
L5 an overview value sits near its label; L6 no strip draws one value as a
comparison or clips a mark, and a decomposition keeps its labels inside its
axis and its sentences capitalised.
"""

import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

#: L5: the review caps the bar at about 480 px; the gap adds two grid gaps and the
#: value's 96 px right-aligned column. Measured 761-777 before, 537-553 after.
LABEL_TO_VALUE_PX = 600

_MEASURE = (
    pages.FULL_LAYOUT_JS
    + r"""
(() => {
  for (const box of document.querySelectorAll("section.chapter")) box.setAttribute("data-open", "true");
  const shown = (node) => { const r = node.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const sans = getComputedStyle(document.documentElement).fontFamily;
  const out = {};
  const h1 = document.getElementById("run-name");
  out.h1 = { scroll: h1.scrollWidth, client: h1.clientWidth, text: h1.textContent };
  const keys = document.querySelector(".toc-keys");
  out.keys = keys ? { text: keys.textContent, kbd: keys.querySelectorAll("kbd").length } : null;
  const title = document.querySelector("button.toc-title");
  out.title = title ? { disabled: title.disabled, border: getComputedStyle(title).borderTopColor } : null;
  out.mono = [...document.querySelectorAll("th.num, .num .description")]
    .filter(shown).filter((node) => getComputedStyle(node).fontFamily !== sans)
    .map((node) => node.textContent.trim().slice(0, 40));
  out.commands = [...document.querySelectorAll("code.next-command")].filter(shown).map((code) => {
    const lines = code.getClientRects().length;
    const style = getComputedStyle(code);
    const line = parseFloat(style.lineHeight) || parseFloat(style.fontSize) * 1.4;
    // clientHeight: a scrolling one-line box's scrollbar is not a second line.
    return { lines, tall: code.clientHeight > line * 1.6, text: code.textContent.slice(0, 50) };
  }).filter((one) => one.lines !== 1 || one.tall);
  out.overview = [...document.querySelectorAll("#overview .wf-row")].filter(shown).map((row) => {
    const label = row.querySelector(".wf-label").getBoundingClientRect();
    const value = row.querySelector(".wf-value");
    const range = document.createRange();
    range.selectNodeContents(value);
    return Math.round(range.getBoundingClientRect().left - label.right);
  });
  out.intervals = [...document.querySelectorAll(".interval[data-drawn='true']")].map((wrap) => {
    const values = [...wrap.querySelectorAll("table[data-role='drawing-twin'] tbody tr td:last-child")]
      .map((td) => td.textContent);
    const box = wrap.querySelector("svg").getBoundingClientRect();
    const clipped = [...wrap.querySelectorAll("svg circle")].filter((mark) => {
      const r = mark.getBoundingClientRect();
      return r.left < box.left - 0.5 || r.right > box.right + 0.5;
    }).length;
    return { distinct: new Set(values).size, clipped };
  });
  out.ticks = [];
  for (const axis of document.querySelectorAll(".decomposition .draw-axis")) {
    if (!shown(axis)) continue;
    const box = axis.getBoundingClientRect();
    for (const tick of axis.querySelectorAll(".draw-tick")) {
      const r = tick.getBoundingClientRect();
      if (r.left < box.left - 0.5 || r.right > box.right + 0.5) {
        out.ticks.push([tick.textContent, Math.round(r.left - box.left), Math.round(box.right - r.right)]);
      }
    }
  }
  out.sentences = [...document.querySelectorAll(".decomposition .density-sentence")]
    .map((node) => node.textContent).filter((text) => /\.\s+[a-z]/.test(text));
  return out;
})()
"""
)


def _two_plane(into):
    import tools.bga_view as view

    run = pages.two_plane_run(into, ("--layers", "8", "--width", "14"))
    page = pathlib.Path(into) / "report.html"
    view.export(str(run), str(page))
    return page.as_uri()


@pytest.fixture(scope="module", params=["two_plane", "golden", "macro_micro"])
def uri(request, tmp_path_factory):
    into = tmp_path_factory.mktemp(f"u1153-{request.param}")
    if request.param == "two_plane":
        return request.param, _two_plane(into)
    return request.param, pages.export_uri(pages.FIXTURES[request.param], into)


@pytest.fixture(scope="module")
def measured(uri):
    label, address = uri
    with Browser(chrome) as opened:
        wide = opened.measure(address, _MEASURE, width=1440, height=900)
        narrow = opened.measure(address, _MEASURE, width=390, height=844)
    return {"label": label, 1440: wide, 390: narrow}


@needs_browser
class TestTheSixLowDefectsStayFixed:
    def test_l1_the_run_name_is_whole_where_the_header_has_room(self, measured):
        h1 = measured[1440]["h1"]
        assert h1["scroll"] <= h1["client"] + 1, (measured["label"], h1)

    def test_l2_the_key_hint_is_keys_not_a_checkbox(self, measured):
        keys = measured[1440]["keys"]
        assert keys and keys["kbd"] == 2 and "[ ]" not in keys["text"], keys

    def test_l2_a_rail_title_that_cannot_fold_wears_no_border(self, measured):
        title = measured[1440]["title"]
        assert title and title["disabled"], title
        assert title["border"] == "rgba(0, 0, 0, 0)", title

    @pytest.mark.parametrize("width", [1440, 390])
    def test_l3_no_numeric_header_or_description_is_monospace(self, measured, width):
        assert measured[width]["mono"] == [], (measured["label"], width, measured[width]["mono"][:5])

    @pytest.mark.parametrize("width", [1440, 390])
    def test_l4_a_command_is_one_line(self, measured, width):
        assert measured[width]["commands"] == [], (measured["label"], width, measured[width]["commands"][:3])

    def test_l5_an_overview_value_sits_near_its_label(self, measured):
        gaps = measured[1440]["overview"]
        assert gaps and max(gaps) <= LABEL_TO_VALUE_PX, (measured["label"], gaps)

    def test_l6_a_strip_compares_at_least_two_values_and_clips_no_mark(self, measured):
        bad = [one for one in measured[1440]["intervals"] if one["distinct"] < 2 or one["clipped"]]
        assert bad == [], (measured["label"], measured[1440]["intervals"])

    @pytest.mark.parametrize("width", [1440, 390])
    def test_l6_a_decomposition_keeps_its_labels_inside_its_axis(self, measured, width):
        assert measured[width]["ticks"] == [], (measured["label"], width, measured[width]["ticks"])

    def test_l6_a_decomposition_sentence_starts_each_sentence_capitalised(self, measured):
        assert measured[1440]["sentences"] == [], (measured["label"], measured[1440]["sentences"])
