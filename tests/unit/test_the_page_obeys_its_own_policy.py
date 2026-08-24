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

    def test_the_html_carries_no_inline_style_either(self):
        html = (VIEWER / "index.html").read_text(encoding="utf-8")
        assert not re.search(r"<[^>]+\sstyle=", html), (
            "index.html has an inline style attribute, which the CSP refuses "
            "at parse time")

    def test_the_drawings_still_set_the_properties_they_used_to(self):
        """The ban is only worth having if the encodings survived it. A
        page that stopped drawing would also pass a ban on drawing."""
        code = _code((VIEWER / "views.js").read_text(encoding="utf-8"))
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
    """The instrument half. Measured in Chrome 141:

    ```text
    el.style.width = "50%"                 -> style="width: 50%;"
    el.style.flexGrow = "428.571"          -> style="flex-grow: 428.571;"
    el.style.setProperty("--w", "18.75%")  -> style="--w: 18.75%;"
    nothing set                            -> no attribute at all
    ```
    """

    SHIMS = ["test_the_first_screen_is_a_decision", "test_what_if_i_fix_these",
             "test_focused_graphs_not_a_dag_viewer",
             "test_every_element_is_one_object",
             "test_one_click_from_investigation",
             "test_a_report_you_can_navigate", "test_the_page_that_answers_why"]

    @pytest.mark.parametrize("name", SHIMS)
    def test_each_shim_reflects_style_into_the_attribute(self, name):
        source = (REPO / "tests/unit" / f"{name}.py").read_text(encoding="utf-8")
        assert "_styleFor" in source, (
            f"{name}'s DOM shim does not reflect `.style` writes into the "
            f"style attribute, so it reports success where a browser "
            f"refuses (UX-263)")
        # `_code`, not the raw source: the swallowing literal appears in
        # the comment inside `_styleFor` that explains why it is gone.
        # This guard shipped with that bug and it is the eighth time -
        # a guard that greps finds its own argument (`UX-239`).
        assert "style: {}" not in _code(source), (
            f"{name} still carries the swallowing `style: {{}}`")

    def test_the_serialisation_matches_what_chrome_does(self):
        """Run the shim's own helper and compare against the strings
        Chrome produced. Asserting the shim against itself would prove
        nothing."""
        import json
        import shutil
        import subprocess

        node = shutil.which("node")
        if node is None:  # pragma: no cover - node is present in CI
            pytest.skip("node is not installed")
        source = (REPO / "tests/unit/test_focused_graphs_not_a_dag_viewer.py"
                  ).read_text(encoding="utf-8")
        helper = source.split("function _styleFor(node) {", 1)[1]
        helper = "function _styleFor(node) {" + helper.split("\n}\n", 1)[0] + "\n}"
        script = helper + """
const mk = () => { const n = {attrs: {}}; n.style = _styleFor(n); return n; };
const a = mk(); a.style.width = "50%";
const b = mk(); b.style.flexGrow = "428.571";
const c = mk(); c.style.setProperty("--w", "18.75%");
const d = mk(); d.style.width = "50%"; d.style.paddingLeft = "1rem";
const e = mk();
console.log(JSON.stringify({width: a.attrs.style, flexGrow: b.attrs.style,
  custom: c.attrs.style, two: d.attrs.style,
  empty: e.attrs.style ?? null}));
"""
        done = subprocess.run([node, "--input-type=module", "-e", script],
                              capture_output=True, text=True, timeout=60)
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
