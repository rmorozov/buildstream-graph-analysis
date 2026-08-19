"""UX-126: the loop as one command, run twice.

`bga snapshot` is composition, so most of what could go wrong here is
composition going wrong: the wrong flag reaching `capture run`, the
previous snapshot chosen after the new one already exists, a refusal
swallowed, a failed build reported as a successful snapshot. Those are
what these pin - not the report text, which belongs to the commands
being composed and is tested where they are.

The `capture run` half is called for real in `test_dual_plane_capture.py`
and friends; here it is replaced by a recorder, because what this file
is about is the argv that reaches it.
"""
import os

import pytest

from bga import run_store
from tools import bga_snapshot
from tools.bga_snapshot import (
    PLANE2_NAME, RUN_SUBDIR, _capture_context, _list, _sticky_config, main,
    take_snapshot,
)


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    (root / "project.conf").write_text("name: p\nmin-version: 2.0\n")
    return root


@pytest.fixture
def recorded(monkeypatch):
    """`capture run`, replaced by something that records its argv and
    lays down the files a successful capture would leave."""
    calls = []

    def fake_capture(argv):
        calls.append(argv)
        run_dir = argv[argv.index("--run-dir") + 1]
        os.makedirs(run_dir, exist_ok=True)
        with open(os.path.join(os.path.dirname(run_dir), PLANE2_NAME), "w") as handle:
            handle.write("{}")
        return fake_capture.returncode

    fake_capture.returncode = 0
    import tools.bst_native_build_tracer as tracer
    monkeypatch.setattr(tracer, "main", fake_capture)
    return calls


class TestWhatReachesCaptureRun:
    def test_the_stored_flags_are_the_ones_passed(self, project, recorded):
        take_snapshot(str(project), ["bst", "build", "all.bst"],
                      {"trace_opens": True, "trace_spine": "auto"})

        [argv] = recorded
        assert argv[0] == "run"
        assert "--trace-opens" in argv
        assert "--trace-spine=auto" in argv
        separator = argv.index("--")
        assert argv[separator - 2] == str(project), "the project is the first positional"
        assert argv[separator - 1].endswith(PLANE2_NAME), "then the report path"

    def test_the_spine_flag_uses_an_equals_sign(self, project, recorded):
        """`--trace-spine` takes an *optional* value, so
        `--trace-spine auto PROJECT` feeds the positional to the flag -
        the exact trap UX-113's own documented capture command hit."""
        take_snapshot(str(project), ["bst", "build", "all.bst"],
                      {"trace_opens": False, "trace_spine": "on"})

        [argv] = recorded
        assert "--trace-spine=on" in argv
        assert "auto" not in argv and "on" not in argv

    def test_opens_off_means_the_flag_is_absent_not_negated(self, project, recorded):
        take_snapshot(str(project), ["bst", "build", "all.bst"],
                      {"trace_opens": False, "trace_spine": "off"})

        [argv] = recorded
        assert "--trace-opens" not in argv

    def test_the_command_is_passed_after_a_separator(self, project, recorded):
        take_snapshot(str(project), ["bst", "--builders", "4", "build", "all.bst"],
                      {"trace_opens": True, "trace_spine": "auto"})

        [argv] = recorded
        assert argv[argv.index("--") + 1:] == [
            "bst", "--builders", "4", "build", "all.bst"]

    def test_the_snapshot_holds_the_documented_layout(self, project, recorded):
        snapshot, _code = take_snapshot(
            str(project), ["bst", "build", "all.bst"],
            {"trace_opens": True, "trace_spine": "auto"})

        assert os.path.isdir(os.path.join(snapshot, RUN_SUBDIR))
        assert os.path.isfile(os.path.join(snapshot, "capture-context.txt"))
        assert snapshot.startswith(run_store.runs_dir(str(project)))


class TestStickyFlags:
    def test_a_new_project_starts_at_the_recommended_setting(self, project):
        config = _sticky_config(str(project), _args())

        assert config == {"trace_opens": True, "trace_spine": "auto"}

    def test_what_was_passed_wins_and_is_remembered(self, project):
        _sticky_config(str(project), _args(trace_spine="off", trace_opens=False))

        assert run_store.read_config(str(project)) == {
            "trace_opens": False, "trace_spine": "off"}

    def test_what_was_not_passed_is_what_the_project_last_used(self, project):
        _sticky_config(str(project), _args(trace_spine="off", trace_opens=False))

        config = _sticky_config(str(project), _args())

        assert config == {"trace_opens": False, "trace_spine": "off"}

    def test_one_flag_changes_without_resetting_the_other(self, project):
        _sticky_config(str(project), _args(trace_spine="off", trace_opens=False))

        config = _sticky_config(str(project), _args(trace_spine="on"))

        assert config == {"trace_opens": False, "trace_spine": "on"}

    def test_the_context_file_records_what_was_used(self, project):
        text = _capture_context(str(project), ["bst", "build", "all.bst"],
                                {"trace_opens": False, "trace_spine": "on"})

        assert "trace_opens=false" in text
        assert "trace_spine=on" in text
        assert "command=bst build all.bst" in text


