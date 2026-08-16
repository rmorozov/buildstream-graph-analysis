"""Tests for UX-24: tools/native_trace_to_chrome_trace.py's standalone
and combined Chrome Trace export - all pure-logic, synthetic data (the
real end-to-end capture path is exercised separately, real-sandbox-
gated, in test_dual_plane_capture.py).

Both functions return a bare event list, not {"traceEvents": [...]} -
matching tools/bst_log_to_chrome_trace.py's own real, already-in-use
output shape exactly (confirmed by reading its get_json() directly) -
an earlier draft assumed the object-wrapped shape, a real bug caught
only once the real end-to-end combined-mode test tried to actually
parse a real Plane 1 output file.
"""
import pytest

from tools.native_trace_to_chrome_trace import (
    assign_element_pids,
    build_combined_chrome_trace,
    build_standalone_chrome_trace,
    compute_clock_offset_us,
)


def _record(pid, cmd, start_ts, end_ts, open_=False, element="core.bst"):
    return {
        "pid": pid, "ppid": 1, "element": element, "cmd": cmd,
        "start_ts": start_ts, "end_ts": end_ts,
        "duration_s": (end_ts - start_ts) if end_ts is not None else None,
        "open": open_,
    }


# --- assign_element_pids --------------------------------------------------

def test_assign_element_pids_never_uses_pid_1():
    """pid: 1 is reserved for Plane 1's own "the BuildStream invocation"
    sentinel - a combined trace must never collide with it."""
    pids = assign_element_pids(["core.bst", "lib-a.bst"])
    assert 1 not in pids.values()


def test_assign_element_pids_deterministic_and_stable():
    pids_a = assign_element_pids(["lib-a.bst", "core.bst"])
    pids_b = assign_element_pids(["core.bst", "lib-a.bst"])
    assert pids_a == pids_b  # order of the input list must not matter (I11)


def test_assign_element_pids_one_per_distinct_element():
    pids = assign_element_pids(["core.bst", "core.bst", "lib-a.bst"])
    assert len(pids) == 2
    assert pids["core.bst"] != pids["lib-a.bst"]


# --- build_standalone_chrome_trace ----------------------------------------

def test_standalone_empty_records():
    assert build_standalone_chrome_trace([]) == []


def test_standalone_produces_one_process_name_event_per_element():
    records = [
        _record(1, "cc1plus a.cpp", 0.0, 1.0, element="core.bst"),
        _record(2, "cc1plus b.cpp", 0.0, 1.0, element="lib-a.bst"),
    ]
    events = build_standalone_chrome_trace(records)

    process_name_events = [e for e in events if e["ph"] == "M"]
    assert len(process_name_events) == 2
    names = {e["args"]["name"] for e in process_name_events}
    assert names == {"native: core.bst", "native: lib-a.bst"}


def test_standalone_matched_record_becomes_complete_event_with_real_duration():
    records = [_record(1, "cc1plus a.cpp", 10.0, 12.5)]
    events = build_standalone_chrome_trace(records)

    x_events = [e for e in events if e["ph"] == "X"]
    assert len(x_events) == 1
    assert x_events[0]["dur"] == pytest.approx(2.5 * 1e6)
    assert x_events[0]["tid"] == 1  # the real OS pid


def test_standalone_open_record_becomes_instant_event_not_a_fabricated_bar():
    records = [_record(1, "gcc", 10.0, None, open_=True)]
    events = build_standalone_chrome_trace(records)

    non_meta = [e for e in events if e["ph"] != "M"]
    assert len(non_meta) == 1
    assert non_meta[0]["ph"] == "i"
    assert "no observed exit" in non_meta[0]["name"]


def test_standalone_normalizes_timestamps_to_start_near_zero():
    """Plane 2's own CLOCK_MONOTONIC epoch is arbitrary and meaningless
    on its own - only relative offsets are real."""
    records = [_record(1, "a", 1000.0, 1001.0)]
    events = build_standalone_chrome_trace(records)

    x_event = next(e for e in events if e["ph"] == "X")
    assert x_event["ts"] == pytest.approx(0.0)


