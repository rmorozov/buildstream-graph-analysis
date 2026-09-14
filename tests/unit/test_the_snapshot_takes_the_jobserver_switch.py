"""UX-856: `bga snapshot --jobserver`/`--plan` compose the same capture
argv `bga capture run` would (`bga.cli.resolve_jobserver_ceiling`), and
name both facts in `capture-context.txt` and the compare header.

`take_snapshot`'s composition is what is pinned - not a real capture,
which `test_dual_plane_capture.py` already covers - the same posture
`test_snapshot.py` takes for every other flag.
"""
import json
import os
import stat

import pytest

from bga import run_store
from tools import bga_snapshot
from tools.bga_snapshot import (
    PLANE2_NAME,
    _jobserver_compare_line,
    create_parser,
    main,
    take_snapshot,
)


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    (root / "project.conf").write_text("name: p\nmin-version: 2.0\n")
    return root


@pytest.fixture
def a_bst_on_path(tmp_path_factory, monkeypatch):
    """A stub `bst` so `UX-324`'s pre-flight passes without a real
    BuildStream install - `test_snapshot.py`'s own fixture, duplicated
    rather than imported: fixtures across files here are self-contained
    per `test_the_key_is_equal_either_way.py`'s constants-only imports."""
    binaries = tmp_path_factory.mktemp("path")
    stub = binaries / "bst"
    stub.write_text("#!/bin/sh\necho 'BuildStream 2.0.0+stub'\n", encoding="utf-8")
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    monkeypatch.setenv("PATH", f"{binaries}{os.pathsep}{os.environ['PATH']}")
    return stub


@pytest.fixture
def recorded(monkeypatch, a_bst_on_path):
    """`capture run`, replaced by something that records its argv and
    lays down the files a successful capture would leave."""
    calls = []

    def fake_capture(argv):
        calls.append(argv)
        run_dir = argv[argv.index("--run-dir") + 1]
        os.makedirs(run_dir, exist_ok=True)
        with open(os.path.join(os.path.dirname(run_dir), PLANE2_NAME), "w") as handle:
            handle.write("{}")
        return 0

    import tools.bst_native_build_tracer as tracer
    monkeypatch.setattr(tracer, "main", fake_capture)
    return calls


class TestTheModePassesThroughToCaptureRun:
    def test_auto_resolves_against_a_faked_core_count(self, project, recorded):
        take_snapshot(str(project), ["bst", "build", "--builders", "3", "all.bst"],
                      {"trace_opens": True, "trace_spine": "auto"},
                      jobserver="auto", cpu_count=8)

        [argv] = recorded
        assert argv[argv.index("--jobserver") + 1] == "5"

    def test_an_explicit_int_passes_through(self, project, recorded):
        take_snapshot(str(project), ["bst", "build", "all.bst"],
                      {"trace_opens": True, "trace_spine": "auto"}, jobserver="4")

        [argv] = recorded
        assert argv[argv.index("--jobserver") + 1] == "4"

    def test_off_is_the_default_and_passes_nothing(self, project, recorded):
        take_snapshot(str(project), ["bst", "build", "all.bst"],
                      {"trace_opens": True, "trace_spine": "auto"})

        [argv] = recorded
        assert "--jobserver" not in argv