def _args(**overrides):
    import argparse
    namespace = argparse.Namespace(trace_opens=None, trace_spine=None)
    for key, value in overrides.items():
        setattr(namespace, key, value)
    return namespace


class TestTheLoop:
    def test_the_first_run_says_what_makes_the_second_one_useful(
            self, project, recorded, monkeypatch, capsys):
        monkeypatch.chdir(project)
        monkeypatch.setattr(bga_snapshot, "_analyze", lambda *a: 0)

        assert main(["--", "bst", "build", "all.bst"]) == 0

        assert "first snapshot" in capsys.readouterr().out

    def test_the_second_run_compares_against_the_first(
            self, project, recorded, monkeypatch, capsys):
        monkeypatch.chdir(project)
        monkeypatch.setattr(bga_snapshot, "_analyze", lambda *a: 0)
        compared = []
        monkeypatch.setattr(bga_snapshot, "_compare",
                            lambda base, cand: compared.append((base, cand)) or 0)

        main(["--", "bst", "build", "all.bst"])
        main(["--", "bst", "build", "all.bst"])

        [(baseline, candidate)] = compared
        snapshots = run_store.list_runs(str(project))
        assert (baseline, candidate) == (snapshots[-2], snapshots[-1])

    def test_the_baseline_is_chosen_before_the_new_snapshot_exists(
            self, project, recorded, monkeypatch):
        """Off-by-one waiting to happen: list the store *after* the
        capture and the new run is its own baseline."""
        monkeypatch.chdir(project)
        monkeypatch.setattr(bga_snapshot, "_analyze", lambda *a: 0)
        compared = []
        monkeypatch.setattr(bga_snapshot, "_compare",
                            lambda base, cand: compared.append((base, cand)) or 0)

        main(["--", "bst", "build", "all.bst"])
        main(["--", "bst", "build", "all.bst"])

        [(baseline, candidate)] = compared
        assert baseline != candidate

    def test_no_compare_takes_the_snapshot_and_stops(
            self, project, recorded, monkeypatch):
        monkeypatch.chdir(project)
        monkeypatch.setattr(bga_snapshot, "_analyze", lambda *a: 0)
        monkeypatch.setattr(bga_snapshot, "_compare",
                            lambda *a: pytest.fail("compared anyway"))

        main(["--", "bst", "build", "all.bst"])
        assert main(["--no-compare", "--", "bst", "build", "all.bst"]) == 0

    def test_both_plane2_reports_are_joined_to_their_own_runs(
            self, project, recorded, monkeypatch):
        """Joining yesterday's report to today's run is precisely the
        mistake this item exists to remove, and the store is the only
        thing that knows which is which."""
        monkeypatch.chdir(project)
        monkeypatch.setattr(bga_snapshot, "_analyze", lambda *a: 0)
        seen = []
        monkeypatch.setattr("bga.cli.main", lambda argv: seen.append(argv) or 0)

        main(["--", "bst", "build", "all.bst"])
        main(["--", "bst", "build", "all.bst"])

        [argv] = [a for a in seen if a and a[0] == "compare"]
        baseline, candidate = argv[1], argv[2]
        assert argv[argv.index("--baseline-plane2") + 1] == os.path.join(
            os.path.dirname(baseline), PLANE2_NAME)
        assert argv[argv.index("--candidate-plane2") + 1] == os.path.join(
            os.path.dirname(candidate), PLANE2_NAME)


class TestTheAnswerIsTheBuildsAnswer:
    def test_a_failed_build_is_not_a_successful_snapshot(
            self, project, recorded, monkeypatch):
        monkeypatch.chdir(project)
        monkeypatch.setattr(bga_snapshot, "_analyze", lambda *a: 0)
        import tools.bst_native_build_tracer as tracer
        tracer.main.returncode = 255

        assert main(["--", "bst", "build", "all.bst"]) == 255

    def test_a_build_that_produced_no_run_directory_says_which_half_survived(
            self, project, monkeypatch, capsys):
        def capture_without_a_run(argv):
            snapshot = os.path.dirname(argv[argv.index("--run-dir") + 1])
            with open(os.path.join(snapshot, PLANE2_NAME), "w") as handle:
                handle.write("{}")
            return 255

        import tools.bst_native_build_tracer as tracer
        monkeypatch.setattr(tracer, "main", capture_without_a_run)
        monkeypatch.chdir(project)

        assert main(["--", "bst", "build", "all.bst"]) == 255

        assert "Plane 2 capture is in" in capsys.readouterr().err


class TestTheFrontDoorsOwnErrors:
    def test_outside_a_project_it_says_so_rather_than_building(
            self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)

        assert main(["--", "bst", "build", "all.bst"]) == 2

        assert "no BuildStream project here" in capsys.readouterr().err

    def test_no_command_is_a_usage_error_not_an_empty_build(
            self, project, monkeypatch, capsys):
        monkeypatch.chdir(project)

        assert main([]) == 2

        assert "nothing to run" in capsys.readouterr().err