# --- compute_clock_offset_us -----------------------------------------------

def _plane1_element_b_event(element, ts_us):
    return {
        "name": f"{element} [build log]", "cat": "bst-builder", "ph": "B",
        "ts": ts_us, "pid": 1, "tid": 2, "args": {"action": "build", "element": element},
    }


def test_compute_offset_from_one_real_anchor_point():
    plane1_events = [_plane1_element_b_event("core.bst", 5_000_000.0)]
    plane2_records = [_record(1, "cmake", 100.0, 101.0, element="core.bst")]

    offset = compute_clock_offset_us(plane1_events, plane2_records, "core.bst")

    # plane2's own earliest ts (100.0s = 100_000_000us) + offset should
    # land exactly on plane1's real wall-clock ts (5_000_000us).
    assert 100.0 * 1e6 + offset == pytest.approx(5_000_000.0)


def test_compute_offset_raises_when_no_plane1_element_b_event_for_element():
    plane1_events = [_plane1_element_b_event("core.bst", 5_000_000.0)]
    plane2_records = [_record(1, "cmake", 100.0, 101.0, element="lib-a.bst")]

    with pytest.raises(ValueError, match="lib-a.bst"):
        compute_clock_offset_us(plane1_events, plane2_records, "lib-a.bst")


def test_compute_offset_raises_when_no_plane2_data_for_element():
    plane1_events = [_plane1_element_b_event("core.bst", 5_000_000.0)]
    plane2_records = [_record(1, "cmake", 100.0, 101.0, element="core.bst")]

    with pytest.raises(ValueError, match="lib-a.bst"):
        compute_clock_offset_us(plane1_events, plane2_records, "lib-a.bst")


def test_compute_offset_uses_earliest_plane2_start_for_the_anchor_element():
    plane1_events = [_plane1_element_b_event("core.bst", 5_000_000.0)]
    plane2_records = [
        _record(2, "make", 105.0, 106.0, element="core.bst"),
        _record(1, "cmake", 100.0, 101.0, element="core.bst"),  # earliest
    ]

    offset = compute_clock_offset_us(plane1_events, plane2_records, "core.bst")

    assert 100.0 * 1e6 + offset == pytest.approx(5_000_000.0)


# --- build_combined_chrome_trace -------------------------------------------

def test_combined_preserves_plane1_events_unmodified():
    plane1_events = [_plane1_element_b_event("core.bst", 5_000_000.0)]
    plane2_records = [_record(1, "cmake", 100.0, 101.0, element="core.bst")]

    combined = build_combined_chrome_trace(plane1_events, plane2_records, "core.bst")

    plane1_survivors = [e for e in combined if e.get("cat") == "bst-builder"]
    assert plane1_survivors == plane1_events


def test_combined_puts_plane2_events_on_the_same_timeline_as_plane1():
    """The real point of combined mode: after correlation, a Plane 2
    event for the anchor element should land at (or very near) Plane 1's
    own real build-task start - not two disjoint clusters from a
    clock-anchoring mismatch."""
    plane1_events = [_plane1_element_b_event("core.bst", 5_000_000.0)]
    plane2_records = [_record(1, "cmake", 100.0, 100.5, element="core.bst")]

    combined = build_combined_chrome_trace(plane1_events, plane2_records, "core.bst")

    plane2_event = next(e for e in combined if e.get("cat") == "native-process")
    assert plane2_event["ts"] == pytest.approx(5_000_000.0)


def test_combined_never_collides_plane2_pids_with_plane1s_pid_1():
    plane1_events = [_plane1_element_b_event("core.bst", 5_000_000.0)]
    plane2_records = [_record(1, "cmake", 100.0, 100.5, element="core.bst")]

    combined = build_combined_chrome_trace(plane1_events, plane2_records, "core.bst")

    plane2_event = next(e for e in combined if e.get("cat") == "native-process")
    assert plane2_event["pid"] != 1
