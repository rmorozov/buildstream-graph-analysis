"""UX-670: a rail click into a folded chapter lands on its section.

`content-visibility: auto` (`UX-399`) estimates the height of a folded
chapter's unrendered sections. The scroll that follows the fold opening
runs against the estimate, and the reader arrives somewhere else.
Measured on `macro_micro`, exported and booted at 1440x900, one fresh
load per link, section top against the 104 px a correct landing gives:

```text
whatif                -736     perfetto-questions    -576
restructuring         -317     critical_path_detail  +673
```

Both directions, so it is not an offset anyone could subtract.
`revealAndLand` opens the chapter and lands again as later frames
settle, after the real height is in - three, since `UX-668`.

The six sections at the document's end land where the page runs out of
scroll, not under the header: that is the page's height, not this
defect, and the split below is asserted rather than allowed for.

UX-722: two rail sub-entries do not name a section at all - `nav.js`
names a fold (`<details class="map">`) too, and both
`restructuring--edges` and `restructuring--projection` sit in a `<td>`
of a table whose `overflow-x: auto` (`main table`, UX-254) makes it a
scroll container. `node.scrollIntoView()` aligned *that* ancestor to
the viewport top - nothing to actually scroll, so the alignment was
free - and the document scroll that followed ran against the rect it
had already touched: 44 px, same as before this file's own fix.
Wrapping the table changes which element that scroll container is and
not the outcome (measured: still ~50 px) - any `overflow-x: auto`
ancestor, table or wrapper, is one to `scrollIntoView`. `revealAndLand`
computes the document scroll itself, from the rect and
`scroll-margin-top`, so no ancestor's scroll runs at all.
"""
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import pages
from browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

#: How far below the viewport top a correct landing may sit.
#: `scroll-margin-top` is `--head + .5rem`, read per-measurement below
#: rather than pasted here - `UX-668` moved it once already.
SLACK_PX = 20

#: Every rail link whose target is a published section inside a chapter
#: that is **folded on a fresh load**. Read from the page rather than
#: listed: a list goes stale the round a chapter's contents move, and
#: the defect is a property of the fold, not of six names.
_FOLDED = r"""
(() => [...document.querySelectorAll('a[href^="#"]')]
   .filter((a) => a.closest("nav, .rail, .toc"))
   .map((a) => {
     const id = a.getAttribute("href").slice(1);
     const t = document.getElementById(id);
     const box = t && t.closest("section.chapter");
     return (t && box && t.tagName === "SECTION"
             && !t.classList.contains("chapter")
             && box.getAttribute("data-open") === "false") ? id : null;
   }).filter(Boolean))()
"""

#: One click, on a page that has just loaded. `fromEnd` is what tells a
#: miss from a section the page cannot scroll any further towards.
_CLICK = r"""
(async () => {
  const wait = (n) => new Promise((r) => {
    let i = 0;
    const step = () => (++i >= n ? r() : requestAnimationFrame(step));
    requestAnimationFrame(step);
  });
  const head = Math.round(
    document.querySelector("header").getBoundingClientRect().height);
  const link = [...document.querySelectorAll('a[href="#__ID__"]')]
    .find((n) => n.closest("nav, .rail, .toc"));
  if (!link) return {id: "__ID__", missing: true};
  link.click();
  await wait(6);
  const target = document.getElementById("__ID__");
  const max = document.documentElement.scrollHeight - window.innerHeight;
  return {id: "__ID__", head,
          top: Math.round(target.getBoundingClientRect().top),
          fromEnd: Math.round(max - window.scrollY)};
})()
"""


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module")
def landings(browser, tmp_path_factory):
    """One fresh load per link. **Not one load driven many times**: the
    first click renders the chapter, and a rendered chapter has a real
    height, so the second link would be measured against the fix rather
    than the defect."""
    into = tmp_path_factory.mktemp("u670")
    uri = pages.export_uri(pages.FIXTURES["macro_micro"], into)
    ids = browser.measure(uri, _FOLDED, 1440, 900)
    return [browser.measure(uri, _CLICK.replace("__ID__", one), 1440, 900)
            for one in ids]


#: `UX-722`: every rail link whose target is a fold rather than a
#: section - `nav.js`'s `subsections` names a `details.map` too, and a
#: rail link is not only ever a way into a section.
_FOLDS = r"""
(() => [...document.querySelectorAll('a[href^="#"]')]
   .filter((a) => a.closest("nav, .rail, .toc"))
   .map((a) => {
     const id = a.getAttribute("href").slice(1);
     const t = document.getElementById(id);
     return (t && t.tagName === "DETAILS") ? id : null;
   }).filter(Boolean))()
"""


@pytest.fixture(scope="module")
def fold_landings(browser, tmp_path_factory):
    """Same method as `landings`, a fresh load per fold rather than per
    section - the two are a different DOM shape (`<details>` in a
    table cell, not `<section>` in a chapter) and neither fixture
    stands in for the other."""
    into = tmp_path_factory.mktemp("u722")
    uri = pages.export_uri(pages.FIXTURES["macro_micro"], into)
    ids = browser.measure(uri, _FOLDS, 1440, 900)
    return [browser.measure(uri, _CLICK.replace("__ID__", one), 1440, 900)
            for one in ids]


