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
import argparse
import functools
import pathlib
import re
import subprocess
from typing import Dict, Optional, Tuple

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
GUIDE = REPO / "docs/contributing/fixing-guide.md"

# Modules small enough or private enough that naming each one would make
# the map longer without making it more useful. Each is *reachable* -
# `bga/__init__.py` is not a place anyone needs directing to.
NOT_ON_THE_MAP = {"bga/__init__.py", "tools/__init__.py",
                  "tools/native_trace/__init__.py"}

# `UX-573`: what `tools/` and `bga/viewer/` are made of. The walk was
# `tools/*.py` non-recursively, so `hook.c`, `spine.c`, `trackevent.py`
# and `bwrap_shim.py` - Plane 2 itself, the map's own subject - were on
# neither the map nor the guard, and `dev_run.sh` with them.
MAPPED_SUFFIXES = {"tools/": (".py", ".c", ".h", ".sh"),
                   "bga/viewer/": (".js", ".html", ".css")}

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

# `UX-590`: the map's one capability row. The formats are the map's
# only non-path vocabulary, and this is where they are named.
FORMAT_ROW = "--format"

# A bare word the map lists among paths that is deliberately neither a
# command nor a format. Word -> the reason it is allowed to be there;
# `UX-573`'s `csv` is *not* one of these, because it is a registered
# `--format` choice and derives.
PROSE_IN_A_PATH_LIST: Dict[str, str] = {}


def _map_text():
    """The map itself - the fenced blocks - and not the prose around it.

    The first draft of this guard read the whole of section 6, and so
    matched the paragraph that *quotes* the old bad map as the reason
    the section was regenerated. A guard that is satisfied by its own
    explanation checks nothing.
    """
    section = _section_six()
    blocks = section.split("```")[1::2]
    assert blocks, "section 6 has no fenced map"
    return "\n".join(block.split("\n", 1)[-1] for block in blocks)


def _section_six():
    text = GUIDE.read_text(encoding="utf-8")
    assert "## 6. Where things live" in text, "the guide has no context map"
    return text.split("## 6. Where things live", 1)[1].split("\n## 7.", 1)[0]


def _format_row():
    """`UX-590`: the `--format` row of the map, as its words.

    The map's only capability vocabulary. Everything left of the ` - `
    is the list; the description after it is prose.
    """
    rows = [line for line in _map_text().splitlines()
            if line.startswith(FORMAT_ROW)]
    assert len(rows) == 1, (
        f"section 6 should carry exactly one `{FORMAT_ROW}` row: {rows}")
    listed = rows[0][len(FORMAT_ROW):].split(" - ", 1)[0]
    return [word.strip() for word in listed.split(",") if word.strip()]


#: A whole hyphenated lowercase word: `cache-trend` is one match, and
#: the `format` in `--format` is none.
WORD = re.compile(r"(?<![\w<>-])[a-z][a-z0-9]*(?:-[a-z0-9]+)*(?![\w>-])")


@functools.lru_cache(maxsize=1)
def _registry() -> Tuple[frozenset, frozenset]:
    """What `bga` registers: (commands, `--format` choices).

    Read off the parser and the alias table rather than a list here -
    a second list would be the thing that drifts.
    """
    import sys

    sys.path.insert(0, str(REPO))
    from bga.cli import create_parser
    from bga.tools_dispatch import TOOL_ALIASES

    commands, formats = set(TOOL_ALIASES), set()
    for action in create_parser()._actions:
        if not isinstance(action, argparse._SubParsersAction):
            continue
        commands |= set(action.choices)
        for sub in action.choices.values():
            for option in sub._actions:
                if "--format" in (option.option_strings or []) and option.choices:
                    formats |= set(option.choices)
    return frozenset(commands), frozenset(formats)


def _path_lists(text):
    """The map's comma lists of things, as `(line, paths, bare words)`.

    `UX-573` dropped a bare `csv` from `bga/report/`'s comma list of
    filenames and recorded that no guard could have seen it. A run ends
    at the first member that is prose - two or more words not starting
    with a path - so `bga/run_store.py .bga/runs, the @last/@prev
    aliases, prune` stops before `prune`, which is a description and not
    a list member.
    """
    lists = []
    for line in text.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 2:
            continue
        paths, bare = [], []
        for part in parts:
            words = part.split()
            if not words:
                break
            if _looks_like_a_path(words[0]):
                paths += [w for w in words if _looks_like_a_path(w)]
            elif len(words) == 1 and WORD.fullmatch(words[0]):
                bare.append(words[0])
            else:
                break
        if len(paths) >= 2:
            lists.append((line.strip(), paths, bare))
    return lists


