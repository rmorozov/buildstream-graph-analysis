"""UX-239: the context map describes the tree, or it is worse than none.

`docs/contributing/fixing-guide.md` section 6 tells a low-context
session **not to re-derive** where things live. Measured when this was
filed, it said:

```text
tests/test_e2e.py      only existing test file
```

against 220 test files, and named none of `schemas.py`, `compare.py`,
`blast.py`, `correlate.py`, `provenance.py`, `whatif.py`,
`store_aggregate.py`, `hostinfo.py`, `run_store.py`, `cache_trend.py`,
`suspend.py`, `sources.py`, `progress.py`, `bga/report/`, `bga/viewer/`
or `tools/` at all.

A map that is confidently wrong exactly where confidence was requested
costs more than no map. So it is checked against the tree, both
directions.
"""
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
GUIDE = REPO / "docs/contributing/fixing-guide.md"

# Modules small enough or private enough that naming each one would make
# the map longer without making it more useful. Each is *reachable* -
# `bga/__init__.py` is not a place anyone needs directing to.
NOT_ON_THE_MAP = {"bga/__init__.py", "tools/__init__.py"}

# `UX-274`: the guard above globbed `bga/` and `tools/` and nothing else,
# so the map's **Tests and docs** block was unguarded prose from the day
# `UX-239` wrote it. Measured at review 2, it had drifted to 5 of the 12
# entries directly under `tests/`, and the three it was missing hardest
# were the harnesses the viewer axis had just built - `dom_shim.mjs`
# (`UX-264`) and `cdp.mjs` + `browser.py` (`UX-257`). A session needing
# to assert something about the page read §6, was pointed at neither, and
# wrote its twenty-sixth inline shim, which is exactly the cost `UX-264`
# measured and removed.
NOT_IN_TESTS = set()

# `UX-512`: two kinds of exemption, and the existence check below is
# right for only one of them. A *source* path that has since vanished
# silently widens the map check, so it must exist. A *build artefact* is
# absent on a fresh clone and present after any run, so requiring it to
# exist made this file red exactly when `UX-508`'s trap tells a round to
# clear bytecode before a same-length mutation - and that presented as a
# flake in one `make test-small` before it was reproduced. Matched by
# directory name, and the artefact never has to be there.
BUILD_ARTEFACTS = {"__pycache__", ".pytest_cache"}


def _map_text():
    """The map itself - the fenced blocks - and not the prose around it.

    The first draft of this guard read the whole of section 6, and so
    matched the paragraph that *quotes* the old bad map as the reason
    the section was regenerated. A guard that is satisfied by its own
    explanation checks nothing.
    """
    text = GUIDE.read_text(encoding="utf-8")
    assert "## 6. Where things live" in text, "the guide has no context map"
    section = text.split("## 6. Where things live", 1)[1].split("\n## 7.", 1)[0]
    blocks = section.split("```")[1::2]
    assert blocks, "section 6 has no fenced map"
    return "\n".join(block.split("\n", 1)[-1] for block in blocks)


def _real_modules():
    modules = set()
    for pattern, root in (("*.py", "bga"), ("*.py", "tools")):
        for path in sorted((REPO / root).glob(pattern)):
            rel = path.relative_to(REPO).as_posix()
            if rel not in NOT_ON_THE_MAP:
                modules.add(rel)
    for package in sorted((REPO / "bga").iterdir()):
        if package.is_dir() and (package / "__init__.py").exists():
            modules.add(package.relative_to(REPO).as_posix() + "/")
    return modules


def _real_test_entries(root=REPO):
    """Everything directly under `tests/`, directories included.

    Directly under, and not recursively: the map points at `tests/unit/`
    on purpose - one line per guard would make §6 a second backlog index
    - while a harness or a suite sitting at the top level is a place a
    session needs directing to."""
    entries = set()
    for path in sorted((root / "tests").iterdir()):
        rel = path.relative_to(root).as_posix()
        if (rel in NOT_IN_TESTS or path.name in BUILD_ARTEFACTS
                or path.name.startswith(".")):
            continue
        entries.add(rel + "/" if path.is_dir() else rel)
    return entries


