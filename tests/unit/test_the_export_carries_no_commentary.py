"""UX-307: the attachment carries the code and none of the argument for it.

This project's modules are commented by design — the argument for a
rule lives beside the rule — and none of those readers ever opens an
exported report. `UX-205` took the whole-line comments; what it could
not take, without understanding literals, was the rest.

**The rule it replaced could only reach a comment that begins a line.**
That is safe by construction and it is also a ceiling: four trailing
`//` comments rode into every export because the rule could not see
them, and it could not be widened to see them, because four other
lines in the same bundle look exactly like a trailing comment and are
not:

```js
const PERFETTO_ORIGIN = "https://ui.perfetto.dev";
const PERFETTO_FRIENDLY_URL = "http://localhost:8080/";
const SVG_NS = "http://www.w3.org/2000/svg";
const SVG = "http://www.w3.org/2000/svg";
```

Cut at the first `//` and those become unterminated strings: the page
does not boot, it does not parse. `views.js` carries the block form of
the same hazard — the regex literal `/\\s*\\n\\s*/g` contains `*/`, so a
`/\\*.*?\\*/` pass over the whole text can pair it with a `/*` anywhere
above and delete everything in between.

So the guard is about the *distinction*, not the bytes. The bytes are
153 of a 223,074 B page — 0.07%, and this file says so out loud rather
than letting a reader assume the pass earns its keep on size. What it
earns is that the export's stripper now knows a comment from a string,
which is the property that lets it take a trailing comment at all.

It is not a minifier and must not become one (`UX-193`: no build step).
Code is left exactly as written, so a stack trace from an exported page
still quotes the source.
"""
import pathlib
import re
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools import bga_view as view  # noqa: E402

VIEWER = REPO / "bga/viewer"
MODULES = tuple(name for name in view.ASSETS if name.endswith(".js"))

# The four literals that make a naive stripper wrong. Each is a `//`
# that must survive, and they are named here rather than counted so a
# failure says which one was eaten.
SURVIVING_SLASHES = (
    '"https://ui.perfetto.dev"',
    '"http://localhost:8080/"',
    '"http://www.w3.org/2000/svg"',
)
# The block form: a regex literal whose body ends `*/`.
SURVIVING_STARSLASH = r"/\s*\n\s*/g"


def _stripped(name):
    return view._uncomment_js((VIEWER / name).read_text(encoding="utf-8"))


class TestTheStripperKnowsACommentFromAString:

    @pytest.mark.parametrize("name", MODULES)
    def test_it_removes_only_comments(self, name):
        """Every span it takes opens a comment, and the text it keeps,
        with those spans put back, is the module again."""
        source = (VIEWER / name).read_text(encoding="utf-8")
        rebuilt, at = [], 0
        for start, end in view._comment_spans(source):
            assert source[start:start + 2] in ("//", "/*"), (
                f"{name}: a removed span at {start} does not open a comment: "
                f"{source[start:start + 40]!r}")
            rebuilt.append(source[at:start])
            rebuilt.append(source[start:end])
            at = end
        rebuilt.append(source[at:])
        assert "".join(rebuilt) == source, (
            f"{name}: the spans do not tile the source, so something was "
            "dropped or double-counted")

    @pytest.mark.parametrize("name", MODULES)
    def test_stripping_twice_changes_nothing(self, name):
        once = _stripped(name)
        assert view._uncomment_js(once) == once, (
            f"{name}: a second pass found more to take, which means the "
            "first pass left something it believes is a comment")

    def test_a_comment_delimiter_inside_a_string_survives(self):
        """The acceptance test's own case, built rather than hoped for."""
        module = "\n".join((
            'const a = "a string with */ inside it";   // a real comment',
            'const b = "https://example.test/x";',
            'const c = /\\s*\\n\\s*/g;   /* a real block comment */',
            'const d = `a template',
            '// this line is data, not a comment',
            '`;',
        ))
        out = view._uncomment_js(module)
        assert '"a string with */ inside it"' in out
        assert '"https://example.test/x";' in out
        assert "const c = /\\s*\\n\\s*/g;" in out
        assert "// this line is data, not a comment" in out, (
            "a line inside a template literal was taken for a comment")
        assert "a real comment" not in out
        assert "a real block comment" not in out

    def test_the_naive_strippers_this_replaced_do_corrupt_it(self):
        """The other half of the claim: that the distinction is needed.

        A guard saying "the careful one is fine" is worth nothing
        without this — it is what makes the mutation in the Outcome a
        real one rather than a hypothetical.
        """
        module = 'const b = "https://example.test/x";\nconst c = /\\s*\\n\\s*/g;'
        naive_line = "\n".join(
            line.split("//")[0].rstrip() for line in module.splitlines())
        assert '"https:' in naive_line and '"https://example.test/x"' \
            not in naive_line, "the naive line stripper did not corrupt it"

        # The block form needs an *unpaired* `/*` for the hazard to bite,
        # which is what a `/*` inside a string literal is. A `/* ... */`
        # that closes itself never reaches the regex below - the first
        # draft of this clause used one and proved nothing.
        block = 'const a = "a glob like /* in a string";\n' + module
        naive_block = re.sub(r"/\*.*?\*/", "", block, flags=re.S)
        assert '"https://example.test/x"' not in naive_block, (
            "the naive block stripper did not pair the `/*` inside the "
            "string with the `*/` inside the regex literal, so this case "
            "no longer discriminates")
        assert view._uncomment_js(block).count("\n") == block.count("\n"), (
            "the careful pass changed the line structure of a module that "
            "contains no comment at all")


