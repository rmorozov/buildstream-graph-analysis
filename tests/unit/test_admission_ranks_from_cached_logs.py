"""UX-1013: with no `--plan`, admission ranks by the build time
BuildStream's own cached log records (`bst artifact log`), longest
first, before falling back to graph structure - and says which ran."""

import json
import math
import os

import pytest

from tools import bst_native_build_tracer as tracer

# The shapes bst 2.8.1 printed on CI bst-examples (PR #303).
GIANT_LOG = "[00:00:01] START   giant.bst: Running commands\n[00:03:09] SUCCESS giant.bst: Running commands\n"
LEAF_LOG = "[00:00:00] START   leaf-a.bst: Running commands\n[00:00:03] SUCCESS leaf-a.bst: Running commands\n"
USAGE = "Usage: bst artifact log [OPTIONS] [ARTIFACTS]...\n"


def test_the_parser_reads_the_elapsed_stamp_of_the_elements_own_success_line():
    assert tracer.parse_cached_build_seconds(GIANT_LOG, "giant.bst") == 189.0
    assert tracer.parse_cached_build_seconds(LEAF_LOG, "leaf-a.bst") == 3.0
    assert tracer.parse_cached_build_seconds(USAGE, "giant.bst") is None


def test_a_success_line_for_another_element_is_not_this_ones():
    assert tracer.parse_cached_build_seconds(GIANT_LOG, "leaf-a.bst") is None


def test_the_longest_cached_build_ranks_first_at_equal_level():
    structural = {"leaf-a.bst": -1.0, "giant.bst": -1.0, "top.bst": 0.0, "nolog.bst": -1.0}
    logs = {"leaf-a.bst": LEAF_LOG, "giant.bst": GIANT_LOG, "top.bst": "[00:00:07] SUCCESS top.bst: Running commands"}
    plan, tried, parsed = tracer.cached_log_ranking(structural, lambda chunk: "".join(logs.get(e, "") for e in chunk))
    order = sorted(plan, key=plan.__getitem__)
    assert order == ["giant.bst", "top.bst", "leaf-a.bst", "nolog.bst"]
    assert (tried, parsed) == (4, 3)


def test_no_parsable_log_falls_back_to_structural():
    plan, tried, parsed = tracer.cached_log_ranking({"a.bst": -1.0, "b.bst": 0.0}, lambda chunk: USAGE)
    assert (plan, tried, parsed) == (None, 2, 0)


def test_one_call_reads_a_chunk_of_elements():
    calls = []
    structural = {f"e{i}.bst": 0.0 for i in range(401)} | {"leaf-a.bst": -1.0, "giant.bst": -1.0}

    def read(chunk):
        calls.append(list(chunk))
        return GIANT_LOG + LEAF_LOG if "giant.bst" in chunk else None

    plan, tried, parsed = tracer.cached_log_ranking(structural, read)
    assert len(calls) == math.ceil(len(structural) / 200) == 3
    assert (tried, parsed) == (403, 2)
    assert sorted(plan, key=plan.__getitem__)[:2] == ["giant.bst", "leaf-a.bst"]


def _run(tmp_path, monkeypatch, logs):
    monkeypatch.setenv("BGA_ADMISSION", "1")
    monkeypatch.setattr(tracer, "compile_hook", lambda d: None)
    monkeypatch.setattr(tracer, "install_bwrap_shim", lambda d: "/usr/bin/bwrap")
    monkeypatch.setattr(tracer, "write_bwrap_shim", lambda d: os.path.join(d, "bwrap"))
    monkeypatch.setattr(tracer, "probe_bwrap_shim", lambda p: None)
    monkeypatch.setattr(
        tracer, "read_cached_build_log", lambda argv, project_dir: "".join(logs.get(e, "") for e in argv[3:]) or None
    )
    monkeypatch.setattr(
        tracer.subprocess, "Popen", lambda cmd, cwd=None, env=None, **kw: type("P", (), {"wait": lambda self: 0})()
    )
    project = tmp_path / "proj"
    project.mkdir()
    status_path = str(tmp_path / "report.json.admission_status.json")
    tracer.run_traced_build(
        str(project),
        ["bst", "build", "all.bst"],
        str(tmp_path / "trace.log"),
        jobserver=4,
        element_kinds={"leaf-a.bst": "cmake", "giant.bst": "cmake"},
        element_deps={"leaf-a.bst": [], "giant.bst": []},
        admission_status_path=status_path,
    )
    with open(status_path, encoding="utf-8") as handle:
        return json.load(handle)["ranking_source"]


@pytest.mark.parametrize(
    ("logs", "source", "said"),
    [
        ({"giant.bst": GIANT_LOG}, "cached-logs", "cached-logs (1 of 2 parsed) | first: giant.bst, leaf-a.bst"),
        ({}, "structural", "structural (cached logs: 0 of 2 parsed)"),
    ],
)
def test_the_report_names_the_source_that_ran(tmp_path, monkeypatch, capsys, logs, source, said):
    assert _run(tmp_path, monkeypatch, logs) == source
    assert f"admission ranking: {said}" in capsys.readouterr().err