class TestPlanResolvesAtPrev:
    def test_plan_at_prev_resolves_to_that_snapshots_analysis(
            self, project, recorded, monkeypatch):
        monkeypatch.chdir(project)

        def fake_analyze(run_dir, plane2, publish_to=None, build_exit=0):
            if publish_to:
                with open(publish_to, "w", encoding="utf-8") as handle:
                    handle.write(json.dumps({"run_instance": {}}))
            return 0

        monkeypatch.setattr(bga_snapshot, "_analyze", fake_analyze)
        monkeypatch.setattr(bga_snapshot, "_compare", lambda *a: 0)

        # `@prev` names the second-newest of the snapshots *already on
        # disk* when it is resolved (`run_store.resolve_snapshot`,
        # unchanged) - two captures first, so the third's `@prev` is the
        # first rather than refusing "needs two snapshots".
        assert main(["--", "bst", "build", "all.bst"]) == 0
        first = run_store.list_runs(str(project))[-1]
        assert main(["--", "bst", "build", "all.bst"]) == 0

        assert main(["--jobserver", "auto", "--plan", "@prev",
                     "--", "bst", "build", "all.bst"]) == 0

        argv = recorded[-1]
        assert argv[argv.index("--plan") + 1] == os.path.join(
            first, run_store.ANALYSIS_NAME)

    def test_plan_without_a_jobserver_mode_is_refused(self, project, recorded, capsys):
        (project / "plan.json").write_text("{}")

        code = main(["--project", str(project), "--plan", str(project / "plan.json"),
                     "--", "bst", "build", "all.bst"])

        assert code == 2
        assert "--plan needs --jobserver" in capsys.readouterr().err
        assert recorded == []


class TestTheContextFileNamesBoth:
    def test_the_mode_ceiling_and_plan_are_recorded(self, project, recorded):
        plan = project / "plan.json"
        plan.write_text("{}")

        snapshot, _code = take_snapshot(
            str(project), ["bst", "build", "all.bst"],
            {"trace_opens": True, "trace_spine": "auto"},
            jobserver="4", plan=str(plan))

        with open(os.path.join(snapshot, "capture-context.txt"),
                  encoding="utf-8") as handle:
            text = handle.read()
        assert "jobserver: n 4" in text
        assert f"plan: {plan}" in text

    def test_off_and_no_plan_are_dashes(self, project, recorded):
        snapshot, _code = take_snapshot(
            str(project), ["bst", "build", "all.bst"],
            {"trace_opens": True, "trace_spine": "auto"})

        with open(os.path.join(snapshot, "capture-context.txt"),
                  encoding="utf-8") as handle:
            text = handle.read()
        assert "jobserver: off -" in text
        assert "plan: -" in text


class TestAnUnparseableValueIsRefusedByArgparse:
    def test_the_three_forms_are_named(self, capsys):
        with pytest.raises(SystemExit):
            create_parser().parse_args(["--jobserver", "bogus", "--", "bst", "build"])

        assert "auto" in capsys.readouterr().err


class TestTheCompareHeaderNamesBothModes:
    def test_off_vs_auto(self, tmp_path):
        baseline = tmp_path / "baseline"
        candidate = tmp_path / "candidate"
        baseline.mkdir()
        candidate.mkdir()
        (baseline / "analyze.json").write_text(json.dumps({"run_instance": {}}))
        (candidate / "analyze.json").write_text(json.dumps({"run_instance": {
            "jobserver": {"mode": "auto", "ceiling": 4, "auth": "fd",
                          "project_max_jobs": None}}}))

        line = _jobserver_compare_line(str(baseline), str(candidate))

        assert line == "jobserver: off -> auto (4)"

    def test_compare_itself_prints_the_line(self, tmp_path, monkeypatch, capsys):
        """`_jobserver_compare_line` alone does not prove `_compare` calls
        it - a deleted `print` there would leave the test above green."""
        baseline = tmp_path / "baseline"
        candidate = tmp_path / "candidate"
        baseline.mkdir()
        candidate.mkdir()
        (baseline / "analyze.json").write_text(json.dumps({"run_instance": {}}))
        (candidate / "analyze.json").write_text(json.dumps({"run_instance": {
            "jobserver": {"mode": "auto", "ceiling": 4, "auth": "fd",
                          "project_max_jobs": None}}}))
        monkeypatch.setattr("bga.cli.main", lambda argv: 0)

        bga_snapshot._compare(str(baseline), str(candidate))

        assert "jobserver: off -> auto (4)" in capsys.readouterr().out
