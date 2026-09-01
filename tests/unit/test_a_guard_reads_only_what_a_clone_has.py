"""UX-276: a test that reads an untracked path guards one machine.

Round 37 shipped two guards whose whole value is that they *recompute*
pasted figures from a real run rather than comparing against a stored
expectation. Both were pointed at

```text
examples/06-macro-micro-optimization/.bga/runs/20260821T170127Z/
```

which `bga snapshot` had written on the machine that ran the build, and
which is ignored **by design**: every store `bga snapshot` creates gets
a `.gitignore` containing `*` (`UX-126`), because captures are build
artifacts (`UX-189`). The full suite passed locally, three times, and CI
failed on all four Python versions with `FileNotFoundError` before a
single assertion ran.

That is `UX-213`'s defect - a guard that only guards one machine - in
the form its own fix did not cover: `UX-213` made the *environment*
portable and said nothing about the *data*.

`UX-213`'s rule was already written down, in a comment three test files
over: *"the real capture stays as extra coverage where it exists, but it
is never the only place a mutation would be caught"*. Four guards follow
it. The two written this round did not, and nothing checked.

So this makes that rule mechanical, and only that rule. A test may name
a path that is untracked - the four that do are right to - as long as it
also names a **committed fixture**, so the untracked run is extra
coverage rather than the only data the file has. Naming an untracked
path *alone* is what passes here and fails in a clone.

The trigger is "exists here and is untracked", not "is untracked": a
path that exists nowhere cannot produce the green-here-red-there
failure, and tests name plenty of those on purpose - asserting a module
was **not** added, or building a path they then create.
"""
import pathlib
import ast
import os
import re
import subprocess
import tempfile

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]

# A path is a *repository* path here if it starts with one of the
# directories a clone has. Anything else in a string literal is a URL, a
# temp path, an element name or prose.
ROOTS = ("bga/", "tools/", "tests/", "docs/", "examples/", "schemas/")

# Written by a test rather than read by it. A test that creates a
# fixture under `tmp_path` names paths that must *not* be tracked.
WRITTEN_NOT_READ = re.compile(r"tmp_path|tmpdir|mkdtemp|TemporaryDirectory")

# Build output, not data. Untracked and present on every machine that has
# run the suite once, which would make it a permanent false positive.
NOT_DATA = ("__pycache__", ".egg-info", ".pytest_cache")

# What makes an untracked citation acceptable: the file also reads
# something a clone has. `tests/fixtures/` is where this repository keeps
# committed run directories, by convention and by the context map.
COMMITTED_DATA = "tests/fixtures/"

# What a `skipif` condition looks like when it is asking "is this path
# here?". Names rather than shapes, because the repository writes the
# question four ways (`os.path.exists`, `os.path.isdir`, `Path.exists`,
# `Path.is_dir`) and all four mean the same thing.
ABSENCE_PROBES = ("'exists'", "'isdir'", "'is_dir'", "'is_file'")

# The group around the alternation is not decoration. Without it the
# `[\w./-]+` binds to the last root only, so the pattern matches almost
# nothing and the check below passes on every file for the wrong reason.
# `TestTheCheckItselfDiscriminates` caught exactly that on this guard's
# first run, which is what those two tests are for.
PATH_LITERAL = re.compile(
    r"""["']((?:""" + "|".join(re.escape(root) for root in ROOTS)
    + r""")[\w./-]+)["']""")


def _tracked():
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=REPO, capture_output=True, text=True,
        check=True).stdout
    files = {name for name in out.split("\0") if name}
    # A directory is "tracked" if anything under it is.
    directories = set()
    for name in files:
        parts = name.split("/")
        for depth in range(1, len(parts)):
            directories.add("/".join(parts[:depth]))
    return files | directories


def _test_files():
    return sorted(p for p in (REPO / "tests").rglob("*.py")
                  if "__pycache__" not in p.parts)


