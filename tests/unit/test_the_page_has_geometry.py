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
    "svg": "inside a drawing, marks sit *on* the line they mark - "
           "UX-303's sparkline puts a circle at each endpoint and at the "
           "peak, and a scan that called that an overlap would be asking "
           "for a chart whose points float beside their own curve",
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


class TestATableSControlsStayInReach:
    """`UX-284`. Reported: *"the search box is buried at the bottom of
    sections."* Measured before, on the served report:

    ```text
    filter/threshold inputs on the page            43
    inputs whose top is *below* their table's top  28
    inputs with `position: static`                 43 of 43
    the jump box sits at y=1236 - below the fold at 900px
    ```

    The `position: static` half bites at every table: the 1,202-element
    report is 18.8 screens and its longest table is taller than the
    viewport, so filtering it meant scroll up, type, scroll down, scroll
    up again. The control that narrows a long table has to stay in reach
    while the reader looks at the result.
    """

    _TOOLS = """
    (() => {
      const tools = [...document.querySelectorAll(".table-tools")];
      let below = 0, sticky = 0;
      for (const box of tools) {
        const table = box.parentElement?.querySelector("table");
        if (!table) continue;
        if (box.getBoundingClientRect().top
            > table.getBoundingClientRect().top) below += 1;
        if (getComputedStyle(box).position === "sticky") sticky += 1;
      }
      const jump = document.getElementById("jump");
      return {
        tools: tools.length,
        below,
        sticky,
        jump_top: jump
          ? Math.round(jump.getBoundingClientRect().top + window.scrollY)
          : null,
        viewport: window.innerHeight,
      };
    })()
    """

    @pytest.mark.parametrize("width,height", VIEWPORTS)
    def test_no_table_hides_its_own_tools_below_itself(
            self, browser, report, width, height):
        out = browser.measure(report, self._TOOLS, width, height)
        assert out["tools"] > 0, "the report drew no table tools at all"
        assert out["below"] == 0, (
            f"{out['below']} of {out['tools']} tool strips start below "
            f"their table at {width}x{height}")

    @pytest.mark.parametrize("width,height", VIEWPORTS)
    def test_every_strip_stays_while_its_table_scrolls(
            self, browser, report, width, height):
        """Sticky *inside the table's own scroll box*, not fixed to the
        viewport - so two tables never both claim the same strip."""
        out = browser.measure(report, self._TOOLS, width, height)
        assert out["sticky"] == out["tools"], (
            f"{out['tools'] - out['sticky']} of {out['tools']} strips are "
            f"not sticky at {width}x{height}")

    def test_the_jump_box_is_on_the_first_screen(self, browser, report):
        """`UX-284` item 3: it is the page's coarse navigation - the
        control a reader reaches for *before* they know which section
        they want - and it was below thirty-odd rail entries."""
        out = browser.measure(report, self._TOOLS, 1440, 900)
        assert out["jump_top"] is not None, "the report has no jump box"
        assert out["jump_top"] < out["viewport"], (
            f"the jump box starts at {out['jump_top']}px, below the "
            f"{out['viewport']}px fold")


