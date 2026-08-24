"""UX-254/UX-255: the chrome is beside the report, and the heading is first.

Reported from a real run and reproduced on `main` at `0.2.0` before a
line was changed. Measured in Chromium on the exported page of a
1,202-element run:

```text
                before                          after
viewport        toc      first content          toc width   first content
1280x800        573px    y=701  (87.6%)         18.8%       y=132  (16.5%)
1440x900        573px    y=701  (77.8%)         16.7%       y=132  (14.7%)
1920x1080       573px    y=701  (64.9%)         12.5%       y=132  (12.2%)
```

**What this file can and cannot check.** The viewer's harness is a
hand-rolled DOM shim in node with no layout engine — no box model, no
cascade, no `getBoundingClientRect`. It is why `UX-235` found `prepend`
implemented as `append` and every order guard reading a reversed
document: *"the page was never wrong; the instrument was."*

So the numbers above are measured by hand and **not held here**. What
is held is the *mechanism* that produces them: the grid that puts the
rail in its own column, the rail's own scroll, the breakpoint that
returns to one column, the offsets that keep an anchor clear of the
sticky heading, and the mount point that puts the heading first. Each
is a property a regression would have to delete, and deleting one is
what this file notices. `UX-257` is the open argument about the
instrument that could check the rest.
"""
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
CSS = (REPO / "bga/viewer/style.css").read_text(encoding="utf-8")
APP = (REPO / "bga/viewer/app.js").read_text(encoding="utf-8")
NAV = (REPO / "bga/viewer/nav.js").read_text(encoding="utf-8")
INDEX = (REPO / "bga/viewer/index.html").read_text(encoding="utf-8")


def _rule(selector):
    """Every declaration block for `selector`, joined.

    Not `re.search`: a selector legitimately appears more than once
    (placement in one rule, appearance in another), and taking the first
    made `test_the_heading_does_not_scroll_away` read the grid-area rule
    and miss the sticky one right below it.
    """
    blocks = re.findall(re.escape(selector) + r"\s*\{([^}]*)\}", CSS)
    return "\n".join(blocks) if blocks else None


def _code(source):
    """`source` with comments stripped.

    The mount check first read the whole file and matched the *comment*
    quoting the old `insertBefore(contents, document.body.firstChild)`
    as evidence that the old call was still there. That is the
    subject-versus-argument failure `UX-239` named, in a sixth place:
    a guard that greps source will find the line in the sentence that
    explains why the line was removed.
    """
    without_block = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
    return re.sub(r"^\s*//.*$", "", without_block, flags=re.M)


class TestTheRailIsItsOwnColumn:
    def test_the_page_becomes_a_grid_when_there_is_a_rail(self):
        block = _rule("body[data-has-toc]")
        assert block, "no `body[data-has-toc]` rule - the two-pane layout is gone"
        assert "grid" in block, block
        assert "grid-template-areas" in block, (
            "the panes are not placed by named areas, so which column the "
            "rail lands in is whatever source order happens to give")

    def test_every_pane_is_placed(self):
        """A grid with an unplaced child puts it wherever it fits, which
        is how a rail ends up back in the reading column."""
        for part in ("header", "nav.toc", "main", "footer"):
            block = _rule(f"body[data-has-toc] > {part}")
            assert block and "grid-area" in block, (
                f"{part} is not assigned a grid area")

    def test_the_rail_scrolls_itself(self):
        """The defect was a rail whose *length* was the page's problem.
        A run with four thousand elements must make the rail scroll,
        not the report start lower."""
        block = _rule("body[data-has-toc] > .toc")
        assert block, "the rail has no rule of its own in the grid"
        assert "overflow-y" in block and "max-height" in block, block

    def test_the_reading_column_can_shrink(self):
        """`minmax(0, 1fr)` rather than `1fr`: a grid track sized `1fr`
        will not go below its content's intrinsic width, so one wide
        table would push the rail off the screen."""
        block = _rule("body[data-has-toc]")
        assert "minmax(0, 1fr)" in block, block
        assert "min-width: 0" in (_rule("body[data-has-toc] > main") or ""), (
            "the reading column has no `min-width: 0`, so wide content "
            "widens the page instead of scrolling inside its own box")

    def test_the_group_that_grows_with_the_run_is_bounded(self):
        """`investigate` is one link per focused element. Bounded in CSS
        with its own scroll rather than truncated in JS, so every link
        stays reachable (`UX-203`)."""
        assert 'data-rail="investigate"' in CSS, (
            "nothing bounds the one rail group whose length is the run's")
        assert 'list.setAttribute("data-rail", rail)' in NAV, (
            "nav.js no longer tags each group, so the stylesheet cannot "
            "tell the growing one from the fixed ones")