class TestListing:
    def test_an_empty_store_says_how_to_fill_it(self, project, capsys):
        assert _list(str(project)) == 0

        assert "bga snapshot" in capsys.readouterr().out

    def test_the_aliases_shown_are_the_ones_resolution_would_give(
            self, project, capsys):
        for stamp in ("20260101T000000Z", "20260102T000000Z", "20260103T000000Z"):
            os.makedirs(os.path.join(run_store.runs_dir(str(project)), stamp, "run"))

        _list(str(project))

        out = capsys.readouterr().out
        assert "20260103T000000Z  @last" in out
        assert "20260102T000000Z  @prev" in out
        assert "20260101T000000Z\n" in out

    def test_an_incomplete_capture_is_listed_without_an_alias(self, project, capsys):
        os.makedirs(os.path.join(
            run_store.runs_dir(str(project)), "20260101T000000Z", "run"))
        os.makedirs(os.path.join(
            run_store.runs_dir(str(project)), "20260102T000000Z"))

        _list(str(project))

        out = capsys.readouterr().out
        assert "20260101T000000Z  @last" in out
        assert "20260102T000000Z  (no run directory" in out


def test_the_size_warning_fires_only_past_the_threshold(project, monkeypatch, capsys):
    monkeypatch.setattr(bga_snapshot, "_SIZE_WARN_BYTES", 10)
    os.makedirs(os.path.join(run_store.runs_dir(str(project)), "20260101T000000Z"))
    with open(os.path.join(run_store.runs_dir(str(project)),
                           "20260101T000000Z", "big"), "wb") as handle:
        handle.write(b"x" * 64)

    bga_snapshot._warn_if_large(str(project))

    assert "Delete snapshot directories" in capsys.readouterr().err


def test_snapshot_is_reachable_through_the_cli():
    from bga.tools_dispatch import TOOL_ALIASES

    assert TOOL_ALIASES["snapshot"][0] == "tools.bga_snapshot"


@pytest.mark.bst
def test_the_two_line_loop_on_a_real_build(tmp_path):
    """UX-126's acceptance, at the size that fits a test suite.

    `examples/01` runs eight `sleep 3`s and nothing else, so this is the
    whole loop - capture, extract, analyze, and compare against the
    previous snapshot - for about eight seconds of wall clock. What it
    proves is the part no mock can: that the argv this builds is one a
    real `bga capture run` accepts, that the run directory it extracts is
    one `bga analyze` reads, and that `@prev`/`@last` name them
    afterwards from a plain shell.
    """
    import shutil
    import subprocess
    import sys

    for tool in ("bst", "bwrap"):
        if not shutil.which(tool):
            pytest.skip(f"{tool} not on PATH")
    if not (shutil.which("cc") or shutil.which("gcc")):
        pytest.skip("no cc/gcc on PATH")
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    source = os.path.join(repo, "examples", "01-resource-contention")
    if not os.path.isfile(os.path.join(source, "files", "runtime", "bin", "sh")):
        pytest.skip("examples/01 is not staged - run examples/stage_runtimes.sh")

    from tests.unit._bst_env import isolated_bst_env

    project = tmp_path / "proj"
    shutil.copytree(source, project, symlinks=True)
    # Prepended, not assigned: `isolated_bst_env` may have put the real
    # user site-packages on PYTHONPATH to survive the changed HOME, and
    # replacing it takes jinja2 away from `bst` (UX-84's own trap).
    env = isolated_bst_env(tmp_path / "home")
    env["PYTHONPATH"] = os.pathsep.join(
        [repo] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))

    def snapshot():
        return subprocess.run(
            [sys.executable, "-m", "bga.cli", "snapshot", "--",
             "bst", "--no-colors", "--builders", "2", "build", "all.bst"],
            cwd=str(project), env=env, capture_output=True, text=True, timeout=900)

    first = snapshot()
    assert first.returncode == 0, first.stderr[-4000:]
    assert "first snapshot" in first.stdout

    # The second build is all cache hits, so the pair is cross-mode and
    # UX-78 refuses it - through `bga compare` itself, which is the point
    # of composing rather than reimplementing. A loop that quietly
    # compared a cold build against a warm one would report the cache as
    # an improvement.
    second = snapshot()
    assert second.returncode == 0, second.stderr[-4000:]
    assert "Refusing to compare these runs" in second.stdout + second.stderr

    # Two warm builds are comparable, and now it compares.
    third = snapshot()
    assert third.returncode == 0, third.stderr[-4000:]
    assert "Verdict:" in third.stdout, "the third run did not compare"

    # The store is what the aliases name, from a shell that knows no paths.
    listed = subprocess.run(
        [sys.executable, "-m", "bga.cli", "snapshot", "--list"],
        cwd=str(project), env=env, capture_output=True, text=True, timeout=60)
    assert "@last" in listed.stdout and "@prev" in listed.stdout

    resolved = subprocess.run(
        [sys.executable, "-m", "bga.cli", "compare", "@prev", "@last"],
        cwd=str(project), env=env, capture_output=True, text=True, timeout=300)
    assert "Verdict:" in resolved.stdout, resolved.stderr[-4000:]
