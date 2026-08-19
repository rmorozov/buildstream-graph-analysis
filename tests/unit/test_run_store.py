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
    CONFIG_NAME, STORE_DIRNAME, StoreError, has_run, is_alias, list_runs,
    list_snapshots, new_snapshot_dir, project_root, read_config, resolve,
    runs_dir, store_size_bytes, write_config,
)


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    (root / "project.conf").write_text("name: p\nmin-version: 2.0\n")
    return root


def _snapshot(project, stamp, with_run=True):
    path = runs_dir(str(project)) + os.sep + stamp
    os.makedirs(path, exist_ok=True)
    if with_run:
        os.makedirs(os.path.join(path, "run"), exist_ok=True)
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

    @pytest.mark.parametrize("token", [
        "@", "@x", "/tmp/run", "run", "", "@last/run", "./@last",
    ])
    def test_these_are_not(self, token):
        """A bare `@`, and anything that is a path, stay paths. A
        directory genuinely named `@last/run` must still be reachable -
        the store is a convenience, not a namespace grab."""
        assert not is_alias(token)

    def test_a_non_alias_is_returned_untouched_without_looking_for_a_project(
            self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        assert resolve("/some/explicit/run") == "/some/explicit/run"
        assert resolve("relative/run") == "relative/run"


class TestWhatAnAliasResolvesTo:
    def test_last_and_prev_are_the_two_newest_by_stamp_not_by_mtime(self, project):
        """Sorted by name, so a copied or restored store keeps its
        meaning - `cp -r` rewrites every mtime."""
        old = _snapshot(project, "20260101T000000Z")
        new = _snapshot(project, "20260819T120000Z")
        os.utime(old, (10 ** 9, 10 ** 9))  # newest mtime, oldest stamp

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
    def test_outside_a_project_the_error_names_the_project_not_the_path(
            self, tmp_path):
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

    def test_a_corrupt_config_reads_as_empty_rather_than_killing_the_build(
            self, project):
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

    def _snapshot_pair(self, project):
        return _snapshot(project, "20260101T000000Z"), _snapshot(project, "20260102T000000Z")

    def test_analyze_resolves_last(self, project, monkeypatch):
        _old, new = self._snapshot_pair(project)
        monkeypatch.chdir(project)
        seen = {}
        import bga.cli as cli
        monkeypatch.setattr(cli, "cmd_analyze",
                            lambda args: seen.setdefault("dir", args.directory) and 0)

        cli.main(["analyze", "@last"])

        assert seen["dir"] == os.path.join(new, "run")

    def test_compare_resolves_both_positionals(self, project, monkeypatch):
        old, new = self._snapshot_pair(project)
        monkeypatch.chdir(project)
        seen = {}
        import bga.cli as cli
        monkeypatch.setattr(cli, "cmd_compare",
                            lambda args: seen.update(b=args.baseline, c=args.candidate))

        cli.main(["compare", "@prev", "@last"])

        assert seen == {"b": os.path.join(old, "run"), "c": os.path.join(new, "run")}

    def test_cache_trend_resolves_a_list_of_them(self, project, monkeypatch):
        old, new = self._snapshot_pair(project)
        monkeypatch.chdir(project)
        seen = {}
        import bga.cli as cli
        monkeypatch.setattr(cli, "cmd_cache_trend",
                            lambda args: seen.setdefault("runs", args.run_dirs) and 0)

        cli.main(["cache-trend", "@prev", "@last"])

        assert seen["runs"] == [os.path.join(old, "run"), os.path.join(new, "run")]

    def test_an_explicit_path_still_means_itself(self, project, monkeypatch):
        self._snapshot_pair(project)
        monkeypatch.chdir(project)
        seen = {}
        import bga.cli as cli
        monkeypatch.setattr(cli, "cmd_analyze",
                            lambda args: seen.setdefault("dir", args.directory) and 0)

        cli.main(["analyze", "/somewhere/else"])

        assert seen["dir"] == "/somewhere/else"

    def test_a_name_with_no_answer_exits_2_before_any_analysis_runs(
            self, tmp_path, monkeypatch, capsys):
        """Exit 2, the code the rest of the CLI uses for "the input to
        this invocation is wrong" - and the analyzer is never reached,
        so the message is the store's rather than a stack trace."""
        monkeypatch.chdir(tmp_path)
        import bga.cli as cli
        monkeypatch.setattr(cli, "cmd_analyze",
                            lambda args: pytest.fail("analysis ran anyway"))

        assert cli.main(["analyze", "@last"]) == 2

        assert "no BuildStream project here" in capsys.readouterr().err

    def test_a_baseline_set_takes_them_too(self, project, monkeypatch):
        """`--baseline-run` is repeatable and each entry is a run
        directory, so the band `bga compare` builds can be named from
        the store like anything else."""
        old, new = self._snapshot_pair(project)
        monkeypatch.chdir(project)
        seen = {}
        import bga.cli as cli
        monkeypatch.setattr(cli, "cmd_compare",
                            lambda args: seen.setdefault("set", args.baseline_run))

        cli.main(["compare", "@prev", "@last", "--baseline-run", "@prev",
                  "--baseline-run", "@last"])

        assert seen["set"] == [os.path.join(old, "run"), os.path.join(new, "run")]
