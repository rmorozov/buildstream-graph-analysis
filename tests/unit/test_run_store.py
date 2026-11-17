"""UX-126: the store is resolution and nothing else.

Every path in every invocation of the documented loop was invented by
the operator, across three audit rounds — so `.bga/runs` exists to name
runs instead. That makes the properties worth pinning here narrow and
specific: an alias must resolve to the run the user means, a *non*-alias
must reach the filesystem exactly as it did before this module existed,
and a name with no answer must fail as itself rather than as a missing
path. "You have only ever taken one snapshot here" and "that directory
is not there" are different sentences with different fixes.
"""

import json
import os

import pytest

from bga.run_store import (
    CONFIG_NAME,
    PLANE2_NAME,
    STORE_DIRNAME,
    StoreError,
    has_run,
    is_alias,
    list_runs,
    list_snapshots,
    new_snapshot_dir,
    project_root,
    read_config,
    resolve,
    resolve_plane2,
    resolve_snapshot,
    runs_dir,
    sibling_plane2,
    store_size_bytes,
    write_config,
)


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    (root / "project.conf").write_text("name: p\nmin-version: 2.0\n")
    return root


def _snapshot(project, stamp, with_run=True, with_plane2=False):
    path = runs_dir(str(project)) + os.sep + stamp
    os.makedirs(path, exist_ok=True)
    if with_run:
        os.makedirs(os.path.join(path, "run"), exist_ok=True)
    if with_plane2:
        with open(os.path.join(path, PLANE2_NAME), "w", encoding="utf-8") as handle:
            handle.write('{"by_element": {}}')
    return path


class TestFindingTheProject:
    def test_a_subdirectory_resolves_to_the_project_above_it(self, project):
        deep = project / "elements" / "nested"
        deep.mkdir(parents=True)

        assert project_root(str(deep)) == str(project)

    def test_outside_any_project_the_answer_is_none_not_an_invention(self, tmp_path):
        """Nothing here creates a directory - resolution has to be safe
        to run anywhere, including where the answer is simply "no"."""
        assert project_root(str(tmp_path)) is None
        assert not os.path.exists(tmp_path / STORE_DIRNAME)


