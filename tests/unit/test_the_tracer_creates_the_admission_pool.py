"""UX-1005 track C, verifier fix: `run_traced_build` never creates a
second FIFO for admission - `BST_TRACE_ADMISSION_POOL` is always the
*same* FIFO `BST_TRACE_JOBSERVER` names, so an admitted sandbox's own
token and its recipe's extra `-jK` draws share the one real supply the
machine's cores bound (a separate pool let a giant draw ~31 jobs on 16
cores, barely better than no admission at all). Sized to `jobserver`
directly, reported alongside the total admission wait. `--jobserver
off` must leave the env and the admission report byte-identical to
before this landed."""
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


def test_the_admission_pool_is_the_same_fifo_the_recipe_pool_uses(
        tmp_path, monkeypatch):
    project = tmp_path / "proj"
    project.mkdir()
    raw_log = tmp_path / "trace.log"
    _stub_shim(monkeypatch)
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
    assert seen["env"]["BST_TRACE_ADMISSION_POOL"] == seen["env"]["BST_TRACE_JOBSERVER"], (
        "admission has no pool of its own - a second FIFO lets a giant's "
        "own -jK draws add on top of every admitted sandbox's token")


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
    assert status["pool_size"] == 16, "the pool is this recipe's own ceiling, not cpu_count"
    assert status["wait_total_us"] == 250


def test_no_plan_falls_back_to_structural_ranking(tmp_path, monkeypatch):
    """UX-1005 track C (Ruslan): `bga capture run` never passes `--plan`
    on a first capture - `element_deps` (from the same `bst show` read
    that already gave `element_kinds`) is enough to rank without one,
    so the broker still runs instead of falling all the way back to
    unordered FIFO wakeups. `ranking_source` says which ran."""
    project = tmp_path / "proj"
    project.mkdir()
    raw_log = tmp_path / "trace.log"
    output = tmp_path / "report.json"
    admission_status_path = str(output) + ".admission_status.json"
    _stub_shim(monkeypatch)
    seen = {}

    def fake_popen(cmd, cwd=None, env=None, **kw):
        seen["env"] = dict(env)
        return type("P", (), {"wait": lambda self: 0})()

    monkeypatch.setattr(tracer.subprocess, "Popen", fake_popen)

    tracer.run_traced_build(
        str(project), ["bst", "build", "x.bst"], str(raw_log), jobserver=4,
        element_kinds={"a.bst": "cmake", "b.bst": "cmake"},
        element_deps={"a.bst": [], "b.bst": ["a.bst"]},
        admission_status_path=admission_status_path)

    assert "BST_TRACE_ADMISSION_BROKER_DIR" in seen["env"], (
        "no --plan given, but element_deps was - the broker must still start")
    with open(admission_status_path, encoding="utf-8") as handle:
        status = json.load(handle)
    assert status["ranking_source"] == "structural"


def test_a_real_plan_wins_over_the_structural_fallback(tmp_path, monkeypatch):
    project = tmp_path / "proj"
    project.mkdir()
    raw_log = tmp_path / "trace.log"
    output = tmp_path / "report.json"
    admission_status_path = str(output) + ".admission_status.json"
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps({"elements": {"slack": {"a.bst": 5}}}))
    _stub_shim(monkeypatch)
    monkeypatch.setattr(tracer.subprocess, "Popen",
                        lambda cmd, cwd=None, env=None, **kw: type(
                            "P", (), {"wait": lambda self: 0})())

    tracer.run_traced_build(
        str(project), ["bst", "build", "x.bst"], str(raw_log), jobserver=4,
        element_kinds={"a.bst": "cmake", "b.bst": "cmake"},
        element_deps={"a.bst": [], "b.bst": ["a.bst"]},
        plan_path=str(plan_path), admission_status_path=admission_status_path)

    with open(admission_status_path, encoding="utf-8") as handle:
        status = json.load(handle)
    assert status["ranking_source"] == "plan"


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
