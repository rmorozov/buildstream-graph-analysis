"""Tests for tools/chrome_trace_to_bga_trace.py - the general (not
fixture-specific) Chrome-Trace-to-trace/v9 adapter built alongside P4-10.

Unlike tests/fixtures/synthetic_multi_subproject/adapter.py (which
recovers task kind from the synthetic model's own invented phase-message
text), this tool reads the `action` field tools/bst_log_to_chrome_trace.py
now records directly in each bst-builder event's args - BuildStream's own
real action word, confirmed against a real, installed BuildStream 2.7.0
build (see docs/ingestion-pipeline.md).
"""
from tools.chrome_trace_to_bga_trace import (
    ACTION_TO_KIND,
    KIND_TO_RESOURCE,
    chrome_events_to_bga_spans,
    invocation_wall_clock,
)


def _builder_event(ph, ts, tid, action=None, element=None, status=None, message=None):
    args = {}
    if action is not None:
        args["action"] = action
    if element is not None:
        args["element"] = element
    if status is not None:
        args["Status"] = status
    if message is not None:
        args["Message"] = message
    return {
        "name": f"{element} [{message or action}]",
        "cat": "bst-builder",
        "ph": ph,
        "ts": ts,
        "pid": 1,
        "tid": tid,
        "args": args,
    }


def test_single_build_task_converts_to_one_span():
    events = [
        _builder_event("B", 1000, 100, action="build", element="app.bst"),
        _builder_event("E", 5000, 100, action="build", element="app.bst", status="SUCCESS", message="log"),
    ]
    spans, dropped = chrome_events_to_bga_spans(events)

    assert dropped == []
    assert spans == [{
        "task_key": "app.bst|BUILD|BUILD|0",
        "ts_us": 1000,
        "dur_us": 4000,
        "resources": ["PROCESS"],
        "primary_resource": "PROCESS",
    }]


def test_every_task_kind_maps_to_the_right_resource():
    events = []
    ts = 0
    for action in ("track", "fetch", "pull", "build", "push"):
        events.append(_builder_event("B", ts, ts + 1, action=action, element="elem.bst"))
        events.append(_builder_event("E", ts + 100, ts + 1, action=action, element="elem.bst", status="SUCCESS"))
        ts += 1000

    spans, dropped = chrome_events_to_bga_spans(events)
    assert dropped == []
    by_kind = {s["task_key"].split("|")[1]: s for s in spans}
    assert by_kind["TRACK"]["primary_resource"] == "DOWNLOAD"
    assert by_kind["FETCH"]["primary_resource"] == "DOWNLOAD"
    assert by_kind["PULL"]["primary_resource"] == "DOWNLOAD"
    assert by_kind["BUILD"]["primary_resource"] == "PROCESS"
    assert by_kind["PUSH"]["primary_resource"] == "UPLOAD"


def test_unrecognized_action_is_dropped_not_crashed():
    """BuildStream's own top-level "main:core activity" pseudo-bracket
    (confirmed real, see docs/ingestion-pipeline.md) has no TaskKind
    equivalent - must be skipped, not misclassified or crash."""
    events = [
        _builder_event("B", 0, 1, action="main", element="core activity"),
        _builder_event("E", 100, 1, action="main", element="core activity", status="SUCCESS"),
    ]
    spans, dropped = chrome_events_to_bga_spans(events)

    assert spans == []
    assert len(dropped) == 1
    assert "main" in dropped[0]


def test_repeated_element_kind_gets_sequential_attempt_numbers():
    """No explicit attempt counter exists in the log - a real re-invocation
    (e.g. a CI retry) is only observable as the same (element, kind)
    recurring; ordinal chronological position is the only real signal."""
    events = [
        _builder_event("B", 0, 1, action="build", element="flaky.bst"),
        _builder_event("E", 100, 1, action="build", element="flaky.bst", status="FAILURE"),
        _builder_event("B", 200, 2, action="build", element="flaky.bst"),
        _builder_event("E", 400, 2, action="build", element="flaky.bst", status="SUCCESS"),
    ]
    spans, dropped = chrome_events_to_bga_spans(events)

    assert dropped == []
    task_keys = sorted(s["task_key"] for s in spans)
    assert task_keys == ["flaky.bst|BUILD|BUILD|0", "flaky.bst|BUILD|BUILD|1"]


def test_non_builder_events_are_ignored():
    events = [
        {"cat": "bst-invocation", "ph": "B", "ts": 0, "pid": 1, "tid": 1, "name": "bst build"},
        {"cat": "wrapper", "ph": "B", "ts": 0, "pid": 1, "tid": 1, "name": "echo hi"},
        {"ph": "M", "name": "process_name"},
    ]
    spans, dropped = chrome_events_to_bga_spans(events)
    assert spans == []
    assert dropped == []


def test_invocation_wall_clock_derived_from_bst_invocation_span():
    events = [
        {"cat": "bst-invocation", "ph": "B", "ts": 1000},
        {"cat": "bst-invocation", "ph": "E", "ts": 9000},
    ]
    start, end = invocation_wall_clock(events)
    assert (start, end) == (1000, 9000)


def test_invocation_wall_clock_none_when_absent():
    assert invocation_wall_clock([{"cat": "bst-builder", "ph": "B", "ts": 0}]) == (None, None)


def test_action_to_kind_and_resource_maps_cover_every_real_task_kind():
    """Regression guard: every TaskKind value used by real BuildStream
    action words (i.e. everything except OTHER, which has no real bst
    action word) must be represented in both lookup tables."""
    assert set(ACTION_TO_KIND.values()) == {"TRACK", "FETCH", "PULL", "BUILD", "PUSH"}
    assert set(KIND_TO_RESOURCE.keys()) == set(ACTION_TO_KIND.values())
