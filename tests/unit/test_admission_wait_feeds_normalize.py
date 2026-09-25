"""UX-1005 track C: `admission_wait_by_element` (`tools.jobserver.
ledger`) has to reach `normalize_trace` for a real analysis to shrink
the BUILD span it names, not just `subtract_admission_wait` in
isolation (`test_admission_wait_leaves_the_build_span.py`). This guards
the wiring itself - remove the call `normalize_trace` makes and the
wait never leaves the span."""
from bga.ingest.models import Graph, Trace
from bga.normalize.timestamps import (
    admission_wait_by_element_from_ledger,
    normalize_trace,
)
from tests.unit.test_normalize import _span


def test_a_recorded_wait_shrinks_the_build_span_through_normalize_trace():
    spans = [_span("a.bst", 1_000_000, 500_000)]
    trace = Trace(spans=spans)
    graph = Graph(elements=[], dependencies=[])

    without = normalize_trace(trace, graph, epsilon_us=1000)[0]
    with_wait = normalize_trace(
        trace, graph, epsilon_us=1000,
        admission_wait_by_element={"a.bst": 100_000})[0]

    assert without[0].finish_us == with_wait[0].finish_us, "finish is immutable"
    assert with_wait[0].start_us > without[0].start_us, (
        "the admission wait must move the BUILD span's start later")


def test_no_wait_recorded_is_byte_identical_to_before_track_c():
    spans = [_span("a.bst", 1_000_000, 500_000)]
    trace = Trace(spans=spans)
    graph = Graph(elements=[], dependencies=[])

    assert normalize_trace(trace, graph, epsilon_us=1000) == \
        normalize_trace(trace, graph, epsilon_us=1000, admission_wait_by_element=None)


def test_admission_wait_by_element_from_ledger_sums_by_element():
    rows = [
        {"event": "admission_wait", "element": "a.bst", "wait_us": 100},
        {"event": "admission_wait", "element": "a.bst", "wait_us": 50},
        {"event": "admission_wait", "element": "b.bst", "wait_us": 20},
        {"event": "grant", "element": "a.bst", "tokens": 1},
    ]
    assert admission_wait_by_element_from_ledger(rows) == {"a.bst": 150, "b.bst": 20}
