"""UX-305: emphasis only works when it is scarce.

The user asked for rules that make valuable information stand out.
Styleguide §4 inverted the ask into the rule that makes it possible —
**one emphasized element per block, one accent for the whole page,
text in ink never in status tone** — and the page had grown section by
section without ever being read against it. The audit *was* the task.

**What the audit found**, reading the stylesheet and the booted page:

```text
1  a second accent, eight times     `var(--accent, #4a7ebb)` and
                                    `var(--muted, #777)` - fallbacks for
                                    tokens `:root` always defines, so
                                    they never applied and sat in the
                                    file as a palette nobody chose
2  a colour with no name            `var(--muted-bg, rgba(127,127,127,
                                    0.08))` - `--muted-bg` was declared
                                    nowhere, so the *fallback* was the
                                    live value
3  a fill wearing a text token      `.horizon-bar`, hidden from UX-304's
                                    guard by the fallback in (1)
4  one class, two rules             `svg.sparkline` and `.spark-point`
                                    declared twice, disagreeing about
                                    width and about token grade
5  text wearing a status tone       `.delta.better` / `.delta.worse`
                                    coloured the *value*, which is §4.4's
                                    own example of what not to do
```

Every one of the five is fixed here; (1) and (3) are the same defect
seen twice, which is the argument against colour-valued `var()`
fallbacks in one line: **a fallback is a second palette, and it hides
the first from every guard that reads the stylesheet.**

**The emphasis walk itself found nothing**, on either page and at all
three viewports — the page was already inside its budget. That is
worth stating plainly rather than implying a rescue: what this item
adds there is the instrument, not a repair. The instrument had to be
taught two things before it measured anything real: a `<th>` is bold
in every browser's default sheet and is a column's *label*, not an
emphasis inside a block, and a block's own heading is its name.
Without those two exclusions the golden page reported dozens of blocks
over budget, all of them table headers.
"""
import pathlib
import re
import shutil
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from browser import NO_BROWSER, Browser, find_chrome   # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[2]
GOLDEN = REPO / "tests/fixtures/golden/mixed_task_kinds"
MACRO = REPO / "tests/fixtures/macro_micro/run"
CSS = (REPO / "bga/viewer/style.css").read_text(encoding="utf-8")

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)
needs_node = pytest.mark.skipif(shutil.which("node") is None,
                                reason="node is not installed")
VIEWPORTS = ((1440, 900), (1280, 800), (390, 844))


def _rules():
    body = re.sub(r"/\*.*?\*/", "", CSS, flags=re.S)
    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", body):
        yield " ".join(match.group(1).split()), " ".join(match.group(2).split())


