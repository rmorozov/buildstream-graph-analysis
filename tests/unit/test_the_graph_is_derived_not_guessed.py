"""UX-340: the instrument that derives the viewer's dependency graph.

`UX-337` moved half the viewer between modules, and the Required Fix put
the graph first: *derived, not guessed*. It was derived twice, because
the first derivation was wrong — and wrong in the direction that does
not announce itself. It reported a **cleaner** split than the truth.

Counting which symbols cross a proposed cut means ignoring names that
only appear in prose. That was done with regexes, and the
template-literal pattern — written to skip `${…}` so an interpolated
expression stayed visible — matched no template that had one. Its
opening backtick paired with a later one and the file between them
vanished:

```text
app.js's declarations, raw   1,124 lines
after block comments         1,024
after line comments          1,024
after template literals        148     <- 87% of the file, silently
```

Three real crossings were missing. Each is a `ReferenceError` in the
concatenated export, which is `UX-199`'s empty report.

**What these clauses are for.** Not that the tool exists — that a
scratch file also satisfies. That its answer agrees with the function
the export actually walks with, and that on a module built out of the
traps the regex fell into, the scanner and the pattern **differ**. A
guard asserting the scanner's output alone would pass with the broken
pattern substituted, which is the shape this repository keeps catching
in its own work.
"""
import json
import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
TOOL = REPO / "tools/dev_js_deps.py"
FIXTURE = REPO / "tests/fixtures/js/interpolated.js"
VIEWER = REPO / "bga/viewer"

# The grouping the fixture is built around: two modules' worth of names.
GROUPS = {"lower": ["LABEL", "HIDDEN", "alpha", "render", "delta"],
          "upper": ["beta", "gamma"]}


def _run(*argv):
    done = subprocess.run([sys.executable, str(TOOL), *argv],
                          capture_output=True, text=True, cwd=REPO)
    return done


def _regex_stripped(source):
    """The instrument that was wrong, kept so the difference is visible.

    Verbatim the three substitutions the first derivation used. It is
    here as the *contrast* — if the scanner is ever replaced by this,
    the clause below stops seeing a difference and reddens.
    """
    text = re.sub(r"/\*.*?\*/", " ", source, flags=re.S)
    text = re.sub(r"(?m)//.*$", " ", text)
    text = re.sub(r"`(?:[^`\\$]|\\.|\$(?!\{))*`", " ", text)
    text = re.sub(r'"(?:[^"\\]|\\.)*"', " ", text)
    text = re.sub(r"'(?:[^'\\]|\\.)*'", " ", text)
    return text


class TestItAgreesWithTheFunctionTheExportUses:

    def test_the_order_is_the_order_the_export_inlines_in(self):
        """Asserted against the real function, not a written-down list.

        An instrument that agrees with the thing it describes only by
        coincidence is not an instrument, and a literal here would go
        stale the first time a module is added.
        """
        import tools.bga_view as view

        done = _run("--order", "bga/viewer")
        assert done.returncode == 0, done.stderr
        assert done.stdout.split() == view._module_order(), (
            f"dev_js_deps and bga_view disagree about the inline order:\n"
            f"  tool   {done.stdout.split()}\n"
            f"  export {view._module_order()}")

    def test_the_viewer_has_no_import_cycle(self):
        done = _run("--graph", "bga/viewer", "--json")
        assert done.returncode == 0, done.stderr
        assert json.loads(done.stdout)["cycles"] == [], (
            "an import cycle in bga/viewer: the export emits an order in "
            "which a module precedes something it imports, and the "
            "concatenated blob reads a const in its temporal dead zone")

    def test_it_reads_every_module_the_directory_holds(self):
        """A walker that silently reached nothing would pass the two
        clauses above by agreeing about an empty answer."""
        done = _run("--graph", "bga/viewer", "--json")
        edges = json.loads(done.stdout)["imports"]
        shipped = {p.name for p in VIEWER.iterdir() if p.suffix == ".js"}
        assert set(edges) == shipped, sorted(shipped ^ set(edges))
        assert sum(len(v) for v in edges.values()) > 20, (
            f"only {sum(len(v) for v in edges.values())} import edges found "
            f"across {len(edges)} modules; the import pattern matched almost "
            f"nothing, which is how the first instrument failed")


