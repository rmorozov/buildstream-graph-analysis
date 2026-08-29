"""UX-399: the browser is the library.

`UX-398` decided no dependency and left the follow-on question: then how
does the page grow? Round 65's answer is that the platform already ships
most of what a table/UI library is adopted for, and the page used none
of it. Two primitives landed:

```text
content-visibility: auto   the platform's virtual scrolling, 0 bytes
IntersectionObserver       the rail learns where the reader is
```

Measured on the fully expanded page - every chapter and fold open, which
is the state a reader who opens the report is in - with the optimisation
forced off and on in the same browser, median of 25 forced reflows:

```text
fixture       DOM nodes    off                     on
scale (1,202)    23,040    70,932 px  25.9 ms      41,669 px   2.2 ms
macro_micro       5,366    48,224 px  12.9 ms      42,777 px   2.3 ms
golden            2,441    23,863 px   6.4 ms      27,214 px   1.9 ms
```

Layout cost stops tracking the document: 6.4 -> 25.9 ms as the run grows
tenfold, against ~2 ms at every size once the browser lays out the
viewport instead of the report.

**Two halves, and they hold each other up.** The volume budget forces
`content-visibility` off before measuring, because `scrollHeight` under
it is an estimate until a section has been rendered once - so a guard
there could no longer notice the optimisation being deleted. This file
is the other half: the shipped stylesheet really carries it, applied
where it pays, and the rail really marks where the reader is.
"""
import pathlib
import re
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import pages                                      # noqa: E402
from tests.browser import NO_BROWSER, Browser, find_chrome    # noqa: E402

STYLE = REPO / "bga/viewer/style.css"
NAV = REPO / "bga/viewer/nav.js"
APP = REPO / "bga/viewer/app.js"
STYLEGUIDE = REPO / "docs/design/styleguide.md"


def stylesheet():
    """The stylesheet with its comments removed.

    Not cosmetic. The first version of these clauses searched the raw
    text, and the mutation that comments the declaration out - which is
    how anyone actually disables a CSS line - left the words in place
    and the clause green. The browser clause below caught it; this one
    was decoration until it stopped reading prose.
    """
    return re.sub(r"/\*.*?\*/", "", STYLE.read_text(encoding="utf-8"),
                  flags=re.S)


class TestTheStylesheetCarriesIt:
    """The half the volume budget can no longer see."""

    def test_content_visibility_is_declared_where_it_pays(self):
        css = stylesheet()
        assert "content-visibility: auto" in css, (
            "styleguide §6c's measurement was taken against a stylesheet "
            "that declares content-visibility; the volume guards force it "
            "off before measuring, so nothing else would notice this "
            "being deleted")
        rule = re.search(
            r"section\.chapter > section\[data-section\]\s*\{[^}]*\}", css)
        assert rule and "content-visibility: auto" in rule.group(0), (
            "the optimisation belongs on the sections *inside* a chapter: "
            "a folded chapter is already display:none, so the chapter "
            "level has nothing to skip")

    def test_the_placeholder_size_is_declared_and_remembers(self):
        """`auto` is the load-bearing word.

        Without it every offscreen section keeps the placeholder size
        forever and the scrollbar never converges on the real height.
        """
        css = stylesheet()
        declared = re.search(r"contain-intrinsic-size:\s*([^;]+);", css)
        assert declared, (
            "content-visibility with no contain-intrinsic-size collapses "
            "every offscreen section to zero height")
        assert declared.group(1).strip().startswith("auto "), (
            "contain-intrinsic-size must start with `auto` so a section "
            f"keeps its real size once rendered; it declares {declared.group(1)!r}")

    def test_the_inventory_is_in_the_styleguide(self):
        """§6c is the living copy, not this file."""
        text = STYLEGUIDE.read_text(encoding="utf-8")
        section = text.split("## 6c.", 1)
        assert len(section) == 2, "styleguide §6c is gone"
        body = section[1].split("\n## ", 1)[0]
        for primitive in ("content-visibility", "IntersectionObserver",
                          "scroll-margin-top", "popover", "@container"):
            assert primitive in body, (
                f"§6c's inventory no longer lists {primitive}, so "
                "'can the platform do it' has lost an answer")


