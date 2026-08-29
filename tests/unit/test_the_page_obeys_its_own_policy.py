"""UX-263: the viewer's own CSP refused four of its drawings.

Reported from a real project: *"lots of errors from latest Chrome about
applying inline style violates the following content security policy
default-src, pointing to views.js"*. Reproduced on the golden run,
served by `bga view` itself, in Chrome 141:

```text
                        violations   wf-fill widths   path-box grow   horizon --w
before                          15   1 distinct       1 distinct      1 distinct
after                            0   4 distinct       3 distinct      5 distinct
```

The server sends `default-src 'self'` (`UX-193`), and a **style
attribute is inline style**: `element.setAttribute("style", ...)` is
refused. `views.js` used it in four places, so the waterfall's width,
the critical path's share, the blast tree's indentation and the
horizon's bar were all set in the DOM and **none of them applied** —
every bar full width, every box the same size. Console noise was the
symptom; four dead visual encodings were the defect.

The fix is CSSOM (`element.style.width = ...`,
`element.style.setProperty("--w", ...)`), which is not inline style and
is not subject to the policy. Relaxing the CSP to `'unsafe-inline'` was
the other option and was declined: this page renders element names and
paths out of a build, and weakening a policy to keep a convenience is
the wrong direction for a document people attach to tickets.

**Why nothing caught it.** The harness is a hand-rolled DOM shim with
no CSS engine, and it carried `style: {}` — a plain object that
swallowed every write and reported success. The shim now reflects
`.style` writes into the `style` attribute and serialises them the way
Chrome does (`width: 50%;`), measured rather than assumed. That is the
third instrument defect in three rounds (`UX-235`, `UX-262`), and
`UX-264` is the argument about the 25 copies of it.
"""
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
VIEWER = REPO / "bga/viewer"
SERVER = (REPO / "tools/bga_view.py").read_text(encoding="utf-8")


def _code(source):
    """`source` with comments stripped.

    Without this the ban below matches the comment that explains the
    ban — the self-matching guard this repository has now filed seven
    times (`UX-239`).
    """
    without_block = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
    return re.sub(r"^\s*//.*$", "", without_block, flags=re.M)


# `UX-373`: `sql.js` is gone - `perfetto_page.js` renders the
# library now, on the page that opens the trace it asks about.
_ENTRY_MODULES = ("app.js", "perfetto_page.js")


def _imports(path):
    """The viewer modules one module imports, by relative path."""
    import re
    source = path.read_text(encoding="utf-8")
    return re.findall(r'from\s+"\./([A-Za-z0-9_]+\.js)"', source)


class TestNothingWritesAStyleAttribute:
    def test_no_viewer_module_sets_style_as_an_attribute(self):
        offenders = {}
        for path in sorted(VIEWER.glob("*.js")):
            code = _code(path.read_text(encoding="utf-8"))
            hits = [n + 1 for n, line in enumerate(code.splitlines())
                    if re.search(r'setAttribute\(\s*["\']style["\']', line)]
            if hits:
                offenders[path.name] = hits
        assert offenders == {}, (
            f"a style *attribute* is inline style and the viewer's own CSP "
            f"refuses it, so the declaration never applies: {offenders}. Use "
            f"`el.style.prop = ...`, or `el.style.setProperty(...)` for a "
            f"custom property (UX-263).")

    def test_no_served_page_carries_inline_style(self):
        """Every page, not one. `UX-266`: this used to read
        `index.html` alone, and `sql.html` was dead for rounds."""
        offenders = {}
        for path in sorted(VIEWER.glob("*.html")):
            if re.search(r"<[^>]+\sstyle=", path.read_text(encoding="utf-8")):
                offenders[path.name] = "inline style attribute"
        assert offenders == {}, offenders