@needs_node
@needs_browser
class TestTheDocumentEndsWithItsIdentity:
    """`UX-285`, in screens rather than in DOM order.

    `test_the_order_the_page_has.py` guards the sequence; this guards
    what the sequence was *for*. Measured on the exported golden report
    and on the 1,202-element run before it landed:

    ```text
                          1,202-element        golden fixture
    summary                 screen 10.5        screen  8.26
    run_instance                   10.69               8.45
    producer                       10.83               8.56
    document height                18.51              11.0
    blast                          18.27              10.76
    findings                        1.36               1.31
    ```

    Two blocks near the top, the third seven screens later, and an
    interactive query at the very foot of the page.
    """

    _WHERE = """
    (() => {
      const vh = window.innerHeight;
      const total = document.documentElement.scrollHeight;
      const box = (name) => {
        const n = document.querySelector(`main section[data-section="${name}"]`);
        if (!n) return null;
        const r = n.getBoundingClientRect();
        return {top: r.top + window.scrollY, bottom: r.bottom + window.scrollY};
      };
      const out = {total, vh};
      for (const key of ["summary", "run_instance", "producer", "findings",
                         "headline", "next_steps", "blast-offline"])
        out[key] = box(key);
      // Everything below the identity group, by pixel rather than by
      // DOM order - the two agree on a page laid out in one column,
      // and disagreeing is itself worth knowing.
      const producer = out["producer"];
      out.below = producer === null ? [] :
        [...document.querySelectorAll("main section[data-section]")]
          .filter((n) => n.getBoundingClientRect().bottom + window.scrollY
                         > producer.bottom + 1)
          .map((n) => n.dataset.section);
      return out;
    })()
    """

    @pytest.mark.parametrize("width,height", VIEWPORTS)
    def test_nothing_is_drawn_below_the_identity(self, browser, report,
                                                 width, height):
        """"Closes the document", in pixels.

        This is the clause that catches the mutation, and the one below
        is not: moving the placement back inside `render` - so the
        identity sits last of the *payload* and above twenty-five
        element blocks - leaves "in the last third" green on this
        fixture, because four element sections and a trend are only a
        quarter of an eleven-screen page. Fourteen geometry checks
        passed under exactly that mutation before this one existed."""
        out = browser.measure(report, self._WHERE, width, height)
        assert out["producer"], "producer did not render; nothing measured"
        assert out["below"] == [], (
            f"{out['below']} are drawn below the identity group at "
            f"{width}x{height}")

    @pytest.mark.parametrize("width,height", VIEWPORTS)
    def test_the_identity_sits_in_the_last_third(self, browser, report,
                                                 width, height):
        """The acceptance test's first clause, read as a fraction of the
        document because the same three blocks are 96% of an 18-screen
        report and 94% of an 11-screen one.

        Weak on this fixture, and recorded as weak: the *pre-change*
        page put `summary` at 75% of the golden report, which already
        satisfies "the last third". It is the item's own wording and it
        is checked; what it does not do is catch a regression on a
        short run. The clause above does."""
        out = browser.measure(report, self._WHERE, width, height)
        for key in ("summary", "run_instance", "producer"):
            assert out[key], f"{key} did not render; nothing measured"
        start = out["summary"]["top"] / out["total"]
        assert start >= 2 / 3, (
            f"the identity group starts at {100 * start:.0f}% of the "
            f"document at {width}x{height}, not in the last third")

    @pytest.mark.parametrize("width,height", VIEWPORTS)
    def test_the_identity_blocks_are_adjacent(self, browser, report,
                                              width, height):
        """"Adjacent" as the reader meets it: no gap wider than a
        quarter-screen between the three of them. The DOM-order guard
        says nothing sits between; this says nothing *looks* like it
        does."""
        out = browser.measure(report, self._WHERE, width, height)
        gaps = [(out["run_instance"]["top"] - out["summary"]["bottom"]) / out["vh"],
                (out["producer"]["top"] - out["run_instance"]["bottom"]) / out["vh"]]
        assert max(gaps) <= 0.25, (
            f"identity blocks {max(gaps):.2f} screens apart at "
            f"{width}x{height}")

    @pytest.mark.parametrize("width,height", VIEWPORTS)
    def test_the_blast_control_is_above_the_midpoint(self, browser, report,
                                                     width, height):
        out = browser.measure(report, self._WHERE, width, height)
        assert out["blast-offline"], "the export drew no blast block"
        at = out["blast-offline"]["top"] / out["total"]
        assert at < 0.5, (
            f"the blast block sits at {100 * at:.0f}% of the document at "
            f"{width}x{height}")

    @pytest.mark.parametrize("width,height", VIEWPORTS[:2])
    def test_the_blast_control_is_within_two_screens_of_the_findings(
            self, browser, report, width, height):
        """The acceptance test's second clause, measured from the *end*
        of `findings` - the scroll a reader actually makes. Top-to-top
        is 2.96 screens on the 1,202-element run for a reason that is
        not a defect: `findings` is itself 1.98 screens tall there, so
        nothing outside it can be within two screens of its top.

        **The two desktop viewports, not all three.** On the 390x844
        phone the same page measures 2.16 screens, and the two screens
        cannot be met by any placement that keeps the diagnosis
        together: `headline` and `next_steps` reflow to 0.93 and 1.11
        screens there, so the narrative alone is 2.04. The clause that
        does hold at every width is the one below - nothing but that
        narrative separates them.

        ```text
                     document   findings   headline   next_steps    gap
        1440x900       11.32       1.12       0.50        0.31      0.92
        1280x800       12.79       1.26       0.56        0.35      1.03
         390x844       20.49       1.55       0.93        1.11      2.16
        ```
        """
        out = browser.measure(report, self._WHERE, width, height)
        gap = (out["blast-offline"]["top"] - out["findings"]["bottom"]) / out["vh"]
        assert gap <= 2.0, (
            f"{gap:.2f} screens between the end of the findings and the "
            f"blast block at {width}x{height}")

    @pytest.mark.parametrize("width,height", VIEWPORTS)
    def test_only_the_diagnosis_separates_them(self, browser, report,
                                               width, height):
        """The width-independent form of the clause above, and the one
        that says what "near findings" means: the only thing between the
        finding and the control is `headline` and `next_steps` - the two
        blocks that turn the finding into a diagnosis and name
        `bga blast` as the command to run. A block inserted between them
        widens this gap beyond what those two occupy, at any width."""
        out = browser.measure(report, self._WHERE, width, height)
        gap = out["blast-offline"]["top"] - out["findings"]["bottom"]
        narrative = out["headline"]["bottom"] - out["headline"]["top"] \
            + out["next_steps"]["bottom"] - out["next_steps"]["top"]
        # A quarter-screen of slack for the margins between four blocks;
        # measured at 0.05-0.12 screens across the three viewports.
        assert gap <= narrative + 0.25 * out["vh"], (
            f"{(gap - narrative) / out['vh']:.2f} screens beyond the "
            f"diagnosis between the findings and the blast block at "
            f"{width}x{height}")


