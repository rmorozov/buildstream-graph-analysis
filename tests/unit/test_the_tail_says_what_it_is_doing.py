"""UX-1077: every post-build phase of `bga snapshot` announces itself and
ends with its elapsed seconds; the last line totals the tail.

The tracer's `main` runs for real on the golden run; only the build
(`run_traced_build`) and `bst show` (`extract_run`) are replaced.
"""

import ast
import os
import re
import shutil
import stat

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GOLDEN = os.path.join(REPO, "tests", "fixtures", "golden", "mixed_task_kinds")

#: The phases a second snapshot runs, in order.
TAIL_PHASES = [
    "before the build",
    "Plane 2 report",
    "run directory",
    "raw log gzip",
    "analyze",
    "element slice",
    "compare",
    "store size",
]
ELAPSED = re.compile(r"^  (.+): \d+\.\ds$")
TOTAL = re.compile(r"^bga's own time after the build: \d+\.\ds")
RAW_LOG = (
    "START pid=10 ppid=1 ts=1.000000 element=app.bst inv=inv-10 src=hook cmd=/usr/bin/cc -c a.c\n"
    "END pid=10 ppid=1 ts=2.000000 element=app.bst inv=inv-10 src=hook exit=0 "
    "utime=0.400 stime=0.050 maxrss_kb=20000 cmd=/usr/bin/cc -c a.c\n"
)


@pytest.fixture
def project(tmp_path, monkeypatch):
    return tailed_project(tmp_path, monkeypatch)


def tailed_project(tmp_path, monkeypatch):
    """A project whose snapshots run the real tail on the golden run."""
    root = tmp_path / "proj"
    root.mkdir()
    (root / "project.conf").write_text("name: p\nmin-version: 2.0\n")
    binaries = tmp_path / "path"
    binaries.mkdir()
    stub = binaries / "bst"
    stub.write_text("#!/bin/sh\necho 'BuildStream 2.0.0+stub'\n")
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{binaries}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.chdir(root)
    monkeypatch.delenv("BGA_NO_PROGRESS", raising=False)
    import tools.bst_extract_run as extract
    import tools.bst_native_build_tracer as tracer

    def fake_build(project_dir, cmd, raw_log_path, wrapped_log_path=None, **_):
        with open(raw_log_path, "w") as handle:
            handle.write(RAW_LOG)
        with open(wrapped_log_path, "w") as handle:
            handle.write("Executing command: bst build all.bst\n[--:--:--] done\n")
        return 0

    def fake_extract(project_dir, wrapped_log, run_dir, **_):
        shutil.copytree(GOLDEN, run_dir)
        os.remove(os.path.join(run_dir, "expected_output.json"))

    monkeypatch.setattr(tracer, "run_traced_build", fake_build)
    monkeypatch.setattr(extract, "extract_run", fake_extract)
    return root


def _second_snapshot(capsys, *flags):
    from tools.bga_snapshot import main

    assert main(list(flags) + ["--", "bst", "build", "all.bst"]) == 0
    capsys.readouterr()
    assert main(list(flags) + ["--", "bst", "build", "all.bst"]) == 0
    return capsys.readouterr().err.splitlines()


def test_each_phase_is_announced_and_timed(project, capsys, monkeypatch):
    monkeypatch.setenv("BGA_FORCE_PROGRESS", "1")
    lines = _second_snapshot(capsys)
    elapsed = [m.group(1) for m in map(ELAPSED.match, lines) if m]
    assert elapsed == TAIL_PHASES, "\n".join(lines)
    pending = 0
    for line in lines:
        if line.endswith("..."):
            pending += 1
        elif ELAPSED.match(line):
            assert pending == 1, f"{line!r} has {pending} announcements"
            pending = 0
    assert TOTAL.match(lines[-1]), "\n".join(lines)


def test_no_progress_prints_the_total_only(project, capsys):
    lines = _second_snapshot(capsys, "--no-progress")
    assert not [l for l in lines if ELAPSED.match(l)], "\n".join(lines)
    assert not [l for l in lines if l.endswith("...")], "\n".join(lines)
    assert len([l for l in lines if TOTAL.match(l)]) == 1, "\n".join(lines)


def test_a_pipe_keeps_one_line_per_phase(project, capsys, monkeypatch):
    monkeypatch.delenv("BGA_FORCE_PROGRESS", raising=False)
    lines = _second_snapshot(capsys)
    assert not [l for l in lines if ELAPSED.match(l)], "\n".join(lines)
    assert len([l for l in lines if l.endswith("...")]) == len(TAIL_PHASES)


def test_the_build_wall_is_timed_around_the_build_alone():
    tree = ast.parse(open(os.path.join(REPO, "tools", "bst_native_build_tracer.py"), encoding="utf-8").read())
    func = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "run_traced_build")
    [timed] = [
        n
        for n in ast.walk(func)
        if isinstance(n, ast.With)
        and any(
            isinstance(i.context_expr, ast.Call) and getattr(i.context_expr.func, "attr", None) == "timed_build"
            for i in n.items
        )
    ]
    called = {getattr(n.func, "id", None) for n in ast.walk(timed) if isinstance(n, ast.Call)}
    assert "run_wrapped" in called
    assert not called & {"compile_hook", "compile_spine", "census_project"}


def test_view_times_its_analyze_compare_and_timeline(tmp_path, capsys, monkeypatch):
    from tools.bga_view import export, payloads

    monkeypatch.setenv("BGA_FORCE_PROGRESS", "1")
    monkeypatch.delenv("BGA_NO_PROGRESS", raising=False)
    fixture = os.path.join(REPO, "tests", "fixtures", "with_timeline")
    for name in ("a", "b"):
        shutil.copytree(fixture, tmp_path / name)
    capsys.readouterr()
    export(str(tmp_path / "b" / "run"), str(tmp_path / "out.html"), reanalyse=True)
    payloads(str(tmp_path / "b" / "run"), baseline=str(tmp_path / "a" / "run"), reanalyse=True)
    lines = capsys.readouterr().err.splitlines()
    elapsed = [m.group(1) for m in map(ELAPSED.match, lines) if m]
    assert {"analyze", "timeline", "compare"} <= set(elapsed), "\n".join(lines)
    announced = [line for line in lines if line.startswith("bga view: ")]
    assert len(announced) == len(elapsed), "\n".join(lines)
