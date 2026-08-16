"""Tests for tools/bst_native_build_tracer.py's trace-log parsing/
pairing/aggregation logic - all pure functions, no bwrap/bst/compiler
dependency (those are exercised separately by the real, environment-
gated end-to-end test below). See docs/scenarios/UX-11-native-build-
system-profiler-tool.md's Deep Experiment Findings for the real raw
trace shape this is modeled on (119 real lines from one element build,
including four cc1plus processes starting within 5ms of each other
under a real -j4 build - reproduced synthetically below as the
regression fixture for compute_max_concurrency).
"""
import os
import shutil
import subprocess

import pytest

from tools.bst_native_build_tracer import (
    STATIC_BINARY_DISCLAIMER,
    compute_max_concurrency,
    pair_events,
    parse_trace_log,
    summarize,
)

BST_AVAILABLE = shutil.which("bst") is not None
BWRAP_AVAILABLE = shutil.which("bwrap") is not None
CC_AVAILABLE = shutil.which("cc") is not None or shutil.which("gcc") is not None


# --- parse_trace_log -----------------------------------------------------

def test_parse_matches_start_and_end_lines():
    text = (
        "START pid=100 ppid=1 ts=10.000000000 cmd=cmake --build .\n"
        "END pid=100 ppid=1 ts=12.500000000 cmd=cmake --build .\n"
    )
    events = parse_trace_log(text)

    assert len(events) == 2
    assert events[0] == {"event": "START", "pid": 100, "ppid": 1, "ts": 10.0, "cmd": "cmake --build ."}
    assert events[1]["event"] == "END"


def test_parse_skips_malformed_and_unrelated_lines():
    text = (
        "START pid=100 ppid=1 ts=10.0 cmd=make\n"
        "this is unrelated stderr noise that ended up in the same file\n"
        "START pid=bogus ppid=1 ts=oops cmd=broken\n"
        "END pid=100 ppid=1 ts=11.0 cmd=make\n"
    )
    events = parse_trace_log(text)

    assert len(events) == 2
    assert all(e["pid"] == 100 for e in events)


def test_parse_handles_cmd_containing_spaces_and_trailing_newlines():
    text = "START pid=5 ppid=1 ts=1.0 cmd=sh -c echo hi there\n"
    events = parse_trace_log(text)

    assert events[0]["cmd"] == "sh -c echo hi there"


def test_parse_empty_text():
    assert parse_trace_log("") == []


# --- pair_events -----------------------------------------------------------

def test_pair_events_matches_start_and_end_by_pid():
    events = [
        {"event": "START", "pid": 1, "ppid": 0, "ts": 0.0, "cmd": "sh"},
        {"event": "END", "pid": 1, "ppid": 0, "ts": 5.0, "cmd": "sh"},
    ]
    records = pair_events(events)

    assert len(records) == 1
    assert records[0]["duration_s"] == 5.0
    assert records[0]["open"] is False


def test_pair_events_reports_unmatched_start_as_open():
    """A process killed by a signal, or still running when the trace was
    captured - no destructor fires, so no END line exists. Must be
    reported honestly (open=True, duration_s=None), not fabricated."""
    events = [{"event": "START", "pid": 7, "ppid": 0, "ts": 0.0, "cmd": "gcc"}]
    records = pair_events(events)

    assert len(records) == 1
    assert records[0]["open"] is True
    assert records[0]["duration_s"] is None
    assert records[0]["end_ts"] is None


def test_pair_events_handles_pid_reuse_via_fifo_ordering():
    """bwrap's --unshare-pid namespace reuses small pids quickly once a
    process exits - two separate, non-overlapping processes with the
    same pid must each get their own correctly-paired record."""
    events = [
        {"event": "START", "pid": 3, "ppid": 1, "ts": 0.0, "cmd": "first"},
        {"event": "END", "pid": 3, "ppid": 1, "ts": 1.0, "cmd": "first"},
        {"event": "START", "pid": 3, "ppid": 1, "ts": 2.0, "cmd": "second"},
        {"event": "END", "pid": 3, "ppid": 1, "ts": 3.0, "cmd": "second"},
    ]
    records = pair_events(events)

    assert len(records) == 2
    assert {r["cmd"] for r in records} == {"first", "second"}
    first = next(r for r in records if r["cmd"] == "first")
    second = next(r for r in records if r["cmd"] == "second")
    assert first["duration_s"] == 1.0
    assert second["duration_s"] == 1.0


def test_pair_events_ignores_end_with_no_matching_start():
    """A truncated log (e.g. this tool started capturing mid-build) -
    an orphan END must not crash or fabricate a record."""
    events = [{"event": "END", "pid": 99, "ppid": 1, "ts": 1.0, "cmd": "x"}]
    assert pair_events(events) == []


def test_pair_events_sorted_by_start_ts():
    events = [
        {"event": "START", "pid": 2, "ppid": 1, "ts": 5.0, "cmd": "b"},
        {"event": "END", "pid": 2, "ppid": 1, "ts": 6.0, "cmd": "b"},
        {"event": "START", "pid": 1, "ppid": 1, "ts": 1.0, "cmd": "a"},
        {"event": "END", "pid": 1, "ppid": 1, "ts": 2.0, "cmd": "a"},
    ]
    records = pair_events(events)

    assert [r["cmd"] for r in records] == ["a", "b"]


# --- compute_max_concurrency ------------------------------------------------

def test_max_concurrency_serial_processes_is_one():
    records = [
        {"start_ts": 0.0, "end_ts": 1.0, "open": False},
        {"start_ts": 1.0, "end_ts": 2.0, "open": False},
    ]
    assert compute_max_concurrency(records) == 1


