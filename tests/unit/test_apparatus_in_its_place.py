"""UX-317: a control's explanation lives with the control.

Styleguide §2b, from two field observations with one placement rule
between them.

**The header.** The save-the-trace sentence rendered in `<header>`,
under the run information and above everything — it "occupies precious
vertical height", and it explains a control that lives two blocks away
in the actions group. The header is *sticky*, so every pixel of it is
paid on every screen rather than once. Measured in Chromium on a served
page with the handoff group open, before and after:

```text
                        before      after
sticky header, 1440x900   172 px      92 px    -47%
sticky header,  390x844   284 px     134 px    -53%
blocks in the header         6           3
controls in the header       4           0
```

The `--head` token — what every anchor's `scroll-margin-top` and the
rail's sticky offset read — was **5.5rem against a 172px header**, so a
jump landed 84px under the heading. That is `UX-254`'s "information
overlaps" report in the one place a reader most often looks, and it is
fixed here as a side effect of the move: the token is now measured
against the header it describes, and a clause below holds it there.

**The descriptions.** `UX-201` sourced the "why does this number
matter" sentence from the schema and put it in a `title`, where
discovery is hover archaeology: the reader who does not know to hover
never learns what `scheduler_wait` means, and the one who does gets a
tooltip they cannot keep open while comparing two values. Every
described value now shows a visible `?` and opens its sentence beside
the value — to the right where the row has room, below where it does
not. Measured on the two committed exports: **60 described values on
the golden page, 72 on macro_micro**, one marker each.

The `title` stays. It costs nothing, it is what a screen reader and a
keyboard focus already read, and §4.3's rule is that hover is never the
*only* door — not that it must be shut.

**`UX-346` closed the door.** The sentence rendered whatever the marker
said — `.description { display: block }` beats `[hidden]`'s UA rule —
so this file's clauses held a mechanism that had no visual effect, and
43% of the golden page's words were the contract's glossary. The clause
below now reads `markers == described - inlined`: a `bga:inline` value keeps
its sentence and has no door, and everything else is behind one.
`tests/unit/test_a_sentence_lives_on_its_door.py` measures the closing
in a browser, where computed style is a fact rather than an attribute.
"""
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from browser import NO_BROWSER, Browser, find_chrome
from pages import snapshot_copy

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
VIEWER = REPO / "bga" / "viewer"
CSS = (VIEWER / "style.css").read_text(encoding="utf-8")
INDEX = (VIEWER / "index.html").read_text(encoding="utf-8")
GOLDEN = REPO / "tests/fixtures/golden/mixed_task_kinds"
MACRO = REPO / "tests/fixtures/macro_micro/run"
SHIM = str(REPO / "tests" / "dom_shim.mjs")

node = shutil.which("node")
chrome = find_chrome()
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

#: §2b.2's budget, in block-level lines. Identity is a name, a path and
#: a producer stamp; a fourth line in a sticky band is paid on every
#: screen, and the guard is what makes "the header carries identity
#: only" a rule rather than a preference.
HEADER_LINE_BUDGET = 3


# --------------------------------------------------------------------------
# 1. The header carries identity only.
# --------------------------------------------------------------------------

def _header_html():
    match = re.search(r"<header>(.*?)</header>", INDEX, re.S)
    assert match, "the page has no header at all"
    return match.group(1)