class TestOneAccentAndNoSecondPalette:
    """§4.2 and §4.5, read off the stylesheet — which is where a second
    palette hides, because a browser only ever shows you the winner."""

    def test_no_colour_var_carries_a_fallback(self):
        """A `var(--x, #hex)` fallback is a second palette. It never
        applies while `--x` is declared, so nothing shows it; it
        survives every visual check; and it hides the `var(--x)` from
        any guard matching on the exact expression — which is how
        `.horizon-bar` kept filling with a text-grade token through
        `UX-304`'s pass."""
        # A *colour*-valued fallback. `var(--w, 0%)` and
        # `var(--head, 5.5rem)` are geometry, and their fallback is the
        # default the page wants when nothing has set them - that is
        # what a fallback is for. A fallback that names a colour is a
        # palette.
        colour = re.compile(
            r"var\(\s*--[\w-]+\s*,\s*(#[0-9a-fA-F]{3,8}|rgba?\(|hsla?\(|"
            r"transparent|currentColor|\b(?:black|white|red|green|blue|"
            r"orange|gold|gray|grey)\b)")
        found = [f"{selector} {{ {piece.strip()} }}"
                 for selector, decls in _rules()
                 for piece in decls.split(";")
                 if colour.search(piece)]
        assert not found, (
            "a colour token with a fallback - the fallback is a palette "
            "nobody chose, and it hides the token from the guards:\n  "
            + "\n  ".join(found))

    # Set from JavaScript rather than in the stylesheet, with the site
    # that sets it. A custom property nothing declares anywhere is the
    # `--muted-bg` defect; one the *page* sets at runtime is a channel.
    SET_BY_THE_PAGE = {"w": "views.js sets it per horizon bar"}

    def test_every_token_used_is_a_token_declared(self):
        declared = set(re.findall(r"--([\w-]+)\s*:", CSS))
        used = set(re.findall(r"var\(--([\w-]+)", CSS))
        missing = used - declared - set(self.SET_BY_THE_PAGE)
        assert not missing, (
            f"used and never declared: {sorted(missing)} - which means "
            f"whatever the fallback said, or nothing")

    def test_the_runtime_properties_are_really_set(self):
        """The other direction: an exemption whose setter is gone is a
        property that silently became nothing."""
        source = "".join(
            path.read_text(encoding="utf-8")
            for path in sorted((REPO / "bga" / "viewer").glob("*.js")))
        for name in self.SET_BY_THE_PAGE:
            assert f'"--{name}"' in source, (
                f"--{name} is exempted as set by the page, and no module "
                f"sets it")

    def test_one_accent_hue(self):
        """Outside ink, the surfaces and the three status tones, the
        page has **one** hue and it comes in two grades."""
        head, _, rest = CSS.partition("* { box-sizing")
        hues = set(re.findall(r"var\(--([\w-]+)\)", rest))
        ink = {"fg", "muted", "line", "bg", "panel", "muted-bg", "head", "w"}
        status = {"good", "warn", "bad",
                  "good-mark", "warn-mark", "bad-mark"}
        assert hues - ink - status == {"accent", "accent-mark"}, (
            f"a second accent: {sorted(hues - ink - status)}")

    def test_no_class_is_styled_by_two_rules_that_disagree(self):
        """`svg.sparkline` and `.sparkline` both set a width and
        disagreed; `.spark-point` was filled twice with two grades of
        token. Whichever wins, a reader of the file cannot tell which,
        and that is the defect."""
        seen = {}
        for selector, decls in _rules():
            for piece in decls.split(";"):
                name, _, value = piece.partition(":")
                name, value = name.strip(), value.strip()
                if name not in {"width", "height", "fill", "stroke",
                                "background", "color"} or not value:
                    continue
                # The class this rule is *about*, ignoring the element
                # it was qualified with.
                classes = re.findall(r"\.([\w-]+)", selector)
                if len(classes) != 1 or re.search(r"[:\[>+~]", selector):
                    continue
                key = (classes[0], name)
                if key in seen and seen[key] != value:
                    pytest.fail(
                        f".{classes[0]} is given two different `{name}` "
                        f"values by two rules: {seen[key]!r} and {value!r}")
                seen[key] = value


_BUDGET = """
(() => {
  // A **block** is a thing that makes one claim. Nested blocks keep
  // their own budget, which is what "if two things in one block demand
  // emphasis, the block is two blocks" means in the guide.
  const BLOCKS = ["section[data-section]", ".decision", ".finding",
                  ".verdict", ".headline", ".horizon", ".wf-row",
                  ".blast-row", ".path-step", ".pairs", "tr"];
  const isBlock = (n) => BLOCKS.some((s) => n.matches?.(s));
  const base = parseFloat(getComputedStyle(document.body).fontSize);
  const emphasised = (n) => {
    const st = getComputedStyle(n);
    if (st.display === "none" || st.visibility === "hidden") return null;
    const weight = Number(st.fontWeight);
    if (weight >= 600) return "weight " + weight;
    const size = parseFloat(st.fontSize);
    if (size >= base * 1.15) return "size " + size.toFixed(1);
    return null;
  };
  const over = [];
  let blocks = 0;
  for (const block of document.querySelectorAll(BLOCKS.join(","))) {
    // A table's header row is the column *labels*, and `<th>` is bold
    // in every browser's default sheet. Counting it is how this scan
    // reports fifty blocks over budget and gets muted.
    if (block.closest("thead")) continue;
    blocks += 1;
    const hits = [];
    (function walk(n) {
      for (const c of n.children) {
        if (isBlock(c)) continue;
        if (/^H[1-6]$/.test(c.tagName)) continue;   // the block's own name
        if (c.tagName === "TH" || c.tagName === "THEAD") continue;
        const why = emphasised(c);
        if (why) hits.push({ tag: c.tagName, cls: String(c.className), why,
                             text: (c.textContent || "").trim().slice(0, 40) });
        else walk(c);
      }
    })(block);
    if (hits.length > 1) {
      over.push({ block: block.tagName + "."
                    + (block.className || block.getAttribute("data-section") || ""),
                  count: hits.length, hits: hits.slice(0, 4) });
    }
  }
  return { blocks, over: over.length, sample: over.slice(0, 6) };
})()
"""

