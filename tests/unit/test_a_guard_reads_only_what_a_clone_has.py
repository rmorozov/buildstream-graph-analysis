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
import re
import subprocess

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


def _cited_paths(path):
    """Repository paths a test file names, minus the ones it creates."""
    cited = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if WRITTEN_NOT_READ.search(line):
            continue
        for match in PATH_LITERAL.finditer(line):
            cited.add(match.group(1).rstrip("/"))
    return cited


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
            if fallback:
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
