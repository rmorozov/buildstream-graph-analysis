"""UX-24 Acceptance Test #2: a real, single `bst build` invocation
captures both planes at once (`run_traced_build`'s new `wrapped_log_path`
param, reusing `tools.bst_run_wrapped.run_wrapped`'s new `env` param),
and `tools/native_trace_to_chrome_trace.py`'s combined mode correctly
correlates Plane 1's wall-clock timeline with Plane 2's own
`CLOCK_MONOTONIC` one - real, environment-gated (needs bst/bwrap/cc),
skipped rather than failed when they're not all present, matching every
other real-sandbox-dependent test in this suite.
"""
import json
import os
import shutil
import subprocess

import pytest

from tools.bst_log_to_chrome_trace import WrapperTraceConverter
from tools.bst_native_build_tracer import parse_trace_log, pair_events, run_traced_build
from tools.native_trace_to_chrome_trace import build_combined_chrome_trace, build_standalone_chrome_trace

BST_AVAILABLE = shutil.which("bst") is not None
BWRAP_AVAILABLE = shutil.which("bwrap") is not None
CC_AVAILABLE = shutil.which("cc") is not None or shutil.which("gcc") is not None


@pytest.mark.bst
@pytest.mark.skipif(
    not (BST_AVAILABLE and BWRAP_AVAILABLE and CC_AVAILABLE),
    reason="bst/bwrap/cc not all found on PATH - see docs/ingestion-pipeline.md",
)
def test_single_real_build_captures_both_planes_and_combined_trace_correlates(tmp_path):
    project_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "examples", "05-cmake-cpp-toolchain",
    )
    if not os.path.isdir(os.path.join(project_dir, "files", "toolchain", "usr", "bin")):
        pytest.skip("examples/05-cmake-cpp-toolchain's toolchain isn't staged - run stage_cpp_toolchain.sh first")

    subprocess.run(["bst", "artifact", "delete", "core.bst"], cwd=project_dir, capture_output=True)

    raw_log = str(tmp_path / "raw.log")
    wrapped_log = str(tmp_path / "wrapped.log")
    returncode = run_traced_build(
        project_dir, ["bst", "--no-colors", "build", "core.bst"], raw_log, wrapped_log_path=wrapped_log,
    )
    assert returncode == 0

    # Plane 2: the real native trace, element-tagged.
    with open(raw_log, encoding="utf-8") as f:
        plane2_records = pair_events(parse_trace_log(f.read()))
    assert any(r["element"] == "core.bst" for r in plane2_records)

    standalone_trace = build_standalone_chrome_trace(plane2_records)
    assert len(standalone_trace) > 0

    # Plane 1: the real wrapped-format log, captured from the *same*
    # invocation, converted the same way tools/bst_log_to_chrome_trace.py's
    # own CLI does.
    with open(wrapped_log, encoding="utf-8") as f:
        wrapped_text = f.read()
    assert "Executing command: bst" in wrapped_text

    converter = WrapperTraceConverter(raw_start_time_us=0)
    for line in wrapped_text.splitlines(keepends=True):
        converter.process_line_wrapped(line)
    converter.end_current_command(converter.last_known_ts)
    plane1_events = json.loads(converter.get_json())  # a bare event list - real shape, see module docstring

    # UX-24's own real correction: Plane 1 emits exactly one outer
    # bst-builder B event per element (nested sub-phases like "Running
    # commands" only affect that same open span's depth counter, they
    # never get their own trace event - confirmed against this real
    # capture, see native_trace_to_chrome_trace.py's own module
    # docstring), so that single B event is the real anchor point.
    element_b_events = [
        e for e in plane1_events
        if e.get("ph") == "B" and e.get("cat") == "bst-builder" and e.get("args", {}).get("element") == "core.bst"
    ]
    assert len(element_b_events) == 1, "expected exactly one real outer bst-builder B event for core.bst"

    combined = build_combined_chrome_trace(plane1_events, plane2_records, "core.bst")

    # Every real Plane 1 event (metadata, bst-invocation, bst-builder
    # alike) must survive into the combined output unmodified - not just
    # the bst-builder ones.
    assert len(combined) == len(plane1_events) + len(plane2_records) + len({r["element"] for r in plane2_records})
    plane1_bst_builder_count = sum(1 for e in plane1_events if e.get("cat") == "bst-builder")
    combined_bst_builder_count = sum(1 for e in combined if e.get("cat") == "bst-builder")
    plane2_event_count = sum(1 for e in combined if e.get("cat") == "native-process")
    assert combined_bst_builder_count == plane1_bst_builder_count
    assert plane2_event_count == len(plane2_records)

    # The real point of combined mode: after correlation, core.bst's own
    # Plane 2 events must land at or after Plane 1's own real build-task
    # start, and well within its own real span - not off in a disjoint
    # cluster from a clock-anchoring mismatch.
    element_start_us = element_b_events[0]["ts"]
    core_plane2_events = [
        e for e in combined
        if e.get("cat") == "native-process" and e.get("args", {}).get("element") == "core.bst"
    ]
    assert core_plane2_events
    for ev in core_plane2_events:
        assert ev["ts"] >= element_start_us - 1_000_000  # within 1s tolerance, never far off
