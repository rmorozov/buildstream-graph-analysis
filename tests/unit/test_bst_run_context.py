"""Tests for tools/bst_run_context.py (P4-09): run-context.json producer
from a real BuildStream invocation's log.
"""
import json

from tools.bst_run_context import build_run_context

RAW_LOG = """\
    Maximum Fetch Tasks:     7
    Maximum Build Tasks:     3
    Maximum Push Tasks:      2
[--:--:--][4a9059d4][   build:base.bst] START   base/4a9059d4-build.log
[00:00:05][4a9059d4][   build:base.bst] SUCCESS base/4a9059d4-build.log
"""


def test_build_run_context_reads_scheduler_config_from_header(tmp_path):
    log = tmp_path / "raw.log"
    log.write_text(RAW_LOG)

    run_context = build_run_context(str(log), log_format="raw", start_time="2026-08-14T00:00:00+00:00")

    assert run_context["resource_capacities"] == {"PROCESS": 3, "DOWNLOAD": 7, "UPLOAD": 2}
    assert run_context["max_jobs"] == 3
    # cpu_accounting is deliberately omitted (P1-33): `builders` is a
    # job-slot scheduling parameter, not a measured CPU count.
    assert "cpu_accounting" not in run_context


def test_build_run_context_derives_wall_clock_from_invocation_span(tmp_path):
    log = tmp_path / "raw.log"
    log.write_text(RAW_LOG)

    start_time_us = 1786665600_000_000  # 2026-08-14T00:00:00+00:00
    run_context = build_run_context(str(log), log_format="raw", start_time="2026-08-14T00:00:00+00:00")

    assert run_context["wall_clock"]["start_us"] == start_time_us
    assert run_context["wall_clock"]["end_us"] == start_time_us + 5_000_000


def test_build_run_context_falls_back_to_buildstream_defaults_without_header(tmp_path):
    log = tmp_path / "raw.log"
    log.write_text(
        "[--:--:--][4a9059d4][   build:base.bst] START   base/4a9059d4-build.log\n"
        "[00:00:01][4a9059d4][   build:base.bst] SUCCESS base/4a9059d4-build.log\n"
    )

    run_context = build_run_context(str(log), log_format="raw", start_time="2026-08-14T00:00:00+00:00")

    assert run_context["resource_capacities"] == {"PROCESS": 4, "DOWNLOAD": 10, "UPLOAD": 4}


def test_build_run_context_omits_wall_clock_when_no_invocation_span(tmp_path):
    """An empty/non-bst log has nothing to derive a wall_clock from -
    must omit the field entirely (Part 4.3's provenance hierarchy: no
    silently-invented fallback), not fabricate a 0/0 span."""
    log = tmp_path / "empty.log"
    log.write_text("not a buildstream log at all\n")

    run_context = build_run_context(str(log), log_format="raw", start_time="2026-08-14T00:00:00+00:00")

    assert "wall_clock" not in run_context


def test_build_run_context_wrapped_mode(tmp_path):
    log = tmp_path / "wrapped.log"
    log.write_text(
        "[wrapper][2026-08-14 11:00:00,000] INFO: Maximum Build Tasks:     6\n"
        "[wrapper][2026-08-14 11:00:00,000] INFO: Executing command: bst build base.bst\n"
        "[wrapper][2026-08-14 11:00:00,100] INFO: "
        "[--:--:--][4a9059d4][   build:base.bst] START   base/4a9059d4-build.log\n"
        "[wrapper][2026-08-14 11:00:05,100] INFO: "
        "[00:00:05][4a9059d4][   build:base.bst] SUCCESS base/4a9059d4-build.log\n"
        "[wrapper][2026-08-14 11:00:05,200] INFO: Return code: 0\n"
    )

    run_context = build_run_context(str(log), log_format="wrapped")

    assert run_context["max_jobs"] == 6
    # wall_clock spans the bst-invocation itself (triggered by "Executing
    # command:" at 11:00:00,000 through "Return code:" at 11:00:05,200),
    # not just the one build task's own start/end.
    assert run_context["wall_clock"]["end_us"] - run_context["wall_clock"]["start_us"] == 5_200_000


def test_host_and_trace_epsilon_passed_through(tmp_path):
    log = tmp_path / "raw.log"
    log.write_text(RAW_LOG)

    run_context = build_run_context(
        str(log), log_format="raw", start_time="2026-08-14T00:00:00+00:00",
        trace_epsilon_us=25000, host="ci-runner-1",
    )

    assert run_context["trace_epsilon_us"] == 25000
    assert run_context["host"] == "ci-runner-1"


def test_output_loads_cleanly_into_bgas_own_loader(tmp_path):
    """End-to-end: the produced JSON must load via bga's real
    load_run_context, not just be valid JSON."""
    from bga.ingest.loader import load_run_context

    log = tmp_path / "raw.log"
    log.write_text(RAW_LOG)
    run_context = build_run_context(str(log), log_format="raw", start_time="2026-08-14T00:00:00+00:00")

    out_path = tmp_path / "run-context.json"
    out_path.write_text(json.dumps(run_context))

    loaded = load_run_context(out_path)
    assert loaded.max_jobs == 3
    assert loaded.resource_capacities["PROCESS"] == 3
    assert not loaded.cpu_accounting
