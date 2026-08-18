"""Tests for tools/bst_native_build_tracer.py's trace-log parsing/
pairing/aggregation logic - all pure functions, no bwrap/bst/compiler
dependency (those are exercised separately by the real, environment-
gated end-to-end test below). See docs/backlog/scenarios/UX-0011-native-build-
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
    detect_redundant_operations,
    normalize_cmd_signature,
    pair_events,
    parse_trace_log,
    summarize,
)

BST_AVAILABLE = shutil.which("bst") is not None
BWRAP_AVAILABLE = shutil.which("bwrap") is not None
CC_AVAILABLE = shutil.which("cc") is not None or shutil.which("gcc") is not None


def _event(event, pid, ppid, ts, cmd, element="unknown"):
    return {"event": event, "pid": pid, "ppid": ppid, "ts": ts, "element": element, "cmd": cmd}


# --- parse_trace_log -----------------------------------------------------

def test_parse_matches_start_and_end_lines():
    text = (
        "START pid=100 ppid=1 ts=10.000000000 cmd=cmake --build .\n"
        "END pid=100 ppid=1 ts=12.500000000 cmd=cmake --build .\n"
    )
    events = parse_trace_log(text)

    assert len(events) == 2
    assert events[0] == {
        "event": "START", "pid": 100, "ppid": 1, "ts": 10.0, "element": "unknown",
        # UX-56: additive, and None here on purpose - a line with no
        # `inv=` predates the sandbox id and must not be given a
        # fabricated one.
        "invocation": None,
        "cmd": "cmake --build .",
    }
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
        _event("START", 1, 0, 0.0, "sh"),
        _event("END", 1, 0, 5.0, "sh"),
    ]
    records = pair_events(events)

    assert len(records) == 1
    assert records[0]["duration_s"] == 5.0
    assert records[0]["open"] is False


def test_pair_events_reports_unmatched_start_as_open():
    """A process killed by a signal, or still running when the trace was
    captured - no destructor fires, so no END line exists. Must be
    reported honestly (open=True, duration_s=None), not fabricated."""
    events = [_event("START", 7, 0, 0.0, "gcc")]
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
        _event("START", 3, 1, 0.0, "first"),
        _event("END", 3, 1, 1.0, "first"),
        _event("START", 3, 1, 2.0, "second"),
        _event("END", 3, 1, 3.0, "second"),
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
    events = [_event("END", 99, 1, 1.0, "x")]
    assert pair_events(events) == []


def test_pair_events_sorted_by_start_ts():
    events = [
        _event("START", 2, 1, 5.0, "b"),
        _event("END", 2, 1, 6.0, "b"),
        _event("START", 1, 1, 1.0, "a"),
        _event("END", 1, 1, 2.0, "a"),
    ]
    records = pair_events(events)

    assert [r["cmd"] for r in records] == ["a", "b"]


def test_pair_events_does_not_cross_pair_same_pid_across_different_elements():
    """UX-23 regression: each element gets its own independent
    --unshare-pid namespace, so the same small pid number (e.g. 2) is
    reused across every element's own sandbox and refers to a different
    real process each time. A START in core.bst's own sandbox must never
    pair with an END from lib-a.bst's sandbox just because they share a
    pid and happen to overlap in time - keying on pid alone (UX-11's
    original single-element design) would get this wrong."""
    events = [
        _event("START", 2, 1, 0.0, "cmake", element="core.bst"),
        _event("START", 2, 1, 0.5, "cmake", element="lib-a.bst"),  # same pid, different element
        _event("END", 2, 1, 10.0, "cmake", element="lib-a.bst"),  # lib-a's own process exits first
        _event("END", 2, 1, 20.0, "cmake", element="core.bst"),
    ]
    records = pair_events(events)

    assert len(records) == 2
    core_record = next(r for r in records if r["element"] == "core.bst")
    lib_a_record = next(r for r in records if r["element"] == "lib-a.bst")
    assert core_record["start_ts"] == 0.0 and core_record["end_ts"] == 20.0
    assert lib_a_record["start_ts"] == 0.5 and lib_a_record["end_ts"] == 10.0


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

def _record(pid, cmd, start_ts, end_ts, open_=False, element="unknown"):
    return {
        # UX-73: `ppid` 0 rather than 1 - a record with pid 2 and ppid 1
        # is the sandbox's own top-level command block, which is excluded
        # from redundancy findings. These fixtures are ordinary traced
        # processes and the value was arbitrary.
        "pid": pid, "ppid": 0, "element": element, "cmd": cmd,
        "start_ts": start_ts, "end_ts": end_ts,
        "duration_s": (end_ts - start_ts) if end_ts is not None else None,
        "open": open_,
    }


def test_summarize_counts_by_binary_from_full_cmd():
    records = [
        _record(1, "/usr/bin/cc1plus -quiet a.cpp", 0.0, 1.0),
        _record(2, "/usr/bin/cc1plus -quiet b.cpp", 0.0, 1.0),
        _record(3, "make -j4", 0.0, 1.0),
    ]
    report = summarize(records)

    assert report["by_binary"] == {"cc1plus": 2, "make": 1}
    assert report["process_count"] == 3
    assert report["matched_count"] == 3
    assert report["open_count"] == 0


def test_summarize_counts_by_element():
    records = [
        _record(1, "cc1plus a.cpp", 0.0, 1.0, element="core.bst"),
        _record(2, "cc1plus b.cpp", 0.0, 1.0, element="core.bst"),
        _record(3, "cc1plus c.cpp", 0.0, 1.0, element="lib-a.bst"),
    ]
    report = summarize(records)

    assert report["by_element"] == {"core.bst": 2, "lib-a.bst": 1}


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
        _record(1, "a", 0.0, 5.0),
        _record(2, "b", 3.0, None, open_=True),
    ]
    report = summarize(records)

    assert report["wall_span_s"] == 5.0  # max(end_ts=5.0, start_ts=3.0 for the open one)


# --- normalize_cmd_signature ---------------------------------------------

def test_normalize_strips_per_element_build_root():
    """The real, largest source of spurious per-element uniqueness for
    an otherwise identical operation - each element's own absolute
    sandbox path."""
    cmd_core = "/buildstream/cmake-cpp-toolchain-example/core.bst/_builddir/x.o"
    cmd_lib_a = "/buildstream/cmake-cpp-toolchain-example/lib-a.bst/_builddir/x.o"

    assert normalize_cmd_signature(cmd_core) == normalize_cmd_signature(cmd_lib_a)


def test_normalize_strips_gcc_temp_filenames():
    assert normalize_cmd_signature("gcc -o /tmp/ccAbC123.s") == normalize_cmd_signature("gcc -o /tmp/ccXyZ789.s")


def test_normalize_strips_cmake_try_compile_scratch_dir():
    """The real, confirmed pattern behind UX-23's own CMakeCXXCompilerABI
    finding: CMake's own randomly-suffixed try-compile directory name."""
    cmd_1 = "cmake --build CMakeFiles/cmTC_9f1fb.dir/CMakeCXXCompilerABI.cpp.o"
    cmd_2 = "cmake --build CMakeFiles/cmTC_ca49d.dir/CMakeCXXCompilerABI.cpp.o"

    assert normalize_cmd_signature(cmd_1) == normalize_cmd_signature(cmd_2)


