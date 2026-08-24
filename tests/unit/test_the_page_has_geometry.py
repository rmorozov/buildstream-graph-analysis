"""UX-257: the page's geometry, read by something that has one.

The user asked to *"recheck that information on page won't overlap"*.
That recheck was done by hand for `UX-254`, in a real browser, and
found nothing — and then **nothing held it**. Every geometric claim in
this repository was in the same position: measured once, written into a
task file, and guarded by no instrument, because the shim the viewer
guards run on has no layout engine at all.

`UX-213` is why that is urgent rather than tidy: a guard that runs on
one machine was the failure that item was filed against, and a
measurement that runs on no machine is one step worse.

**What this instrument is.** A real Chrome, driven over the DevTools
protocol by forty lines of node (`tests/cdp.mjs`) using only built-in
`WebSocket` and `fetch`. No Playwright, no browser download, no new
package. The argument is in `tests/browser.py`.

**What it cannot see**, named here rather than left implied:

- Anything on a machine with no Chrome. These skip there, and the skip
  is declared in the census (`tests/conftest.py`) so it cannot go quiet.
- Fonts. The measurements below are thresholds with slack, never exact
  pixels: a font stack that resolves differently moves text by a few
  pixels and must not redden a guard (`UX-257` declined screenshot
  baselines for exactly this reason).
- The served page's dynamic halves — `?url=` deep links, the Perfetto
  hand-off, the blast endpoint. This loads the **exported** report,
  which is one file with its payloads inlined.
"""
import pathlib
import shutil
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from browser import NO_BROWSER, Browser, find_chrome  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[2]
GOLDEN = REPO / "tests/fixtures/golden/mixed_task_kinds"

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)
needs_node = pytest.mark.skipif(shutil.which("node") is None,
                                reason="node is not installed")

# The viewports this claims to have checked. Part of the contract: a
# claim about "the page" that was measured at one width is a claim
# about one width.
VIEWPORTS = ((1440, 900), (1280, 800), (390, 844))


@pytest.fixture(scope="module")
def report(tmp_path_factory):
    """The exported report of the golden run: one file, no server."""
    from tools.bga_view import export

    run = tmp_path_factory.mktemp("run") / "run"
    shutil.copytree(GOLDEN, run)
    (run / "expected_output.json").unlink(missing_ok=True)
    path = tmp_path_factory.mktemp("page") / "report.html"
    export(str(run), str(path))
    return path.as_uri()


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


# Boxes that legitimately sit on top of other boxes, and why. An
# overlap scan with no exemptions reports every tooltip and every
# sticky heading; one with unexplained exemptions reports nothing.
ALLOWED_TO_OVERLAP = {
    "header": "sticky by design (UX-254): it is *supposed* to sit over "
              "the reading column as it scrolls",
    ".toc": "the rail is a fixed column beside the text, and folds over "
            "it at narrow widths by design (UX-254's breakpoint)",
}

_OVERLAP_SCAN = """
(() => {
  const allowed = %s;
  const boxes = [...document.querySelectorAll("main *")]
    .filter((n) => {
      const style = getComputedStyle(n);
      if (style.display === "none" || style.visibility === "hidden") return false;
      // Out-of-flow boxes are *placed* on top of things on purpose -
      // a copy button over a command, a badge over a bar. Overlap is
      // their job, and reporting it is how a scan gets muted.
      if (style.position === "sticky" || style.position === "fixed"
          || style.position === "absolute") return false;
      if (allowed.some((s) => n.closest(s))) return false;
      const box = n.getBoundingClientRect();
      return box.width > 4 && box.height > 4;
    });
  // Siblings only. A child is inside its parent by definition, and
  // reporting that as an overlap is how an overlap scan gets muted.
  const hits = [];
  for (const node of boxes) {
    const siblings = [...(node.parentElement?.children ?? [])]
      .filter((s) => s !== node && boxes.includes(s));
    // `getClientRects()`, not `getBoundingClientRect()`: an inline
    // element that wraps has one box per line, and its *bounding* box
    // is the union of them - a rectangle covering text that is not
    // there. Two wrapped links in a paragraph reported a 141x18
    // overlap on the first run of this scan, and neither was touching
    // the other. Measuring the union of an inline box is the same
    // class of error as the shim inventing geometry.
    for (const other of siblings) {
      let worst = null;
      for (const a of node.getClientRects()) {
        for (const b of other.getClientRects()) {
          const across = Math.min(a.right, b.right) - Math.max(a.left, b.left);
          const down = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
          if (across > 1 && down > 1
              && (worst === null || across * down > worst.across * worst.down)) {
            worst = {across: Math.round(across), down: Math.round(down)};
          }
        }
      }
      if (worst) {
        hits.push({
          a: node.tagName + "." + node.className,
          b: other.tagName + "." + other.className, ...worst,
        });
      }
    }
  }
  return {count: hits.length, sample: hits.slice(0, 5),
          scanned: boxes.length};
})()
"""