class TestNoPageRunsAnInlineScript:
    """UX-266: reported from a real project - *"there is a problem on
    sql.html"*.

    `default-src 'self'` refuses inline **script** exactly as it
    refuses inline style, and two of the three served pages had one.
    Measured in Chrome 141 against the page `bga view` serves:

    ```text
                   violations   main children   body text
    index.html              0              26      11,056
    sql.html                1               0         508   <- rendered nothing
    perfetto.html           1               4         398   <- button did nothing
    ```

    `sql.html` was **completely dead**: the questions list never
    existed. `perfetto.html` is quieter and worse - the page renders,
    the "Open in Perfetto" button is *there*, and nothing was
    listening to it, so `bga view --perfetto` lands on a button that
    does nothing.

    `UX-263` fixed the style half and checked `index.html` only, which
    is why this survived it.
    """

    def test_no_served_page_has_an_inline_script(self):
        offenders = {}
        for path in sorted(VIEWER.glob("*.html")):
            html = path.read_text(encoding="utf-8")
            for match in re.finditer(r"<script(?![^>]*\ssrc=)[^>]*>", html):
                offenders.setdefault(path.name, []).append(match.group(0))
        assert offenders == {}, (
            f"inline <script> in {offenders}. The server sends "
            f"`default-src 'self'`, which refuses it - the page loads and "
            f"does nothing at all (UX-266).")

    def test_every_page_still_runs_something(self):
        """The other direction, and the one that matters: a page with
        no script at all would also pass the ban above. Each served
        page names the module that drives it."""
        expected = {"index.html": "app.js",
                    "perfetto.html": "perfetto_page.js"}
        for name, module in expected.items():
            html = (VIEWER / name).read_text(encoding="utf-8")
            assert f'src="{module}"' in html, f"{name} no longer loads {module}"
            assert (VIEWER / module).exists(), f"{module} is not there"
        # `UX-373`: `sql.html` runs nothing on purpose - it is a
        # redirect to the page its content moved to. That is the one
        # exemption from the clause above, and it is one only because
        # the page still *does* something without script, which is the
        # property being defended.
        redirect = (VIEWER / "sql.html").read_text(encoding="utf-8")
        assert "<script" not in redirect and 'http-equiv="refresh"' in redirect, (
            "sql.html neither runs a module nor redirects, so it is the "
            "blank page this clause exists to catch")

    def test_every_page_script_is_served(self):
        """A module the server does not list is a 404, which is the
        same dead page by a different route.

        **Every module each page imports, not just the three it loads
        directly.** This named `app.js`, `sql.js` and
        `perfetto_page.js`, and passed while `UX-286`'s `chapters.js` -
        imported by `app.js` and by `nav.js` - was missing from
        `ASSETS`: the served page 404'd on the import, `boot` never
        ran, and the report was the word "Loading…" in a real browser.
        A guard that checks the entry points of a module graph checks
        the one part of it that cannot go wrong."""
        server = (REPO / "tools/bga_view.py").read_text(encoding="utf-8")
        # `UX-373`: to the tuple's **closing line**, not to the first
        # `)`. The comments inside `ASSETS` are prose, and one of them
        # acquired a parenthesis - which truncated this slice a third of
        # the way in and reported six served modules as missing. The
        # traversal floor below caught that it had stopped reading;
        # nothing said why.
        assets = server.split("ASSETS = (", 1)[1].split("\n)", 1)[0]
        assert assets.count("\n") > 20, (
            "the ASSETS slice stops early again; it is reading part of the "
            "tuple and will report the rest as missing")
        wanted, seen = list(_ENTRY_MODULES), set()
        while wanted:
            module = wanted.pop()
            if module in seen:
                continue
            seen.add(module)
            assert f'"{module}"' in assets, (
                f"{module} is imported by a served page and is not in "
                f"ASSETS - the browser 404s on it and the page dies")
            wanted.extend(_imports(VIEWER / module))
        # The traversal has to have gone somewhere: an import regex that
        # matched nothing would leave this checking three names.
        assert len(seen) >= 8, f"only reached {sorted(seen)}"

    def test_the_drawings_still_set_the_properties_they_used_to(self):
        """The ban is only worth having if the encodings survived it. A
        page that stopped drawing would also pass a ban on drawing."""
        # `UX-337`: `bar` - and `fill.style.width` with it - moved to
        # `primitives.js`, the module the chapters sit on. The
        # encodings are what this defends, not the filename.
        code = _code("\n".join(
            (VIEWER / name).read_text(encoding="utf-8")
            for name in ("views.js", "element.js", "decision.js",
                         "primitives.js")))
        for expected in ("fill.style.width", "box.style.flexGrow",
                         "row.style.paddingLeft",
                         'bar.style.setProperty("--w"'):
            assert expected in code, (
                f"{expected} is gone - the width channel it carries is not "
                f"drawn any more (UX-263)")