class TestTheHeaderCarriesIdentityOnly:
    def test_it_holds_no_control(self):
        """§2b.2. Not "few controls" - none: the header is what this run
        *is*, and every control is a thing to do about it."""
        body = re.sub(r"<!--.*?-->", "", _header_html(), flags=re.S)
        for tag in ("button", "select", "input", "<a "):
            assert tag not in body, (
                f"a {tag.strip('< ')} is back in the header: §2b.2 says "
                f"actions and their apparatus live in the actions group")

    def test_it_fits_the_line_budget(self):
        body = re.sub(r"<!--.*?-->", "", _header_html(), flags=re.S)
        blocks = re.findall(r"<(h1|p|div|ul|ol|table|section)\b", body)
        assert len(blocks) <= HEADER_LINE_BUDGET, (
            f"the header is {len(blocks)} lines against a budget of "
            f"{HEADER_LINE_BUDGET}: {blocks}. It is sticky, so each one is "
            f"paid on every screen.")

    def test_the_download_sentence_sits_under_the_control_it_explains(self):
        """§2b.1, and the exact line the field pass flagged twice: it
        explained the Perfetto handoff from two blocks above it."""
        group = re.search(r'<div id="actions-group".*?</div>', INDEX, re.S)
        assert group, "there is no actions group"
        body = group.group(0)
        for part in ('id="perfetto"', 'id="actions-fallback"',
                     'id="actions-download"'):
            assert part in body, f"{part} is not in the actions group"
        assert body.index('id="perfetto"') < body.index('id="actions-download"'), (
            "the explanation renders above the control it explains")
        assert 'id="actions-download"' not in _header_html()


@needs_browser
class TestTheHeaderIsAsSmallAsItSays:
    """The static clauses above count *tags*; these measure **pixels**,
    which is what a reader pays. Both, because a header could satisfy
    one and not the other - three lines of a 4rem font is still a
    screenful."""

    #: What a header may occupy of a viewport's height. 92px of 900 is
    #: 10%; 134px of 844 is 16%. Before this item: 19% and 34%.
    MAX_SHARE = 0.20

    _MEASURE = """
(() => {
  // The field pass read a *served* page with a trace behind it. The
  // committed fixtures have none, so the handoff never unhides its
  // group; forced open here, because the question is placement and
  // height rather than whether this run has a timeline.
  for (const id of ["actions", "actions-fallback", "actions-download"]) {
    const n = document.getElementById(id);
    if (n) n.hidden = false;
  }
  const header = document.querySelector("header");
  const box = header.getBoundingClientRect();
  const rem = parseFloat(getComputedStyle(document.documentElement).fontSize);
  const head = getComputedStyle(document.body).getPropertyValue("--head").trim();
  const shown = (n) => n && getComputedStyle(n).display !== "none"
    && n.getBoundingClientRect().height > 0;
  return {
    header_px: Math.round(box.height),
    viewport: window.innerHeight,
    sticky: getComputedStyle(header).position,
    blocks: [...header.children].filter(shown).length,
    controls: header.querySelectorAll("button, select, input, a").length,
    head_px: head.endsWith("rem") ? Math.round(parseFloat(head) * rem)
      : Math.round(parseFloat(head)),
    group_px: Math.round(
      document.querySelector("#actions-group")?.getBoundingClientRect().height ?? 0),
  };
})()
"""

    @pytest.mark.parametrize("width,height", [(1440, 900), (390, 844)])
    def test_the_header_is_identity_and_fits(self, browser, page, width, height):
        out = browser.measure(page, self._MEASURE, width=width, height=height)
        assert out["controls"] == 0, out
        assert out["blocks"] <= HEADER_LINE_BUDGET, out
        assert out["header_px"] / out["viewport"] <= self.MAX_SHARE, out

    @pytest.mark.parametrize("width,height", [(1440, 900), (390, 844)])
    def test_the_anchor_offset_covers_the_sticky_header(
            self, browser, page, width, height):
        """`--head` is what every anchor's `scroll-margin-top` reads. A
        token smaller than the band it describes lands every jump under
        the heading - which it did, by 84px, for as long as the header
        held the actions."""
        out = browser.measure(page, self._MEASURE, width=width, height=height)
        assert out["sticky"] == "sticky", out
        assert out["head_px"] >= out["header_px"], (
            f"--head is {out['head_px']}px against a {out['header_px']}px "
            f"sticky header: an anchor lands "
            f"{out['header_px'] - out['head_px']}px under it")

    @pytest.mark.parametrize("width,height", [(1440, 900), (390, 844)])
    def test_the_actions_group_is_not_sticky_and_scrolls_away(
            self, browser, page, width, height):
        """The move is only a win if the group's height is paid once.
        A second sticky band would be the same defect with a new name."""
        out = browser.measure(page, self._MEASURE, width=width, height=height)
        assert out["group_px"] > 0, "the actions group rendered nothing"
        position = browser.measure(page, """
(() => getComputedStyle(document.querySelector("#actions-group")).position)()
""", width=width, height=height)
        assert position == "static", position


