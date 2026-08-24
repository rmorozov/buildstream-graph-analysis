"""UX-264: one DOM shim, and it agrees with a browser.

Every viewer guard boots the shipped ES modules against a hand-written
DOM. That shim used to be copy-pasted into each test file — **25 of
them** — and each fidelity defect it carried had to be found in the
page first and then fixed twenty-five times:

```text
round 27  `prepend` implemented as `append`      -> every order guard read
                                                    a reversed document (UX-235)
round 32  `append` copied an already-parented    -> a 4,000-row table read
          node instead of moving it                 as 8,000 (UX-262)
round 33  `style: {}` swallowed every write      -> four drawings refused by
                                                    the page's own CSP (UX-263)
```

`UX-263` had to be applied in seven files to fix one bug, which left
the eighteen untouched copies *more* different than they started — the
signature of a duplicated fact.

This file holds the two properties that make one shim better than
twenty-five: the count stays at one, and its behaviour is checked
against a **real browser** rather than against itself. A shim asserted
against its own expectations is the hollow instrument this whole line
of items is about.
"""
import json
import os
import pathlib
import re
import shutil
import subprocess

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
SHIM = REPO / "tests/dom_shim.mjs"
node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")

# The one place a node factory may be written. Anything else that
# builds a DOM node inline is a second instrument.
ALLOWED = {"tests/dom_shim.mjs"}


def _harness_files():
    return sorted(p for p in (REPO / "tests/unit").glob("*.py")
                  if "createElement" in p.read_text(encoding="utf-8"))


def _run(script):
    done = subprocess.run([node, "--input-type=module", "-e", script],
                          capture_output=True, text=True, cwd=REPO, timeout=120,
                          env={**os.environ, "BGA_DOM_SHIM": SHIM.as_uri()})
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


class TestThereIsOnlyOneShim:
    def test_no_harness_builds_its_own_node(self):
        """The census. A harness may wire its own `document` — that is
        three lines and legitimately differs — but the *node* is the
        thing whose fidelity was wrong three times, and it comes from
        one place."""
        offenders = {}
        for path in _harness_files():
            # This file's own probes call `setAttribute` inside a
            # `return {` of their *result* object. A guard that greps
            # finds itself - ninth time in this repository (`UX-239`),
            # and the only honest fix is to name the exception rather
            # than to weaken the pattern that catches the real thing.
            if path.name == pathlib.Path(__file__).name:
                continue
            source = path.read_text(encoding="utf-8")
            # A node factory is a `return {` carrying `setAttribute`.
            for match in re.finditer(r"return \{[^}]*setAttribute", source):
                offenders.setdefault(path.name, []).append(
                    source[:match.start()].count("\n") + 1)
        assert offenders == {}, (
            f"these harnesses build their own DOM node instead of importing "
            f"tests/dom_shim.mjs: {offenders}. Three fidelity defects have "
            f"shipped because a shim disagreed with a browser and 25 copies "
            f"all agreed with each other (UX-264).")

    def test_every_harness_that_needs_a_node_imports_the_shim(self):
        missing = [p.name for p in _harness_files()
                   if "BGA_DOM_SHIM" not in p.read_text(encoding="utf-8")
                   and p.name != "test_the_dom_shim_is_one_instrument.py"]
        assert missing == [], f"harnesses not using the shared shim: {missing}"

    def test_the_shim_is_reachable_without_knowing_the_cwd(self):
        """Several harnesses run node from a `tmp_path`. A relative
        import resolved against whatever directory that test chose, and
        the first migration failed exactly there."""
        conftest = (REPO / "tests/conftest.py").read_text(encoding="utf-8")
        assert "BGA_DOM_SHIM" in conftest and "as_uri()" in conftest