#: A path claim is rooted or suffixed. A slash alone is not enough:
#: §6 writes `cold/structural analysis` and `.bga/runs`, which are
#: English and a directory a build makes, not entries in a list.
PATH_ROOTS = ("bga/", "tools/", "tests/", "docs/", "examples/")
PATH_SUFFIXES = (".py", ".c", ".h", ".sh", ".js", ".mjs", ".html", ".css",
                 ".json", ".md", ".toml", ".yml")


def _looks_like_a_path(word):
    return bool(re.fullmatch(r"[\w./-]+", word)) and (
        word.startswith(PATH_ROOTS) or word.endswith(PATH_SUFFIXES))


@functools.lru_cache(maxsize=1)
def _tracked() -> Tuple[str, ...]:
    """The paths git has, in order. Not the paths on disk.

    `Path.glob` walks whatever the checkout holds, and a main checkout
    holds `.claude/worktrees/<agent>/` - whole copies of the tree at
    older commits, whose stale contents a walk then reports as this
    tree's. That defect landed and was fixed twice in round 83, and
    this walk is the widest one in the suite.
    """
    out = subprocess.run(["git", "ls-files"], cwd=REPO, check=True,
                         capture_output=True, text=True).stdout
    return tuple(out.splitlines())


def _real_modules(tracked: Optional[Tuple[str, ...]] = None):
    """Every path §6 has to name.

    `UX-573`: recursive under `tools/` and into `bga/viewer/`, because
    the non-recursive `tools/*.py` left the LD_PRELOAD hook and the
    ptrace spine - Plane 2, which is what the map is a map of - with no
    row and the guard green.
    """
    tracked = _tracked() if tracked is None else tracked
    modules = set()
    for rel in tracked:
        if rel in NOT_ON_THE_MAP:
            continue
        root = next((r for r in MAPPED_SUFFIXES if rel.startswith(r)), None)
        if root is not None:
            if rel.endswith(MAPPED_SUFFIXES[root]):
                modules.add(rel)
        elif rel.startswith("bga/") and rel.count("/") == 1 and rel.endswith(".py"):
            modules.add(rel)
        elif rel.count("/") == 2 and rel.startswith("bga/") and rel.endswith(
                "/__init__.py"):
            modules.add(rel.rsplit("/", 1)[0] + "/")
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

    def test_the_walk_finds_each_population_it_claims_to_walk(self):
        """`UX-573`'s vacuity clause: a walk that finds no files passes
        anything, and the way this one gets narrowed again is a suffix
        or a level quietly dropping out. One named member per suffix the
        walk added, so the set shrinking is a failure and not a green."""
        modules = _real_modules()
        assert modules, "the walk found nothing at all"
        for name in ("tools/native_trace/hook.c",       # C, one level down
                     "tools/native_trace/trackevent.py",
                     "tools/dev_run.sh",                # shell
                     "bga/viewer/views.js",
                     "bga/viewer/perfetto.html",
                     "bga/viewer/style.css"):
            assert name in modules, f"the walk does not reach {name}"

    def test_the_walk_reads_git_and_not_the_checkout(self):
        """A main checkout holds `.claude/worktrees/<agent>/` - a whole
        copy of the tree at an older commit - so a walk over `tools/**`
        reports files no clone has. The population is what git tracks,
        which an untracked file on disk cannot enter."""
        probe = REPO / "tools" / "native_trace" / "ux573_untracked_probe.sh"
        assert not probe.exists(), probe
        probe.write_text("# left by a failed run of this guard\n")
        # The cache is what made the first draft of this guard green
        # against a mutation that read the checkout: it had been filled
        # before the probe existed.
        _tracked.cache_clear()
        try:
            assert probe.relative_to(REPO).as_posix() not in _real_modules()
        finally:
            probe.unlink()
            _tracked.cache_clear()

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
        names = NOT_IN_TESTS | NOT_ON_THE_MAP
        assert _stale(names) == [], (
            f"exemption(s) for no such path: {_stale(names)}")

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


