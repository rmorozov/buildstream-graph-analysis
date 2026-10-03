"""UX-1304: `project.conf`'s `bga-jobserver-env` reaches the shim, and a kind
outside the table with no composed width sets each declared `NAME`."""

import json
import os

from tests.unit.test_a_nameless_make_sandbox_joins_through_its_makeflags import AUTH, _argv
from tests.unit.test_bwrap_shim import _decide_through_the_real_gate, _fake_bwrap_with_make
from tests.unit.test_the_lto_link_survives_the_jobserver import BIND_DST, _setenv_values
from tests.unit.test_the_tracer_creates_the_admission_pool import _stub_shim
from tools import bst_native_build_tracer as tracer
from tools.bst_native_build_tracer import _declared_jobserver_env
from tools.native_trace.bwrap_shim import (
    build_shim_argv,
    kind_job_env,
    parse_element_max_jobs,
    recipe_promise,
    sandbox_make_auth_style,
)

DECLARED = "MYJOBS=-j,OTHER=--jobs="
FIFO_AUTH = f"--jobserver-auth=fifo:{BIND_DST}/jobserver"
_CUSTOM_BST_ARGS = ["--unshare-pid", "--dir", "core.bst", "--chdir", "core.bst", "sh", "-c", "mybuild"]


def _declare(monkeypatch, declared=DECLARED, max_jobs="4"):
    monkeypatch.setenv("BST_TRACE_JOBSERVER_ENV", declared)
    monkeypatch.setenv("BST_TRACE_PROJECT_MAX_JOBS", max_jobs)


def test_an_unknown_kind_sets_each_declared_name_to_its_prefix_and_width(monkeypatch):
    _declare(monkeypatch)
    assert kind_job_env("custom", AUTH) == (
        [("MYJOBS", "-j4"), ("OTHER", "--jobs=4"), ("MAKEFLAGS", AUTH)],
        [],
        "declared_env",
    )


def test_without_a_declaration_an_unknown_kind_still_gets_nothing(monkeypatch):
    monkeypatch.delenv("BST_TRACE_JOBSERVER_ENV", raising=False)
    monkeypatch.setenv("BST_TRACE_PROJECT_MAX_JOBS", "4")
    assert kind_job_env("custom", AUTH) == ([], [], "unknown_kind")


def test_an_unknown_project_width_leaves_the_declaration_unapplied(monkeypatch):
    monkeypatch.setenv("BST_TRACE_JOBSERVER_ENV", DECLARED)
    monkeypatch.delenv("BST_TRACE_PROJECT_MAX_JOBS", raising=False)
    assert kind_job_env("custom", AUTH)[2] == "unknown_kind"


def test_a_shipped_kind_and_a_composed_promise_ignore_the_declaration(monkeypatch):
    _declare(monkeypatch)
    assert kind_job_env("make", AUTH) == ([("MAKEFLAGS", AUTH)], [], "make")
    opts = _argv(MAXJOBS="4")
    assert kind_job_env("custom", AUTH, jobs_present=recipe_promise(opts))[2] == "maxjobs_env"


def test_the_decision_log_reads_joined_and_declared_env(tmp_path, monkeypatch):
    _declare(monkeypatch)
    opts = _argv()
    assert recipe_promise(opts) is None
    policy, _marker = _decide_through_the_real_gate(tmp_path, monkeypatch, "custom", opts, "exit 127\n")
    assert policy == "declared_env"
    with open(tmp_path / "decisions.jsonl", encoding="utf-8") as handle:
        assert json.loads(handle.readline())["decision"] == "joined"


def _shim_argv(tmp_path, monkeypatch, **setenv):
    _declare(monkeypatch)
    fake = _fake_bwrap_with_make(tmp_path / "real-bwrap", tmp_path / "marker", BIND_DST, "4.4")
    bind_src = str(tmp_path / "host-trace-dir")
    os.makedirs(bind_src, exist_ok=True)
    monkeypatch.setenv("BST_TRACE_JOBSERVER", os.path.join(bind_src, "jobserver"))
    bst_args = list(_CUSTOM_BST_ARGS)
    at = bst_args.index("sh")
    for name, value in setenv.items():
        bst_args[at:at] = ["--setenv", name, value]
    read_fd, write_fd = os.pipe()
    try:
        return build_shim_argv(
            real_bwrap=fake,
            bst_args=bst_args,
            bind_src=bind_src,
            bind_dst=BIND_DST,
            preload_so=f"{BIND_DST}/hook.so",
            trace_log=f"{BIND_DST}/trace.log",
            jobserver_fd=read_fd,
            project_max_jobs=4,
            element_kind="custom",
        )
    finally:
        os.close(read_fd)
        os.close(write_fd)


def test_the_sandbox_argv_carries_each_name_beside_the_auth(tmp_path, monkeypatch):
    argv = _shim_argv(tmp_path, monkeypatch)
    assert _setenv_values(argv, "MYJOBS") == ["-j4"]
    assert _setenv_values(argv, "OTHER") == ["--jobs=4"]
    assert _setenv_values(argv, "MAKEFLAGS") == [FIFO_AUTH]


