"""UX-674: eighteen computed font sizes, and an `h3` UA-default larger
than its own `h2`.

Measured on the booted golden export at 1440x900, before this item:
18 distinct `getComputedStyle(...).fontSize` values across every
element that carries text, from `body/td` at 15px to `h3` at 17.55px -
the browser's own `1.17em` default, on an element `style.css` never
set a size for, sitting *above* the 16.8px `h2` it renders under.

Styleguide §4f's fix is a four-step scale (`--font-h1/-h2/-body
/-small`) that every `font-size` declaration in `style.css` now
resolves to, `h3` folded into `--font-body` at weight 600 rather than
given a step of its own, and `p, li > p, dd {max-width: 72ch}` so a
line stays a line. This file is the guard: distinct computed sizes,
`h3` against `h2`, and no prose box wider than its own 72ch.
"""
import pathlib
import shutil
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from browser import NO_BROWSER, Browser, find_chrome

REPO = pathlib.Path(__file__).resolve().parents[2]
GOLDEN = REPO / "tests/fixtures/golden/mixed_task_kinds"
MACRO_MICRO = REPO / "tests/fixtures/macro_micro/run"

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)
needs_node = pytest.mark.skipif(shutil.which("node") is None,
                                 reason="node is not installed")

#: The scale itself (styleguide §4f). A guard against the rule, not
#: against today's stylesheet - a fifth value anywhere fails this.
SCALE_STEPS = 4


def _export(fixture, tmp_path_factory, name):
    from tools.bga_view import export

    run = tmp_path_factory.mktemp(name) / "run"
    shutil.copytree(fixture, run)
    (run / "expected_output.json").unlink(missing_ok=True)
    page = tmp_path_factory.mktemp(f"{name}-page") / "report.html"
    export(str(run), str(page))
    return page.as_uri()


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module")
def golden(tmp_path_factory):
    return _export(GOLDEN, tmp_path_factory, "scale-golden")


@pytest.fixture(scope="module")
def macro_micro(tmp_path_factory):
    return _export(MACRO_MICRO, tmp_path_factory, "scale-macro")


#: Every element that actually carries a text node, in the three
#: landmarks a reader's eye crosses - not just `main`, or the rail and
#: the sticky heading hide a fifth size from the count they are part
#: of the same page.
_SIZE_SCAN = """
(() => {
  const sizes = new Set();
  document.querySelectorAll("main *, header *, footer *, nav *")
    .forEach((n) => {
      const style = getComputedStyle(n);
      if (style.display === "none") return;
      const hasText = [...n.childNodes].some(
        (c) => c.nodeType === 3 && c.textContent.trim());
      if (hasText) sizes.add(style.fontSize);
    });
  return [...sizes];
})()
"""

_HEADING_SCAN = """
(() => {
  const px = (sel) => [...document.querySelectorAll(sel)]
    .map((n) => parseFloat(getComputedStyle(n).fontSize));
  return {h2: px("h2"), h3: px("h3")};
})()
"""

#: §4f's budget is 72 *characters*, not "whatever `max-width` happens
#: to say" - a rule widened to `130ch` would still pass a check against
#: its own declared `max-width`. So the ceiling here is measured
#: independently, from a canvas 2D context set to the box's own font,
#: as 72 widths of its widest common glyph - the same instrument a
#: `ch` unit itself is defined against.
_PROSE_SCAN = """
(() => {
  const ctx = new OffscreenCanvas(10, 10).getContext("2d");
  const hits = [];
  document.querySelectorAll("p, li > p, dd").forEach((n) => {
    const width = n.getBoundingClientRect().width;
    if (width <= 0) return;
    const cs = getComputedStyle(n);
    ctx.font = `${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
    const budget = ctx.measureText("0").width * 72;
    if (width > budget + 2) {
      hits.push({tag: n.tagName, cls: n.className,
                 width: Math.round(width), budget: Math.round(budget)});
    }
  });
  return hits;
})()
"""


@needs_node
@needs_browser
class TestTheScaleHasFourSteps:
    @pytest.mark.parametrize("page", ["golden", "macro_micro"])
    def test_distinct_computed_sizes_at_most_four(self, browser, page,
                                                   request):
        url = request.getfixturevalue(page)
        sizes = browser.measure(url, _SIZE_SCAN, width=1440, height=900)
        assert len(sizes) <= SCALE_STEPS, (
            f"{len(sizes)} distinct computed font sizes on {page}: "
            f"{sorted(sizes)} - §4f's scale is {SCALE_STEPS} steps "
            f"(UX-674)")

    def test_every_h3_is_smaller_than_every_h2(self, browser, golden):
        out = browser.measure(golden, _HEADING_SCAN, width=1440, height=900)
        assert out["h2"] and out["h3"], (
            "no h2/h3 on the golden page - this claim needs both to exist "
            f"to mean anything: {out}")
        assert max(out["h3"]) < min(out["h2"]), (
            f"an h3 ({max(out['h3'])}px) is at or above an h2 "
            f"({min(out['h2'])}px) - the unstyled UA default (1.17em) is "
            f"back (UX-674)")

    @pytest.mark.parametrize("page", ["golden", "macro_micro"])
    def test_no_prose_box_exceeds_its_own_72ch(self, browser, page, request):
        url = request.getfixturevalue(page)
        hits = browser.measure(url, _PROSE_SCAN, width=1440, height=900)
        assert hits == [], (
            f"{len(hits)} prose box(es) wider than their own computed "
            f"max-width on {page}: {hits[:5]} - `p, li > p, dd "
            f"{{max-width: 72ch}}` (styleguide §4f) is not reaching them "
            f"(UX-674)")


class TestTheScaleIsDeclared:
    """The rule as written, independent of any one render."""

    def test_the_stylesheet_names_four_tokens(self):
        css = (REPO / "bga/viewer/style.css").read_text(encoding="utf-8")
        for token in ("--font-h1", "--font-h2", "--font-body",
                      "--font-small"):
            assert f"{token}:" in css, (
                f"{token} is not declared in style.css - §4f's scale is "
                "four named steps, not four numbers picked ad hoc "
                "(UX-674)")

    def test_the_72ch_rule_is_declared(self):
        css = (REPO / "bga/viewer/style.css").read_text(encoding="utf-8")
        assert "max-width: 72ch" in css, (
            "no selector sets max-width: 72ch - styleguide §4f's line "
            "budget (UX-674)")

    def test_the_skip_reason_is_declared(self):
        conftest = (REPO / "tests/conftest.py").read_text(encoding="utf-8")
        assert NO_BROWSER in conftest, (
            "the no-browser skip is not in the census, so these guards can "
            "go quiet on every machine and the suite stays green (UX-235)")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