class TestTheMapsCapabilitiesDerive:
    """`UX-590`: §6's non-path claims, held to the registry.

    The path directions above read only what has a slash, so a bare
    `csv` in `bga/report/`'s row was invisible to them - `UX-573` had to
    drop one by hand and recorded that nothing could have caught it.
    """

    def test_every_format_the_map_names_is_registered(self):
        """The existence direction, for the map's one vocabulary. A
        format a reader finds here and `bga` refuses is the `csv`
        defect with the sign flipped."""
        _commands, formats = _registry()
        unknown = sorted(word for word in _format_row()
                         if word not in formats
                         and word not in PROSE_IN_A_PATH_LIST)
        assert unknown == [], (
            f"§6's `--format` row names choice(s) `bga/cli.py` does not "
            f"declare: {unknown}")

    def test_every_registered_format_is_on_the_map(self):
        """The other direction, and the one a new renderer trips: a
        `--format` a run can be asked for and the map does not name is
        a capability every session rediscovers."""
        _commands, formats = _registry()
        missing = sorted(set(formats) - set(_format_row()))
        assert missing == [], (
            f"`--format` choice(s) §6 does not name: {missing}. "
            f"docs/contributing/fixing-guide.md §6.")

    def test_the_registry_is_a_non_empty_population(self):
        """The vacuity floor for both directions above: an empty
        registry passes the first and an empty map row the second. One
        named member per source the registry reads."""
        commands, formats = _registry()
        assert "analyze" in commands, "the parser's own subcommands are gone"
        assert "snapshot" in commands, "the tools_dispatch aliases are gone"
        assert {"text", "json", "csv"} <= formats, sorted(formats)
        assert len(commands) > 20, sorted(commands)
        assert len(_format_row()) > 1, _format_row()

    def test_the_format_row_answers_no_path_question(self):
        """A vocabulary inside the map could satisfy the module
        direction with a word that is not a path - `graph` would answer
        `bga/graph/`. These four cannot."""
        basenames = {name.rstrip("/").split("/")[-1].removesuffix(".py")
                     for name in _real_modules()} | {
            name.rstrip("/").split("/")[-1] for name in _real_test_entries()}
        assert not basenames & set(_format_row()), (
            f"the `--format` row would answer a path question: "
            f"{sorted(basenames & set(_format_row()))}")

    def test_a_bare_word_among_paths_is_a_claim_the_registry_answers(self):
        """`UX-573`'s `csv`, as a direction. A comma list of paths with
        a bare word in it is claiming that word is a thing, and the
        registry - commands and formats both - is what says whether it
        is."""
        commands, formats = _registry()
        offenders = sorted(
            f"{word!r} in {line!r}"
            for line, _paths, bare in _path_lists(_map_text())
            for word in bare
            if word not in commands and word not in formats
            and word not in PROSE_IN_A_PATH_LIST)
        assert offenders == [], (
            f"the map lists word(s) among paths that `bga` registers as "
            f"neither a command nor a format: {offenders}")

    def test_the_path_list_scan_reads_a_non_empty_population(self):
        """The vacuity floor `UX-573` asks for: a scan finding no list
        at all would pass any bare word in one. Measured at seven lists
        in §6; the number is a floor, not a target."""
        lists = _path_lists(_map_text())
        assert len(lists) >= 5, [line for line, _, _ in lists]
        assert any("help_format.py" in line for line, _, _ in lists), (
            "the scan no longer reaches the `bga/progress.py` list")

    def test_the_scan_stops_at_a_description_rather_than_reading_it(self):
        """`prune` and `analysis` are English, not list members. A scan
        that read to the end of the line would demand a reason for
        every adjective in §6."""
        line = ("bga/report/   text.py, json.py, ci_comment.py - renderers, "
                "no analysis")
        lists = _path_lists(line)
        assert len(lists) == 1, lists
        assert lists[0][2] == [], lists[0][2]
        assert _path_lists("bga/a.py, bga/b.py, the @last aliases, prune") == [
            ("bga/a.py, bga/b.py, the @last aliases, prune",
             ["bga/a.py", "bga/b.py"], [])]

    def test_a_slash_alone_does_not_make_a_path(self):
        """The false positives this scan had on its first run: §6 says
        `cold/structural analysis` and `.bga/runs`, and counting those
        as list members made `networkx-based` a capability claim."""
        assert not _looks_like_a_path("cold/structural")
        assert not _looks_like_a_path(".bga/runs")
        assert _looks_like_a_path("bga/structural/")
        assert _looks_like_a_path("help_format.py")
        assert _path_lists("bga/structural/  cold/structural analysis, "
                           "networkx-based") == []

    def test_an_unregistered_bare_word_in_a_path_list_is_seen(self):
        """The allowlist is empty, so the clause above passes on an
        empty set and says nothing about the scan. This one keeps it
        honest: a word in neither registry is found where `csv` sat."""
        line = "bga/report/   text.py, json.py, parquet, ci_comment.py"
        commands, formats = _registry()
        bare = [word for _line, _paths, words in _path_lists(line)
                for word in words]
        assert bare == ["parquet"], bare
        assert "parquet" not in commands and "parquet" not in formats

    def test_each_prose_exemption_carries_a_reason(self):
        """An allowlist entry with no reason is a hole nobody argued
        for, and the next session cannot tell it from an oversight."""
        empty = sorted(word for word, why in PROSE_IN_A_PATH_LIST.items()
                       if not why or not why.strip())
        assert empty == [], f"exemption(s) with no reason: {empty}"


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
