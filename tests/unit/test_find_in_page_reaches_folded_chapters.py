"""UX-1015 (styleguide §6e.11, Rule 11): find-in-page reaches a folded
chapter's text.

Measured on `main` before this: `section.chapter[data-open="false"] >
section[data-section] { display: none; }` (`style.css`) hides every
section behind a shut chapter - and a `display` rule always hides its
text from `Ctrl+F`, which no `aria-*` attribute changes
(<https://developer.mozilla.org/.../hidden>). 5 of 6 chapters on
`macro_micro` are folded at rest, so a search for text inside any of
them misses.

`hidden="until-found"` is the platform's own answer (§6c's list gains
the row): a browser reveals it and fires `beforematch` on a match,
`content-visibility: hidden` while it is set, and no `display` rule at
all - so `Ctrl+F` finds it. The fold is that one attribute now;
`setOpen` writes it alongside `data-open` and `aria-expanded`, so the
three can never disagree.
"""
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
VIEWER = REPO / "bga" / "viewer"
CHAPTERS_JS = VIEWER / "chapters.js"
STYLE = VIEWER / "style.css"
SHIM = str(REPO / "tests" / "dom_shim.mjs")

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")

sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import pages
from browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

MACRO = REPO / "tests" / "fixtures" / "macro_micro" / "run"


# --------------------------------------------------------------------------
# 1. The mechanism, in `style.css` - read once, statically.
# --------------------------------------------------------------------------

class TestTheMechanismIsThreePlaces:
    def test_the_display_none_fold_rule_is_gone(self):
        css = STYLE.read_text(encoding="utf-8")
        assert 'section[data-section] { display: none; }' not in css, (
            "the old fold rule is still here - it hides text from find "
            "the same way whether or not hidden=\"until-found\" is also set")

    def test_content_visibility_excludes_a_hidden_section(self):
        css = STYLE.read_text(encoding="utf-8")
        assert re.search(
            r"section\.chapter > section\[data-section\]:not\(\[hidden\]\)"
            r"\s*\{[^}]*content-visibility:\s*auto", css), (
            "the content-visibility rule does not exclude [hidden] - it "
            "would override the browser's own content-visibility: hidden "
            "on a folded (hidden=\"until-found\") section")

    def test_print_reveals_a_folded_section_by_the_attribute(self):
        css = STYLE.read_text(encoding="utf-8")
        blocks = re.findall(r"@media print \{(.*?)\n\}", css, re.S)
        assert any('[hidden="until-found"]' in b and "display: block" in b
                  for b in blocks), (
            "no print rule reveals a hidden=\"until-found\" section")


# --------------------------------------------------------------------------
# 2. `setOpen` is the one writer of `data-open`, `hidden` and
#    `aria-expanded` - driven with the shim, no browser needed for the
#    attribute logic itself.
# --------------------------------------------------------------------------

_PROBE = r"""
const shim = await import(process.env.BGA_DOM_SHIM);
shim.installDocument();
globalThis.window = { location: { hash: "", search: "" }, addEventListener() {},
                      matchMedia: () => ({ matches: false, addEventListener() {} }) };
const chapters = await import(process.env.MOD);
const root = shim.makeNode("div");
// "findings" (in "decide", the always-open first chapter) plus one
// member of "elements" (by prefix), so both boxes exist before the
// second half of this probe closes the second one.
for (const key of ["findings", "elements"]) {
  const node = shim.makeNode("section");
  node.setAttribute("data-section", key);
  root.append(node);
}
const boxes = chapters.chapters(root, globalThis.document);
const box = boxes.find((b) => b.getAttribute("data-chapter") === "elements");
const before = read(box);
chapters.setOpen(box, false);
const closed = read(box);
// A dispatched `beforematch` on the folded section opens the whole
// chapter - the one path find, a fragment and the controls share.
const section = box.querySelectorAll("[data-section]")[0];
section.dispatchEvent({ type: "beforematch" });
const reopened = read(box);
chapters.setOpen(box, false);
const closedAgain = read(box);
// `UX-1015`: a section that arrives after its chapter is already shut
// joins it shut.
const late = shim.makeNode("section");
late.setAttribute("data-section", "element-late");
chapters.fileInChapter(root, late, globalThis.document);
function read(box) {
  return {
    dataOpen: box.getAttribute("data-open"),
    hidden: box.querySelectorAll("[data-section]")
      .map((n) => n.getAttribute("hidden")),
    ariaExpanded: box.querySelector("[data-chapter-open]")
      ?.getAttribute("aria-expanded"),
  };
}
console.log(JSON.stringify({
  before, closed, reopened, closedAgain,
  lateHidden: late.getAttribute("hidden"),
}));
"""