def test_max_concurrency_four_overlapping_processes():
    """Reproduces the real shape UX-11's Deep Experiment observed: four
    cc1plus invocations starting within 5ms of each other under a real
    `-j4` build, all genuinely overlapping."""
    records = [
        {"start_ts": 0.0000, "end_ts": 1.0, "open": False},
        {"start_ts": 0.0001, "end_ts": 1.0, "open": False},
        {"start_ts": 0.0002, "end_ts": 1.0, "open": False},
        {"start_ts": 0.0003, "end_ts": 1.0, "open": False},
    ]
    assert compute_max_concurrency(records) == 4


def test_max_concurrency_excludes_open_records_entirely():
    """Regression: an earlier version of this function extended an open
    (no observed exit) record all the way to the trace's last known
    timestamp - against a real build, every open record turned out to be
    a quick-exiting `sh -c` wrapper (see compute_max_concurrency's own
    docstring), and that heuristic inflated a real -j4 build's
    concurrency to an implausible 24. Open records must not affect this
    figure at all."""
    records = [
        {"start_ts": 0.0, "end_ts": 10.0, "open": False},
        {"start_ts": 5.0, "end_ts": None, "open": True},
        {"start_ts": 5.1, "end_ts": None, "open": True},
        {"start_ts": 5.2, "end_ts": None, "open": True},
    ]
    assert compute_max_concurrency(records) == 1


def test_max_concurrency_empty():
    assert compute_max_concurrency([]) == 0


def test_max_concurrency_touching_intervals_do_not_overlap():
    """One process's END at ts=T and another's START at exactly ts=T
    must not be double-counted as concurrent - matches real process
    semantics (the first has already exited)."""
    records = [
        {"start_ts": 0.0, "end_ts": 1.0, "open": False},
        {"start_ts": 1.0, "end_ts": 2.0, "open": False},
    ]
    assert compute_max_concurrency(records) == 1


# --- summarize ---------------------------------------------------------

def test_summarize_counts_by_binary_from_full_cmd():
    records = [
        {"pid": 1, "cmd": "/usr/bin/cc1plus -quiet a.cpp", "start_ts": 0.0, "end_ts": 1.0, "open": False},
        {"pid": 2, "cmd": "/usr/bin/cc1plus -quiet b.cpp", "start_ts": 0.0, "end_ts": 1.0, "open": False},
        {"pid": 3, "cmd": "make -j4", "start_ts": 0.0, "end_ts": 1.0, "open": False},
    ]
    report = summarize(records)

    assert report["by_binary"] == {"cc1plus": 2, "make": 1}
    assert report["process_count"] == 3
    assert report["matched_count"] == 3
    assert report["open_count"] == 0


def test_summarize_always_includes_static_binary_disclaimer():
    """The one non-negotiable output requirement (UX-11's Risk 2, real
    and confirmed - this tool cannot detect a statically-linked process
    it never saw): the disclaimer must be present even for an empty
    trace, so a user can't mistake "0 processes traced" for "genuinely
    nothing ran"."""
    assert summarize([])["static_binary_disclaimer"] == STATIC_BINARY_DISCLAIMER
    assert STATIC_BINARY_DISCLAIMER in summarize([])["static_binary_disclaimer"]


def test_summarize_empty_records():
    report = summarize([])

    assert report["process_count"] == 0
    assert report["max_concurrency"] == 0
    assert report["wall_span_s"] is None


def test_summarize_wall_span_covers_open_records():
    records = [
        {"pid": 1, "cmd": "a", "start_ts": 0.0, "end_ts": 5.0, "open": False},
        {"pid": 2, "cmd": "b", "start_ts": 3.0, "end_ts": None, "open": True},
    ]
    report = summarize(records)

    assert report["wall_span_s"] == 5.0  # max(end_ts=5.0, start_ts=3.0 for the open one)


# --- Real end-to-end: run_traced_build against a real bst build ------------

@pytest.mark.skipif(
    not (BST_AVAILABLE and BWRAP_AVAILABLE and CC_AVAILABLE),
    reason="bst/bwrap/cc not all found on PATH - see docs/ingestion-pipeline.md",
)
def test_run_traced_build_captures_real_process_lifecycle(tmp_path):
    """Real, live smoke test of the full mechanism against this repo's
    own examples/05-cmake-cpp-toolchain fixture - the same real target
    UX-11's Deep Experiment used to get its first 119-line trace.
    Skipped (not failed) when bst/bwrap/cc aren't all present, matching
    every other real-sandbox-dependent test in this suite."""
    from tools.bst_native_build_tracer import run_traced_build

    project_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "examples", "05-cmake-cpp-toolchain",
    )
    if not os.path.isdir(os.path.join(project_dir, "files", "toolchain", "usr", "bin")):
        pytest.skip("examples/05-cmake-cpp-toolchain's toolchain isn't staged - run stage_cpp_toolchain.sh first")

    subprocess.run(["bst", "artifact", "delete", "core.bst"], cwd=project_dir, capture_output=True)

    raw_log = str(tmp_path / "trace.log")
    returncode = run_traced_build(project_dir, ["bst", "--no-colors", "build", "core.bst"], raw_log)

    assert returncode == 0
    with open(raw_log, encoding="utf-8") as f:
        events = parse_trace_log(f.read())
    assert len(events) > 0, "expected at least one real traced process from a real cmake/make/gcc build"
    records = pair_events(events)
    report = summarize(records)
    assert report["process_count"] > 0
    assert any(name in report["by_binary"] for name in ("cmake", "make", "cc1plus", "c++", "as", "ld"))