class TestThePolicyItselfStaysStrict:
    def test_the_server_sends_a_policy(self):
        assert "Content-Security-Policy" in SERVER
        assert "default-src 'self'" in SERVER

    def test_it_was_not_relaxed_to_make_the_page_work(self):
        """The declined alternative, pinned. A future reader hitting a
        refusal will find `'unsafe-inline'` first and this second."""
        assert "unsafe-inline" not in SERVER, (
            "the CSP was relaxed rather than the page fixed. The report "
            "renders element names and paths from a build; UX-263 chose "
            "CSSOM over weakening the policy")
        assert "unsafe-eval" not in SERVER


class TestTheShimAgreesWithTheBrowser:
    """The instrument half, after `UX-264` moved it.

    This used to assert that each of seven harnesses carried its own
    `_styleFor`. `UX-264` replaced the twenty-five copies with one
    `tests/dom_shim.mjs`, so the property is now stated once — which is
    the whole point of that item, and this guard following it there is
    the evidence that the move was real rather than additive.

    Measured in Chrome 141:

    ```text
    el.style.width = "50%"                 -> style="width: 50%;"
    el.style.setProperty("--w", "18.75%")  -> style="--w: 18.75%;"
    nothing set                            -> no attribute at all
    ```
    """

    def test_the_one_shim_reflects_style_into_the_attribute(self):
        shim = (REPO / "tests/dom_shim.mjs").read_text(encoding="utf-8")
        assert "styleFor" in shim, (
            "the shared DOM shim no longer reflects `.style` writes into the "
            "style attribute, so it reports success where a browser refuses "
            "(UX-263)")
        assert "node.attrs.style" in shim

    def test_no_harness_carries_the_swallowing_stub(self):
        """`style: {}` is what swallowed every write. It must not come
        back in any harness, nor in the shim."""
        offenders = []
        # The two guard files that *argue about* the stub name it in
        # their prose, and `_code` strips JavaScript comments rather
        # than Python docstrings. Ninth and tenth instance of a grep
        # finding its own argument (`UX-239`); named rather than
        # papered over with a looser pattern.
        arguing = {"test_the_page_obeys_its_own_policy.py",
                   "test_the_dom_shim_is_one_instrument.py"}
        for path in sorted((REPO / "tests/unit").glob("*.py")):
            if path.name in arguing:
                continue
            source = path.read_text(encoding="utf-8")
            if "createElement" not in source:
                continue
            # `_code`, not the raw source: the literal appears in the
            # comment that explains why it is gone. This guard shipped
            # with that bug - the eighth time in this repository that a
            # grep found its own argument (`UX-239`).
            if "style: {}" in _code(source):
                offenders.append(path.name)
        assert offenders == [], f"the swallowing stub is back in: {offenders}"

    def test_the_serialisation_matches_what_chrome_does(self):
        """Run the shim and compare against the strings Chrome
        produced. Asserting the shim against itself would prove
        nothing."""
        import json
        import shutil
        import subprocess

        node = shutil.which("node")
        if node is None:  # pragma: no cover - node is present in CI
            pytest.skip("node is not installed")
        script = """
const { makeNode } = await import(process.env.BGA_DOM_SHIM);
const a = makeNode("div"); a.style.width = "50%";
const b = makeNode("div"); b.style.flexGrow = "428.571";
const c = makeNode("div"); c.style.setProperty("--w", "18.75%");
const d = makeNode("div"); d.style.width = "50%"; d.style.paddingLeft = "1rem";
const e = makeNode("div");
console.log(JSON.stringify({width: a.attrs.style, flexGrow: b.attrs.style,
  custom: c.attrs.style, two: d.attrs.style, empty: e.attrs.style ?? null}));
"""
        import os
        done = subprocess.run(
            [node, "--input-type=module", "-e", script],
            capture_output=True, text=True, timeout=60,
            env={**os.environ,
                 "BGA_DOM_SHIM": (REPO / "tests/dom_shim.mjs").as_uri()})
        assert done.returncode == 0, done.stderr
        assert json.loads(done.stdout) == {
            "width": "width: 50%;",
            "flexGrow": "flex-grow: 428.571;",
            "custom": "--w: 18.75%;",
            "two": "width: 50%; padding-left: 1rem;",
            "empty": None,
        }, done.stdout


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