def test_a_composed_name_of_one_pins_the_element(tmp_path, monkeypatch):
    _declare(monkeypatch)
    opts = _argv(MYJOBS="-j1")
    assert parse_element_max_jobs(opts) == 1
    policy, _marker = _decide_through_the_real_gate(tmp_path, monkeypatch, "custom", opts, "exit 127\n")
    assert policy is None
    with open(tmp_path / "decisions.jsonl", encoding="utf-8") as handle:
        assert json.loads(handle.readline())["decision"] == "pinned"
    argv = _shim_argv(tmp_path, monkeypatch, MYJOBS="-j1")
    assert _setenv_values(argv, "MYJOBS") == ["-j1"]
    assert _setenv_values(argv, "MAKEFLAGS") == []


def test_a_composed_name_keeps_its_own_width_and_blocks_every_other(tmp_path, monkeypatch):
    argv = _shim_argv(tmp_path, monkeypatch, MYJOBS="-j2")
    assert _setenv_values(argv, "MYJOBS") == ["-j2"]
    assert _setenv_values(argv, "OTHER") == []
    assert _setenv_values(argv, "MAKEFLAGS") == []


def test_a_composed_name_off_its_prefix_injects_nothing(tmp_path, monkeypatch):
    _declare(monkeypatch)
    opts = _argv(MYJOBS="--jobs=1")
    assert parse_element_max_jobs(opts) is None
    policy, _marker = _decide_through_the_real_gate(tmp_path, monkeypatch, "custom", opts, "exit 127\n")
    assert policy == "unknown_kind"
    argv = _shim_argv(tmp_path, monkeypatch, MYJOBS="--jobs=1")
    assert _setenv_values(argv, "MYJOBS") == ["--jobs=1"]
    assert _setenv_values(argv, "OTHER") == []
    assert _setenv_values(argv, "MAKEFLAGS") == []


def test_a_composed_makeflags_keeps_its_contents(tmp_path, monkeypatch):
    argv = _shim_argv(tmp_path, monkeypatch, MAKEFLAGS="-s")
    assert _setenv_values(argv, "MAKEFLAGS") == ["-s", f"-s {FIFO_AUTH}"]


def test_a_sandbox_make_below_4_4_gets_the_fd_style(tmp_path, monkeypatch):
    _declare(monkeypatch)
    fake = _fake_bwrap_with_make(tmp_path / "real-bwrap", tmp_path / "marker", BIND_DST, "4.3")
    assert sandbox_make_auth_style("custom", fake, [], str(tmp_path / "make_probe.json")) == "fd"


def test_a_project_width_of_one_leaves_the_declaration_unapplied(monkeypatch):
    _declare(monkeypatch, max_jobs="1")
    assert kind_job_env("custom", AUTH)[2] == "unknown_kind"


def test_the_tracer_reserializes_project_conf_for_the_shim(tmp_path):
    (tmp_path / "project.conf").write_text("variables:\n  bga-jobserver-env: 'MYJOBS=-j, OTHER=--jobs='\n")
    assert _declared_jobserver_env(str(tmp_path)) == "MYJOBS=-j,OTHER=--jobs="


def test_a_malformed_or_absent_declaration_reaches_the_shim_as_nothing(tmp_path):
    assert _declared_jobserver_env(str(tmp_path)) is None
    (tmp_path / "project.conf").write_text("variables:\n  bga-jobserver-env: 'MYJOBS'\n")
    assert _declared_jobserver_env(str(tmp_path)) is None


def _build_env(tmp_path, monkeypatch, jobserver):
    project = tmp_path / "proj"
    project.mkdir()
    (project / "project.conf").write_text("variables:\n  bga-jobserver-env: 'MYJOBS=-j'\n")
    _stub_shim(monkeypatch)
    seen = {}

    def fake_popen(cmd, cwd=None, env=None, **kw):
        seen["env"] = dict(env)
        return type("P", (), {"wait": lambda self: 0})()

    monkeypatch.setattr(tracer.subprocess, "Popen", fake_popen)
    monkeypatch.setenv("BST_TRACE_JOBSERVER_ENV", "STALE=-j")
    tracer.run_traced_build(str(project), ["bst", "build", "x.bst"], str(tmp_path / "t.log"), jobserver=jobserver)
    return seen["env"]


def test_a_capture_under_the_mode_hands_the_declaration_to_the_shim(tmp_path, monkeypatch):
    assert _build_env(tmp_path, monkeypatch, 4)["BST_TRACE_JOBSERVER_ENV"] == "MYJOBS=-j"


def test_a_capture_with_the_mode_off_hands_it_nothing(tmp_path, monkeypatch):
    assert "BST_TRACE_JOBSERVER_ENV" not in _build_env(tmp_path, monkeypatch, None)
