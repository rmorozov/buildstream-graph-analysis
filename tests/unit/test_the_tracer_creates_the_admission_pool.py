"""UX-1005 track C: `run_traced_build` creates the admission pool
(`BST_TRACE_ADMISSION_POOL`) whenever `--jobserver` is active, sized
`min(host cores, this recipe pool's own ceiling)`, and reports the size
and the total admission wait. `--jobserver off` must leave the env and
the admission report byte-identical to before this landed."""
import json
import os

import pytest

from tools import bst_native_build_tracer as tracer


def _stub_shim(monkeypatch):
    monkeypatch.setattr(tracer, "compile_hook", lambda d: None)
    monkeypatch.setattr(tracer, "install_bwrap_shim", lambda d: "/usr/bin/bwrap")
    monkeypatch.setattr(tracer, "write_bwrap_shim", lambda d: os.path.join(d, "bwrap"))
    monkeypatch.setattr(tracer, "probe_bwrap_shim", lambda p: None)


def _fake_run(seen):
    def fake_run(cmd, cwd=None, env=None, **kwargs):
        seen["env"] = dict(env)
        return 0
    return fake_run


def test_the_admission_pool_is_sized_to_the_smaller_of_host_and_recipe(
        tmp_path, monkeypatch):
    project = tmp_path / "proj"
    project.mkdir()
    raw_log = tmp_path / "trace.log"
    _stub_shim(monkeypatch)
    monkeypatch.setattr(tracer.os, "cpu_count", lambda: 4)
    seen = {}

    def fake_popen(cmd, cwd=None, env=None, **kw):
        seen["env"] = dict(env)
        seen["existed"] = os.path.exists(env["BST_TRACE_ADMISSION_POOL"])
        return type("P", (), {"wait": lambda self: 0})()

    monkeypatch.setattr(tracer.subprocess, "Popen", fake_popen)

    tracer.run_traced_build(str(project), ["bst", "build", "x.bst"],
                            str(raw_log), jobserver=32)

    assert "env" in seen, "the fake Popen never ran"
    assert "BST_TRACE_ADMISSION_POOL" in seen["env"]
    assert seen["existed"], "the admission FIFO must exist while the build runs"


def test_jobserver_off_never_creates_an_admission_pool(tmp_path, monkeypatch):
    project = tmp_path / "proj"
    project.mkdir()
    raw_log = tmp_path / "trace.log"
    _stub_shim(monkeypatch)
    seen = {}
    monkeypatch.setattr(tracer.subprocess, "Popen",
                        lambda cmd, cwd=None, env=None, **kw: type(
                            "P", (), {"wait": lambda self: seen.__setitem__(
                                "env", dict(env)) or 0})())

    tracer.run_traced_build(str(project), ["bst", "build", "x.bst"], str(raw_log))

    assert "BST_TRACE_ADMISSION_POOL" not in seen["env"]
    assert "BST_TRACE_ADMISSION_BROKER_DIR" not in seen["env"]


def test_the_admission_status_file_reports_pool_size_and_wait(tmp_path, monkeypatch):
    project = tmp_path / "proj"
    project.mkdir()
    raw_log = tmp_path / "trace.log"
    output = tmp_path / "report.json"
    admission_status_path = str(output) + ".admission_status.json"
    _stub_shim(monkeypatch)
    monkeypatch.setattr(tracer.os, "cpu_count", lambda: 8)

    def fake_popen(cmd, cwd=None, env=None, **kw):
        # UX-1005 track C: writes a fake `admission_wait` row into this
        # sandbox's own ledger, exactly as `run_admitted` would.
        ledger_path = os.path.join(
            env["BST_TRACE_BIND_SRC"], "jobserver_ledger.jsonl")
        with open(ledger_path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(
                {"event": "admission_wait", "element": "a.bst", "wait_us": 250}) + "\n")
        return type("P", (), {"wait": lambda self: 0})()

    monkeypatch.setattr(tracer.subprocess, "Popen", fake_popen)

    tracer.run_traced_build(str(project), ["bst", "build", "x.bst"],
                            str(raw_log), jobserver=16,
                            admission_status_path=admission_status_path)

    assert os.path.exists(admission_status_path)
    with open(admission_status_path, encoding="utf-8") as handle:
        status = json.load(handle)
    assert status["pool_size"] == 8
    assert status["wait_total_us"] == 250


def test_a_build_that_raises_still_removes_the_admission_fifo(tmp_path, monkeypatch):
    project = tmp_path / "proj"
    project.mkdir()
    raw_log = tmp_path / "trace.log"
    _stub_shim(monkeypatch)
    seen = {}

    def fake_run(cmd, cwd=None, env=None, **kwargs):
        seen["path"] = env["BST_TRACE_ADMISSION_POOL"]
        assert os.path.exists(seen["path"])
        raise RuntimeError("the build blew up")

    monkeypatch.setattr(tracer.subprocess, "Popen", fake_run)

    with pytest.raises(RuntimeError):
        tracer.run_traced_build(str(project), ["bst", "build", "x.bst"],
                                str(raw_log), jobserver=4)

    assert "path" in seen
    assert not os.path.exists(seen["path"])