# --------------------------------------------------------------------------
# 2. A described value shows its affordance.
# --------------------------------------------------------------------------

def _probe_source():
    source = (REPO / "tests/unit/test_a_report_you_can_navigate.py").read_text()
    return source.split('_PROBE = r"""', 1)[1].rsplit('"""', 1)[0]


_TAIL = r"""
const all = (n, pred, out = []) => {
  if (pred(n)) out.push(n);
  for (const c of n.children ?? []) all(c, pred, out);
  return out;
};
const text = (n) => !n ? "" : ((n.children ?? []).length
  ? (n._text ?? "") + n.children.map(text).join("") : (n._text ?? ""));
const root = named["report"] ?? body;
const described = all(root, (n) => n.attrs?.["data-described"] === "true");
const markers = all(root, (n) => n.attrs?.["data-describe"]);
const sentences = all(root, (n) => n.attrs?.["data-role"] === "description");
// UX-346: a declared exception keeps its sentence beside the value and
// therefore has no door - a `?` offering to show what is already shown
// is the duplication that item removed.
const inlined = all(root, (n) => n.attrs?.["data-inline"]
                                 && n.attrs?.["data-role"] === "description");
// Each sentence beside its value, not under its term: the `<dd>` is
// where the number is.
const parents = [...new Set(sentences.map((n) => n._parent?.tagName))];
// The marker's own claim, before and after a click, and back.
const first = markers[0] ?? null;
const shown = sentences[0] ?? null;
const trip = [];
for (let i = 0; i < 3; i++) {
  trip.push([first?.attrs["aria-expanded"] ?? null, shown ? shown.hidden : null]);
  if (i < 2) first?.click();
}
// The term still carries the sentence as a title: §4.3 asks that hover
// is not the only door, not that it is shut.
const titled = described.filter((n) => (n.attrs.title ?? "").length > 0).length;
console.log(JSON.stringify({
  described: described.length, markers: markers.length,
  sentences: sentences.length, inlined: inlined.length, parents, trip, titled,
  sample: shown ? text(shown) : null,
  error: failure }));
"""


def _boot(run_dir, tmp):
    run = snapshot_copy(run_dir, tmp)

    import tools.bga_view as view

    page = tmp / "report.html"
    view.export(str(run), str(page))
    html = page.read_text(encoding="utf-8")
    module = tmp / "inline.mjs"
    module.write_text(
        re.search(r'<script type="module">(.*?)</script>', html, re.S).group(1),
        encoding="utf-8")
    probe = tmp / "probe.mjs"
    probe.write_text(_probe_source().split("const report =", 1)[0] + _TAIL,
                     encoding="utf-8")
    result = subprocess.run(
        [node, str(probe)], capture_output=True, text=True, cwd=REPO,
        timeout=180,
        env=dict(os.environ, PAGE=str(page), MOD=str(module),
                 PROTOCOL="file:", BGA_DOM_SHIM=SHIM))
    assert result.returncode == 0, result.stderr[-4000:]
    out = json.loads(result.stdout)
    assert out["error"] is None, out["error"]
    return out


@pytest.fixture(scope="module")
def booted(tmp_path_factory):
    pages = {}
    for name, run in (("golden", GOLDEN), ("macro_micro", MACRO)):
        pages[name] = _boot(run, tmp_path_factory.mktemp(name))
    return pages


