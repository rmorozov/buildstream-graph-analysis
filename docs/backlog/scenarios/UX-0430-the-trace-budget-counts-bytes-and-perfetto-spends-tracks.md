# UX-430: the trace budget counts bytes, and Perfetto spends tracks

**Priority:** High | **Status:** 🔴 Not Started | **Found by:** round 69, an outside walk of `bga snapshot` → `bga view` → Perfetto, after a field report of the UI freezing on a real build | **Serves:** anyone who clicks "Open timeline in Perfetto" on a build big enough to be worth analysing | **Topic:** viewer

## Motivation

`tools/bga_view.py:601` holds the only bound the handoff has:

```python
TRACE_BUDGET_B = 4 * 1024 * 1024
```

It gates two things — whether the export inlines the trace, and whether
the served page uses `postMessage` or the `?url=` deep link.

Measured on a 1,202-element run with both planes, 14,424 traced
processes (`tools/bga_timeline.py`, trackevent format):

```text
                      measured        bound
trace bytes            795,371    4,194,304    19.0% of it
slices                  14,446            -
tracks                  15,650            -    nothing bounds this
counters                 2,001            -
```

**The trace is a fifth of its byte budget and carries more tracks than
slices.** `_write_trackevent` opens one process track per element and
one thread track per traced pid (`bga_timeline.py:1181`), so track
count rises with the process population, which is exactly what a build
worth tracing has a lot of.

Bytes are what the budget counts. Tracks are what the viewer spends —
Perfetto draws a row per track, and the reported freeze is a drawing
cost, not a transfer cost. The one number bga has cannot see the
quantity that decides whether the handoff opens at all.

**This is the fixing guide's §5 arriving on the design side**, where it
is easy to miss: the byte figure is real, cheaply obtained and honestly
reported. It is simply a measurement of a different thing. A capture
can pass this budget with room to spare and still be unopenable.

## Required Fix

- **Count the unit the consumer spends.** Bound the track count
  alongside the byte count, measured at the size `gen-synthetic` exists
  to probe rather than at eleven elements (§3f).
- **Give the reader the choice the size forces.** `bga timeline` and
  `bga view` expose no way to ask for less: `with_trace=False` is a
  Python kwarg with one caller in a test and no CLI surface, and there
  is no Plane-1-only or per-element option at all. A capture that
  exceeds the track bound should be able to hand over Plane 1 alone, or
  one element's Plane 2, rather than all or nothing.
- **Say which bound was hit, in the units of that bound.** A refusal
  reading "4 MiB" when the problem was 15,650 tracks sends the reader
  to compress something that is not the cost.

## Out of Scope

- **Whether Perfetto could draw 15,650 tracks faster** — that is
  Perfetto's business and this item does not file a bug there.
- **Lowering `TRACE_BUDGET_B`**: the byte bound is doing its own job
  correctly (transfer and inlining) and this item adds a second bound
  rather than retuning the first.
- **Merging pids onto one track per element** — a plausible fix that
  changes what the trace *means*, and it needs its own item because
  overlapping slices on one track is a different reading (`UX-188`
  chose the present shape deliberately).

## Acceptance Test

```bash
bga gen-synthetic /tmp/scale --seed 1
bga timeline /tmp/snapshot -o /tmp/two.pftrace     # both planes present
```

The emitter's result names a track count and the bound it was measured
against; a capture over the bound is refused, or narrowed, with a
message naming tracks. A mutation that doubles the per-pid track count
while leaving bytes unchanged must redden the guard — a guard that only
reads bytes passes that mutation, which is the defect this item is.

## Outcome

_Not started._