def test_normalize_does_not_conflate_genuinely_different_operations():
    assert normalize_cmd_signature("cc1plus a.cpp") != normalize_cmd_signature("cc1plus b.cpp")


# --- detect_redundant_operations ------------------------------------------

def test_detect_redundant_flags_signature_repeated_across_elements():
    records = [
        # UX-37: the real shape of CMake's own ABI probe, taken from a
        # real trace. (This fixture previously used a synthetic
        # `cmake --build ...` command, which UX-37's build-driver filter
        # now correctly excludes - an element's own build driver is
        # identical across elements by construction and is not
        # redundancy. The probe itself, which this test is about, is.)
        _record(1, "/usr/bin/c++ -o CMakeFiles/cmTC_aaaaa.dir/CMakeCXXCompilerABI.cpp.o -c abi.cpp", 0.0, 0.1, element="core.bst"),
        _record(2, "/usr/bin/c++ -o CMakeFiles/cmTC_bbbbb.dir/CMakeCXXCompilerABI.cpp.o -c abi.cpp", 1.0, 1.1, element="lib-a.bst"),
        _record(3, "/usr/bin/c++ -o CMakeFiles/cmTC_ccccc.dir/CMakeCXXCompilerABI.cpp.o -c abi.cpp", 2.0, 2.1, element="lib-b.bst"),
    ]
    findings, _coverage = detect_redundant_operations(records)

    assert len(findings) == 1
    assert findings[0]["elements"] == ["core.bst", "lib-a.bst", "lib-b.bst"]
    assert findings[0]["occurrence_count"] == 3
    assert findings[0]["total_duration_s"] == pytest.approx(0.3)


