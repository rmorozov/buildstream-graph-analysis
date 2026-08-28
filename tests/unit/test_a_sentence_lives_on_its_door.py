"""UX-346: the page is this run's numbers; the glossary is one click away.

`UX-220` gave every declared quantity a sentence and `UX-201` sourced
it from the contract. `UX-317` then built the door - a visible `?`
beside the term, the sentence opening beside the value - and the door
never closed:

```text
golden export, Chrome 1440x900, before this item
  sentence.hidden       true
  computed display      "inline"
  bounding box          458 x 15
```

`[hidden]` is a UA rule of specificity (0,0,0); `.description` sets
`display: block` at (0,1,0) and `display: inline` again in the wide
breakpoint. Both beat it, so every sentence rendered on every load and
the `?` toggled a property with no visual effect. Measured on the two
committed exports, that was **1,479 of the golden page's 3,466 words
(43%)** and **2,312 of macro_micro's 6,283 (37%)** - prose identical
on every run, printed beside a control offering to print it.

`.description[hidden] { display: none }` is (0,2,0) and closes it.

**The exceptions are declared, not decided here.** `bga:inline` names
one of two reasons (`bga/schemas.py::INLINE_REASONS`), and the page
renders those sentences with no door at all - a `?` beside a sentence
already on screen is the duplication this item is about.

After, on the same two exports:

```text
             height       words   inline sentence words   inline / described
golden       10,423 px    2,303          249  (10.8%)          12 / 86
macro_micro  20,393 px    4,478          403  ( 9.0%)          18 / 146
```
"""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from browser import NO_BROWSER, Browser, find_chrome    # noqa: E402
from pages import snapshot_copy    # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
FIXTURES = {"golden": REPO / "tests/fixtures/golden/mixed_task_kinds",
            "macro_micro": REPO / "tests/fixtures/macro_micro/run"}

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

#: The share of a page's words that may be the contract's own prose.
#: The measurement this item was filed on was 43% and 37%; the two
#: declared exception classes land at 11% and 9%, and the bound is
#: where the acceptance test put it.
MAX_NOTE_SHARE = 0.25


def _declared_inline():
    """`{key: reason}` for every `bga:inline` in every published schema."""
    from bga import schemas

    found = {}

    def walk(node, key=None):
        if isinstance(node, dict):
            if schemas.INLINE in node:
                found.setdefault(key, node[schemas.INLINE])
            for name, sub in node.items():
                walk(sub, name if name not in
                     ("properties", "items", "additionalProperties") else key)
        elif isinstance(node, list):
            for sub in node:
                walk(sub, key)

    for name in schemas.names():
        walk(schemas.schema(name))
    return found


class TestTheContractSaysWhichSentencesStayInline:
    """Neither clause needs a browser: an exception that names no reason
    is a per-call-site decision wearing a declaration's clothes."""

    def test_every_declaration_names_one_of_the_two_reasons(self):
        from bga import schemas

        wrong = {key: reason for key, reason in _declared_inline().items()
                 if reason not in schemas.INLINE_REASONS}
        assert wrong == {}, (
            f"a `bga:inline` outside {schemas.INLINE_REASONS}: {wrong}")

    def test_every_declaration_has_a_sentence_to_keep_inline(self):
        """`bga:inline` on a node with no `description` renders nothing
        and reads, to the next person, as a rule that is being applied."""
        from bga import schemas

        empty = []

        def walk(node):
            if isinstance(node, dict):
                if schemas.INLINE in node and not node.get("description"):
                    empty.append(sorted(node))
                for sub in node.values():
                    walk(sub)
            elif isinstance(node, list):
                for sub in node:
                    walk(sub)

        for name in schemas.names():
            walk(schemas.schema(name))
        assert empty == [], f"a `bga:inline` with nothing to show: {empty}"

    def test_the_exception_list_is_short_enough_to_read(self):
        """A declaration per field is the mechanism; a declaration on
        every field is the defect back under a new name."""
        declared = _declared_inline()
        assert 0 < len(declared) <= 40, sorted(declared)


