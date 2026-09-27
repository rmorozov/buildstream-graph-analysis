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
import re
import shutil
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

from pages import export_uri, scale_run
from pages import pages as fixture_pages

from tests.browser import NO_BROWSER, Browser, find_chrome

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
    # UX-1027 (styleguide §6e.5): accent fill, at most one per chapter -
    # `--accent-mark`'s light-theme value (a fill takes the mark grade,
    # not the text grade `test_the_palette_is_validated.py` holds it to;
    # this is its computed color, read the same way every other grade
    # here is).
    "primary": ("rgb(43, 87, 151)", "solid", "3px"),
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


#: UX-1027: every chapter a `button.primary` lands in, forced open
#: first - a chapter other than the first is folded by default and a
#: query over a folded page would undercount.
PRIMARY_PER_CHAPTER = """
(() => {
  document.querySelectorAll("section.chapter").forEach(
    (c) => c.setAttribute("data-open", "true"));
  const counts = {};
  document.querySelectorAll("button.primary").forEach((b) => {
    const chapter = b.closest("section[data-chapter]");
    const key = chapter ? chapter.getAttribute("data-chapter") : "(none)";
    counts[key] = (counts[key] ?? 0) + 1;
  });
  return JSON.stringify(counts);
})()
"""


def _primary_per_chapter(uri, opened):
    return json.loads(opened.observe(uri, PRIMARY_PER_CHAPTER)["value"])


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

    def test_at_most_one_primary_control_per_chapter(self, tmp_path_factory):
        """UX-1027 (styleguide §6e.5): §6a's row, never decided until
        this - a chapter with no runnable next step wears no primary
        rather than a promoted lesser control."""
        scale = scale_run(tmp_path_factory.mktemp("primary-scale"))
        pages = {"macro_micro": export_uri(MACRO, tmp_path_factory.mktemp("primary-macro")),
                 "scale": export_uri(scale, tmp_path_factory.mktemp("primary-page"))}
        with Browser(chrome) as opened:
            for name, uri in pages.items():
                counts = _primary_per_chapter(uri, opened)
                over = {k: v for k, v in counts.items() if v > 1}
                assert over == {}, (name, over)


#: `UX-834`: the disclosure buttons this repository already gives
#: `aria-expanded` (round 115's design review), plus `twin-toggle` -
#: named explicitly because it is the one the review found missing.
#: `path-more` is excluded on purpose: it reveals once and hides
#: itself rather than toggling back, so it is not this shape.
DISCLOSURE_BUTTONS = (
    "button.collapse", "button.json-toggle", "button.chapter-open",
    "button.twin-toggle",
)

DISCLOSURE_JS = (
    "(() => { const selectors = " + json.dumps(DISCLOSURE_BUTTONS) + "; "
    "const out = {}; "
    "for (const sel of selectors) { "
    "  const button = document.querySelector(sel); "
    "  if (!button) { out[sel] = null; continue; } "
    "  const before = button.getAttribute('aria-expanded'); "
    "  button.click(); "
    "  const after = button.getAttribute('aria-expanded'); "
    "  button.click(); "
    "  const restored = button.getAttribute('aria-expanded'); "
    "  out[sel] = {before, after, restored}; "
    "} "
    "const box = document.querySelector('a.path-box'); "
    "out['a.path-box'] = box ? box.getAttribute('aria-label') : null; "
    "return JSON.stringify(out); })()"
)


@pytest.fixture(scope="module")
def disclosures(tmp_path_factory):
    """Every named disclosure button's `aria-expanded`, clicked twice,
    plus `a.path-box`'s `aria-label` - on the same two pages `drawn`
    boots, so a fold (`scale`, folded past `PATH_HEAD+PATH_TAIL`) and
    an unfolded path (`macro_micro`) are both read. No `chrome`/`node`
    guard here: `TestDisclosuresAndLinksAreLegible`'s own `@needs_browser`
    `@needs_node` already skip every test that would request this
    fixture, so a second `NO_BROWSER` site would count nothing new."""
    scale = scale_run(tmp_path_factory.mktemp("scale-834"))
    pages = {"macro_micro": export_uri(MACRO, tmp_path_factory.mktemp("macro-834")),
             "scale": export_uri(scale, tmp_path_factory.mktemp("page-834"))}
    with Browser(chrome) as opened:
        yield {name: json.loads(opened.observe(uri, DISCLOSURE_JS)["value"])
               for name, uri in pages.items()}


@needs_browser
@needs_node
class TestDisclosuresAndLinksAreLegible:
    """UX-834. Measured on the golden export before the fix:
    `twin-toggle` had no `aria-expanded` at all (`null` before and
    after a click); `path-box`'s accessible name glued three spans
    into `"base.bst0.0 sunknown"`, no separator."""

    def test_every_named_disclosure_flips_aria_expanded(self, disclosures):
        for name, found in disclosures.items():
            for sel in DISCLOSURE_BUTTONS:
                state = found.get(sel)
                if state is None:
                    continue    # not every page carries every control
                assert state["before"] in ("true", "false"), (name, sel, state)
                assert state["after"] != state["before"], (name, sel, state)
                assert state["restored"] == state["before"], (name, sel, state)

    def test_the_twin_toggle_is_checked_on_both_pages(self, disclosures):
        """The field pass's own example - if this selector ever stops
        matching, the clause above silently checks nothing for it."""
        for name, found in disclosures.items():
            assert found.get("button.twin-toggle") is not None, name

    def test_path_box_name_separates_its_three_values(self, disclosures):
        for name, found in disclosures.items():
            label = found.get("a.path-box")
            assert label, name
            parts = [part.strip() for part in label.split(",")]
            assert len(parts) >= 2 and all(parts), (name, label)