@needs_node
@pytest.mark.medium
class TestEveryDescribedValueShowsItsAffordance:
    def test_the_marker_count_equals_the_described_count(self, booted):
        """§2b.3, and the acceptance's own phrasing. Not "there are
        markers" - one per described value, so a renderer that grew a
        fourth `<dt>` site and forgot the marker reddens.

        `UX-346` subtracts the declared exceptions: a `bga:inline`
        value's sentence is beside it already, so it has no door and
        must not have one. Measured on the golden export: 86 described,
        12 inline, 74 markers."""
        for page, out in booted.items():
            assert out["described"] > 0, f"{page} describes nothing at all"
            assert out["sentences"] == out["described"], (page, out)
            assert out["markers"] == out["described"] - out["inlined"], (page, out)
            assert 0 < out["inlined"] < out["described"], (page, out)

    def test_the_sentence_opens_beside_the_value(self, booted):
        """Beside, not under the term: the `<dd>` holds the number, and
        §2b.3 places the description with it."""
        for page, out in booted.items():
            assert out["parents"] == ["dd"], (page, out["parents"])

    def test_it_starts_closed_and_the_marker_round_trips(self, booted):
        for page, out in booted.items():
            assert out["trip"] == [["false", True], ["true", False],
                                   ["false", True]], (page, out["trip"])

    def test_hover_is_not_shut_only_no_longer_the_only_door(self, booted):
        for page, out in booted.items():
            assert out["titled"] == out["described"], (page, out)


@needs_node
class TestAnAriaAttributeIsAnAttribute:
    """The defect `UX-317`'s own marker surfaced, and it is older than
    this item: `el()` set anything that was not `class` or `data-*` as a
    **property**, so five `aria-label`s in `app.js` had been invisible
    since they were written.

    Measured in Chromium 141 on a blank page, which is why this is a
    guard rather than an opinion:

    ```text
    node["aria-label"] = "filter rows"   getAttribute -> null
    node.setAttribute("aria-label", …)   getAttribute -> "filter rows"
    ```

    A property assignment reflects nowhere: not into the attribute, not
    into a `[aria-expanded="true"]` selector, and not into the
    accessibility tree.
    """

    def test_every_aria_the_page_builds_reads_back(self):
        out = json.loads(subprocess.run(
            [node, "--input-type=module", "-e", """
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;
globalThis._installDocument ??= (await import(process.env.BGA_DOM_SHIM)).installDocument;
_installDocument();
globalThis.location = { protocol: "http:", href: "http://x/" };
globalThis.window = { localStorage: { getItem: () => null, setItem: () => {} } };
globalThis.CSS = { escape: (s) => s };
globalThis.Event = class { constructor(t) { this.type = t; } };
const { buildTable } = await import("./tests/viewer.mjs");
const { table, tools } = buildTable("t",
  Array.from({ length: 50 }, (_, i) => ({ key: `e${i}.bst`, value: i })),
  {}, undefined, 0);
const all = (n, out = []) => {
  out.push(n);
  for (const c of n.children ?? []) all(c, out);
  return out;
};
const aria = [];
for (const node of [...all(table), ...all(tools)]) {
  for (const [name, value] of Object.entries(node.attrs ?? {})) {
    if (name.startsWith("aria-")) aria.push([node.tagName, name, value]);
  }
  // The other half: a name a browser would not reflect, sitting on the
  // node as a plain property instead of an attribute.
  for (const name of Object.keys(node)) {
    if (name.startsWith("aria-")) aria.push([node.tagName, "PROPERTY:" + name, ""]);
  }
}
console.log(JSON.stringify(aria));
"""],
            capture_output=True, text=True, cwd=REPO, timeout=90,
            env=dict(os.environ, BGA_DOM_SHIM=SHIM)).stdout or "[]")
        assert out, "the table built no aria attributes at all"
        stray = [entry for entry in out if entry[1].startswith("PROPERTY:")]
        assert not stray, (
            f"an aria name is a property rather than an attribute, so a "
            f"browser reflects it nowhere: {stray}")