def _joined_paths(text):
    """Paths assembled from `os.path.join` fragments.

    Round 43 found the hole by walking into it: a guard wrote its
    capture path as

    ```python
    os.path.join(REPO, "examples", "06-...", ".bga", "runs", ...)
    ```

    and `PATH_LITERAL` - which reads one quoted string at a time - saw
    only the fragments, none of which is a path. The file rested
    entirely on two gitignored captures, passed this check, and failed
    in CI. So the fragments are re-joined here before they are matched.

    A syntax error is not this guard's business to report; the file that
    cannot be parsed simply contributes nothing, and every other check
    in the suite will have something to say about it.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set()
    found = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = getattr(node.func, "attr", None) or getattr(node.func, "id", "")
        if name != "join":
            continue
        parts = [arg.value for arg in node.args
                 if isinstance(arg, ast.Constant) and isinstance(arg.value, str)]
        if len(parts) < 2:
            continue
        joined = "/".join(part.strip("/") for part in parts)
        if joined.startswith(ROOTS):
            found.add(joined.rstrip("/"))
    return found


def _guards_absence(text):
    """Whether the file skips when a path it names is missing.

    The other way to be safe. `COMMITTED_DATA` beside the citation was
    the only way this guard recognised, and it is not the only way the
    repository actually uses: a `skipif` keyed on the path's existence
    means the clause does not run in a clone rather than failing there,
    which is exactly the outcome this guard exists to secure.

    Round 43 found the gap by fixing a file the honest way - skip-marks
    plus generated stand-ins for the properties - and watching this
    guard still call it an offender. Recognising a committed fixture
    and not a skip was a rule about *how* rather than about *whether*.

    The detection is a proxy: a `skipif` whose condition mentions an
    existence test. It cannot tell which clauses that mark covers, so a
    file that skips one clause and leaves another unguarded still gets
    past - which is why the suite is also run with the untracked paths
    moved aside, and why that is the check this one only approximates.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if getattr(node.func, "attr", None) != "skipif":
            continue
        condition = ast.dump(node.args[0]) if node.args else ""
        if any(probe in condition for probe in ABSENCE_PROBES):
            return True
    return False