class TestTheRailKnowsWhereYouAre:
    def test_the_scrollspy_needs_no_library_and_degrades(self):
        source = NAV.read_text(encoding="utf-8")
        assert "IntersectionObserver" in source, (
            "the scrollspy is the platform's observer or it is a scroll "
            "handler reading layout every frame")
        assert 'typeof IntersectionObserver === "function"' in source, (
            "the shim has no IntersectionObserver, so scrollspy has to "
            "return null rather than throw where there is none")
        assert "scrollspy(root, contents)" in APP.read_text(encoding="utf-8"), (
            "an exported function nothing calls is not a feature")

    def test_the_mark_is_weight_and_a_marker_not_a_tone(self):
        """§4's emphasis budget is spent on findings, not on orientation."""
        css = stylesheet()
        rule = re.search(r"\.toc a\[data-current\]\s*\{[^}]*\}", css)
        assert rule, "nothing styles the rail's current entry"
        assert "font-weight" in rule.group(0), (
            "the current entry is marked by weight; a color-only mark "
            "disappears in forced-colors and on paper")
        assert re.search(r"\.toc a\[data-current\]::before", css), (
            "and by a marker, for the same reason")


@pytest.fixture(scope="module")
def page(tmp_path_factory):
    into = tmp_path_factory.mktemp("browser-is-the-library")
    return pages.export_uri(pages.FIXTURES["macro_micro"], into)


@pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
class TestInARealBrowser:
    """The claims that are only true if a layout engine agrees."""

    def test_the_rail_marks_the_section_the_reader_scrolled_to(self, page):
        look = r"""(async () => {
          const wait = () => new Promise((r) => setTimeout(r, 300));
          await wait();
          const shown = [...document.querySelectorAll("section[data-section]")]
            .filter((s) => s.getBoundingClientRect().height > 0);
          const mark = () => [...document.querySelectorAll(
            "[data-toc][data-current]")].map((a) => a.getAttribute("data-toc"));
          const out = { atTop: mark(), shown: shown.length, jumps: [] };
          for (const target of [shown.at(-1), shown.at(-3)]) {
            target.scrollIntoView();
            await wait();
            out.jumps.push([target.getAttribute("data-section"), mark()]);
          }
          out.aria = [...document.querySelectorAll(
            '[data-toc][aria-current="location"]')].length;
          return out;
        })()"""
        with Browser(find_chrome()) as browser:
            seen = browser.measure(page, look, 1440, 900)

        assert seen["shown"] > 1, seen
        assert len(seen["atTop"]) == 1, (
            f"exactly one rail entry is 'here'; got {seen['atTop']}")
        for where, marked in seen["jumps"]:
            assert marked == [where], (
                f"scrolled to {where}, rail says {marked}")
        assert seen["aria"] == 1, (
            "a screen reader learns the same fact through aria-current")

    def test_the_layout_cost_stops_tracking_the_document(self, page):
        """The claim is a layout claim, so the number is a layout number."""
        look = r"""(() => {
          for (const b of document.querySelectorAll("[data-chapter-open]")) b.click();
          for (const b of document.querySelectorAll('[data-all="false"]')) b.click();
          for (const d of document.querySelectorAll("details")) d.open = true;
          void document.documentElement.offsetHeight;
          const reflow = () => {
            const t = [];
            for (let i = 0; i < 25; i++) {
              document.body.style.setProperty("--probe", String(i));
              const t0 = performance.now();
              void document.documentElement.offsetHeight;
              t.push(performance.now() - t0);
            }
            t.sort((a, b) => a - b);
            return t[Math.floor(t.length / 2)];
          };
          const on = reflow();
          """ + pages.FULL_LAYOUT_JS + r"""
          void document.documentElement.offsetHeight;
          return { on, off: reflow(),
                   nodes: document.querySelectorAll("*").length };
        })()"""
        with Browser(find_chrome()) as browser:
            seen = browser.measure(page, look, 1440, 900)

        assert seen["nodes"] > 2000, seen
        # Measured 2.3 ms against 12.9 ms on this fixture and 2.2 against
        # 25.9 at 1,202 elements. Held as a ratio with room, not as the
        # figure: the number is the machine's, the property is the page's.
        assert seen["on"] < seen["off"] / 2, (
            f"content-visibility bought nothing: {seen['on']:.1f} ms with "
            f"it against {seen['off']:.1f} ms without, on a "
            f"{seen['nodes']}-element page")
