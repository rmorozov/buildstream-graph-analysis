"""UX-892: the per-element token record keeps the timestamp it was given.

The wrapper writes `{"event":..., "pid":..., "tokens":..., "t":...}` on
every grant (`tools/native_trace/wrappers/_common.sh`) and the reducer
read `pid` and `tokens` and never `t`, so p50 and max were all that
survived. "Four tokens for two seconds of a ninety-second element" and
"four tokens throughout" reduced to the same pair.

Only wrapped tools write these rows: a real `make` reads the jobserver
pipe itself and holds tokens nobody logs. So the series covers the
wrapped share and publishes that share as a number, the way `UX-891`
publishes `lb_cpu_coverage`.
"""
from tools.bst_native_build_tracer import (
    JOBSERVER_SERIES_CAP,
    summarize_jobserver_tokens_by_element,
)

T0 = 1_700_000_000.0
SPAN_S = 90.0
WRAPPED_PID, UNWRAPPED_PID = 4001, 4002
ELEMENT = "wide.bst"


def _row(event, pid, tokens, t):
    return {"event": event, "tool": "ninja", "pid": pid,
            "tokens": tokens, "t": t}


def _summarize(rows, tools=(WRAPPED_PID,), end=T0 + SPAN_S):
    by_element, unmapped = summarize_jobserver_tokens_by_element(
        rows,
        {WRAPPED_PID: ELEMENT, UNWRAPPED_PID: ELEMENT},
        {ELEMENT: set(tools)},
        {ELEMENT: int(end * 1_000_000)},
    )
    return by_element.get(ELEMENT) or {}, unmapped


def _mean_width(series, span_s):
    """The step function's time-weighted mean over the element's span -
    what the two scalars cannot say."""
    total = 0.0
    for (t_us, tokens), (next_us, _) in zip(series, series[1:]):
        total += tokens * (next_us - t_us) / 1e6
    return total / span_s


def test_two_seconds_of_four_tokens_is_not_four_tokens_throughout():
    """The acceptance case: the same p50 and max, a different series."""
    record, _ = _summarize([
        _row("acquire", WRAPPED_PID, 4, T0),
        _row("release", WRAPPED_PID, 4, T0 + 2.0),
    ])

    assert record["tokens_held_p50"] == 4
    assert record["tokens_held_max"] == 4
    assert record["tokens_held_series"] == [
        [int(T0 * 1_000_000), 4],
        [int((T0 + 2.0) * 1_000_000), 0],
    ]
    assert _mean_width(record["tokens_held_series"], SPAN_S) != 4
    assert round(_mean_width(record["tokens_held_series"], SPAN_S), 4) == 0.0889


def test_the_series_covers_the_wrapped_share_and_says_so():
    """An unwrapped `make` in the same element holds tokens nobody
    logged, so the share is a half and the series is not the element."""
    record, _ = _summarize([
        _row("acquire", WRAPPED_PID, 4, T0),
        _row("release", WRAPPED_PID, 4, T0 + 2.0),
    ], tools=(WRAPPED_PID, UNWRAPPED_PID))

    assert record["tokens_series_coverage"] == 0.5


def test_an_element_whose_only_tool_is_unwrapped_has_no_series():
    """Absent rather than empty - a zero-width series would read as an
    element that held nothing, which is not what was measured."""
    record, _ = _summarize([], tools=(UNWRAPPED_PID,))

    assert record["tokens_series_coverage"] == 0.0
    assert "tokens_held_series" not in record
    assert record["tokens_held_p50"] is None


def test_a_row_with_no_timestamp_leaves_the_scalars_and_drops_the_series():
    """The defect this item is about, in miniature: without `t` there
    is no interval to publish, and p50 and max are what they were."""
    record, _ = _summarize([
        {"event": "acquire", "tool": "ninja", "pid": WRAPPED_PID,
         "tokens": 4},
    ])

    assert record["tokens_held_p50"] == 4 and record["tokens_held_max"] == 4
    assert "tokens_held_series" not in record


def test_a_release_without_its_acquire_is_skipped_not_negative():
    record, _ = _summarize([
        _row("release", WRAPPED_PID, 2, T0 + 1.0),
        _row("acquire", WRAPPED_PID, 3, T0 + 2.0),
        _row("release", WRAPPED_PID, 3, T0 + 3.0),
    ])

    assert [point[1] for point in record["tokens_held_series"]] == [3, 0]
    assert record["tokens_series_open"] == 0


def test_a_wrapper_killed_before_its_trap_leaves_the_interval_open():
    """`UX-852`'s leak: closed at the element's span end and counted,
    rather than drawn as running for ever."""
    record, _ = _summarize([_row("acquire", WRAPPED_PID, 4, T0)])

    assert record["tokens_series_open"] == 1
    assert record["tokens_held_series"][-1] == [int((T0 + SPAN_S) * 1e6), 0]


def test_an_acquire_no_element_owns_is_unmapped_as_before():
    _, unmapped = _summarize([_row("acquire", 9999, 4, T0)])

    assert unmapped == 1


def test_the_series_is_bounded_and_says_when_it_was_cut():
    rows = []
    for i in range(JOBSERVER_SERIES_CAP):
        rows.append(_row("acquire", WRAPPED_PID, 1, T0 + i * 0.01))
        rows.append(_row("release", WRAPPED_PID, 1, T0 + i * 0.01 + 0.005))
    record, _ = _summarize(rows)

    assert len(record["tokens_held_series"]) == JOBSERVER_SERIES_CAP
    assert record["tokens_series_truncated"] is True