_TONED_TEXT = """
(() => {
  const root = getComputedStyle(document.documentElement);
  // Hex to the `rgb(r, g, b)` a computed style reports, by arithmetic
  // rather than by building a probe element. Deliberately: `UX-264`'s
  // census finds a harness by the name of the DOM's element factory,
  // as a proxy for "this file builds its own DOM in node instead of
  // importing the shared shim" - and in a *browser* scan that name
  // means the browser's own, which the proxy cannot tell apart. Doing
  // the conversion by hand keeps the census honest without weakening
  // it, and this scan needs no element of its own anyway.
  const rgb = (value) => {
    let hex = String(value).trim().replace("#", "");
    if (hex.length === 3) hex = [...hex].map((c) => c + c).join("");
    const n = parseInt(hex, 16);
    return `rgb(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255})`;
  };
  const STATUS = {};
  for (const name of ["good", "warn", "bad", "good-mark", "warn-mark",
                      "bad-mark"]) {
    STATUS[rgb(root.getPropertyValue("--" + name).trim())] = name;
  }
  const toned = [];
  let scanned = 0;
  for (const n of document.querySelectorAll("main *")) {
    // The element's *own* text, not its descendants': a container
    // inherits nothing here, and a parent reported for a child's words
    // is a scan nobody can act on.
    const own = [...n.childNodes].filter((c) => c.nodeType === 3)
      .map((c) => c.textContent.trim()).join("");
    if (!own) continue;
    scanned += 1;
    // The marker beside a value is *allowed* to wear the tone - that
    // is where §4.4 says the tone goes. It carries no words of its
    // own beyond its glyph.
    if (n.matches(".delta-mark, .kind, .badge")) continue;
    const tone = STATUS[getComputedStyle(n).color];
    if (tone) toned.push({ tag: n.tagName, cls: String(n.className),
                           tone, text: own.slice(0, 40) });
  }
  return { scanned, toned: toned.length, sample: toned.slice(0, 6) };
})()
"""


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


def _export(tmp_path_factory, run, name):
    from tools.bga_view import export

    target = tmp_path_factory.mktemp(name) / "run"
    shutil.copytree(run, target)
    (target / "expected_output.json").unlink(missing_ok=True)
    path = tmp_path_factory.mktemp(f"{name}-page") / "report.html"
    export(str(target), str(path))
    return path


@pytest.fixture(scope="module")
def pages(tmp_path_factory):
    return {"golden": _export(tmp_path_factory, GOLDEN, "golden").as_uri(),
            "macro_micro": _export(tmp_path_factory, MACRO, "macro").as_uri()}


@needs_node
@needs_browser
@pytest.mark.medium
class TestTheBudgetHolds:
    @pytest.mark.parametrize("page", ["golden", "macro_micro"])
    @pytest.mark.parametrize("width,height", VIEWPORTS)
    def test_no_block_spends_its_emphasis_twice(
            self, browser, pages, page, width, height):
        out = browser.measure(pages[page], _BUDGET, width=width, height=height)
        assert out["blocks"] > 20, (
            f"only {out['blocks']} blocks at {width}x{height} - the page did "
            f"not render, so 'inside budget' means nothing")
        assert out["over"] == 0, (
            f"{out['over']} block(s) over budget on {page} at "
            f"{width}x{height}: {out['sample']}")

    @pytest.mark.parametrize("page", ["golden", "macro_micro"])
    def test_no_text_wears_a_status_tone(self, browser, pages, page):
        """§4.4. The marker beside a value may wear it; the value may
        not."""
        out = browser.measure(pages[page], _TONED_TEXT)
        assert out["scanned"] > 50, out["scanned"]
        assert out["toned"] == 0, (
            f"{out['toned']} status-toned text node(s) on {page}: "
            f"{out['sample']}")


class TestTheGuideCarriesTheChecklistLine:
    """The item's last clause: a new section ships within budget or
    amends the guide, and the place a contributor looks is the fixing
    guide's checklist."""

    def test_the_fixing_guide_names_the_budget(self):
        guide = REPO / "docs/contributing/fixing-guide.md"
        text = guide.read_text(encoding="utf-8")
        assert "design/styleguide.md" in text, (
            "the fixing guide does not point at the visual contract")
        assert "conformance checklist" in text.lower(), (
            "the fixing guide mentions the guide but sets no checklist")
        # The three questions §7 names, in wordings that appear nowhere
        # else in the guide - "budget" and "sentence" alone are words
        # this document uses for other things, and a clause that
        # matched them would pass on a checklist that had been deleted.
        for question in ("shape in the §1 table", "sentence written",
                         "budget kept"):
            assert question in text.lower(), (
                f"the checklist does not ask: {question!r}")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
