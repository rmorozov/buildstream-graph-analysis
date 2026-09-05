"""UX-436: forty-four controls were the browser's, not the page's.

`style.css` had **no base `button` rule**. Controls were styled where a
section happened to need one and the rest got the UA default. Counted
over the booted export at 1440x900, before this item:

```text
                    macro_micro      scale (seed 1)
buttons                     429                1591
distinct looks               11                   -
UA-default surface           52                   -
```

and the signature line, 44 of them:

```text
rgb(239, 239, 239) | 2px outset rgb(0, 0, 0) | 0px | 1px 6px | 12.75px
```

`2px outset` on beveled grey is the 1995 UA button inside a page that
otherwise runs on a declared token palette. After:

```text
                    macro_micro      scale (seed 1)
buttons                     429                1591
distinct looks                3                   4
UA-default surface            0                   0
```

**Four grades, not three.** The item asked for three; the page has four,
and the fourth is `GRADES["reveal"]` - `fold-more` and `path-more`,
dashed rather than solid because they show more of what is already on
the page rather than acting on it. There are exactly two of them and
they now match each other, so it is a grade rather than one control's
exception. Deleting a real distinction to reach a number would be the
number driving the design.

`macro_micro` shows three because it has no folded table and no long
path - which is why the bound below is read at scale as well, and why
this file boots two pages rather than one.

**What this is not.** §6a refuses motion and ornament on the export
constraint and that refusal stands: no transition, no shadow, nothing
that needs a server. A control that looks like the page it is in
requires no animation.
"""
import collections
import json
import pathlib
import shutil
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

from browser import NO_BROWSER, Browser, find_chrome
from pages import export_uri, scale_run

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)
needs_node = pytest.mark.skipif(shutil.which("node") is None,
                                reason="node is not installed")

MACRO = REPO / "tests/fixtures/macro_micro/run"

#: The grades §6d names, by the part of the appearance that carries
#: them: `(background, border-style, border-radius)`. Read rather than
#: counted - a bound alone would let one grade drift into another's
#: look and still pass, which is how twelve arrived.
GRADES = {
    "standing": ("rgb(242, 242, 242)", "solid", "3px"),
    "quiet": ("rgba(0, 0, 0, 0)", "solid", "3px"),
    "reveal": ("rgba(0, 0, 0, 0)", "dashed", "3px"),
    "door": ("rgba(0, 0, 0, 0)", "solid", "50%"),
}

#: What a control drawn by nobody looks like: the UA button.
UA_BEVEL = "outset"

LOOKS = """
(() => JSON.stringify([...document.querySelectorAll("button")].map((b) => {
  const s = getComputedStyle(b);
  return [s.backgroundColor, s.borderTopStyle, s.borderRadius, s.padding,
          s.fontSize, s.color, s.transitionDuration, s.boxShadow];
})))()
"""


def _looks(uri, opened):
    return [tuple(one) for one in json.loads(opened.observe(uri, LOOKS)["value"])]


@pytest.fixture(scope="module")
def drawn(tmp_path_factory):
    """Every button's computed appearance, on two pages, one browser."""
    if chrome is None or shutil.which("node") is None:    # pragma: no cover
        pytest.skip(NO_BROWSER)
    scale = scale_run(tmp_path_factory.mktemp("scale"))
    pages = {"macro_micro": export_uri(MACRO, tmp_path_factory.mktemp("macro")),
             "scale": export_uri(scale, tmp_path_factory.mktemp("page"))}
    with Browser(chrome) as opened:
        yield {name: _looks(uri, opened) for name, uri in pages.items()}


@needs_browser
@needs_node
class TestNoControlIsTheBrowsers:

    def test_the_pages_really_have_controls(self, drawn):
        """A page that drew none would pass every clause below."""
        for name, looks in drawn.items():
            assert len(looks) > 100, (name, len(looks))

    def test_nothing_renders_the_ua_button(self, drawn):
        """The 52. `outset` is a border style no rule in this
        repository has ever written, so its presence means the browser
        drew the control and nobody else did."""
        for name, looks in drawn.items():
            bevelled = [one for one in looks if one[1] == UA_BEVEL]
            assert bevelled == [], (name, len(bevelled), bevelled[:2])

    def test_every_control_is_one_of_the_named_grades(self, drawn):
        """Not a count: a bound alone lets one grade drift into
        another's look and still pass."""
        named = set(GRADES.values())
        for name, looks in drawn.items():
            stray = sorted({(one[0], one[1], one[2]) for one in looks} - named)
            assert stray == [], (name, stray)

    def test_the_grades_stay_four(self, drawn):
        """Twelve is what drift looks like. The bound is over the whole
        appearance, not just the three fields the grades are keyed on,
        so padding and font-size drift inside a grade reddens too."""
        for name, looks in drawn.items():
            seen = collections.Counter(looks)
            assert len(seen) <= len(GRADES), (
                f"{name}: {len(seen)} distinct control appearances, over the "
                f"{len(GRADES)} grades §6d names: "
                f"{json.dumps(sorted(seen), indent=1)[:900]}")

    def test_every_grade_is_actually_used(self, drawn):
        """A grade nothing draws is a rule nobody reads - the same
        emptiness `UX-306` holds the hint table to."""
        keyed = {(one[0], one[1], one[2]) for looks in drawn.values()
                 for one in looks}
        unused = sorted(name for name, look in GRADES.items()
                        if look not in keyed)
        assert unused == [], unused

    def test_no_control_animates_or_casts_a_shadow(self, drawn):
        """§6a's refusal, held rather than quietly relaxed: this item
        gave controls a resting appearance and spent nothing on motion.
        """
        for name, looks in drawn.items():
            moving = [one for one in looks
                      if one[6] not in ("0s", "0s, 0s", "") or one[7] != "none"]
            assert moving == [], (name, moving[:2])