def test_detect_redundant_requires_two_distinct_elements_not_just_occurrences():
    """Two occurrences of the same normalized signature *within the same
    element* (e.g. a real, legitimate repeated invocation) is not
    cross-element redundancy - must not be flagged."""
    records = [
        _record(1, "cc1plus a.cpp", 0.0, 0.1, element="core.bst"),
        _record(2, "cc1plus a.cpp", 1.0, 1.1, element="core.bst"),
    ]
    assert detect_redundant_operations(records)[0] == []


def test_detect_redundant_excludes_unknown_element():
    """A trace with no real element attribution (a raw log captured
    before element-tagging existed, or a standalone single-element
    capture) must never claim cross-element redundancy it can't
    actually attribute."""
    records = [
        _record(1, "cc1plus a.cpp", 0.0, 0.1, element="unknown"),
        _record(2, "cc1plus a.cpp", 1.0, 1.1, element="unknown"),
    ]
    assert detect_redundant_operations(records)[0] == []


def test_detect_redundant_excludes_open_records():
    records = [
        _record(1, "cc1plus a.cpp", 0.0, None, open_=True, element="core.bst"),
        _record(2, "cc1plus a.cpp", 1.0, None, open_=True, element="lib-a.bst"),
    ]
    assert detect_redundant_operations(records)[0] == []


def test_detect_redundant_sorted_by_total_duration_most_costly_first():
    records = [
        _record(1, "cheap_probe", 0.0, 0.1, element="core.bst"),
        _record(2, "cheap_probe", 1.0, 1.1, element="lib-a.bst"),
        _record(3, "expensive_codegen", 2.0, 32.0, element="core.bst"),
        _record(4, "expensive_codegen", 33.0, 63.0, element="lib-a.bst"),
    ]
    findings, _coverage = detect_redundant_operations(records)

    assert len(findings) == 2
    assert findings[0]["example_cmd"] == "expensive_codegen"
    assert findings[1]["example_cmd"] == "cheap_probe"


def test_summarize_includes_redundant_operations():
    records = [
        _record(1, "cc1plus a.cpp", 0.0, 1.0, element="core.bst"),
        _record(2, "cc1plus a.cpp", 1.0, 2.0, element="lib-a.bst"),
    ]
    report = summarize(records)

    assert len(report["redundant_operations"]) == 1
    assert report["redundant_operations"][0]["elements"] == ["core.bst", "lib-a.bst"]


# --- Real end-to-end: run_traced_build against a real bst build ------------

@pytest.mark.bst
@pytest.mark.skipif(
    not (BST_AVAILABLE and BWRAP_AVAILABLE and CC_AVAILABLE),
    reason="bst/bwrap/cc not all found on PATH - see docs/spec/ingestion-pipeline.md",
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
