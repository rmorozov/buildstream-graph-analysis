# UX-310: the counters the reserved constant was waiting for

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-298 (which reserved `TYPE_COUNTER`), UX-297 (the streaming pass that computes them) | **Serves:** R1, R5 | **Topic:** capture | **Area:** tools

## Motivation

`UX-298` pinned `TYPE_COUNTER = 4` with the comment "reserved
rather than used". The capture stream can fold three series that
answer questions no slice view can, all computable in the same
single pass the reductions already make:

- **cores busy** over time (the scalar the aggregate reads,
  as the series it was reduced from) — the one-glance answer to
  "was the machine ever actually saturated";
- **traced RSS** over time, per element lane where measured —
  where the memory envelope's peak came *from*;
- **open process count** — the storm shape `examples/08` exists to
  show, as a line instead of a wall of slices.

Perfetto renders counter tracks as graphs above the lanes; the
resource half of the user's "resource attributions" question is
this filing.

## Required Fix

Counter-track support in the emitter (`TrackDescriptor.counter`,
`TYPE_COUNTER` packets — proto-read numbers); the timeline folds
the series during the existing streaming pass (capture computes;
view serves — the series never exists as a document, only as
packets); units named in track names; a sampling stride argued and
recorded (a counter per event is packet spam; a stride is a
decision with a number).

## Out of Scope

- Host-wide counters bga did not capture (a counter must come from
  the trace's own records — `UX-186`'s manifest states the host,
  it does not sample it).
- Viewer rendering (Perfetto is the viewer for these).

## Acceptance Test

`trace_processor` counts the expected counter tracks with values
matching a hand-folded sample window on the golden capture; peak
of the RSS series equals the published `peak_memory` figure for
the sampled element (the reduction and the series must agree —
one pass, one truth); stride and cost recorded; RSS ceiling holds.

## Progress (2026-08-26)

🟢 **Done — one series of the three, and the other two are refused
rather than omitted.**

**The memory curve does not exist, and that is a finding.**
`max_rss_kb` is `ru_maxrss`: a per-process peak over that process's
*whole lifetime*, not a sample at a moment. A curve drawn from it would
sum peaks that never coexisted - precisely what `compute_peak_memory`
refuses at length ("two processes that each peaked at 500 MB at
different moments never held 1 GB between them"). The rule that kept
`TYPE_COUNTER` reserved for two rounds - an event stream may carry only
what a capture measured - is the rule that keeps this series out of the
trace. A guard asserts there is no memory counter, so the refusal is a
clause and not a gap.

**"Cores busy" and "open process count" are one question.** Both are
"how many traced processes were running at time t", and `bga` has one
answer already: `compute_max_concurrency`, over **matched** records
only, because a `sh -c` wrapper that `_exit()`s never runs its
destructor and its end is unknown. Excluding it from the peak and
including it in the curve would be two answers to one question.

**So: one series, and the clause that makes it worth having** is that
its peak **equals** the published `max_concurrency` - 20 on
`examples/06`, both ways. The tie rule is taken from the scalar rather
than re-decided, and asserted: a process that starts exactly as another
ends never reads as two.

**The stride, as a decision with a number.** A sample per endpoint is
two packets per process - 400,000 on a 200,000-process trace. The build
is bucketed into `COUNTER_WINDOWS = 1000` windows, each contributing
its **maximum** and its closing value, so the cost is independent of
the build's size and the peak survives the stride exactly. On
`examples/06`: 813 records, 1,626 raw endpoints, **538 samples**, peak
still 20. A guard turns the knob (10, 100, 1000 windows) and holds the
peak equal at each.

**What it costs**, same snapshot, this tree against the commit before:

```text
              packets       raw        gzipped
before          2,338   348,014 B     58,150 B
after           2,877   361,521 B     61,561 B
                 +539   +13,507 B     +3,411 B
```

One packet a sample plus one for the track - 25.1 B a sample
uncompressed, 6.3 B compressed - and the guard asserts the packet
arithmetic rather than the constant, by rendering the same capture with
the series silenced.

**Also recorded.** `trace_processor` still does not count these tracks
in CI (`UX-298`'s open deviation, `UX-312`'s first clause); the
counter tracks and their samples are read back by the in-repo protobuf
decoder, extended here to `CounterDescriptor`.

**Falsification.** Recorded in the Verification Log with the rest of
round 43.