def _stale(names):
    """The exemptions naming a path this tree does not have."""
    return sorted(name for name in names if not (REPO / name).exists())


def _named(text, name):
    """The map names an entry if it names the path or its basename."""
    return (name in text
            or name.rstrip("/").split("/")[-1].removesuffix(".py") in text)


class TestTheMapNamesTheTree:
    def test_every_module_is_on_the_map(self):
        """A module nobody is pointed at is one every session
        rediscovers - which is the cost the map exists to remove."""
        text = _map_text()
        missing = sorted(
            name for name in _real_modules()
            if name.rstrip("/").split("/")[-1].removesuffix(".py") not in text
            and name not in text)
        assert missing == [], (
            f"module(s) the context map does not mention: {missing}. "
            f"docs/contributing/fixing-guide.md section 6.")

    def test_the_map_names_nothing_that_does_not_exist(self):
        """The other direction, and the one that actually bit: the map
        described `tests/test_e2e.py` as the only test file for the
        whole life of the repository after that stopped being true."""
        import re

        text = _map_text()
        # The lookbehind matters: `.bga/runs` is a directory a build
        # creates, not a path in the tree, and `\b` alone matched the
        # `bga/runs` inside it.
        named = set(re.findall(
            r"(?<![\w./-])((?:bga|tools|tests|docs)/[\w./-]+)", text))
        stale = sorted(
            path for path in named
            if not (REPO / path.rstrip("/")).exists()
            and not (REPO / path.rstrip("/")).is_dir())
        assert stale == [], (
            f"the context map names path(s) that do not exist: {stale}")

    def test_every_test_entry_is_on_the_map(self):
        """`UX-274`: the half the guard did not cover. The two harnesses
        this axis runs on were absent for the rounds that built them."""
        text = _map_text()
        missing = sorted(name for name in _real_test_entries()
                         if not _named(text, name))
        assert missing == [], (
            f"entr(y/ies) directly under tests/ the context map does not "
            f"mention: {missing}. docs/contributing/fixing-guide.md §6.")

    def test_the_exemption_list_names_only_real_paths(self):
        """An exemption for something that no longer exists silently
        widens the check it is an exception to."""
        assert _stale(NOT_IN_TESTS) == [], (
            f"exemption(s) for no such path: {_stale(NOT_IN_TESTS)}")

    def test_the_existence_check_would_still_catch_a_stale_entry(self):
        """`NOT_IN_TESTS` is empty today, so the clause above passes on
        an empty set and says nothing about the check. This one keeps it
        honest: `UX-512` moved the one entry it had into
        `BUILD_ARTEFACTS`, and the source-path rule outlived it."""
        assert _stale(NOT_IN_TESTS | {"tests/no-such-thing"}) == [
            "tests/no-such-thing"]

    def test_a_build_artefact_is_exempt_whether_or_not_it_is_there(self, tmp_path):
        """The acceptance, as a guard: the entry set is the same with
        the bytecode directory present and absent. Before `UX-512` the
        exemption was a path that had to exist, so clearing
        `__pycache__` - which `UX-508` tells a round to do - reddened
        this file."""
        (tmp_path / "tests" / "unit").mkdir(parents=True)
        (tmp_path / "tests" / "support").mkdir()
        (tmp_path / "tests" / "conftest.py").write_text("")
        without = _real_test_entries(tmp_path)

        (tmp_path / "tests" / "__pycache__").mkdir()
        (tmp_path / "tests" / "__pycache__" / "x.pyc").write_bytes(b"")
        assert _real_test_entries(tmp_path) == without
        assert "tests/__pycache__/" not in without

    def test_a_build_artefact_exemption_is_a_name_and_not_a_path(self):
        """A path in `BUILD_ARTEFACTS` would smuggle a source exemption
        past the existence check that exists for source exemptions."""
        assert not [name for name in BUILD_ARTEFACTS if "/" in name]

    def test_the_map_states_no_count_it_does_not_check(self):
        """`UX-274`'s third clause. The block used to say `218 files,
        ~3,100 tests` against 240 and 3,327, and `the 233 closed rows`
        against 263 - three figures stated as current, read as current,
        five rounds old. A figure nothing checks is the defect, not the
        count, so the map states none.

        Deliberately narrow: `UX-238`, `UX-264` and the rest are ids and
        not counts, and a rule that banned digits would ban those."""
        import re

        text = _map_text()
        # One optional adjective between the number and the noun: the
        # first draft matched `218 files` and missed `the 233 closed
        # rows` two lines below it, which is half a guard.
        counted = re.findall(
            r"(?<![\w-])[~]?[\d,]{2,}\s+(?:[a-z-]+\s+)?"
            r"(?:files?|tests?|rows?|elements?|items?|scenarios?)\b", text)
        assert counted == [], (
            f"the context map states counted figure(s) nothing checks: "
            f"{counted}. Name the thing, not how many of it there are.")

    def test_the_test_layout_is_not_from_the_first_week(self):
        """The specific claim that motivated this, pinned so it cannot
        come back: one test file."""
        text = _map_text()
        assert "only existing test file" not in text
        assert "tests/unit/" in text, "the map does not mention where tests live"