@needs_node
@needs_browser
class TestNothingOverlaps:
    @pytest.mark.parametrize("width,height", VIEWPORTS)
    def test_no_two_siblings_share_pixels(self, browser, report, width, height):
        """The claim `UX-254` made by hand, now made by the browser."""
        import json

        out = browser.measure(
            report, _OVERLAP_SCAN % json.dumps(sorted(ALLOWED_TO_OVERLAP)),
            width=width, height=height)
        assert out["scanned"] > 20, (
            f"only {out['scanned']} boxes were scanned at {width}x{height} - "
            f"the page did not render, so 'no overlaps' means nothing")
        assert out["count"] == 0, (
            f"{out['count']} overlapping sibling pair(s) at {width}x{height}: "
            f"{out['sample']}")

    def test_every_exemption_carries_a_reason(self):
        for selector, reason in ALLOWED_TO_OVERLAP.items():
            assert "UX-" in reason, f"{selector}: no item id"
            assert len(reason) > 40, f"{selector}: the reason is a label"


@needs_node
@needs_browser
class TestTheReadingColumnComesFirst:
    """`UX-254`'s measurement, which was 573px of navigation above the
    run's own name. Thresholds rather than the exact pixels: fonts move
    text a few pixels and a guard that fails on that gets muted."""

    _FIRST_CONTENT = """
    (() => {
      const heading = document.querySelector("header");
      const main = document.querySelector("main");
      const toc = document.querySelector(".toc");
      return {
        headerTop: Math.round(heading.getBoundingClientRect().top),
        mainTop: Math.round(main.getBoundingClientRect().top),
        tocLeft: toc ? Math.round(toc.getBoundingClientRect().left) : null,
        mainLeft: Math.round(main.getBoundingClientRect().left),
        viewport: window.innerHeight,
        docWidth: document.documentElement.scrollWidth,
        innerWidth: window.innerWidth,
      };
    })()
    """

    @pytest.mark.parametrize("width,height", [(1440, 900), (1280, 800)])
    def test_the_heading_is_the_first_thing_on_the_page(
            self, browser, report, width, height):
        out = browser.measure(report, self._FIRST_CONTENT, width, height)
        assert out["headerTop"] < out["mainTop"], out
        assert out["mainTop"] < out["viewport"] * 0.5, (
            f"the reading column starts at y={out['mainTop']} of "
            f"{out['viewport']} - more than half the first screen is chrome, "
            f"which is the defect UX-254 fixed")

    def test_the_rail_is_beside_the_text_not_above_it(self, browser, report):
        out = browser.measure(report, self._FIRST_CONTENT, 1440, 900)
        if out["tocLeft"] is None:
            pytest.skip("this run rendered no rail")
        assert out["tocLeft"] < out["mainLeft"], (
            f"the rail is not in its own column left of the text: {out}")

    @pytest.mark.parametrize("width,height", VIEWPORTS)
    def test_the_page_never_scrolls_sideways(
            self, browser, report, width, height):
        """Measured at 390px before `UX-254`: tables 217px wide against
        a 390px viewport, so the whole report scrolled horizontally."""
        out = browser.measure(report, self._FIRST_CONTENT, width, height)
        assert out["docWidth"] <= out["innerWidth"] + 2, (
            f"the document is {out['docWidth']}px wide in a "
            f"{out['innerWidth']}px viewport at {width}x{height}")


@needs_node
@needs_browser
class TestAnAnchorLandsWhereYouCanReadIt:
    def test_a_jump_does_not_land_under_the_sticky_heading(
            self, browser, report):
        """The reader-visible half of "information overlaps": a jump
        that lands behind the heading that never scrolls away."""
        out = browser.measure(report, """
        (() => {
          const target = document.querySelector("section[id]");
          if (!target) return null;
          location.hash = "#" + target.id;
          const header = document.querySelector("header");
          const headerBox = header.getBoundingClientRect();
          const box = target.getBoundingClientRect();
          return {hidden: Math.round(headerBox.bottom - box.top),
                  id: target.id};
        })()
        """, 1440, 900)
        if out is None:
            pytest.skip("this run rendered no anchored section")
        assert out["hidden"] <= 0, (
            f"#{out['id']} lands {out['hidden']}px under the sticky heading")


class TestTheInstrumentSaysWhatItCannotSee:
    """The half `UX-257` insisted on: whichever instrument is chosen,
    it must name the claims it does not cover."""

    def test_the_skip_reason_is_declared(self):
        conftest = (REPO / "tests/conftest.py").read_text(encoding="utf-8")
        assert NO_BROWSER in conftest, (
            "the no-browser skip is not in the census, so these guards can "
            "go quiet on every machine and the suite stays green (UX-235)")

    def test_the_shim_still_refuses_to_invent_geometry(self):
        shim = (REPO / "tests/dom_shim.mjs").read_text(encoding="utf-8")
        assert "There is no layout" in shim, (
            "tests/dom_shim.mjs no longer says it has no layout engine - if "
            "it grew one, this file is redundant; if it grew a fake one, "
            "every geometric guard built on it is invented")

    def test_the_viewports_are_part_of_the_contract(self):
        assert (390, 844) in VIEWPORTS, (
            "the narrow viewport is where the sideways-scroll defect was "
            "found; dropping it makes this suite blind to it")
        assert len(VIEWPORTS) >= 3


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