class TestTheEntryPointsLandRatherThanScroll:
    def test_every_way_in_goes_through_the_settle(self):
        """The rail, the jump box and a pasted `#anchor` are three
        callers of one helper. A site left on `revealChapter` scrolls
        against the estimate and this file cannot see it: the rail is
        the only one it drives."""
        app = (REPO / "bga" / "viewer" / "app.js").read_text()
        assert "revealChapter" not in app
        assert app.count("revealAndLand") == 3

    def test_the_helper_lands_now_and_again_as_frames_settle(self):
        """Both, and the source is where it is asserted: the browser
        clauses below cannot tell the landings apart on this fixture,
        because the rail link's own anchor scroll supplies the first.
        The jump box has no such scroll, and one frame lands 6 of 61 -
        worse than none - so neither half is spare. `UX-668`: two
        frames stopped settling `blast` once the header and decision
        panel moved the estimate one section further out; three does."""
        text = (REPO / "bga" / "viewer" / "chapters.js").read_text()
        body = text[text.index("export function revealAndLand("):]
        body = body[:body.index("\n}\n")]
        assert "\n  land();\n" in body
        assert "frame(() => frame(() => frame(land)))" in body

    def test_the_landing_is_computed_not_delegated(self):
        """`UX-722`: `scrollIntoView` aligns the nearest scroll
        container - a wide table or its wrapper alike - to the
        viewport top, which is free when there is nothing to scroll
        and wrong regardless. The document scroll is computed from the
        rect and the node's own `scroll-margin-top` instead."""
        text = (REPO / "bga" / "viewer" / "chapters.js").read_text()
        body = text[text.index("export function revealAndLand("):]
        body = body[:body.index("\n}\n")]
        assert "scrollIntoView" not in body
        assert "getBoundingClientRect" in body
        assert "scrollMarginTop" in body


@needs_browser
class TestARailClickLandsUnderTheHeader:
    def test_every_link_lands_or_runs_out_of_page(self, landings):
        missed = [row for row in landings
                  if not (0 <= row["top"] <= row["head"] + SLACK_PX)
                  and row["fromEnd"] != 0]
        assert missed == [], (
            f"{len(missed)} of {len(landings)} rail links land away from "
            f"the section they name, and the page had somewhere left to "
            f"scroll: {missed}")

    def test_the_split_is_the_one_measured(self, landings):
        """Pasted, so the escape cannot quietly grow. 61 folded section
        links on `macro_micro`: 55 land under the header, and the 6 in
        the identity block at the foot of the page are where the
        document ends."""
        under = [row for row in landings if row["fromEnd"] != 0]
        at_end = [row for row in landings if row["fromEnd"] == 0]
        assert (len(landings), len(under), len(at_end)) == (61, 55, 6)
        assert sorted(row["id"] for row in at_end) == [
            "cpu_time", "document_shape", "peak_memory", "producer",
            "run_instance", "utilization_envelope"]

    #: `scroll-margin-top` is `--head + .5rem`. `UX-668`'s header
    #: control wraps the identity line to a second row, so `--head` grew
    #: 6rem -> 7rem and the landing moved 104 -> 119-121. A set equality
    #: was this clause's first form and it went red in the suite for
    #: that pixel, so the band is +-2 and stated.
    BAND = (117, 123)

    def test_the_landing_is_the_header_and_not_merely_close(self, landings):
        """A narrow band, not "somewhere near the top" - which is what
        the -317 and +673 above would also satisfy against a loose
        bound. Four pixels wide against a 900 px viewport."""
        low, high = self.BAND
        tops = sorted({row["top"] for row in landings
                       if row["fromEnd"] != 0})
        assert tops and low <= min(tops) and max(tops) <= high, tops


@needs_browser
class TestARailClickIntoAFoldLandsUnderTheHeader:
    """`UX-722`: `restructuring--edges` and `restructuring--projection`,
    measured on `macro_micro` at 1440x900 before this item's fix:

    ```text
    restructuring--edges        44 px   fromEnd 895
    restructuring--projection   44 px   fromEnd 895
    restructuring               104 px  fromEnd 1042   (the control)
    ```

    Both sit in a `<td>` of the `restructuring` table, whose
    `overflow-x: auto` (UX-254) makes it a scroll container between the
    fold and the document.
    """

    def test_every_fold_link_lands_or_runs_out_of_page(self, fold_landings):
        assert fold_landings, "no rail link targets a fold on this fixture"
        missed = [row for row in fold_landings
                  if not (0 <= row["top"] <= row["head"] + SLACK_PX)
                  and row["fromEnd"] != 0]
        assert missed == [], (
            f"{len(missed)} of {len(fold_landings)} fold links land away "
            f"from the fold they name, and the page had somewhere left to "
            f"scroll: {missed}")

    def test_the_two_known_folds_are_the_ones_measured(self, fold_landings):
        """Pasted, so a third fold target does not silently join the
        passing set unmeasured."""
        assert sorted(row["id"] for row in fold_landings) == [
            "restructuring--edges", "restructuring--projection"]

    def test_the_landing_is_the_header_and_not_merely_close(
            self, fold_landings):
        low, high = TestARailClickLandsUnderTheHeader.BAND
        tops = sorted({row["top"] for row in fold_landings})
        assert tops and low <= min(tops) and max(tops) <= high, tops