class TestTheDescriptionSurvivesPaperAndTheRoomRule:
    def _rules(self):
        css = re.sub(r"/\*.*?\*/", "", CSS, flags=re.S)
        return [(" ".join(sel.split()), body)
                for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css)]

    def test_nothing_hides_a_description_in_print(self):
        """§2b.3: in print the marker survives and an opened
        description renders. Paper has no pointer, so a rule that hid
        either would make hover the only door on the one surface that
        has none."""
        blocks = re.findall(r"@media print \{(.*?)\n\}", CSS, re.S)
        for block in blocks:
            for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", block):
                names = " ".join(selector.split())
                if ".description" not in names and ".describe" not in names:
                    continue
                assert "display: none" not in body, (
                    f"print hides a description or its marker: {names}")

    def test_no_description_is_revealed_by_hover_alone(self):
        """The defect being replaced, held as a rule: a sentence whose
        only appearance is a `:hover` rule is a sentence nobody
        discovers, and on a touch screen nobody reaches at all."""
        for selector, body in self._rules():
            if ":hover" not in selector or ".description" not in selector:
                continue
            assert "display" not in body and "visibility" not in body, (
                f"a description is revealed by hover: {selector}")

    def test_the_room_rule_is_a_breakpoint_not_a_default(self):
        """§2b.3's "to its right where the row has room, below it where
        it does not". Below is the base - the narrow case is the one a
        default must be safe for - and the inline placement is the
        wide-viewport override."""
        base = [body for selector, body in self._rules()
                if selector == ".description"]
        assert base and "display: block" in base[0], base
        wide = re.search(
            r"@media \(min-width: 60rem\) \{(.*?)\n\}", CSS, re.S)
        assert wide and "display: inline" in wide.group(1), (
            "the sentence never moves beside the value where there is room")


@needs_browser
class TestTheRoomRuleHoldsAtBothViewports:
    """The breakpoint above is a claim about layout, and layout is the
    one thing the shim cannot model (`UX-257`). Measured: opened, the
    sentence is to the *right* of its value at 1440 and *below* it at
    390."""

    _PLACE = """
(() => {
  const marker = document.querySelector("button.describe");
  if (!marker) return { none: true };
  marker.click();
  const term = marker.closest("dt");
  const value = term.nextElementSibling;
  const sentence = value.querySelector(".description");
  const v = value.getBoundingClientRect();
  const s = sentence.getBoundingClientRect();
  return {
    display: getComputedStyle(sentence).display,
    // The value's own text box, not the `<dd>`'s: the sentence lives
    // inside it, so the `<dd>` grew to hold both.
    below: s.top >= v.top + 1,
    right: s.left > v.left + 1,
    hidden: sentence.hidden,
  };
})()
"""

    def test_it_sits_beside_the_value_where_there_is_room(self, browser, page):
        out = browser.measure(page, self._PLACE, width=1440, height=900)
        assert not out.get("none"), "no described value on the page"
        assert out["hidden"] is False
        assert out["display"] == "inline", out
        assert out["right"] is True, out

    def test_it_sits_below_the_value_where_there_is_not(self, browser, page):
        out = browser.measure(page, self._PLACE, width=390, height=844)
        assert not out.get("none"), "no described value on the page"
        assert out["hidden"] is False
        assert out["display"] == "block", out
        assert out["below"] is True, out


# --------------------------------------------------------------------------
# The browser harness.
# --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module")
def page(tmp_path_factory):
    """The macro_micro export, as a `file:` URL.

    The header measurement wants a *served* page - that is the mode the
    field pass read - but the header, its budget and the room rule are
    identical in both, and an export needs no port. The one thing that
    differs is whether the handoff group unhides itself, which the
    measurement forces.
    """
    from tools.bga_view import export

    run = snapshot_copy(MACRO, tmp_path_factory.mktemp("apparatus"))
    path = tmp_path_factory.mktemp("apparatus-page") / "report.html"
    export(str(run), str(path))
    return f"file://{path}"
