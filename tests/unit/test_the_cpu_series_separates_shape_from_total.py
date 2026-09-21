"""UX-893: cores busy is an average over the span, not a curve.

`hook.c` takes one `getrusage` per process and the spine one
`/proc/<pid>/stat` in `write_end`, so everything downstream is a total
divided by a span. `cores_busy` is 1.60 on `tests/fixtures/macro_micro`
(69,786,259 us over 43.508 s) - and a build that pinned four cores for
seventeen seconds and idled for twenty-six reports the same 1.60.

The curve is published beside the total, never instead of it.
"""
import os

from tools.bst_native_build_tracer import (
    ELEMENT_CPU_SERIES_CAP,
    element_cpu_series,
    read_pid_cpu_us,
)

TICK = 2.0
#: Both elements burn the same CPU over the same span: 8 core-seconds
#: across four ticks. One front-loads it, the other spreads it flat.
FRONT_LOADED = (4.0, 4.0, 0.0, 0.0)
FLAT = (2.0, 2.0, 2.0, 2.0)


def _rows(element, pid, cores_per_tick):
    """One sampler row per tick, cumulative CPU as `/proc` reports it."""
    rows = [{"t": 0.0, "pid": pid, "element": element, "cpu_us": 0}]
    total = 0.0
    for index, cores in enumerate(cores_per_tick, start=1):
        total += cores * TICK
        rows.append({"t": index * TICK, "pid": pid, "element": element,
                     "cpu_us": int(total * 1e6)})
    return rows


def _total_us(rows):
    return max(row["cpu_us"] for row in rows)


def test_two_elements_with_one_total_have_two_curves():
    """The acceptance case. Same CPU, same span, same `cores_busy` -
    and the shapes are not the same shape."""
    front = _rows("front.bst", 101, FRONT_LOADED)
    flat = _rows("flat.bst", 102, FLAT)
    assert _total_us(front) == _total_us(flat)

    series = element_cpu_series(front + flat)

    assert [point[1] for point in series["front.bst"]] == list(FRONT_LOADED)
    assert [point[1] for point in series["flat.bst"]] == list(FLAT)
    assert series["front.bst"] != series["flat.bst"]


def test_a_pid_shorter_than_one_tick_is_absent_from_the_curve():
    """In the total and not in the curve - a known undersampling, and
    one a reader can see rather than one the series hides."""
    series = element_cpu_series(
        [{"t": 2.0, "pid": 103, "element": "brief.bst", "cpu_us": 500_000}])

    assert "brief.bst" not in series


def test_a_read_that_failed_ends_the_series_and_does_not_read_zero():
    """The rule `hook.c:523-528` already states for an unmeasured CPU
    time: the samples simply stop, and no zero-rate point is invented
    for the ticks after them."""
    rows = _rows("gone.bst", 104, (3.0, 3.0))          # then /proc vanished
    series = element_cpu_series(rows + _rows("other.bst", 105, FLAT))

    assert [point[0] for point in series["gone.bst"]] == [2_000_000, 4_000_000]
    assert len(series["other.bst"]) == 4


def test_one_element_with_two_pids_sums_them_at_the_same_instant():
    """The element's rate is its processes' rates, not one of them."""
    series = element_cpu_series(
        _rows("wide.bst", 106, FLAT) + _rows("wide.bst", 107, FLAT))

    assert [point[1] for point in series["wide.bst"]] == [4.0, 4.0, 4.0, 4.0]


def test_the_curve_is_bounded():
    rows = _rows("long.bst", 108, tuple([1.0] * (ELEMENT_CPU_SERIES_CAP + 50)))

    assert len(element_cpu_series(rows)["long.bst"]) == ELEMENT_CPU_SERIES_CAP


def test_a_pid_with_no_proc_entry_is_none_and_not_zero():
    assert read_pid_cpu_us(os.getpid()) is not None
    assert read_pid_cpu_us(2 ** 30) is None
