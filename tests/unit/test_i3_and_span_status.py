"""UX-60 (`I3`) and UX-62 (per-span terminal status).

**`I3`** — `T∞,observed >= max(observed task duration)` — is stated in the
spec and was implemented nowhere, which is why `UX-53` could change the
per-element duration definition with no check noticing. It holds
trivially under the current definition, and that is the point: it is the
guard that would catch a future definition which stops holding.

**Per-span status** was known at extraction and discarded. `UX-54`
recorded failure at the *run* level, which was the right scope for the
hazard it fixed, and left two things unanswerable: which of an element's
attempts failed, and whether a span's duration was useful work or work
thrown away. Attribution deliberately still counts a failed attempt as
`EXECUTION_ON_CHAIN` — moving it changes `I4`'s identity, a decision with
a proof obligation rather than a re-bucketing — so the report states the
waste instead of silently reclassifying it.
"""
from bga.ingest.models import NormalizedTask, TaskKey, TaskKind, TaskSpan
from bga.validation.invariants import compute_confidence


def _task(uid, dur_us, status=None):
    return NormalizedTask(
        task_key=TaskKey(element_uid=uid, task_kind=TaskKind.BUILD, phase="EXECUTION"),
        ready_us=0, start_us=0, finish_us=dur_us, status=status,
    )


def _confidence(tasks, floors):
    conf, violations = compute_confidence(
        normalized_tasks=tasks, run_context=None, trace=None, graph=None,
        violations=[], attribution_segments=[], graph_analysis={},
        attribution={}, floors=floors,
    )
    return conf, violations


# --- I3 ------------------------------------------------------------------


def test_i3_fires_when_the_floor_is_shorter_than_one_task():
    """A floor below a single observed task claims a schedule that cannot
    exist: no amount of capacity makes one task finish sooner than it
    did."""
    _, violations = _confidence([_task("a.bst", 10_000_000)],
                                {"t_infinity_observed": 5_000_000})

    assert [v["invariant"] for v in violations] == ["I3"]
    assert violations[0]["longest_task_us"] == 10_000_000


def test_i3_is_satisfied_by_the_current_definition():
    """The per-element duration *is* the longest task, and the chain
    contains that element, so this holds by construction today."""
    _, violations = _confidence([_task("a.bst", 10_000_000)],
                                {"t_infinity_observed": 10_000_000})

    assert not violations


def test_i3_does_not_fire_without_a_floor():
    _, violations = _confidence([_task("a.bst", 10_000_000)], {})

    assert not violations


def test_i3_does_not_fire_on_a_run_with_no_tasks():
    """A capture with nothing measured must not be reported as violating
    an invariant about its measurements."""
    _, violations = _confidence([], {"t_infinity_observed": 0})

    assert not violations


def _event(ph, ts, status=None):
    """The real `bst-builder` event shape the converter matches on."""
    args = {"action": "build", "element": "app.bst"}
    if status is not None:
        args["Status"] = status
    return {"name": "app.bst [build]", "cat": "bst-builder", "ph": ph,
            "ts": ts, "pid": 1, "tid": 100, "args": args}


# --- per-span status -----------------------------------------------------


def test_a_span_carries_its_terminal_status():
    span = TaskSpan(
        task_key=TaskKey(element_uid="a.bst", task_kind=TaskKind.BUILD, phase="EXECUTION"),
        ts_us=0, dur_us=1000, status="FAILURE",
    )

    assert span.failed is True


def test_an_unrecorded_status_is_not_a_failure():
    """Every capture before UX-62 omits the field, and none of them may
    be read as having failed - nor as having succeeded."""
    span = TaskSpan(
        task_key=TaskKey(element_uid="a.bst", task_kind=TaskKind.BUILD, phase="EXECUTION"),
        ts_us=0, dur_us=1000,
    )

    assert span.status is None
    assert span.failed is False


def test_failed_work_is_measured_and_published():
    tasks = [_task("a.bst", 5_000_000, status="FAILURE"),
             _task("b.bst", 3_000_000, status="SUCCESS")]

    confidence, _ = _confidence(tasks, {})

    assert confidence["failed_task_count"] == 1
    assert confidence["failed_task_us"] == 5_000_000


def test_failed_work_is_zero_when_no_status_was_recorded():
    confidence, _ = _confidence([_task("a.bst", 5_000_000)], {})

    assert confidence["failed_task_count"] == 0
    assert confidence["failed_task_us"] == 0


def test_the_converter_records_the_status_it_read():
    from tools.chrome_trace_to_bga_trace import chrome_events_to_bga_spans

    events = [
        _event("B", 1000), _event("E", 5000, status="FAILURE"),
    ]

    spans, _ = chrome_events_to_bga_spans(events)

    assert spans[0]["status"] == "FAILURE"


def test_the_converter_omits_the_status_it_could_not_read():
    """Omitted rather than defaulted - 'not recorded' and 'SUCCESS' are
    different claims, the same rule UX-45 applies to unmeasured CPU."""
    from tools.chrome_trace_to_bga_trace import chrome_events_to_bga_spans

    events = [_event("B", 1000), _event("E", 5000)]

    spans, _ = chrome_events_to_bga_spans(events)

    assert "status" not in spans[0]