class TestNarrowViewportsGetOneColumn:
    def test_there_is_a_breakpoint_back_to_one_column(self):
        assert re.search(r"@media \(max-width: 60rem\)", CSS), (
            "no single-column fallback - two panes on a phone is the same "
            "defect at a different width")

    def test_the_rail_folds_rather_than_filling_the_screen(self):
        assert 'data-folded="true"' in CSS, (
            "the folded state has no styling, so folding hides nothing")
        assert "foldOnNarrow" in APP, "nothing sets the folded state"

    def test_folding_is_guarded_against_a_browser_that_cannot_match(self):
        """`matchMedia` is absent in the node harness these guards boot
        the page in. A missing browser API must not stop the page."""
        fold = APP.split("export function foldOnNarrow", 1)[1].split("\n}", 1)[0]
        assert "matchMedia?." in fold, fold
        assert "defaultView?." in fold, fold

    def test_wide_content_scrolls_inside_its_own_box(self):
        """Measured at 390px before this: tables 217px wide against a
        390px viewport, so the whole report scrolled sideways."""
        assert "main table" in CSS and "overflow-x: auto" in CSS
        assert "min-width: min(12rem, 100%)" in CSS, (
            "the table filter still has a flat `min-width` that will not "
            "shrink, which is what widened the page at 390px")


class TestTheHeadingComesFirst:
    def test_the_contents_mount_after_the_heading(self):
        """This used to be `insertBefore(contents, body.firstChild)`,
        which put 573px of navigation above the run's own name."""
        code = _code(APP)
        before = code.split("const heading = document.querySelector", 1)[0]
        assert "insertBefore(contents, document.body.firstChild)" not in before, (
            "the contents are still mounted before the heading")
        assert "heading.after(contents)" in code, (
            "the contents are not mounted after the header, so DOM order - "
            "which is the order a screen reader and Tab follow - still "
            "leads with navigation")

    def test_the_heading_carries_the_producer_stamp(self):
        assert 'id="run-producer"' in INDEX, (
            "the heading has no slot for which build measured the run")
        assert "stampHeader" in APP

    def test_an_unstamped_run_says_so_rather_than_guessing(self):
        body = APP.split("export function stampHeader", 1)[1].split("\n}", 1)[0]
        assert "unrecorded build" in body, body
        assert "measured by ${tool} ${version}" in body

    def test_the_heading_does_not_scroll_away(self):
        block = _rule("body[data-has-toc] > header")
        assert block and "sticky" in block, block

    def test_an_anchor_lands_clear_of_the_heading(self):
        """The reader-visible half of "information overlaps": a jump
        that lands under the sticky heading. Measured after the fix at
        1440x900 and 390x844: 0px hidden."""
        assert "scroll-margin-top" in CSS, (
            "nothing offsets an anchor for the sticky heading")
        assert "--head" in CSS, (
            "the heading's height is not named once, so the rail's offset "
            "and the anchor's landing can drift apart")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))


class TestNoSectionGrowsWithoutBound:
    """UX-262: a table longer than the bound opens on its top rows.

    `UX-187` capped the tables that grow with *element count*. This one
    grows with **critical-path depth**, which nobody had a run deep
    enough to notice. Measured in Chromium at 1440x900:

    ```text
    run                             signals section       rows
    1,202 elements, shallow path      1884px  2.1 screens   24
      482 elements, 122-deep path     5539px  6.2 screens  132   <- before
      482 elements, 122-deep path     2292px  2.5 screens  132   <- after
    ```

    The section tripled while the run got *smaller*. As everywhere else
    in this file, the pixels are measured by hand and what is held here
    is the mechanism (`UX-257`).
    """

    def test_a_long_table_opens_bounded(self):
        code = _code(APP)
        assert "TABLE_OPENS_BOUNDED_ABOVE" in code, (
            "nothing bounds a table's default, so depth goes straight to "
            "the page")
        assert "if (total > TABLE_OPENS_BOUNDED_ABOVE)" in code, code[-1500:]

    def test_the_bound_clears_the_ordinary_case(self):
        """A bound that fired on the ordinary table would train readers
        to reset it every load. The 1,202-element run's widest table is
        26 rows; the 122-deep path is 132."""
        from bga.viewer import __name__ as _  # noqa: F401 - viewer is not importable

        found = re.search(r"TABLE_OPENS_BOUNDED_ABOVE = (\d+)", APP)
        assert found, "the bound is not a named constant"
        bound = int(found.group(1))
        assert 26 < bound < 132, (
            f"the bound is {bound}: it must clear the 1,202-element run's "
            f"widest table (26 rows) and catch a 122-deep critical path")

    def test_the_reader_still_sees_what_they_are_not_seeing(self):
        """`UX-208`'s rule: a reader who cannot see the denominator
        cannot tell a filtered table from a small one. Measured after:
        the badge reads `25 of 122`."""
        code = _code(APP)
        bounded = code.split("if (total > TABLE_OPENS_BOUNDED_ABOVE)", 1)[1]
        bounded = bounded.split("\n    }", 1)[0]
        assert "badgeText(" in bounded and "total" in bounded, bounded

    def test_all_rows_is_still_reachable(self):
        """Bounding the default must not remove the opt-out - `UX-187`
        chose top-N *plus* an escape and it works."""
        assert '"All rows"' in APP