class TestTheScannerSeesWhatThePatternAte:

    def test_the_pattern_eats_a_whole_function_and_the_scanner_does_not(self):
        """The difference, on the module built out of the traps.

        Not "the scanner keeps N tokens" — that passes with the broken
        pattern substituted for a small enough N. What is asserted is
        that the two disagree, and about what: `gamma` sits between two
        template literals, so the pattern's first unmatched closing
        backtick pairs with the second template's opening one and takes
        the function with it.
        """
        from tools.dev_js_deps import strip_comments

        source = FIXTURE.read_text(encoding="utf-8")
        scanned = strip_comments(source)
        pattern = _regex_stripped(source)
        assert scanned.count("gamma") == 1 and pattern.count("gamma") == 0, (
            f"the pattern sees `gamma` {pattern.count('gamma')} time(s) and "
            f"the scanner {scanned.count('gamma')}. `gamma` is supposed to "
            f"vanish from the pattern's output entirely — if it no longer "
            f"does, either the fixture lost one of its two templates or "
            f"`_regex_stripped` is no longer the instrument that was wrong, "
            f"and this clause asserts nothing")
        # Counted, not searched for: both names are *declared* at the top
        # level as well as used in `gamma`, and both instruments keep a
        # declaration. Two occurrences means the use survived.
        for name in ("LABEL", "HIDDEN"):
            assert scanned.count(name) == 2, (
                f"the scanner sees {scanned.count(name)} `{name}`, not the "
                f"declaration and the use in `gamma`")
            assert pattern.count(name) == 1, (
                f"the pattern sees {pattern.count(name)} `{name}` — it is "
                f"supposed to lose the use inside the eaten function")
        assert len(scanned.split()) > len(pattern.split()), (
            f"the pattern kept as much as the scanner "
            f"({len(pattern.split())} vs {len(scanned.split())} tokens)")

    def test_a_comment_and_a_string_make_no_reference(self):
        from tools.dev_js_deps import strip_comments

        scanned = strip_comments(FIXTURE.read_text(encoding="utf-8"))
        assert scanned.count("alpha") == 1, (
            f"`alpha` appears {scanned.count('alpha')} times after "
            f"stripping: it is declared once and named once in a comment, "
            f"and the comment must not read as a use")
        assert "example.invalid" not in scanned, (
            "a string body survived — and that string holds a `//`, so a "
            "line-comment pattern applied to it eats the rest of the line")

    def test_the_crossing_count_is_the_real_one(self):
        done = _run("--crossings", str(FIXTURE), "--groups",
                    json.dumps(GROUPS), "--json")
        assert done.returncode == 0, done.stderr
        result = json.loads(done.stdout)
        assert result["unplaced"] == [], result["unplaced"]
        assert result["crossings"] == {"upper <- lower": ["HIDDEN", "LABEL"]}, (
            f"the crossing count changed: {result['crossings']}. `LABEL` is "
            f"reachable only through an interpolation, `render` is gamma's "
            f"parameter and `alpha` is named only in prose — the last two "
            f"are the false edges UX-337 had to spot by reading")

    def test_a_declaration_owns_the_comment_block_above_it(self):
        """The seam is the prose, not the line number.

        Cutting at the declaration leaves each docstring attached to the
        function *before* it, which is how a move turns into a diff
        nobody can read.
        """
        from tools.dev_js_deps import declarations

        blocks = {b["name"]: b for b in declarations(FIXTURE)}
        assert set(blocks) == {"LABEL", "HIDDEN", "alpha", "render", "beta",
                               "gamma", "delta"}, sorted(blocks)
        # The prose above `delta` belongs to `delta`. Cutting at the
        # declaration line instead leaves it attached to `gamma`, the
        # function before it — which is how a move turns into a diff
        # nobody can read.
        assert "second template" in blocks["delta"]["text"], (
            "delta lost the comment block written above it")
        assert "second template" not in blocks["gamma"]["text"], (
            "gamma absorbed the comment block that introduces delta: the "
            "carver is cutting on the declaration line, not on the seam")
        assert blocks["gamma"]["end"] < blocks["delta"]["start"], (
            "the blocks overlap")


class TestTheToolRefusesRatherThanGuesses:

    def test_a_grouping_that_leaves_a_declaration_out_is_named(self):
        """A partial grouping silently answered would report a clean
        split that is clean only because half of it was not counted."""
        done = _run("--crossings", str(FIXTURE), "--groups",
                    json.dumps({"lower": ["LABEL"], "upper": ["beta"]}),
                    "--json")
        assert done.returncode == 1, done.stdout
        left_out = json.loads(done.stdout)["unplaced"]
        assert set(left_out) == {"HIDDEN", "alpha", "delta", "gamma",
                                 "render"}, left_out

    def test_crossings_without_a_grouping_is_an_error(self):
        done = _run("--crossings", str(FIXTURE))
        assert done.returncode != 0
        assert "--groups" in done.stderr

    def test_it_says_what_it_reads(self):
        """UX-340's Out of Scope: not a JavaScript parser, and it has to
        say so where the reader is, not only in the task file."""
        source = " ".join(TOOL.read_text(encoding="utf-8").split())
        assert "not a JavaScript parser" in source
        assert "not a scope analysis" in source, (
            "the parameter subtraction is not scope analysis, and a reader "
            "who assumes it is will trust an answer it cannot give")
