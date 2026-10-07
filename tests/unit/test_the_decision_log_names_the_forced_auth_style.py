"""UX-1310: the shim's decision row names the auth style a per-element
override forced and which switch forced it; the capture's summary names
each forced element and warns on an override that reached nothing."""

import json
import os
import subprocess
import sys

import pytest

from tests.unit.test_bwrap_shim import REAL_BWRAP_ARGV, _argv_with_jobs
from tools.bst_native_build_tracer import FIELD_SEP, RECORD_SEP, _parse_jobserver_show_records, forced_auth_summary

SHIM = os.path.join(os.path.dirname(__file__), "..", "..", "tools", "native_trace", "bwrap_shim.py")


def _run_shim(tmp_path, argv, cmdline_map=None, annotations=None, no_inject=False):
    """One real shim process, exec'ing a fake `bwrap` that exits 0; the decision row it wrote."""
    fake = tmp_path / "real-bwrap"
    fake.write_text("#!/bin/sh\nexit 0\n")
    fake.chmod(0o755)
    fifo = tmp_path / "jobserver.fifo"
    if not fifo.exists():
        os.mkfifo(fifo)
    log = tmp_path / "decisions.jsonl"
    log.unlink(missing_ok=True)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BST_TRACE_")}
    env.update(
        BST_TRACE_REAL_BWRAP=str(fake),
        BST_TRACE_BIND_SRC=str(tmp_path),
        BST_TRACE_BIND_DST="/bga-trace",
        BST_TRACE_PRELOAD_SO="/bga-trace/hook.so",
        BST_TRACE_LOG_DST="/bga-trace/log",
        BST_TRACE_JOBSERVER=str(fifo),
        BST_TRACE_PROJECT_MAX_JOBS="4",
        BST_TRACE_JOBSERVER_DECISIONS=str(log),
    )
    if cmdline_map is not None:
        env["BST_TRACE_JOBSERVER_AUTH_MAP"] = cmdline_map
    if annotations is not None:
        path = tmp_path / "element_auth_map.json"
        path.write_text(json.dumps(annotations))
        env["BST_TRACE_ELEMENT_AUTH_MAP"] = str(path)
    if no_inject:
        env["BST_TRACE_NO_INJECT"] = "1"
    proc = subprocess.run([sys.executable, SHIM, *argv], env=env, capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr
    return json.loads(log.read_text().splitlines()[0])


def _forced(row):
    return row.get("forced_style"), row.get("forced_by")


@pytest.mark.parametrize(
    ("cmdline_map", "annotations", "expected"),
    [
        ("off:core.bst", None, ("off", "command_line")),
        (None, {"core.bst": "fifo"}, ("fifo", "annotation")),
        ("fd:core.*", {"core.bst": "off"}, ("fd", "command_line")),
        ("off:other.bst", {"other.bst": "off"}, (None, None)),
        (None, {"core.bst": "keep"}, (None, None)),
    ],
    ids=["command-line", "annotation", "both", "neither", "out-of-four"],
)
def test_the_row_names_the_forced_style_and_its_switch(tmp_path, cmdline_map, annotations, expected):
    assert _forced(_run_shim(tmp_path, REAL_BWRAP_ARGV, cmdline_map, annotations)) == expected


def test_a_pinned_element_names_nothing(tmp_path):
    row = _run_shim(tmp_path, _argv_with_jobs("-j1"), "off:core.bst", {"core.bst": "fd"})
    assert row["decision"] == "pinned"
    assert _forced(row) == (None, None)


def test_a_no_inject_sandbox_names_nothing(tmp_path):
    assert _forced(_run_shim(tmp_path, REAL_BWRAP_ARGV, "off:core.bst", no_inject=True)) == (None, None)


def test_the_summary_names_each_forced_element_once(tmp_path):
    row = _run_shim(tmp_path, REAL_BWRAP_ARGV, "off:core.bst")
    assert forced_auth_summary([row, row], "off:core.bst", {}) == [
        "Jobserver auth: core.bst forced to off by --jobserver-auth-override"
    ]


def test_an_unmatched_glob_is_warned_exactly_once(tmp_path):
    row = _run_shim(tmp_path, REAL_BWRAP_ARGV, "off:giant.bst;fd:giant.bst,core.bst")
    lines = forced_auth_summary([row, row], "off:giant.bst;fd:giant.bst,core.bst", {})
    warnings = [line for line in lines if "giant.bst" in line]
    assert warnings == ["Warning: --jobserver-auth-override glob 'giant.bst' matched no element in this build"]


def test_an_annotation_on_an_element_that_never_ran_is_warned(tmp_path):
    row = _run_shim(tmp_path, REAL_BWRAP_ARGV)
    lines = forced_auth_summary([row], None, {"gone.bst": "off"})
    assert lines == ["Warning: gone.bst's jobserver-auth annotation names an element this build never ran"]


def test_an_out_of_four_annotation_is_warned_not_forced(tmp_path):
    row = _run_shim(tmp_path, REAL_BWRAP_ARGV, annotations={"core.bst": "keep"})
    assert _forced(row) == (None, None)
    assert forced_auth_summary([row], None, {"core.bst": "keep"}) == [
        "Warning: core.bst annotates jobserver-auth: keep, not one of fd, fifo, flto, off; ignored"
    ]


def test_the_show_parse_keeps_an_out_of_four_style_for_the_warning():
    public = "bga:\n  jobserver-auth: keep\n"
    stdout = FIELD_SEP.join(["core.bst", "make", "{}", public, "[]", "[]"]) + RECORD_SEP
    assert _parse_jobserver_show_records(stdout)[2] == {"core.bst": "keep"}


def test_a_junctioned_annotation_that_ran_by_its_short_name_is_not_warned(tmp_path):
    public = "bga:\n  jobserver-auth: off\n"
    stdout = FIELD_SEP.join(["toolchain.bst:core.bst", "make", "{}", public, "[]", "[]"]) + RECORD_SEP
    auth_map = _parse_jobserver_show_records(stdout)[2]
    row = _run_shim(tmp_path, REAL_BWRAP_ARGV, annotations=auth_map)
    assert _forced(row) == ("off", "annotation")
    assert forced_auth_summary([row], None, auth_map) == [
        "Jobserver auth: core.bst forced to off by its public: annotation"
    ]