_PAGE = r"""
(() => {
  // UX-347: every chapter but the first folds now, and a folded
  // chapter draws nothing at all. These clauses are about what the
  // page says *when it is read* - a note share measured over hidden
  // sections would read as zero and mean nothing, and a door inside a
  // fold cannot be clicked without opening the fold a reader would
  // have opened first. So the document is opened here, in the
  // instrument, rather than in the page.
  for (const box of document.querySelectorAll("section.chapter")) {
    box.setAttribute("data-open", "true");
  }
  const words = (el) => ((el?.innerText || "").match(/\S+/g) || []).length;
  const seen = (el) => { const r = el.getBoundingClientRect();
                         return r.width > 0 && r.height > 0; };
  const all = [...document.querySelectorAll('[data-role="description"]')];
  const shown = all.filter(seen);
  return {
    totalWords: words(document.body),
    described: all.length,
    shown: shown.length,
    shownWords: shown.reduce((n, el) => n + words(el), 0),
    shownKeys: shown.map((el) => el.getAttribute("data-describes")),
    shownUndeclared: shown.filter((el) => !el.getAttribute("data-inline"))
                          .map((el) => el.getAttribute("data-describes")),
    inlineKeys: all.filter((el) => el.getAttribute("data-inline"))
                   .map((el) => el.getAttribute("data-describes")),
    describedKeys: all.map((el) => el.getAttribute("data-describes")),
    // A door for every sentence that has one, and none for the rest.
    doors: document.querySelectorAll("button.describe").length,
    doorsOnInline: [...document.querySelectorAll("button.describe")].filter(
      (b) => b.closest("dt")?.getAttribute("data-inline")).length,
  };
})()
"""

_EVERY_DOOR = r"""
(() => {
  // UX-347: every chapter but the first folds now, and a folded
  // chapter draws nothing at all. These clauses are about what the
  // page says *when it is read* - a note share measured over hidden
  // sections would read as zero and mean nothing, and a door inside a
  // fold cannot be clicked without opening the fold a reader would
  // have opened first. So the document is opened here, in the
  // instrument, rather than in the page.
  for (const box of document.querySelectorAll("section.chapter")) {
    box.setAttribute("data-open", "true");
  }
  // UX-347: every chapter but the first folds now, and a folded
  // chapter draws nothing at all. These clauses are about what the
  // page says *when it is read* - a note share measured over hidden
  // sections would read as zero and mean nothing, and a door inside a
  // fold cannot be clicked without opening the fold a reader would
  // have opened first. So the document is opened here, in the
  // instrument, rather than in the page.
  for (const box of document.querySelectorAll("section.chapter")) {
    box.setAttribute("data-open", "true");
  }
  const shut = [], stuck = [], missing = [];
  for (const marker of document.querySelectorAll("button.describe")) {
    const term = marker.closest("dt");
    const sentence = term?.nextElementSibling?.querySelector(
      '[data-role="description"]');
    if (!sentence) { missing.push(marker.getAttribute("data-describe")); continue; }
    const box = () => sentence.getBoundingClientRect().height;
    if (box() !== 0) shut.push(marker.getAttribute("data-describe"));
    marker.click();
    if (box() === 0 || getComputedStyle(sentence).display === "none") {
      stuck.push(marker.getAttribute("data-describe"));
    }
    marker.click();
  }
  return { doors: document.querySelectorAll("button.describe").length,
           openBeforeClick: shut, doesNotOpen: stuck, noSentence: missing };
})()
"""

_DOOR = r"""
(() => {
  const marker = document.querySelector("button.describe");
  if (!marker) return { none: true };
  const sentence = marker.closest("dt").nextElementSibling
                         .querySelector('[data-role="description"]');
  const state = () => ({ display: getComputedStyle(sentence).display,
                         height: Math.round(
                           sentence.getBoundingClientRect().height),
                         expanded: marker.getAttribute("aria-expanded") });
  const closed = state();
  marker.click();
  const open = state();
  marker.click();
  return { closed, open, shut: state(), text: sentence.textContent.length };
})()
"""


