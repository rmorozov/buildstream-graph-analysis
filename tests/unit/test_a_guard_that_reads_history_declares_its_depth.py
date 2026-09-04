"""UX-637: a guard that reads history says what it does about depth.

A shallow clone answers reachability from the commits it has and stops
at the boundary in `.git/shallow`. It does not warn. Measured in round
86, on this environment's own checkout:

```text
git rev-list <the PR merge ref> | wc -l          562  ->  1202 unshallowed
git merge-base --is-ancestor v0.2.0 origin/main  exit 1  ->  exit 0
```

`UX-633` was filed on the first answer and CI, which sets
`fetch-depth: 0`, was right every time. That is `UX-213`'s defect one
turn worse: not a guard that checks nothing here, a guard that reaches
the **opposite** conclusion here and states it with confidence.

Round 86 fixed the release-reachability clause. This is the sweep, and
it is prospective: the population was two files when it was written, so
the value is that the third cannot arrive undeclared.

Depth-dependent is *ancestry*, not *content*: `git show <ref>:<path>`
reads a tree that is either present or absent and fails loudly, while
`log`, `rev-list`, `merge-base` and `--diff-filter` answer a question
whose truth changes with how much history the clone has.

Its limit, stated: this reads that a module **names** the predicate,
not that it branches on it. A dead `_shallow()` nobody calls would pass
here and is `test_a_release_records_a_contract_state.py`'s own skip to
hold.

holds: rules.md#a-history-figure-from-a-shallow-clone-is-worth-nothing-ask-is-shallow-repository-first
"""
import ast
import functools
import pathlib
import subprocess

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]

#: An argv token whose answer moves with the clone's depth. Whole
#: literals only - `"git log --oneline -1"` is a sentence a document
#: quotes, `"log"` is an argument a subprocess is handed.
DEPTH_DEPENDENT = frozenset({
    "log", "rev-list", "merge-base", "describe", "blame", "shortlog"})

#: The same question written as an option rather than a subcommand.
DEPTH_DEPENDENT_PREFIXES = ("--diff-filter",)

#: How a file declines. `--is-shallow-repository` is git's own answer;
#: `shallow` is the boundary file under the git dir, which
#: `test_the_verification_log_is_true.py` reads instead - deliberately,
#: because this repository is normally worked in a grafted clone that
#: is shallow *and* carries the commits that guard needs.
DECLARES_DEPTH = ("--is-shallow-repository", "shallow")


def _strings(nodes):
    return [n.value for n in nodes
            if isinstance(n, ast.Constant) and isinstance(n.value, str)]


def argv_literals(source):
    """Every string a module hands to **git**, not every string it holds.

    Two shapes, both in this tree: a sequence whose first token is
    `"git"`, and a call to a helper whose name says git - the release
    guard writes `_git("merge-base", …)` and the argv is assembled
    inside. Position, not presence: `open(tmp_path / "log")` and
    `message="log"` are the two false positives the first writing had,
    and a bare-literal scan cannot tell either from an argument.

    Pure, so its discrimination is a testable claim rather than an
    intention.
    """
    found = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.List, ast.Tuple)):
            tokens = _strings(node.elts)
            if tokens and tokens[0] == "git":
                found.update(tokens[1:])
        elif isinstance(node, ast.Call):
            name = getattr(node.func, "id", None) or getattr(
                node.func, "attr", "")
            if "git" in name.lower():
                found.update(_strings(node.args))
    return found


def reads_history(source):
    """Does this module ask git a question whose answer moves with depth?"""
    literals = argv_literals(source)
    if literals & DEPTH_DEPENDENT:
        return True
    return any(one.startswith(DEPTH_DEPENDENT_PREFIXES) for one in literals)


def declares_depth(source):
    """Does it say what it does about a truncated history?

    A whole string constant, never a substring: `--is-shallow-repository`
    is an argv token and `shallow` a path segment, and both are things a
    module *runs*. A file that only writes the word in a docstring has
    explained the hazard and still concludes from a truncated history,
    which is the defect wearing its own explanation.
    """
    return any(node.value in DECLARES_DEPTH for node in ast.walk(
        ast.parse(source)) if isinstance(node, ast.Constant)
        and isinstance(node.value, str))


@functools.lru_cache(maxsize=1)
def _tracked_tests():
    """git's list, never a glob: the main checkout carries
    `.claude/worktrees/<agent>/`, a whole second tree (`UX-577`)."""
    out = subprocess.run(["git", "ls-files", "tests/"], cwd=REPO, check=True,
                         capture_output=True, text=True).stdout.split()
    return tuple(sorted(rel for rel in out if rel.endswith(".py")))


@functools.lru_cache(maxsize=1)
def _population():
    """`{path: source}` for every test module that reads history.

    Cached: three clauses read it, and parsing 487 modules three times
    put this file over `tests/tiers.py`'s 1.0s medium floor for nothing.
    """
    found = {}
    for rel in _tracked_tests():
        source = (REPO / rel).read_text(encoding="utf-8")
        # Not a heuristic: `argv_literals` only yields a token from a
        # sequence headed by `"git"` or a call whose name says git, so a
        # module without the substring cannot produce one. Skipping its
        # parse cannot change the answer, only the seconds.
        if "git" in source and reads_history(source):
            found[rel] = source
    return found