#: UX-1051 (styleguide §6d's sixth grade, **form-control**): the tokens
#: `.top-n` already draws with, read per scheme from `style.css`'s two
#: `:root` blocks (`--panel`, `--line`) rather than hardcoded, so a
#: token edit moves the expectation with it instead of silently
#: reddening for the wrong reason.
_ROOT = REPO / "bga/viewer/style.css"


def _root_tokens(css, marker=None):
    head, _, _ = css.partition("* { box-sizing")
    block = head if marker is None else head.split(marker, 1)[1]
    body = block.split(":root {", 1)[1].split("}", 1)[0]
    return dict(re.findall(r"--([\w-]+)\s*:\s*(#[0-9a-fA-F]{3,6})\s*;", body))


def _rgb(hexvalue):
    hexvalue = hexvalue.lstrip("#")
    if len(hexvalue) == 3:
        hexvalue = "".join(c * 2 for c in hexvalue)
    r, g, b = (int(hexvalue[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgb({r}, {g}, {b})"


_CSS = _ROOT.read_text(encoding="utf-8")
_TOKENS = {"dark": _root_tokens(_CSS),
           "light": _root_tokens(_CSS, "@media (prefers-color-scheme: light)")}

#: The three looks a `select` or text `input` renders in today, keyed
#: on (background, border-style, border-radius) - border color is
#: `--line` in every one of them, so it is not part of the key.
#: `form-control` is this item's base rule (`.top-n`'s tokens); the
#: other two predate it (`#jump`/`.table-filter` on `--panel`,
#: `.th-filter`/`[data-role=blast-form] input` on `--bg`, the latter
#: one radius step down).
FORM_LOOKS = {
    scheme: {
        "form-control": (_rgb(tok["panel"]), "solid", "3px"),
        "on-surface": (_rgb(tok["bg"]), "solid", "3px"),
        "on-surface-thin": (_rgb(tok["bg"]), "solid", "2px"),
    }
    for scheme, tok in _TOKENS.items()
}

FORM_JS = """
(() => JSON.stringify([...document.querySelectorAll("select, input")]
  .filter((el) => el.tagName === "SELECT" || el.type === "text"
                || el.type === "search")
  .map((el) => {
    const s = getComputedStyle(el);
    const name = el.tagName.toLowerCase()
      + (el.className ? "." + el.className.trim().split(/\\s+/).join(".") : "")
      + (el.id ? "#" + el.id : "");
    return [name, s.backgroundColor, s.borderTopStyle, s.borderRadius];
  })))()
"""


@pytest.fixture(scope="module")
def forms(tmp_path_factory):
    """`{scheme: {page: [(name, background, border-style, radius), ...]}}`
    - `golden` and `macro_micro`, light and dark, one browser."""
    if chrome is None or shutil.which("node") is None:    # pragma: no cover
        pytest.skip(NO_BROWSER)
    uris = fixture_pages(tmp_path_factory, prefix="forms")
    out = {}
    with Browser(chrome) as opened:
        for scheme in ("light", "dark"):
            out[scheme] = {
                name: [tuple(row) for row in json.loads(
                    opened.observe(uri, FORM_JS, scheme=scheme)["value"])]
                for name, uri in uris.items()
            }
    return out


@needs_browser
@needs_node
class TestEverySelectAndTextInputRests:
    """UX-1051. `style.css:824` gave `.preset-view` only a font size and
    `.run-picker select` (`style.css:1372`) only a font size and a
    width - both fell through to the browser's own control beside
    `.top-n`, drawn from tokens, in the same tool row. One base rule on
    `select, input[type="text"], input[type="search"]` closes both."""

    def test_the_pages_really_have_form_controls(self, forms):
        for scheme, pages_ in forms.items():
            for page, rows in pages_.items():
                assert len(rows) >= 3, (scheme, page, len(rows))

    def test_every_control_is_one_of_the_declared_looks(self, forms):
        """Not a count: a bound alone lets one grade drift into
        another's look and still pass (mirrors the button guard
        above)."""
        for scheme, pages_ in forms.items():
            named = set(FORM_LOOKS[scheme].values())
            for page, rows in pages_.items():
                stray = sorted((name, bg, style, radius)
                                for name, bg, style, radius in rows
                                if (bg, style, radius) not in named)
                assert stray == [], (scheme, page, stray)

    def test_the_preset_view_wears_the_form_control_look(self, forms):
        """The item's named defect: two dropdowns, one tool row, one
        look now."""
        for scheme, pages_ in forms.items():
            wanted = FORM_LOOKS[scheme]["form-control"]
            for page, rows in pages_.items():
                found = {name: (bg, style, radius)
                         for name, bg, style, radius in rows}
                preset = [name for name in found if "preset-view" in name]
                assert preset, (scheme, page, sorted(found))
                for name in preset:
                    assert found[name] == wanted, (scheme, page, name, found[name])

    def test_the_reader_and_view_selects_match(self, forms):
        """`select.top-n` and `select.preset-view` are one tool row -
        `UX-369`'s own claim, checked rather than assumed."""
        for scheme, pages_ in forms.items():
            for page, rows in pages_.items():
                found = {name: (bg, style, radius)
                         for name, bg, style, radius in rows}
                top_n = [v for k, v in found.items() if "top-n" in k]
                preset = [v for k, v in found.items() if "preset-view" in k]
                if top_n and preset:
                    assert set(top_n) == set(preset), (scheme, page, found)