class TestNothingCommentedReachesTheAttachment:

    def test_no_module_arrives_with_a_comment_in_it(self):
        for name in MODULES:
            spans = list(view._comment_spans(_stripped(name)))
            assert not spans, f"{name}: {len(spans)} comments survived"

    def test_no_line_of_a_stripped_module_opens_a_comment(self):
        """Read a second way, so a bug in the scanner cannot hide behind
        the scanner. Whole-line comments need no literal analysis."""
        for name in MODULES:
            opens = [line for line in _stripped(name).splitlines()
                     if line.lstrip().startswith(("//", "/*", "*/"))]
            assert not opens, f"{name}: {opens[:3]}"

    def test_every_double_slash_left_is_one_of_the_named_literals(self):
        """The sharpest form, and independent of the scanner: count them.

        Every `//` remaining in the inlined bundle is inside a URL this
        file names. If a real comment survives, this is the clause that
        says so.
        """
        bundle = "\n".join(_stripped(name) for name in MODULES)
        lines = [line for line in bundle.splitlines() if "//" in line]
        for line in lines:
            assert any(literal in line for literal in SURVIVING_SLASHES), (
                f"a `//` that is not one of the named URL literals: {line!r}")
        assert len(lines) >= 4, (
            f"only {len(lines)} lines still carry a `//`; this clause was "
            "written against four URL constants and a pass over none of "
            "them would prove nothing")

    def test_the_literals_that_look_like_comments_are_still_there(self):
        bundle = "\n".join(_stripped(name) for name in MODULES)
        for literal in SURVIVING_SLASHES:
            assert literal in bundle, f"{literal} did not survive the pass"
        assert SURVIVING_STARSLASH in bundle, (
            f"{SURVIVING_STARSLASH} did not survive - a block-comment pass "
            "paired its `*/` with a `/*` somewhere above")


class TestTheRepositoryKeepsEveryWord:

    def test_the_served_page_is_the_file_on_disk(self):
        """Served mode keeps the comments: `view-source:` is a debugging
        affordance for whoever is working on the tree."""
        served = pathlib.Path(view.ASSET_DIR)
        for name in MODULES:
            on_disk = (served / name).read_text(encoding="utf-8")
            assert on_disk == (VIEWER / name).read_text(encoding="utf-8")
        app = (served / "app.js").read_text(encoding="utf-8")
        assert list(view._comment_spans(app)), (
            "app.js as served carries no comment at all, which means the "
            "stripper has been applied to the tree rather than to the copy")

    def test_the_stripped_copy_is_smaller_and_the_source_is_not(self):
        source = sum(len((VIEWER / n).read_text(encoding="utf-8"))
                     for n in MODULES)
        stripped = sum(len(_stripped(n)) for n in MODULES)
        assert stripped < source
        assert source > 300_000, (
            f"the modules total {source:,} B; this clause was written "
            "against 351,930 B and a near-empty tree would pass it")


class TestTheStylesheetsOwnHazard:

    def test_no_css_string_carries_a_comment_delimiter(self):
        """`_uncommented_css` strips `/* */` over the whole text with a
        regex, and its docstring says the one hazard is a `/*` inside a
        `content:` string, "which this file does not have and a guard
        would catch". No guard did. This is it."""
        css = (VIEWER / "style.css").read_text(encoding="utf-8")
        strings = re.findall(r"\"[^\"\n]*\"|'[^'\n]*'", css)
        carriers = [s for s in strings if "/*" in s or "*/" in s]
        assert not carriers, (
            f"a CSS string carries a comment delimiter: {carriers}. The "
            "stylesheet's stripper is a whole-text regex and would pair it "
            "with the wrong partner.")
        assert strings, (
            "no quoted string was found in style.css at all; this clause "
            "would pass vacuously and needs re-pointing")