class TestTheAliasGrammar:
    @pytest.mark.parametrize("token", ["@last", "@prev", "@20260819T120000Z", "@2026"])
    def test_these_are_aliases(self, token):
        assert is_alias(token)

    @pytest.mark.parametrize(
        "token",
        [
            "@",
            "@x",
            "/tmp/run",
            "run",
            "",
            "@last/run",
            "./@last",
        ],
    )
    def test_these_are_not(self, token):
        """A bare `@`, and anything that is a path, stay paths. A
        directory genuinely named `@last/run` must still be reachable -
        the store is a convenience, not a namespace grab."""
        assert not is_alias(token)

    def test_a_non_alias_is_returned_untouched_without_looking_for_a_project(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        assert resolve("/some/explicit/run") == "/some/explicit/run"
        assert resolve("relative/run") == "relative/run"


class TestWhatAnAliasResolvesTo:
    def test_last_and_prev_are_the_two_newest_by_stamp_not_by_mtime(self, project):
        """Sorted by name, so a copied or restored store keeps its
        meaning - `cp -r` rewrites every mtime."""
        old = _snapshot(project, "20260101T000000Z")
        new = _snapshot(project, "20260819T120000Z")
        os.utime(old, (10**9, 10**9))  # newest mtime, oldest stamp

        assert resolve("@last", str(project)) == os.path.join(new, "run")
        assert resolve("@prev", str(project)) == os.path.join(old, "run")

    def test_a_stamp_prefix_names_one_snapshot(self, project):
        _snapshot(project, "20260101T000000Z")
        target = _snapshot(project, "20260819T120000Z")

        assert resolve("@20260819", str(project)) == os.path.join(target, "run")

    def test_an_ambiguous_prefix_says_which_ones_rather_than_guessing(self, project):
        _snapshot(project, "20260819T120000Z")
        _snapshot(project, "20260819T130000Z")

        with pytest.raises(StoreError) as exc:
            resolve("@20260819", str(project))

        assert "matches 2 snapshots" in str(exc.value)
        assert "20260819T120000Z" in str(exc.value)

    def test_an_unmatched_prefix_lists_what_is_there(self, project):
        _snapshot(project, "20260819T120000Z")

        with pytest.raises(StoreError) as exc:
            resolve("@20251231", str(project))

        assert "20260819T120000Z" in str(exc.value)


class TestTheFailuresAreDifferentSentences:
    def test_outside_a_project_the_error_names_the_project_not_the_path(self, tmp_path):
        with pytest.raises(StoreError) as exc:
            resolve("@last", str(tmp_path))

        assert "no project.conf" in str(exc.value)

    def test_an_empty_store_says_how_to_fill_it(self, project):
        with pytest.raises(StoreError) as exc:
            resolve("@last", str(project))

        assert "bga snapshot" in str(exc.value)

    def test_prev_with_one_snapshot_is_its_own_message(self, project):
        """The commonest first-run confusion, and it is not "missing
        directory" - it is "the comparison needs a second build"."""
        _snapshot(project, "20260819T120000Z")

        with pytest.raises(StoreError) as exc:
            resolve("@prev", str(project))

        assert "@prev needs two snapshots" in str(exc.value)


class TestAnIncompleteCaptureIsNotPrev:
    """Found by one: a snapshot whose capture crashed left a directory
    with the Plane 2 report and no `run/`, became `@prev`, and turned the
    next comparison into "baseline directory does not exist" - an error
    about a path the user never typed."""

    def test_it_is_listed_but_never_resolved_to(self, project):
        complete = _snapshot(project, "20260819T120000Z")
        broken = _snapshot(project, "20260819T130000Z", with_run=False)

        assert list_snapshots(str(project)) == [complete, broken]
        assert list_runs(str(project)) == [complete]
        assert has_run(complete) and not has_run(broken)
        assert resolve("@last", str(project)) == os.path.join(complete, "run")

    def test_a_store_of_only_broken_captures_says_which_problem_it_is(self, project):
        _snapshot(project, "20260819T130000Z", with_run=False)

        with pytest.raises(StoreError) as exc:
            resolve("@last", str(project))

        assert "produced no run directory" in str(exc.value)


class TestCreatingOne:
    def test_two_snapshots_in_one_second_do_not_collide(self, project):
        from datetime import datetime, timezone

        now = datetime(2026, 8, 19, 12, 0, 0, tzinfo=timezone.utc)

        first = new_snapshot_dir(str(project), now)
        second = new_snapshot_dir(str(project), now)

        assert first != second
        assert sorted([first, second]) == [first, second], "still time-ordered by name"

    def test_the_store_gitignores_itself(self, project):
        """Dropped rather than asked for: a store the user has to
        remember to gitignore is a store that ends up committed."""
        new_snapshot_dir(str(project))

        assert (project / STORE_DIRNAME / ".gitignore").read_text().endswith("*\n")

    def test_an_existing_gitignore_is_not_overwritten(self, project):
        os.makedirs(project / STORE_DIRNAME)
        (project / STORE_DIRNAME / ".gitignore").write_text("mine\n")

        new_snapshot_dir(str(project))

        assert (project / STORE_DIRNAME / ".gitignore").read_text() == "mine\n"


class TestStickyFlags:
    def test_a_roundtrip(self, project):
        write_config(str(project), {"trace_spine": "on", "trace_opens": False})

        assert read_config(str(project)) == {"trace_spine": "on", "trace_opens": False}

    def test_a_project_with_no_config_reads_as_empty_not_as_an_error(self, project):
        assert read_config(str(project)) == {}

    def test_a_corrupt_config_reads_as_empty_rather_than_killing_the_build(self, project):
        """The config is a convenience. Losing it must cost the defaults,
        not the capture the user is waiting on."""
        os.makedirs(project / STORE_DIRNAME, exist_ok=True)
        (project / STORE_DIRNAME / CONFIG_NAME).write_text("{not json")

        assert read_config(str(project)) == {}

    def test_a_config_that_is_not_an_object_is_ignored(self, project):
        os.makedirs(project / STORE_DIRNAME, exist_ok=True)
        (project / STORE_DIRNAME / CONFIG_NAME).write_text(json.dumps([1, 2]))

        assert read_config(str(project)) == {}


def test_the_size_warning_counts_what_is_on_disk(project):
    snapshot = _snapshot(project, "20260819T120000Z")
    with open(os.path.join(snapshot, "run", "trace.json"), "wb") as handle:
        handle.write(b"x" * 4096)

    assert store_size_bytes(str(project)) >= 4096


def test_an_absent_store_has_no_snapshots_and_no_size(project):
    assert list_snapshots(str(project)) == []
    assert store_size_bytes(str(project)) == 0


class TestAliasesReachEveryCommandThatTakesARun:
    """Resolution is threaded once, over the *attribute names* that hold
    a run directory, rather than per command - so a new command reusing
    `directory` gets aliases for free and one inventing a new name does
    not half-work silently."""

    def _snapshot_pair(self, project, with_plane2=False):
        return (
            _snapshot(project, "20260101T000000Z", with_plane2=with_plane2),
            _snapshot(project, "20260102T000000Z", with_plane2=with_plane2),
        )

    def test_analyze_resolves_last(self, project, monkeypatch):
        _old, new = self._snapshot_pair(project)
        monkeypatch.chdir(project)
        seen = {}
        import bga.cli as cli

        monkeypatch.setattr(cli, "cmd_analyze", lambda args: seen.setdefault("dir", args.directory) and 0)

        cli.main(["analyze", "@last"])

        assert seen["dir"] == os.path.join(new, "run")

    def test_compare_resolves_both_positionals(self, project, monkeypatch):
        old, new = self._snapshot_pair(project)
        monkeypatch.chdir(project)
        seen = {}
        import bga.cli as cli

        monkeypatch.setattr(cli, "cmd_compare", lambda args: seen.update(b=args.baseline, c=args.candidate))

        cli.main(["compare", "@prev", "@last"])

        assert seen == {"b": os.path.join(old, "run"), "c": os.path.join(new, "run")}

    def test_cache_trend_resolves_a_list_of_them(self, project, monkeypatch):
        old, new = self._snapshot_pair(project)
        monkeypatch.chdir(project)
        seen = {}
        import bga.cli as cli

        monkeypatch.setattr(cli, "cmd_cache_trend", lambda args: seen.setdefault("runs", args.run_dirs) and 0)

        cli.main(["cache-trend", "@prev", "@last"])

        assert seen["runs"] == [os.path.join(old, "run"), os.path.join(new, "run")]

    def test_an_explicit_path_still_means_itself(self, project, monkeypatch):
        self._snapshot_pair(project)
        monkeypatch.chdir(project)
        seen = {}
        import bga.cli as cli

        monkeypatch.setattr(cli, "cmd_analyze", lambda args: seen.setdefault("dir", args.directory) and 0)

        cli.main(["analyze", "/somewhere/else"])

        assert seen["dir"] == "/somewhere/else"

    def test_a_name_with_no_answer_exits_2_before_any_analysis_runs(self, tmp_path, monkeypatch, capsys):
        """Exit 2, the code the rest of the CLI uses for "the input to
        this invocation is wrong" - and the analyzer is never reached,
        so the message is the store's rather than a stack trace."""
        monkeypatch.chdir(tmp_path)
        import bga.cli as cli

        monkeypatch.setattr(cli, "cmd_analyze", lambda args: pytest.fail("analysis ran anyway"))

        assert cli.main(["analyze", "@last"]) == 2

        assert "no BuildStream project here" in capsys.readouterr().err

    def test_every_plane_2_argument_takes_them(self, project, monkeypatch):
        """UX-134: `--plane2`, both of `compare`'s, and `correlate`'s
        positional. Listed together because the seam was that some of a
        capture had names and some did not."""
        old, new = self._snapshot_pair(project, with_plane2=True)
        monkeypatch.chdir(project)
        seen = {}
        import bga.cli as cli

        monkeypatch.setattr(cli, "cmd_analyze", lambda args: seen.setdefault("plane2", args.plane2) and 0)
        monkeypatch.setattr(
            cli, "cmd_compare", lambda args: seen.update(b=args.baseline_plane2, c=args.candidate_plane2)
        )
        monkeypatch.setattr(cli, "cmd_correlate", lambda args: seen.setdefault("report", args.native_report))

        cli.main(["analyze", "@last", "--plane2", "@last"])
        cli.main(["compare", "@prev", "@last", "--baseline-plane2", "@prev", "--candidate-plane2", "@last"])
        cli.main(["correlate", "@last", "@prev"])

        assert seen["plane2"] == os.path.join(new, PLANE2_NAME)
        assert seen["b"] == os.path.join(old, PLANE2_NAME)
        assert seen["c"] == os.path.join(new, PLANE2_NAME)
        assert seen["report"] == os.path.join(old, PLANE2_NAME), (
            "a report named from one snapshot and a run from another is a legitimate thing to ask for"
        )

    def test_a_report_alias_with_no_report_stops_before_any_analysis(self, project, monkeypatch, capsys):
        self._snapshot_pair(project)
        monkeypatch.chdir(project)
        import bga.cli as cli

        monkeypatch.setattr(cli, "cmd_analyze", lambda args: pytest.fail("analysis ran anyway"))

        assert cli.main(["analyze", "@last", "--plane2", "@last"]) == 2

        assert "no plane2.json" in capsys.readouterr().err

    def test_a_baseline_set_takes_them_too(self, project, monkeypatch):
        """`--baseline-run` is repeatable and each entry is a run
        directory, so the band `bga compare` builds can be named from
        the store like anything else."""
        old, new = self._snapshot_pair(project)
        monkeypatch.chdir(project)
        seen = {}
        import bga.cli as cli

        monkeypatch.setattr(cli, "cmd_compare", lambda args: seen.setdefault("set", args.baseline_run))

        cli.main(["compare", "@prev", "@last", "--baseline-run", "@prev", "--baseline-run", "@last"])

        assert seen["set"] == [os.path.join(old, "run"), os.path.join(new, "run")]


class TestTheSameAliasNamesBothHalvesOfACapture:
    """UX-134: a snapshot holds the run and its Plane 2 report side by
    side, and the join is the one command that needs both at once - so
    it was also the one command the store did not finish."""

    def test_one_alias_is_one_snapshot_whichever_artifact_is_asked_for(self, project):
        """The failure this prevents: `bga correlate @last @last` pairing
        one snapshot's run directory with another's report, which is
        exactly the mistake the store exists to make impossible."""
        _snapshot(project, "20260101T000000Z", with_plane2=True)
        newest = _snapshot(project, "20260102T000000Z", with_plane2=True)

        assert resolve_snapshot("@last", str(project)) == newest
        assert resolve("@last", str(project)) == os.path.join(newest, "run")
        assert resolve_plane2("@last", str(project)) == os.path.join(newest, PLANE2_NAME)

    def test_a_non_alias_is_returned_untouched(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        assert resolve_plane2("/explicit/plane2.json") == "/explicit/plane2.json"

    def test_a_snapshot_without_a_report_fails_by_name(self, project):
        """ "That capture recorded Plane 1 and not Plane 2" and "no such
        file" are different problems. Only the first has a remedy the
        user can act on without going and looking."""
        _snapshot(project, "20260101T000000Z", with_plane2=True)
        _snapshot(project, "20260102T000000Z")

        with pytest.raises(StoreError) as exc:
            resolve_plane2("@last", str(project))

        assert "20260102T000000Z" in str(exc.value)
        assert "no plane2.json" in str(exc.value)

    def test_the_run_half_still_resolves_when_the_report_is_missing(self, project):
        """A capture that recorded Plane 1 and not Plane 2 is a usable
        run - only the join is unavailable."""
        snapshot = _snapshot(project, "20260102T000000Z")

        assert resolve("@last", str(project)) == os.path.join(snapshot, "run")


class TestTheReportBesideARunDirectory:
    """UX-134 item 2, read off the filesystem rather than off how the
    argument was spelled - so `@last` and the full path it resolves to
    behave identically."""

    def test_a_snapshot_run_finds_its_own_report(self, project):
        snapshot = _snapshot(project, "20260101T000000Z", with_plane2=True)

        assert sibling_plane2(os.path.join(snapshot, "run")) == os.path.join(snapshot, PLANE2_NAME)

    def test_a_trailing_slash_does_not_change_the_answer(self, project):
        snapshot = _snapshot(project, "20260101T000000Z", with_plane2=True)

        assert sibling_plane2(os.path.join(snapshot, "run") + os.sep) == (os.path.join(snapshot, PLANE2_NAME))

    def test_a_run_directory_with_no_report_beside_it_has_none(self, project):
        snapshot = _snapshot(project, "20260101T000000Z")

        assert sibling_plane2(os.path.join(snapshot, "run")) is None

    def test_a_directory_that_is_not_called_run_is_not_guessed_about(self, tmp_path):
        """The inference is "the run directory of a capture", not "any
        directory with a JSON file near it"."""
        (tmp_path / "elsewhere").mkdir()
        (tmp_path / PLANE2_NAME).write_text("{}")

        assert sibling_plane2(str(tmp_path / "elsewhere")) is None


class _Reached(Exception):
    """The tool got past argument resolution to its first read."""


# UX-1385: (argv, the snapshot file it must reach, module, the function it reads through, which argument).
_TOOL_CASES = [
    (["extract", ".", "@last", "out"], "build.log", "tools.bst_extract_run", "extract_run", 1),
    (["run-context", "@last", "out.json"], "build.log", "tools.bst_run_context", "build_run_context", 0),
    (
        ["native-to-chrome", "standalone", "@last", "out.json"],
        "plane2.log.gz",
        "tools.bst_native_build_tracer",
        "load_records",
        0,
    ),
]

# argv, the member a snapshot lacking it must be refused by name for.
_REFUSAL_CASES = [
    (["extract", ".", "@last", "out"], "build.log"),
    (["run-context", "@last", "out.json"], "build.log"),
    (["log-to-chrome", "@last", "out.json"], "build.log"),
    (["rebuild-set", "@last", "--cut", "a.bst"], os.path.join("run", "graph.json")),
    (["cross-check", "@last", "@last"], "analyze.json"),
    (["native-to-chrome", "standalone", "@last", "out.json"], "plane2.log.gz"),
    (
        ["native-to-chrome", "combined", "@last", "@last", "out.json", "--anchor-element", "a.bst"],
        os.path.join("run", "chrome_trace.json"),
    ),
]


class TestTheToolsTakeTheStoresNamesToo:
    """UX-1385: a dispatched tool parses its own argv, so `bga.cli`'s pass never reaches it;
    each declares `SNAPSHOT_ARGUMENTS` and resolves through `run_store.resolve_arguments`."""

    def _two(self, project, *members):
        snapshots = []
        for stamp in ("20260101T000000Z", "20260102T000000Z"):
            path = _snapshot(project, stamp)
            for member in members:
                with open(os.path.join(path, member), "w", encoding="utf-8") as handle:
                    handle.write("{}")
            snapshots.append(path)
        return snapshots

    @pytest.mark.parametrize(
        "argv, member, module, function, index", _TOOL_CASES, ids=lambda v: v[0] if isinstance(v, list) else None
    )
    def test_last_reaches_that_snapshots_file(self, project, monkeypatch, argv, member, module, function, index):
        _old, new = self._two(project, member)
        monkeypatch.chdir(project)
        import importlib

        import bga.cli as cli

        seen = []

        def record(*args, **_kwargs):
            seen.append(args[index])
            raise _Reached

        monkeypatch.setattr(importlib.import_module(module), function, record)

        with pytest.raises(_Reached):
            cli.main(argv)

        assert seen == [os.path.join(new, member)]

    def test_log_to_chrome_converts_that_snapshots_log(self, project, monkeypatch, tmp_path):
        self._two(project, "build.log")
        monkeypatch.chdir(project)
        import bga.cli as cli

        out = tmp_path / "lc.json"
        assert cli.main(["log-to-chrome", "@last", str(out)]) == 0, "a file called @last does not exist"

        assert out.is_file()

    def test_rebuild_set_reads_that_snapshots_graph(self, project, monkeypatch, capsys):
        old, _new = self._two(project)
        graph = {
            "elements": [{"uid": "a.bst"}, {"uid": "b.bst"}],
            "dependencies": [{"predecessor": "a.bst", "successor": "b.bst", "dependency_type": "build"}],
        }
        with open(os.path.join(old, "run", "graph.json"), "w", encoding="utf-8") as handle:
            json.dump(graph, handle)
        monkeypatch.chdir(project)
        import bga.cli as cli

        assert cli.main(["rebuild-set", "@prev", "--cut", "a.bst", "--count-only"]) == 0

        assert capsys.readouterr().out.strip() == "2"

    def test_cross_check_takes_one_snapshots_run_and_analysis(self, project, monkeypatch):
        old, new = self._two(project, "analyze.json")
        monkeypatch.chdir(project)
        import bga.cli as cli
        import tools.bga_cross_check as cross_check

        seen = {}
        monkeypatch.setattr(cross_check, "run", lambda run_dir, analysis: seen.update(run=run_dir) or 0)
        real_load = json.load
        monkeypatch.setattr(
            cross_check.json, "load", lambda handle: seen.update(analysis=handle.name) or real_load(handle)
        )

        assert cli.main(["cross-check", "@prev", "@last"]) == 0

        assert seen == {"run": os.path.join(old, "run"), "analysis": os.path.join(new, "analyze.json")}

    def test_native_to_chrome_reads_the_gzipped_raw_log_a_snapshot_keeps(self, project, monkeypatch, tmp_path):
        import gzip

        _old, new = self._two(project)
        log = "START pid=1 ppid=0 ts=1.0 element=a.bst inv=i1 src=spine cmd=cc\nEND pid=1 ppid=0 ts=2.0 element=a.bst inv=i1 src=spine exit=0 cmd=cc\n"
        with gzip.open(os.path.join(new, "plane2.log.gz"), "wt", encoding="utf-8") as handle:
            handle.write(log)
        monkeypatch.chdir(project)
        import bga.cli as cli

        out = tmp_path / "n.json"
        assert cli.main(["native-to-chrome", "standalone", "@last", str(out)]) == 0

        assert json.loads(out.read_text()), "the gzipped log parsed to no events"

    @pytest.mark.parametrize(
        "argv, member", _REFUSAL_CASES, ids=lambda v: " ".join(v[:2]) if isinstance(v, list) else None
    )
    def test_a_snapshot_without_the_file_is_refused_by_name(self, project, monkeypatch, capsys, argv, member):
        present = {"build.log", "plane2.log.gz", "analyze.json", os.path.join("run", "graph.json")} - {member}
        self._two(project, *present)
        monkeypatch.chdir(project)
        import bga.cli as cli

        assert cli.main(argv) == 2

        assert f"20260102T000000Z, which has no {member}" in capsys.readouterr().err

    def test_an_explicit_path_still_means_itself(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        import bga.cli as cli
        import tools.bst_extract_run as extract

        seen = []
        monkeypatch.setattr(
            extract, "extract_run", lambda *args, **_kw: seen.append(args[1]) or (_ for _ in ()).throw(_Reached())
        )

        with pytest.raises(_Reached):
            cli.main(["extract", ".", "my.log", "out"])

        assert seen == ["my.log"]


# Every dispatched tool, and how `@last`/`@prev` reach its arguments - or why none takes them.
_RESOLVES_ITS_OWN = {
    "view": "run_store.resolve on RUN and --compare",
    "timeline": "run_store.resolve_snapshot on RUN",
    "snapshot": "the store's own command; --compare and --plan",
    "baseline": "--candidate, through run_store.resolve",
    "cache-logs": "--native-report, through run_store.resolve_plane2",
}
_TAKES_NO_SNAPSHOT = {
    "wrap": "runs a build and writes a new log; a snapshot is its output, never its input",
    "capture": "runs a build; a snapshot is its output",
    "graph-from-show": "reads a project through `bst show`, not a file",
    "gen-synthetic": "writes a new run directory",
    "doctor": "reads this machine and a project directory",
    "checkout-cost": "measures a checkout; its log is not one a snapshot keeps",
    "chrome-to-trace": "every snapshot's run/ already holds the trace.json this would convert to",
    "release-notes": "a maintainer tool over the backlog",
}


def test_every_tool_is_classified_for_aliases():
    """A new tool lands in one of three places, or this reds before it half-works."""
    import importlib

    from bga.tools_dispatch import TOOL_ALIASES

    declared = set()
    for alias, (module_name, _help) in TOOL_ALIASES.items():
        if getattr(importlib.import_module(module_name), "SNAPSHOT_ARGUMENTS", None):
            declared.add(alias)

    assert declared == {"extract", "run-context", "log-to-chrome", "native-to-chrome", "rebuild-set", "cross-check"}
    assert not declared & (_RESOLVES_ITS_OWN.keys() | _TAKES_NO_SNAPSHOT.keys())
    assert declared | _RESOLVES_ITS_OWN.keys() | _TAKES_NO_SNAPSHOT.keys() == set(TOOL_ALIASES)
