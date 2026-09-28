"""UX-1044 (styleguide §3l, §6e.13): a chapter's fold sits at one place
and says the same thing in the rail and the document.

Both controls carry `▸`/`▾`, the count and the chapter's title in their
accessible name; each glyph follows its own control (the document fold's
`data-open`, the rail row's `data-current`, `UX-1046`). The document
control's offset in `h2.chapter-title` is held with `UX-1042`'s
placement rule: dx from either edge and dy each spread by at most 24 px.
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

#: `UX-1042`'s placement tolerance, px.
SPREAD = 24
#: How far the control's right edge may sit from its head's, px.
EDGE = 2
VIEWPORTS = [(1440, 900), (390, 844)]

_READ = r"""
(async () => {
  const settle = (n) => new Promise((r) => {
    let i = 0;
    const step = () => (++i >= n ? r() : requestAnimationFrame(step));
    requestAnimationFrame(step);
  });
  const name = (b) => b.getAttribute("aria-label") || b.textContent;
  const read = () => [...document.querySelectorAll("button.chapter-open")].map((b) => {
    const id = b.getAttribute("data-chapter-open");
    const box = b.closest("section.chapter");
    const head = b.closest("h2.chapter-title").getBoundingClientRect();
    const r = b.getBoundingClientRect();
    const rail = document.querySelector(`nav.toc [data-toc-chapter="${id}"]`);
    return {
      id, title: box.getAttribute("aria-label"),
      open: box.getAttribute("data-open") === "true",
      doc: b.textContent, docName: name(b),
      rail: rail.textContent, railName: name(rail),
      railCurrent: rail.closest("li[data-chapter]").hasAttribute("data-current"),
      dxl: r.left - head.left, dxr: head.right - r.right, dy: r.top - head.top,
    };
  });
  const folded = read();
  for (const b of document.querySelectorAll("button.chapter-open")) b.click();
  await settle(10);
  const opened = read();
  const rows = [...document.querySelectorAll("nav.toc [data-toc-chapter]")];
  rows[rows.length - 1].click();
  await settle(30);
  return { folded, opened, pressed: read() };
})()
"""


@pytest.fixture(scope="module", params=VIEWPORTS, ids=lambda v: f"{v[0]}x{v[1]}")
def measured(request, tmp_path_factory):
    uri = pages.export_uri(pages.FIXTURES["macro_micro"],
                           tmp_path_factory.mktemp("u1044"))
    with Browser(chrome) as opened:
        return opened.measure(uri, _READ, *request.param)


def _glyph(label):
    return label.split(" ", 1)[0]


def _count(label):
    return [word for word in label.replace("·", " ").split() if word.isdigit()]


@needs_browser
class TestBothControlsSayOneThing:
    def test_each_glyph_follows_its_own_disclosure(self, measured):
        for state in ("folded", "opened", "pressed"):
            for row in measured[state]:
                assert _glyph(row["doc"]) == ("▾" if row["open"] else "▸"), (state, row)
                assert _glyph(row["rail"]) == ("▾" if row["railCurrent"] else "▸"), (
                    state, row)
        assert any(row["railCurrent"] for row in measured["pressed"]), measured["pressed"]

    def test_both_controls_carry_the_same_count(self, measured):
        for state in ("folded", "opened"):
            for row in measured[state]:
                assert _count(row["doc"]) and _count(row["doc"]) == _count(row["rail"]), (
                    state, row)

    def test_each_accessible_name_holds_the_chapter_title(self, measured):
        rows = measured["folded"] + measured["opened"]
        assert rows, measured
        for row in rows:
            assert row["title"] in row["docName"], row
            assert row["title"] in row["railName"], row


@needs_browser
class TestTheDocumentFoldSitsAtOnePlace:
    def test_the_offset_in_the_chapter_head_spreads_at_most_24_px(self, measured):
        rows = measured["opened"]
        assert len(rows) > 1, rows

        def spread(key):
            return max(row[key] for row in rows) - min(row[key] for row in rows)

        assert min(spread("dxl"), spread("dxr")) <= SPREAD, [
            (row["id"], round(row["dxl"]), round(row["dxr"])) for row in rows]
        assert spread("dy") <= SPREAD, [(row["id"], round(row["dy"])) for row in rows]

    def test_the_control_ends_at_the_chapter_heads_right_edge(self, measured):
        """At every width: 390 wraps each title, so a spread alone could
        pass a control that merely trails a long title."""
        rows = measured["folded"] + measured["opened"]
        assert rows, measured
        off = [(row["id"], round(row["dxr"], 1)) for row in rows
               if abs(row["dxr"]) > EDGE]
        assert off == [], off


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