class TestTheStreamsAreNamed:
    """`§1`'s "pick the highest-priority 🔴 row" is right for a feature
    and wrong for an audit, which has no row until it has been done."""

    STREAMS = ("design", "audit", "feature", "fix", "documentation",
               "refactor", "review", "release")

    def test_every_stream_this_repository_runs_is_described(self):
        text = GUIDE.read_text(encoding="utf-8")
        section = text.split("## 6a. Which kind of session is this?", 1)
        assert len(section) == 2, "the guide does not name the streams"
        body = section[1].split("\n## ", 1)[0]
        missing = [s for s in self.STREAMS if f"**{s}**" not in body]
        assert missing == [], f"stream(s) with no row: {missing}"

    def test_each_stream_says_where_it_starts_and_when_it_is_done(self):
        text = GUIDE.read_text(encoding="utf-8")
        body = text.split("## 6a. Which kind of session is this?", 1)[1]
        body = body.split("\n## ", 1)[0]
        for stream in self.STREAMS:
            row = next((line for line in body.splitlines()
                        if f"**{stream}**" in line), None)
            assert row is not None, stream
            cells = [c.strip() for c in row.strip().strip("|").split("|")]
            assert len(cells) == 4, f"{stream}: {cells}"
            assert all(cells), f"{stream} has an empty cell: {cells}"

    def test_picking_a_task_branches_on_the_stream_first(self):
        """`§1` used to open with "find the highest-priority row",
        which is an instruction an audit session cannot follow."""
        text = GUIDE.read_text(encoding="utf-8")
        section = text.split("## 1. How to pick a task", 1)[1]
        section = section.split("\n## ", 1)[0]
        steps = [line for line in section.splitlines()
                 if line[:2] in ("1.", "2.", "3.", "4.", "5.")]
        assert steps, "section 1 has no numbered steps"
        assert "6a" in steps[0], (
            f"the first thing section 1 says is not which stream this is: "
            f"{steps[0]!r}")
        row = next((i for i, s in enumerate(steps) if "🔴" in s), None)
        assert row is not None and row > 0, (
            "picking a backlog row is still the first step")

    def test_the_verification_discipline_is_not_per_stream(self):
        """The part that works is the part that must not fragment."""
        body = GUIDE.read_text(encoding="utf-8")
        body = body.split("## 6a. Which kind of session is this?", 1)[1]
        body = body.split("\n## ", 1)[0]
        assert "does not vary by stream" in body, (
            "section 6a does not say the discipline is shared")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