class TestTheInstrumentDiscriminates:
    """The population is decided by `reads_history`, so every clause
    below is a claim about what it selects. A looser scan only *grows*
    the population and a tighter one empties it, and neither reddens
    the clause that matters - so the two directions are read here."""

    def test_an_argument_counts_and_a_sentence_does_not(self):
        assert reads_history('subprocess.run(["git", "log", "-1"])')
        assert reads_history('_git("merge-base", a, b)')
        assert reads_history('run(["git", "diff", "--diff-filter=A"])')
        assert not reads_history('CMD = "git log --oneline -1"')

    def test_a_docstring_naming_git_log_is_not_a_call(self):
        assert not reads_history('"""run `git log` first."""\nx = 1\n')
        assert not reads_history('def f():\n    "log"\n')

    def test_a_literal_outside_a_git_argv_is_not_an_argument(self):
        """The two false positives the first writing had: a file named
        `log` under `tmp_path`, and `message="log"` in a fixture."""
        assert not reads_history('open(tmp_path / "log", "w")')
        assert not reads_history('_event("E", message="log")')
        assert not reads_history('CMDS = ["bst", "log"]')

    def test_reading_a_tree_is_not_reading_history(self):
        """`git show <ref>:<path>` and `git ls-files` are content. A
        shallow clone either has that object or fails - it cannot
        answer differently, which is the whole defect."""
        assert not reads_history('_git("show", f"{tag}:pyproject.toml")')
        assert not reads_history('run(["git", "ls-files", "-z"])')

    def test_the_declaration_is_a_literal_and_not_a_word(self):
        """A whole constant. The first writing skipped docstrings to get
        this, and the mutation that removed the skip left every clause
        green - the exclusion was doing nothing, because prose is never
        equal to `shallow`. This reads the property that is actually
        load-bearing."""
        assert declares_depth('_git("rev-parse", "--is-shallow-repository")')
        assert declares_depth('pathlib.Path(gitdir, "shallow")')
        assert not declares_depth('"""a shallow clone answers."""\nx = 1\n')
        assert not declares_depth('MSG = "this checkout is shallow"')
        # The other direction: `DECLARES_DEPTH` is an exemption, and an
        # exemption widened to an ordinary argv token excuses the whole
        # population at once without failing anything above.
        assert not declares_depth('_git("merge-base", "HEAD", "-1")')


class TestThePopulationIsNotEmpty:
    """Every clause below passes on a scan that finds nothing."""

    def test_the_scan_reads_the_whole_test_tree(self):
        assert len(_tracked_tests()) >= 300, (
            f"{len(_tracked_tests())} test modules - `git ls-files tests/` "
            f"stopped resolving")

    def test_the_guards_this_item_was_filed_about_are_in_it(self):
        """Named, so a `DEPTH_DEPENDENT` narrowed to nothing reddens
        here rather than emptying the clause below in silence."""
        found = set(_population())
        for rel in ("tests/unit/test_a_release_records_a_contract_state.py",
                    "tests/unit/test_the_verification_log_is_true.py"):
            assert rel in found, (
                f"{rel} reads history and this scan does not see it; "
                f"the population is {sorted(found)}")

    def test_the_scan_selects_rather_than_sweeps(self):
        """A population of everything is the other way to be vacuous."""
        population = _population()
        assert len(population) <= len(_tracked_tests()) // 4, (
            f"{len(population)} of {len(_tracked_tests())} modules read "
            f"history; `reads_history` has stopped selecting")


class TestEveryHistoryReadingGuardDeclaresItsDepth:

    def test_a_guard_that_reads_history_says_what_a_shallow_clone_gets(self):
        """The item's sweep. A module added after this reads history and
        neither declines nor says why is named here, by path."""
        silent = sorted(rel for rel, source in _population().items()
                        if not declares_depth(source))
        assert silent == [], (
            f"test module(s) reading git history with nothing said about "
            f"depth: {silent}. Ask `git rev-parse --is-shallow-repository` "
            f"and skip with a reason in `KNOWN_SKIP_REASONS`, or read the "
            f"graft boundary - a shallow clone answers and does not say so "
            f"(UX-637)")

    def test_ci_asks_for_the_history_these_guards_read(self):
        """The declines above are a skip, and a skip on every machine is
        a guard that checks nothing. CI is the machine that must not
        have a shallow clone."""
        workflow = (REPO / ".github/workflows/ci.yml").read_text(
            encoding="utf-8")
        assert "fetch-depth: 0" in workflow, (
            "ci.yml's checkout does not ask for the whole history, so every "
            "clause above declines there and the sweep guards nothing")


def test_the_contributing_guide_tells_a_session_its_clone_may_be_shallow():
    """The developer-facing half. A guard cannot help a session that
    measures a history figure by hand and pastes it into a round
    document, which is what round 86 did four times."""
    guide = (REPO / "docs/contributing/fixing-guide.md").read_text(
        encoding="utf-8")
    for stated in ("--is-shallow-repository", "git fetch --unshallow"):
        assert stated in guide, (
            f"the fixing guide does not name {stated!r} - a session has no "
            f"way to learn its clone is truncated before it measures")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