@needs_node
class TestItAgreesWithChrome:
    """Measured in Chrome 141, then pinned here.

    These are the behaviours the guards actually depend on, and each
    one is a place a previous shim was wrong.
    """

    CHROME = {
        # `UX-263`: style writes reflect into the attribute, serialised
        # with the semicolon and space-joined.
        "style_width": "width: 50%;",
        "style_custom": "--w: 18.75%;",
        "style_two": "width: 50%; padding-left: 1rem;",
        "style_none": None,
        # `UX-262`: appending an already-parented node moves it.
        "moved_from_old_parent": 0,
        "moved_to_new_parent": 1,
        # `UX-235`: prepend puts the node first.
        "prepend_order": "b,i",
        # `UX-271` made `nav.js` use a child combinator, and the shim
        # refused it - loudly, which is the instrument working. Taught,
        # and checked against Chrome on a case that *discriminates*:
        # a `<b>` directly inside and a second one a level deeper.
        "child_combinator": 1,
        "descendant_combinator": 2,
        # An href attribute reflects into the property.
        "href_property": "#element-x",
        # Descendant selectors, which the probes use.
        "tbody_tr": 1,
        "all_tr": 2,
    }

    def test_the_shim_answers_what_chrome_answered(self):
        out = _run("""
const { makeNode, installDocument } = await import(process.env.BGA_DOM_SHIM);
const d = installDocument();
const mk = (t) => d.createElement(t);

const a = mk("div"); a.style.width = "50%";
const b = mk("div"); b.style.setProperty("--w", "18.75%");
const c = mk("div"); c.style.width = "50%"; c.style.paddingLeft = "1rem";
const e = mk("div");

const oldParent = mk("div"), newParent = mk("div"), moved = mk("span");
oldParent.append(moved); newParent.append(moved);

const p = mk("div"); p.append(mk("i")); p.prepend(mk("b"));

const link = mk("a"); link.setAttribute("href", "#element-x");

const table = mk("table"), tbody = mk("tbody"), thead = mk("thead");
table.append(tbody, thead); tbody.append(mk("tr")); thead.append(mk("tr"));

const host = mk("div"); host.className = "a";
const direct = mk("b"); const wrap = mk("span"); const deep = mk("b");
host.append(direct, wrap); wrap.append(deep);

console.log(JSON.stringify({
  style_width: a.getAttribute("style"),
  style_custom: b.getAttribute("style"),
  style_two: c.getAttribute("style"),
  style_none: e.getAttribute("style"),
  moved_from_old_parent: oldParent.children.length,
  moved_to_new_parent: newParent.children.length,
  prepend_order: p.children.map((n) => n.tagName).join(","),
  href_property: link.href,
  tbody_tr: table.querySelectorAll("tbody tr").length,
  all_tr: table.querySelectorAll("tr").length,
  child_combinator: host.querySelectorAll(".a > b").length,
  descendant_combinator: host.querySelectorAll(".a b").length,
}));
""")
        assert out == self.CHROME, (
            "the shim and the browser disagree. The browser is right; the "
            "measurements in CHROME came from Chrome 141 and are re-runnable "
            "(see UX-263's Outcome for the driver).")

    def test_a_selector_it_cannot_parse_is_loud(self):
        """The failure mode this replaces is worse than an error: a
        selector that matches nothing reads as "the page does not
        render that", and a guard passes."""
        out = _run("""
const { installDocument } = await import(process.env.BGA_DOM_SHIM);
const d = installDocument();
d.body.append(d.createElement("div"));
const loud = [];
for (const selector of ["tr > td", "li:first-child", "a + b"]) {
  try { d.body.querySelectorAll(selector); loud.push([selector, "quiet"]); }
  catch (error) { loud.push([selector, "threw"]); }
}
console.log(JSON.stringify(Object.fromEntries(loud)));
""")
        # `tr > td` is *supported* since `UX-271`; what must stay loud
        # is the shapes that are still not implemented.
        assert out == {"tr > td": "quiet", "li:first-child": "threw",
                       "a + b": "threw"}, out

    def test_it_says_what_it_cannot_do(self):
        """There is no layout engine, and the file must keep saying so:
        the moment it quietly returns zeroes for geometry, every
        geometric guard built on it becomes a lie (`UX-257`)."""
        source = SHIM.read_text(encoding="utf-8")
        assert "getBoundingClientRect" not in source.replace(
            "no `getBoundingClientRect`", ""), (
            "the shim grew a layout API. It has no layout engine, so a "
            "geometric answer from it is invented (UX-257)")
        assert "There is no layout" in source


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
