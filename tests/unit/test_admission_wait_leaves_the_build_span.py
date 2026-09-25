"""UX-1005 track B: `subtract_admission_wait` moves a BUILD span's start
later by the shim's own recorded wait, finish held fixed - this
module's own contract (`bga/normalize/timestamps.py`'s docstring)."""
from bga.ingest.models import TaskKey, TaskKind, TaskSpan
from bga.normalize.timestamps import subtract_admission_wait


def _span(uid, kind, ts_us, dur_us):
    return TaskSpan(task_key=TaskKey(uid, kind, kind.value, 0),
                    ts_us=ts_us, dur_us=dur_us)


def test_the_wait_leaves_the_build_span():
    spans = [_span("mod-a.bst", TaskKind.BUILD, 1_000_000, 500_000)]

    adjusted = subtract_admission_wait(spans, {"mod-a.bst": 100_000})

    (span,) = adjusted
    assert span.dur_us == 400_000, "the wait must leave the span, shortening its duration"
    assert span.finish_us == 1_500_000, "finish is immutable - only the start moves"
    assert span.ts_us == 1_100_000


def test_a_wait_longer_than_the_span_clamps_rather_than_inverting():
    spans = [_span("mod-a.bst", TaskKind.BUILD, 1_000_000, 500_000)]

    adjusted = subtract_admission_wait(spans, {"mod-a.bst": 999_000_000})

    (span,) = adjusted
    assert span.dur_us == 0
    assert span.finish_us == 1_500_000


def test_a_non_build_span_is_never_touched():
    spans = [_span("mod-a.bst", TaskKind.FETCH, 1_000_000, 500_000)]

    adjusted = subtract_admission_wait(spans, {"mod-a.bst": 100_000})

    assert adjusted == spans


def test_no_wait_recorded_is_a_no_op():
    spans = [_span("mod-a.bst", TaskKind.BUILD, 1_000_000, 500_000)]

    assert subtract_admission_wait(spans, {}) == spans
    assert subtract_admission_wait(spans, None) == spans