@needs_node
@needs_browser
class TestChaptersCostNoHeight:
    """`UX-286`'s third clause, and Direction 13's refusal of the other
    half of the proposal it came from.

    Grouping was accepted on the argument that it adds structure and not
    height; padding each section to one screen was refused on the
    measurement that it adds 31.3 screens of whitespace to the synthetic
    run. Both halves are checked here, because "chapters" implemented as
    a fixed grid would satisfy every other guard in the suite.

    Measured on the exported golden report after this landed:

    ```text
                    document   headings   heading cost   section heights
    1440x900          11.29      0.33 scr      2.9%      0.07 - 1.17 (16x)
    1280x800          12.76      0.37         2.9%       0.08 - 1.31 (16x)
     390x844          20.58      0.47         2.3%       0.08 - 3.20 (42x)
    ```

    The document was 11.32 screens before the chapters and 11.29 after:
    the seven headings are paid for by the space the sections no longer
    need between them, which is the whole claim.
    """

    _COST = """
    (() => {
      const vh = window.innerHeight;
      const total = document.documentElement.scrollHeight;
      const titles = [...document.querySelectorAll("h2.chapter-title")];
      const heads = titles.reduce(
        (sum, n) => sum + n.getBoundingClientRect().height, 0);
      const chapters = [...document.querySelectorAll("section.chapter")]
        .map((box) => {
          const own = box.getBoundingClientRect().height;
          const inner = [...box.querySelectorAll("section[data-section]")]
            .reduce((sum, n) => sum + n.getBoundingClientRect().height, 0);
          return { id: box.dataset.chapter, slack: (own - inner) / vh };
        });
      const heights = [...document.querySelectorAll("main section[data-section]")]
        .map((s) => s.getBoundingClientRect().height / vh);
      return { total: total / vh, headings: heads / vh, chapters,
               tallest: Math.max(...heights), shortest: Math.min(...heights),
               sections: heights.length };
    })()
    """

    @pytest.mark.parametrize("width,height", VIEWPORTS)
    def test_the_headings_cost_a_twentieth_of_the_document_at_most(
            self, browser, report, width, height):
        out = browser.measure(report, self._COST, width, height)
        assert out["chapters"], "the page drew no chapters"
        share = out["headings"] / out["total"]
        assert share <= 0.05, (
            f"the chapter headings are {100 * share:.1f}% of the document "
            f"at {width}x{height}")

    @pytest.mark.parametrize("width,height", VIEWPORTS)
    def test_no_chapter_pads_its_sections(self, browser, report,
                                          width, height):
        """A chapter is as tall as what is in it. The difference between
        a chapter's height and the sum of its sections is its heading
        and the margins around it - a quarter-screen of slack, not the
        several screens a fixed-height grid would introduce."""
        out = browser.measure(report, self._COST, width, height)
        padded = {chapter["id"]: round(chapter["slack"], 2)
                  for chapter in out["chapters"] if chapter["slack"] > 0.25}
        assert padded == {}, (
            f"{padded} screens of chapter beyond their sections at "
            f"{width}x{height}")

    @pytest.mark.parametrize("width,height", VIEWPORTS)
    def test_the_sections_are_still_as_tall_as_their_content(
            self, browser, report, width, height):
        """Direction 13's refusal, guarded: section height spans a 49x
        range across the two runs because ten sections on each size
        themselves from the run. A layout that equalised them would
        read as "chapters" and be the change the measurement refused."""
        out = browser.measure(report, self._COST, width, height)
        assert out["sections"] >= 10, out["sections"]
        spread = out["tallest"] / max(out["shortest"], 0.001)
        assert spread >= 8, (
            f"the tallest section is only {spread:.1f}x the shortest at "
            f"{width}x{height} - something is equalising them")


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
