"""UX-667 (styleguide §3h): the rail is a source list.

Round 90's design review measured `nav.toc` on a two-plane capture: 82
entries, a flat `<ul>` per chapter, 0 disclosure elements, 16 of 82
visible without scrolling, and `scrollspy`'s mark set `aria-current`
while `rail.scrollTop` stayed 0 - marking, never revealing. The fix is
disclosure by chapter, sharing the document's own fold, plus a scroll
that follows the mark.
"""
import pathlib
import re
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import pages
from browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

FIXTURE = pages.FIXTURES["macro_micro"]


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module")
def uri(tmp_path_factory):
    into = tmp_path_factory.mktemp("u667")
    return pages.export_uri(FIXTURE, into)


#: At landing: every chapter has a row, and only the open (first)
#: chapter's section links have a laid-out rect.
_LANDING = r"""
(() => {
  const nav = document.querySelector("nav.toc");
  const rows = [...nav.querySelectorAll("li[data-chapter]")];
  const links = [...nav.querySelectorAll("a[data-toc]")];
  const laid = (n) => {
    const r = n.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };
  const visible = links.filter(laid);
  const openRows = rows.filter((r) => r.getAttribute("data-open") === "true");
  return {
    rows: rows.length,
    links: links.length,
    visible: visible.length,
    openRows: openRows.map((r) => r.getAttribute("data-chapter")),
    visibleOutsideOpen: visible.filter((a) => {
      const row = a.closest("li[data-chapter]");
      return row?.getAttribute("data-open") !== "true";
    }).length,
  };
})()
"""

#: Click every rail link in turn (a fresh page, not a fresh load per
#: link - the mark and the rail's own scroll are cumulative state, and
#: this claim is about the rail keeping up with the reader moving
#: through the whole document, not about any one landing).
_WALK = r"""
(async () => {
  const settle = (n) => new Promise((r) => {
    let i = 0;
    const step = () => (++i >= n ? r() : requestAnimationFrame(step));
    requestAnimationFrame(step);
  });
  const nav = document.querySelector("nav.toc");
  const links = [...nav.querySelectorAll("a[data-toc]")];
  const out = [];
  for (const link of links) {
    link.click();
    await settle(8);
    const mark = nav.querySelector('[aria-current="location"]');
    if (!mark) { out.push({key: link.getAttribute("data-toc"), mark: false}); continue; }
    const mr = mark.getBoundingClientRect();
    const nr = nav.getBoundingClientRect();
    const inside = mr.top >= nr.top - 1 && mr.bottom <= nr.bottom + 1;
    out.push({key: link.getAttribute("data-toc"), mark: true, inside,
              markTop: Math.round(mr.top), markBottom: Math.round(mr.bottom),
              navTop: Math.round(nr.top), navBottom: Math.round(nr.bottom)});
  }
  return out;
})()
"""


@needs_browser
class TestTheRailDisclosesByChapter:
    def test_at_landing_only_the_open_chapters_sections_show(self, browser, uri):
        out = browser.measure(uri, _LANDING, 1440, 900)
        assert out["rows"] > 1, out
        assert out["openRows"] == ["decide"], (
            f"exactly one chapter is open at landing, and it is the "
            f"decision: {out}")
        assert out["visible"] > 0, out
        assert out["visible"] < out["links"], (
            f"every rail link is laid out - disclosure is not hiding "
            f"anything: {out}")
        assert out["visibleOutsideOpen"] == 0, (
            f"{out['visibleOutsideOpen']} rail link(s) outside the open "
            f"chapter are still laid out: {out}")


@needs_browser
class TestTheMarkStaysInView:
    def test_every_section_the_reader_reaches_keeps_its_mark_in_the_rail(
            self, browser, uri):
        out = browser.measure(uri, _WALK, 1440, 900)
        marked = [row for row in out if row["mark"]]
        assert len(marked) > 20, (
            f"only {len(marked)} of {len(out)} clicks left a mark - not "
            f"enough of a walk to trust the clause below")
        outside = [row for row in marked if not row["inside"]]
        assert outside == [], (
            f"{len(outside)} of {len(marked)} marks sit outside the "
            f"rail's own rect: {outside[:8]}")


#: `UX-667`'s third clause, and `UX-318`'s nested-scrollbox mechanism
#: held to a new surface: a scrollbox nested inside the rail's own
#: scroll is the shape that item already abolished for tables.
def _rules():
    css = (REPO / "bga/viewer/style.css").read_text(encoding="utf-8")
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out = []
    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        selector = " ".join(match.group(1).split())
        decls = {}
        for part in match.group(2).split(";"):
            if ":" in part:
                name, value = part.split(":", 1)
                decls[name.strip()] = value.strip()
        out.append((selector, decls))
    return out


class TestNoNestedScrollboxInTheRail:
    def test_no_descendant_of_the_rail_scrolls_on_its_own(self):
        """`.toc` itself scrolls as one sticky column (`body[data-has-toc]
        > .toc`) - that is the rail's own axis, not a nested one. A rule
        for anything *inside* it - a descendant combinator on `.toc` -
        must not add a second `overflow-y`."""
        offenders = []
        for selector, decls in _rules():
            if selector in (".toc", "body[data-has-toc] > .toc"):
                continue
            if ".toc " not in f" {selector} " and not selector.startswith(".toc "):
                continue
            value = decls.get("overflow-y") or decls.get("overflow")
            if value in ("auto", "scroll"):
                offenders.append((selector, decls))
        assert offenders == [], (
            f"a descendant of nav.toc still scrolls on its own: {offenders}")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