def _compared_not_opened(text):
    """Path literals every occurrence of which is a comparison operand.

    `UX-462`. The third shape this guard could not see, and the first
    one in the other direction — a false positive rather than a miss.
    `tests/unit/test_fine_grained_fixture.py` names the generated bulk
    tree exactly once:

    ```python
    assert "examples/09-fine-grained-siblings/files/bulk/" in ignored
    ```

    which asserts the string is a *line of `.gitignore`*. The file
    never opens it. But `examples/README.md` tells the reader to
    generate that tree, so on any machine that followed the guide the
    path exists and is untracked, and this guard reported the file as
    resting on it — red from machine state, with nothing in the diff.

    A comparison operand is the one position in which a literal
    provably cannot reach the filesystem: nothing downstream of `in`,
    `==` or `!=` opens anything. That is why the rule is stated over
    AST position and not over the spelling. A trailing slash, or the
    word `gitignore` on the line, would be a proxy for "this is not a
    read" — fixing guide §5, in the guard whose subject is §5's cousin.

    Every occurrence, not any: a file that compares the path on one
    line and opens it on another still depends on it, and is still
    reported.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set()
    literals, compared = {}, set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            for operand in (node.left, *node.comparators):
                compared.add(id(operand))
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            literals.setdefault(node.value, []).append(id(node))
    names = set()
    for value, occurrences in literals.items():
        if not all(where in compared for where in occurrences):
            continue
        for match in PATH_LITERAL.finditer(f'"{value}"'):
            names.add(match.group(1).rstrip("/"))
    return names


def _cited_paths(path):
    """Repository paths a test file names, minus the ones it creates."""
    text = path.read_text(encoding="utf-8")
    cited = set()
    for line in text.splitlines():
        if WRITTEN_NOT_READ.search(line):
            continue
        for match in PATH_LITERAL.finditer(line):
            cited.add(match.group(1).rstrip("/"))
    # `os.path.join` fragments, which the line-at-a-time regex cannot
    # see. Not filtered by `WRITTEN_NOT_READ`: a join that builds a
    # path under `tmp_path` has a non-constant first argument, so it
    # never reaches `ROOTS` in the first place.
    return (cited | _joined_paths(text)) - _compared_not_opened(text)


def _cited_paths_of(source, tmp=None):
    """`_cited_paths` over a source string, for the checks below."""
    handle = tempfile.NamedTemporaryFile(
        "w", suffix=".py", delete=False, encoding="utf-8")
    with handle:
        handle.write(source)
    try:
        return _cited_paths(pathlib.Path(handle.name))
    finally:
        os.unlink(handle.name)


def _untracked_but_present(cited, tracked):
    """The dangerous class, and only it."""
    return sorted(
        name for name in cited
        if name not in tracked
        and not any(part in name for part in NOT_DATA)
        and (REPO / name).exists())


class TestEveryPathAGuardNamesIsInTheClone:
    def test_no_test_rests_only_on_an_untracked_path(self):
        tracked = _tracked()
        offenders = []
        for path in _test_files():
            cited = _cited_paths(path)
            risky = _untracked_but_present(cited, tracked)
            if not risky:
                continue
            fallback = [name for name in cited
                        if name.startswith(COMMITTED_DATA) and name in tracked]
            if fallback or _guards_absence(path.read_text(encoding="utf-8")):
                continue
            offenders.append(
                f"{path.relative_to(REPO)} -> {risky} (and no committed "
                f"fixture beside it)")
        assert offenders == [], (
            "test(s) whose only data is a path git does not track. It "
            "exists on this machine and will not exist in a clone, so they "
            "pass here and fail in CI before an assertion runs:\n  "
            + "\n  ".join(offenders))

    def test_the_files_that_use_a_real_capture_as_extra_coverage_are_allowed(self):
        """`UX-213`'s rule, from the other side: four guards name the
        ignored snapshot deliberately, beside a committed fixture. This
        check must not push them into deleting the extra coverage.

        Only observable where the capture exists. In a clone - and in
        CI - there is nothing untracked to be exempted, so there is
        nothing to check, and this **skips with the reason** rather than
        passing: "we could not look" must not read as "we looked and it
        was fine". `conftest`'s skip census (`UX-235`) surfaces it.

        Getting this wrong is the same defect one level up, and it was
        caught the same way - by running the suite in a real clone
        instead of trusting a local green.
        """
        tracked = _tracked()
        pairs = [p for p in _test_files()
                 if _untracked_but_present(_cited_paths(p), tracked)
                 and any(n.startswith(COMMITTED_DATA) and n in tracked
                         for n in _cited_paths(p))]
        if not pairs:
            candidates = [p for p in _test_files()
                          if any(n.startswith("examples/") and ".bga" in n
                                 for n in _cited_paths(p))]
            assert candidates, (
                "no test names a capture under a snapshot store at all, so "
                "the exemption is dead code - remove it or re-point it")
            pytest.skip(
                f"no local capture to exempt: {len(candidates)} test file(s) "
                f"name one and none is present in this checkout")
        assert pairs

    def test_the_snapshot_store_is_the_case_this_was_filed_on(self):
        """Pinned, because it is the shape that will recur: `bga
        snapshot` writes a `.gitignore` of `*` into every store it
        creates, so a path under one is never in a clone."""
        store = REPO / "examples/06-macro-micro-optimization/.bga/.gitignore"
        if not store.exists():
            pytest.skip("no snapshot store in this checkout")
        assert store.read_text(encoding="utf-8").rstrip().endswith("*"), (
            "the snapshot store no longer ignores everything, which is the "
            "premise this guard rests on")

    def test_the_replacement_fixture_is_tracked(self):
        """And the fixture the two round-37 guards moved onto is."""
        tracked = _tracked()
        for name in ("tests/fixtures/macro_micro/run/run-context.json",
                     "tests/fixtures/macro_micro/run/graph.json",
                     "tests/fixtures/macro_micro/run/trace.json",
                     "tests/fixtures/macro_micro/plane2.json"):
            assert name in tracked, f"{name} is not tracked"


class TestTheCheckItselfDiscriminates:
    """A path checker that matches nothing passes everywhere."""

    def test_it_finds_the_paths_that_are_there(self):
        cited = _cited_paths(
            REPO / "tests/unit/test_the_journey_reaches_what_if.py")
        assert "tests/fixtures/macro_micro/run" in cited, (
            f"the extractor found no fixture path in a file that names one: "
            f"{sorted(cited)}")

    def test_it_reads_a_path_assembled_from_join_fragments(self):
        """The hole round 43 walked into.

        `test_the_pairing_pass_streams.py` wrote its two captures as
        `os.path.join` fragments, so the line-at-a-time regex saw
        `"examples"` and `".bga"` and nothing that looked like a path.
        The file rested entirely on two gitignored captures, passed
        this check, and failed in CI on three clauses.
        """
        source = (
            'import os\n'
            'X = os.path.join(REPO, "examples", "06-macro-micro-optimization",'
            ' ".bga", "runs", "20260821T170127Z", "plane2.log.gz")\n')
        assert not PATH_LITERAL.search(source), (
            "the regex now reads this on its own, so this test no longer "
            "shows what the join walk is for")
        assert _joined_paths(source) == {
            "examples/06-macro-micro-optimization/.bga/runs/"
            "20260821T170127Z/plane2.log.gz"}

    def test_the_join_walk_ignores_a_join_that_builds_nothing(self):
        """Two fragments that are not a repository path, and a join
        whose parts are not constants, must not become citations."""
        assert _joined_paths('os.path.join(a, b)') == set()
        assert _joined_paths('os.path.join("var", "log")') == set()
        assert _joined_paths('os.path.join(tmp, "out.json")') == set()

    def test_a_skipif_on_the_paths_absence_is_the_other_way_to_be_safe(self):
        """A clause that skips when the capture is gone does not fail in
        a clone, which is the whole property this guard secures."""
        assert _guards_absence(
            'import os, pytest\n'
            'M = pytest.mark.skipif(not os.path.exists(P), reason="gone")\n')
        assert _guards_absence(
            'import pytest\n'
            'M = pytest.mark.skipif(not CAPTURE.is_dir(), reason="gone")\n')

    def test_a_skipif_about_something_else_does_not_count(self):
        """`node is None` says nothing about whether the capture is
        here, and must not buy a file an exemption."""
        assert not _guards_absence(
            'import pytest, shutil\n'
            'M = pytest.mark.skipif(shutil.which("node") is None, reason="x")\n')
        assert not _guards_absence('x = 1\n')

    def test_a_path_only_ever_compared_as_text_is_not_a_citation(self):
        """`UX-462`. The gitignore-membership assertion, in miniature:
        the literal reaches no filesystem call, so whether it exists on
        this machine cannot change the outcome."""
        source = ('with open(".gitignore") as handle:\n'
                  '    ignored = handle.read()\n'
                  'assert "examples/09-fine-grained-siblings/files/bulk/"'
                  ' in ignored\n')
        assert PATH_LITERAL.search(source), (
            "the extractor no longer reads this literal at all, so this "
            "test no longer shows what the comparison filter is for")
        assert "examples/09-fine-grained-siblings/files/bulk" not in \
            _cited_paths_of(source)

    def test_a_path_compared_on_one_line_and_opened_on_another_still_counts(self):
        """Every occurrence, not any. A file that also opens the path
        depends on it, and the comparison must not buy it an exemption."""
        source = ('assert "tests/fixtures/macro_micro/run" in ignored\n'
                  'open("tests/fixtures/macro_micro/run")\n')
        assert "tests/fixtures/macro_micro/run" in _cited_paths_of(source)

    def test_the_filter_does_not_swallow_a_different_path(self):
        """Two literals, one compared and one opened. Only the compared
        one is dropped - a filter keyed on the file rather than on the
        literal would clear both."""
        source = ('assert "docs/spec/specification.md" in text\n'
                  'open("tests/fixtures/macro_micro/run")\n')
        cited = _cited_paths_of(source)
        assert "docs/spec/specification.md" not in cited
        assert "tests/fixtures/macro_micro/run" in cited

    def test_the_case_this_was_filed_on_is_not_reported(self):
        """The real file, against the real tree. Only observable where
        the generated tree is present; in a clone there is nothing
        untracked to mis-report, so this **skips with the reason**."""
        bulk = REPO / "examples/09-fine-grained-siblings/files/bulk"
        if not bulk.is_dir():
            pytest.skip(
                "no bulk tree in this checkout - examples/README.md says "
                "how to make one")
        target = REPO / "tests/unit/test_fine_grained_fixture.py"
        assert "examples/09-fine-grained-siblings/files/bulk" not in \
            _untracked_but_present(_cited_paths(target), _tracked())

    def test_it_would_have_flagged_the_original(self):
        """The literal that shipped, checked against the tree."""
        original = ("examples/06-macro-micro-optimization/"
                    ".bga/runs/20260821T170127Z/run")
        assert PATH_LITERAL.search(f'"{original}"'), (
            "the extractor does not recognise the path this was filed on")
        assert original not in _tracked(), (
            "the snapshot store is tracked now, so this check no longer "
            "demonstrates anything - re-point it at a real ignored path")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