@needs_browser
@pytest.mark.parametrize("label", sorted(FIXTURES))
class TestThePageIsThisRunsNumbers:
    def test_the_contracts_prose_is_under_the_bound(self, browser, pages, label):
        out = browser.measure(pages[label], _PAGE, width=1440, height=900)
        share = out["shownWords"] / out["totalWords"]
        assert share <= MAX_NOTE_SHARE, (
            f"{label}: {out['shownWords']} of {out['totalWords']} words "
            f"({share:.0%}) are the schema's own sentences, against a bound "
            f"of {MAX_NOTE_SHARE:.0%}")

    def test_only_a_declared_exception_renders_beside_its_value(
            self, browser, pages, label):
        out = browser.measure(pages[label], _PAGE, width=1440, height=900)
        assert out["described"] > 0, f"{label} describes nothing at all"
        assert out["shownUndeclared"] == [], (
            f"{label}: sentences on screen with no `bga:inline` behind "
            f"them: {sorted(set(out['shownUndeclared']))[:8]}")
        assert sorted(set(out["shownKeys"])) == sorted(set(out["inlineKeys"])), (
            label, out["shownKeys"], out["inlineKeys"])

    def test_every_key_that_renders_inline_is_declared_in_the_contract(
            self, browser, pages, label):
        declared = _declared_inline()
        out = browser.measure(pages[label], _PAGE, width=1440, height=900)
        stray = sorted({key for key in out["inlineKeys"] if key not in declared})
        assert stray == [], (
            f"{label}: the page renders these inline and the contract does "
            f"not declare them: {stray}")

    def test_a_declared_exception_really_does_render_inline(
            self, browser, pages, label):
        """The other direction, and the one a page that ignored the
        hint entirely would pass without: every declared key this page
        actually draws has its sentence on screen."""
        declared = _declared_inline()
        out = browser.measure(pages[label], _PAGE, width=1440, height=900)
        drawn = {key for key in out["describedKeys"] if key in declared}
        assert drawn, (
            f"{label}: none of the {len(declared)} declared exceptions is on "
            f"this page - the clause below is measuring nothing")
        missing = sorted(drawn - set(out["shownKeys"]))
        assert missing == [], (
            f"{label}: declared inline and behind a door anyway: {missing}")

    def test_a_declared_exception_carries_no_door(self, browser, pages, label):
        """The `?` is the affordance for a sentence that is not here.
        Beside one that is, it is the duplication this item removed."""
        out = browser.measure(pages[label], _PAGE, width=1440, height=900)
        assert out["doorsOnInline"] == 0, (label, out["doorsOnInline"])
        # `UX-344`: counted per *render*, not per key. `UX-346` could
        # use the set because no declared key was drawn twice; lifting
        # `joint_saving` out of `signals` made `sum_of_individual_us` a
        # row of a section as well as a finding's evidence, and the two
        # renders are two doors that are not there.
        assert out["doors"] == out["described"] - len(out["inlineKeys"]), (
            label, out["doors"], out["described"], sorted(out["inlineKeys"]))

    def test_every_door_on_the_page_opens_its_own_sentence(
            self, browser, pages, label):
        """The acceptance test's own phrasing: every sentence taken
        from beside a value is reachable from that value's door. Walked,
        not sampled - 74 doors on one page and 128 on the other, each
        clicked open and shut again."""
        out = browser.measure(pages[label], _EVERY_DOOR, width=1440, height=900)
        assert out["doors"] > 50, (label, out["doors"])
        assert out["noSentence"] == [], (label, out["noSentence"][:8])
        assert out["openBeforeClick"] == [], (
            f"{label}: a closed door already showing its sentence: "
            f"{out['openBeforeClick'][:8]}")
        assert out["doesNotOpen"] == [], (
            f"{label}: a door that opens nothing: {out['doesNotOpen'][:8]}")

    def test_the_door_opens_and_shuts_what_it_says(self, browser, pages, label):
        """The defect, held: `hidden` was true and the sentence was
        458x15 px of rendered text. Measured as *computed style and
        box*, never as the attribute - the attribute was right the
        whole time."""
        out = browser.measure(pages[label], _DOOR, width=1440, height=900)
        assert not out.get("none"), f"{label} has no door at all"
        assert out["text"] > 0, out
        assert out["closed"] == {"display": "none", "height": 0,
                                 "expanded": "false"}, out
        assert out["open"]["display"] == "inline", out
        assert out["open"]["height"] > 0, out
        assert out["shut"]["display"] == "none", out


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module")
def pages(tmp_path_factory):
    """Both committed fixtures, exported as `file:` URLs."""
    from tools.bga_view import export

    out = {}
    for label, fixture in FIXTURES.items():
        run = snapshot_copy(fixture, tmp_path_factory.mktemp(f"sentence-{label}"))
        path = tmp_path_factory.mktemp(f"sentence-page-{label}") / "report.html"
        export(str(run), str(path))
        out[label] = f"file://{path}"
    return out
