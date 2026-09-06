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
`revealAndLand` opens the chapter and lands again two frames later,
after the real height is in.

The six sections at the document's end land where the page runs out of
scroll, not under the header: that is the page's height, not this
defect, and the split below is asserted rather than allowed for.
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

#: How far below the viewport top a correct landing may sit. The sticky
#: header is 92 px and `scroll-margin-top` is `--head + .5rem` = 104, so
#: every landing measured lands at 104-105.
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


class TestTheEntryPointsLandRatherThanScroll:
    def test_every_way_in_goes_through_the_settle(self):
        """The rail, the jump box and a pasted `#anchor` are three
        callers of one helper. A site left on `revealChapter` scrolls
        against the estimate and this file cannot see it: the rail is
        the only one it drives."""
        app = (REPO / "bga" / "viewer" / "app.js").read_text()
        assert "revealChapter" not in app
        assert app.count("revealAndLand") == 3

    def test_the_helper_lands_now_and_again_two_frames_later(self):
        """Both, and the source is where it is asserted: the browser
        clauses below cannot tell the two landings apart on this
        fixture, because the rail link's own anchor scroll supplies the
        first. The jump box has no such scroll, and one frame lands
        6 of 61 - worse than none - so neither half is spare."""
        text = (REPO / "bga" / "viewer" / "chapters.js").read_text()
        body = text[text.index("export function revealAndLand("):]
        body = body[:body.index("\n}\n")]
        assert "\n  land();\n" in body
        assert "frame(() => frame(land))" in body


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

    #: `scroll-margin-top` is `--head + .5rem` = 104. Measured tops:
    #: 104-105 single-process, 103-105 under `-n auto` - the same
    #: landing, rounded differently under load. A set equality on
    #: `[104, 105]` was this clause's first form and it went red in the
    #: suite for that pixel, so the band is +-2 and stated.
    BAND = (102, 106)

    def test_the_landing_is_the_header_and_not_merely_close(self, landings):
        """A narrow band, not "somewhere near the top" - which is what
        the -317 and +673 above would also satisfy against a loose
        bound. Four pixels wide against a 900 px viewport."""
        low, high = self.BAND
        tops = sorted({row["top"] for row in landings
                       if row["fromEnd"] != 0})
        assert tops and low <= min(tops) and max(tops) <= high, tops
