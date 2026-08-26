"""UX-313: why the record list cannot be windowed away.

`UX-297` made parsing and pairing one streaming pass and then measured
what was left. On a 200,000-process trace the record list was 185.8 MB
of a 221.1 MB peak, and the filing asked the obvious next question:
could a *bounded reorder window* replace it, making extraction
`O(concurrency)` instead of `O(processes)`?

Two things stand in the way, and the filing named them as questions
rather than answers:

* `stream_records` yields a record when its **END** arrives, and the
  order every downstream reader has always seen is **start** order.
* `merge_record_streams` joins the spine and hook streams whole.

**The answer is no, and the reason is structural rather than a property
of any one build.** Measured on this repository's real capture of
`examples/06` (813 records, 9 elements):

```text
records                            813
  paired (an END was observed)     663
  open   (no END ever arrived)     150
window over paired records only     83
window over open records           663   the whole tail
earliest open record, in start order   position 0
```

Every one of the nine elements leaves open records - 16 to 21 each -
because BuildStream tears the sandbox down around the element's shell,
so the hook never observes its exit. `stream_records` therefore cannot
know those records exist until the stream ends. To emit in start order
a buffer must hold every record that starts after the earliest open
one, and the earliest open one is the **first process of the build**:
the buffer is 813 of 813 records, 100% of the list.

Absent open records the window really is bounded by concurrency - on
synthetic traces it is ~1.2x the concurrency and flat in the build's
length. That is what makes the finding worth writing down rather than
assuming: the bound exists, and the shape of a real BuildStream capture
defeats it with the very first process it runs.

So this file does not guard a window. It guards the *reason there
isn't one*, so that a later round reaching for `O(concurrency)` finds
the measurement instead of re-deriving it - and so that if the capture
ever stops leaving open records, this goes red and says the question
is worth reopening.
"""
import gzip
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools import bst_native_build_tracer as tracer  # noqa: E402

CAPTURE = REPO / ("examples/06-macro-micro-optimization/.bga/runs/"
                  "20260821T170127Z/plane2.log.gz")

needs_capture = pytest.mark.skipif(
    not CAPTURE.exists(),
    reason="the example capture is not in this clone (UX-189)")


def _records():
    with gzip.open(CAPTURE, "rt", errors="replace") as handle:
        return list(tracer.stream_records(
            tracer.stream_trace_events(handle)))


def _displacement(records):
    """How far each record is yielded from where start order puts it."""
    order = sorted(range(len(records)),
                   key=lambda i: records[i]["start_ts"])
    sorted_at = {yielded: i for i, yielded in enumerate(order)}
    return [yielded - sorted_at[yielded] for yielded in range(len(records))]


def _synthesise(processes, concurrency, long_lived=0):
    """A trace of `processes` short jobs at `concurrency`, interleaved."""
    events, clock, running = [], 0.0, []
    for index in range(processes):
        start = clock
        end = start + 0.5 + (index % 7) / 20
        events.append(("START", index, start))
        events.append(("END", index, end))
        running.append(end)
        if len(running) >= concurrency:
            running.sort()
            clock = running.pop(0)
    span = max(when for _, _, when in events)
    for extra in range(long_lived):
        events.append(("START", processes + extra, 0.01 * extra))
        events.append(("END", processes + extra, span + 0.01 * extra))
    events.sort(key=lambda event: event[2])
    return [f"{kind} pid={2000 + pid} ppid=1 ts={when:.6f} element=e.bst "
            f"inv=a cmd=cc" + (" utime_us=10 stime_us=5" if kind == "END"
                               else "")
            for kind, pid, when in events]


def _window(lines):
    records = list(tracer.stream_records(
        tracer.stream_trace_events(iter(lines))))
    return len(records), max(_displacement(records), default=0)


class TestTheWindowIsBoundedUntilAProcessOutlivesTheCapture:
    """The half that is good news, so the finding is not one-sided."""

    @pytest.mark.parametrize("processes", (500, 1000, 2000))
    def test_it_does_not_grow_with_the_build(self, processes):
        total, window = _window(_synthesise(processes, concurrency=8))
        assert total == processes
        assert window < 40, (
            f"{processes} processes at concurrency 8 needed a window of "
            f"{window}; with every process paired the window is a property "
            "of concurrency and should not follow the build's length")

    @pytest.mark.parametrize("concurrency,ceiling",
                             ((1, 3), (8, 40), (32, 120)))
    def test_it_grows_with_concurrency(self, concurrency, ceiling):
        _, window = _window(_synthesise(2000, concurrency=concurrency))
        assert window <= ceiling, (
            f"concurrency {concurrency} needed a window of {window}, over "
            f"the stated {ceiling}")

    def test_one_process_that_outlives_the_others_takes_the_whole_list(self):
        """The case the filing named, built rather than argued."""
        _, without = _window(_synthesise(2000, concurrency=8))
        total, with_one = _window(_synthesise(2000, concurrency=8,
                                              long_lived=1))
        assert without < 40, without
        assert with_one > total * 0.9, (
            f"one long-lived process moved the window only to {with_one} "
            f"of {total}; the filing's premise was that it takes "
            "essentially the whole list, and this clause exists to hold "
            "that premise to a number")


@needs_capture
class TestTheRealCaptureDefeatsItWithItsFirstProcess:

    def test_every_element_leaves_a_record_that_never_closed(self):
        records = _records()
        elements = {r["element"] for r in records}
        with_open = {r["element"] for r in records if r.get("open")}
        assert with_open == elements, (
            "some element closed every one of its processes: "
            f"{sorted(elements - with_open)}. If BuildStream stopped "
            "tearing the sandbox down around the element's shell, the "
            "windowing question in UX-313 is worth reopening.")

    def test_the_earliest_unclosed_record_is_the_start_of_the_build(self):
        """The whole argument, in one number.

        A reorder buffer must hold every record starting after the
        earliest record it does not yet know is open. That record is
        the build's first process, so the buffer is the record list.
        """
        records = _records()
        order = sorted(range(len(records)),
                       key=lambda i: records[i]["start_ts"])
        open_positions = [i for i, yielded in enumerate(order)
                          if records[yielded].get("open")]
        assert open_positions, "no open record in the capture at all"
        must_hold = len(records) - min(open_positions)
        assert must_hold == len(records), (
            f"a buffer would have to hold {must_hold:,} of "
            f"{len(records):,} records. It was the whole list when UX-313 "
            "measured it, which is what closed the item; a smaller number "
            "means the premise moved.")

    def test_the_paired_records_alone_would_have_been_windowable(self):
        """Why this is a finding and not a shrug: the bound was real."""
        records = _records()
        displaced = _displacement(records)
        paired = [d for d, r in zip(displaced, records) if not r.get("open")]
        assert max(paired) < len(records) / 4, (
            f"paired records alone needed {max(paired)} of {len(records)}. "
            "UX-313 measured 83, which is what made the open records the "
            "whole of the problem rather than one contributor among many.")