def _run_probe(source=_PROBE):
    tmp = pathlib.Path(tempfile.mkdtemp())
    probe = tmp / "probe.mjs"
    probe.write_text(source, encoding="utf-8")
    done = subprocess.run(
        [node, str(probe)], capture_output=True, text=True, cwd=REPO, timeout=60,
        env=dict(os.environ, BGA_DOM_SHIM=SHIM, MOD=str(CHAPTERS_JS)))
    assert done.returncode == 0, done.stderr[-3000:]
    return json.loads(done.stdout)


@needs_node
class TestSetOpenIsTheOneStateSetter:
    def test_a_chapter_other_than_the_first_is_hidden_at_construction(self):
        """`UX-347`: every chapter but the first starts shut - and
        `UX-1015` makes that mean `hidden="until-found"` on its
        sections from the moment they join it, in `chapters()`'s own
        loop, not only on a later `setOpen(box, false)` call."""
        out = _run_probe()
        assert out["before"]["dataOpen"] == "false"
        assert out["before"]["hidden"] == ["until-found"]
        assert out["before"]["ariaExpanded"] == "false"

    def test_closing_hides_every_direct_section_until_found(self):
        out = _run_probe()
        assert out["closed"]["dataOpen"] == "false"
        assert out["closed"]["hidden"] == ["until-found"]
        assert out["closed"]["ariaExpanded"] == "false"

    def test_a_dispatched_beforematch_opens_the_whole_chapter(self):
        out = _run_probe()
        assert out["reopened"]["dataOpen"] == "true"
        assert out["reopened"]["hidden"] == [None]
        assert out["reopened"]["ariaExpanded"] == "true"

    def test_it_round_trips(self):
        out = _run_probe()
        assert out["closedAgain"] == out["closed"]

    def test_a_late_arriving_section_joins_a_shut_chapter_shut(self):
        out = _run_probe()
        assert out["lateHidden"] == "until-found"


# --------------------------------------------------------------------------
# 3. The one clause a shim cannot see: a real browser's computed style
#    on a folded section - the mutation's own target (restoring
#    `display: none` flips `display` back to `"none"` here).
# --------------------------------------------------------------------------

_FOLDED_STYLE = r"""
(() => {
  const box = document.querySelector('section.chapter[data-open="false"]');
  if (!box) return null;
  const section = box.querySelector('section[data-section]');
  if (!section) return null;
  const cs = getComputedStyle(section);
  return { hiddenAttr: section.getAttribute("hidden"),
           display: cs.display, contentVisibility: cs.contentVisibility };
})()
"""


@needs_browser
class TestAFoldedSectionIsHiddenUntilFoundOnScreen:
    def test_a_folded_section_computes_hidden_but_not_display_none(self):
        into = pathlib.Path(tempfile.mkdtemp())
        uri = pages.export_uri(MACRO, into)
        with Browser(chrome) as browser:
            out = browser.measure(uri, _FOLDED_STYLE, 1440, 900)
        assert out, "no folded chapter with a section found on this fixture"
        assert out["hiddenAttr"] == "until-found", out
        assert out["display"] != "none", out
        assert out["contentVisibility"] == "hidden", out
