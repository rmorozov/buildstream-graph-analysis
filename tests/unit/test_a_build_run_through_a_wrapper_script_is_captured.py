"""UX-1322: a build run through a wrapper script is captured; one that runs no `bst build` is refused.

A fake `bst` on PATH stands in for BuildStream: the wrapper reaches it through bga's `bst` shim,
which records the first `bst build` as `run_wrapped` records a direct one.
"""

import os
import pathlib
import re
import stat
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import run_store
from tools import bga_snapshot, bst_run_wrapped
from tools import bst_native_build_tracer as tracer

FIRST_LINE = re.compile(r"^\[wrapper\]\[\d{4}-\d\d-\d\d \d\d:\d\d:\d\d,\d{3}\] INFO: Executing command: (.*)$")


def _script(path: pathlib.Path, body: str) -> pathlib.Path:
    path.write_text("#!/bin/sh\n" + body)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


@pytest.fixture
def project(tmp_path):
    bin_dir = tmp_path / "fakebin"
    bin_dir.mkdir()
    _script(bin_dir / "bst", 'echo "fake-bst $*"\n')
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "project.conf").write_text("name: ux1322\n")
    _script(proj / "build.sh", 'echo wrapping\nbst show t.bst\nbst --max-jobs 3 --on-error continue build "$@"\n')
    _script(proj / "twice.sh", "bst build a.bst\nbst build b.bst\n")
    _script(proj / "nobst.sh", "echo no build here\nbst show t.bst\n")
    env = dict(os.environ, PATH=f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    return proj, env


def test_the_first_line_is_the_inner_bst_argv(project, capsys):
    proj, env = project
    log = proj / "build.log"
    code = bst_run_wrapped.run_wrapper_command(str(proj), ["./build.sh", "t.bst"], str(log), env=env)
    assert code == 0
    lines = log.read_text().splitlines()
    assert FIRST_LINE.match(lines[0]).group(1) == "bst --max-jobs 3 --on-error continue build t.bst"
    assert any(line.endswith("INFO: fake-bst --max-jobs 3 --on-error continue build t.bst") for line in lines)
    assert not any("fake-bst show" in line for line in lines), "a non-build subcommand is passed through"
    assert lines[-1].endswith("INFO: Return code: 0")
    assert bst_run_wrapped.recorded_bst_argv(str(log)) == ["bst", "--max-jobs", "3", "--on-error", "continue"] + [
        "build",
        "t.bst",
    ]


def test_a_second_build_is_named_not_recorded(project, capsys):
    proj, env = project
    log = proj / "build.log"
    bst_run_wrapped.run_wrapper_command(str(proj), ["./twice.sh"], str(log), env=env)
    assert FIRST_LINE.match(log.read_text().splitlines()[0]).group(1) == "bst build a.bst"
    assert "b.bst" not in log.read_text()
    assert "1 more time(s)" in capsys.readouterr().err


def test_the_shim_never_finds_itself(tmp_path):
    shim_dir = tmp_path / "shim"
    shim_dir.mkdir()
    bst_run_wrapped.write_bst_shim(str(shim_dir))
    real = tmp_path / "real"
    real.mkdir()
    _script(real / "bst", "true\n")
    assert bst_run_wrapped.find_real_bst(str(shim_dir), f"{shim_dir}{os.pathsep}{real}") == str(real / "bst")


def test_a_command_that_runs_no_bst_build_is_refused_in_one_line(project, capsys, monkeypatch):
    proj, env = project
    monkeypatch.setenv("PATH", env["PATH"])
    log = proj / "build.log"
    monkeypatch.setattr(sys, "argv", ["bst_run_wrapped", str(proj), str(log), "--", "./nobst.sh"])
    code = bst_run_wrapped.main()
    err = capsys.readouterr().err
    assert code == bst_run_wrapped.NO_BST_BUILD_EXIT
    refusal = [line for line in err.splitlines() if line.startswith("Error:")]
    assert refusal == [
        "Error: `./nobst.sh` exited 0 without running `bst build`, so there was no build to capture. "
        "bga records the first `bst build` a wrapper runs through `bst` on its PATH."
    ]
    assert "Traceback" not in err
    assert not log.exists()


def test_a_snapshot_with_no_bst_build_leaves_no_husk(project, capsys, monkeypatch):
    proj, _env = project
    monkeypatch.setattr(tracer, "main", lambda argv: bst_run_wrapped.NO_BST_BUILD_EXIT)
    code = bga_snapshot.main(["--project", str(proj), "--no-progress", "--", str(proj / "nobst.sh")])
    assert code == bst_run_wrapped.NO_BST_BUILD_EXIT
    assert run_store.list_snapshots(str(proj)) == []
    assert "Nothing was kept" in capsys.readouterr().err


def test_a_wrapper_with_a_jobserver_is_refused_before_the_hook_compiles(project, capsys, monkeypatch):
    proj, _env = project

    def compile_hook(_dir):
        raise AssertionError("the hook compiled before the refusal")

    monkeypatch.setattr(tracer, "compile_hook", compile_hook)
    code = tracer.main(["run", "--jobserver", "4", str(proj), str(proj / "p2.json"), "--", "./build.sh"])
    assert code == bst_run_wrapped.NO_BST_BUILD_EXIT
    assert capsys.readouterr().err.startswith("Error: --jobserver needs the `bst` command itself")


def test_the_readers_after_the_build_get_the_inner_bst_argv(project, monkeypatch):
    """The run directory's `bst show` replays the inner build's options, not the wrapper's (none)."""
    proj, _env = project
    inner = "bst -o arch x86_64 --on-error continue build t.bst"

    def fake_build(project_dir, cmd, raw_log_path, wrapped_log_path=None, **_kwargs):
        open(raw_log_path, "w").close()
        with open(wrapped_log_path, "w", encoding="utf-8") as handle:
            handle.write(f"[wrapper][2026-10-03 14:48:15,759] INFO: Executing command: {inner}\n")
        return 0

    seen = {}

    def fake_extract(*_args, bst_global_options=None, **_kwargs):
        seen["options"] = bst_global_options
        raise RuntimeError("stop after the read under test")

    monkeypatch.setattr(tracer, "run_traced_build", fake_build)
    monkeypatch.setattr("tools.bst_extract_run.extract_run", fake_extract)
    argv = ["run", "--wrapped-log", str(proj / "build.log"), "--run-dir", str(proj / "run"), "--json"]
    tracer.main([*argv, str(proj), str(proj / "p2.json"), "--", "./build.sh", "t.bst"])
    assert seen["options"] == ["-o", "arch", "x86_64", "--on-error", "continue"]


def test_the_closing_hint_repeats_the_wrapper(tmp_path):
    from bga.findings import compute_next_steps
    from bga.ingest.models import AnalysisResult

    snapshot = tmp_path / ".bga" / "runs" / "20261003T144815Z"
    (snapshot / "run").mkdir(parents=True)
    (snapshot / "capture-context.txt").write_text(f"project={tmp_path}\ncommand=./build.sh groups/all.bst\n")
    result = AnalysisResult(run_id="r", total_duration_us=1)
    result.run_instance = {"run_dir": str(snapshot / "run"), "targets": ["groups/all.bst"]}
    step = next(s for s in compute_next_steps(result) if s["id"] == "measure-again")
    assert step["argv"] == ["bga", "snapshot", "--", "./build.sh", "groups/all.bst"]
    (snapshot / "capture-context.txt").write_text("command=bst --on-error continue build groups/all.bst\n")
    step = next(s for s in compute_next_steps(result) if s["id"] == "measure-again")
    assert step["argv"] == ["bga", "snapshot", "--", "bst", "build", "groups/all.bst"]
