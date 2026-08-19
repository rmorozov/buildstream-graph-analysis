# UX-110: Plane 1 under-reports a task whose log lines it flushed late

**Priority:** Medium | **Status:** 🟢 Done — measured, bounded, and reported; corrected deliberately not | **Depends on:** — (found by UX-108's ground-truth check)

## Motivation

`examples/01-resource-contention` runs eight identical elements, each of
which does `sleep 3` and nothing else. Both planes measured the same
build:

| element | Plane 1 | Plane 2 (spine) |
|---|---|---|
| work-a … work-f | 3.004 – 3.005s | 3.010 – 3.012s |
| work-g | **2.687s** | 3.010s |
| work-h | **2.686s** | 3.010s |

Plane 1's spread across eight elements doing identical work is
**0.319s**; Plane 2's is **0.002s**. Two of the eight are reported 11%
shorter than the `sleep 3` they ran — a duration that is not merely
imprecise but *impossible*.

The cause is in Plane 1's own transport, not in BuildStream. A wrapped
log line is stamped when the wrapper **reads** it, and BuildStream
flushes in bursts, so a START line can be stamped after the task really
started. `work-g`'s own build log is named
`0c5f1a72-build.20260819-061746.log` — BuildStream created it during
second `:46` — while the wrapper stamped its `START` at `:47.199`.

Every Plane 1 signal is built on these spans: element durations, the
critical path, `T_C`, the efficiency score, wait-gap classification. A
0.3s error on a 3s task is 11%; on a 30s task the same absolute lag is
1%, which is why nothing has noticed. It took a project with a *known*
answer and a second plane to see it at all — neither of which existed
before `UX-106`.

## Required Fix

1. Quantify it where it matters: the same two-plane comparison on
   `examples/06` (real compile work, 30–60s tasks) and, if a spine
   capture of fdsdk exists, at real scale. The question to answer is
   whether the lag is bounded in absolute terms (a flush interval) or
   proportional (a queue that grows with output volume) — the two have
   different consequences for a long build.
2. Prefer a timestamp BuildStream itself produced where one is
   available. Its per-element log *file name* carries a second-resolution
   creation time, and the element log's own first line carries more;
   either anchors a task's start better than the moment the wrapper's
   read returned.
3. Failing that, state the resolution. A span whose ends carry an
   unquantified lag should not be rendered to millisecond precision, and
   a run whose tasks are short relative to the lag should say so rather
   than let the reader take 2.686s at face value.

## Out of Scope

- Plane 2's own timestamps (`CLOCK_MONOTONIC` inside the sandbox, and
  the plane that exposed this).
- The `--format raw` path, which has no wall-clock anchor at all
  (`UX-06`) and is a different problem.

## Acceptance Test

On `examples/01`, the eight identical elements' Plane 1 durations agree
with each other and with Plane 2 to within the resolution the fix
claims, or the report states a resolution wide enough to contain the
disagreement. No element's reported duration is shorter than a command
it provably ran.

---

## Fix Implemented

`WrapperTraceConverter._check_span_against_bst_elapsed` /
`get_timestamp_agreement` in `tools/bst_log_to_chrome_trace.py`, carried
into `run-context.json` by `bst_extract_run`, through
`RunContext.timestamp_agreement` / `plane1_resolution_s`, and rendered
by `bga analyze` beside the confidence block.

### The same duration, already in the log twice

The fix needed no new capture and no new mechanism: a wrapped log
carries each task's length **twice**. The wrapper's own timestamps
bracket the span, and the closing line carries BuildStream's
`[HH:MM:SS]` elapsed prefix — its own timing, truncated to whole
seconds, and independent of when anybody read anything. `UX-53`'s rule
applies directly: a quantity computed twice is a free test, and nothing
was running it.

### Bounded, not proportional — measured on three scales

| build | tasks | shorter than BuildStream's own | worst shortfall | worst excess |
|---|---|---|---|---|
| `examples/01` (12s build, 3s tasks) | 20 | 2 | **-0.314s** | +0.005s |
| `examples/06` (46s build) | 22 | 1 | -0.255s | +1.006s |
| freedesktop-sdk (3261s build, tasks to 1415s) | 25 | 5 | -0.556s | **+1.501s** |

The lag envelope is about **-0.6s to +1.5s** and does not grow with the
build or with the task: freedesktop-sdk's 1415-second element is off by
0.43s, the same order as a three-second one. That answers the question
the task poses — a flush interval, not a queue that grows — and it is
why this has been invisible: 1.5s is 0.03% of a 1415s element and 11% of
a `sleep 3`.

### Compared, not corrected — and why

The task asks for a BuildStream-produced timestamp to be preferred where
one exists. Implemented as a **cross-check rather than a substitution**,
for two reasons the measurement itself supplies:

- The elapsed prefix is a *second-resolution lower bound*. It can say a
  span is too short; it cannot say what the span was. Substituting it
  would replace a millisecond figure that is up to 1.5s wrong with a
  one-second figure that is up to 1s wrong.
- Repairing a span means moving its `B` earlier or its `E` later, and
  both manufacture overlap with the neighbouring task on the same
  builder — which the capacity model would then report as an
  oversubscription violation. Trading a bounded measurement error for a
  fabricated finding is a bad trade, and this repository's posture
  everywhere else ("reported, not averaged"; "uncovered rather than
  guessed") is to name the disagreement instead.

Recorded here as a deviation from the task's own wording rather than
implemented quietly the other way.

### What a reader sees

Silent on a real build, because a 1.5s resolution on a forty-minute
compile is furniture. It speaks when the lag is a material share of some
task's own duration — `_RESOLUTION_MATERIAL_SHARE`, 5%, chosen because
it clears `bga compare`'s own 1% significance rule by a comfortable
margin — and always when a task is reported as *shorter* than
BuildStream timed it:

```text
Confidence:
  Overall: 0.90 (high)

  Duration resolution: ±0.31s, measured - each task's length is in this capture
  twice (the wrapped log's own timestamps, stamped when the wrapper read each
  line, against BuildStream's own elapsed) and 20 task(s) were compared
    that is more than 5% of the duration for 8 of 8 measured task(s) - the
    shortest is 2.69s
    2 task(s) are reported SHORTER than BuildStream's own timing of them -
    work-g.bst at 2.687s against 3s, which is a duration that did not happen
    rather than one measured imprecisely (UX-110)
```

`bst_extract_run` warns at extraction time as well, where the log is
still in hand. On freedesktop-sdk the same block reads ±1.50s, material
for **13 of 23** task spans — an incremental capture is mostly short
tasks even when four long elements dominate its wall clock.

A raw-format capture gets **no** line at all, and the field is absent
rather than empty: raw-mode timestamps are reconstructed *from* the
elapsed prefix, so comparing them would be a tautology, and "not
compared" must not read as "compared and agreed".

Tests: 10 in `tests/unit/test_plane1_timestamp_resolution.py`, including
the four-hand-off round trip from log line to rendered report. Suite:
1399 → 1409.

## Verification Log

Done 2026-08-19. The three-scale table is from three real builds — a
traced `examples/01`, a traced `examples/06`, and the freedesktop-sdk
capture published as run 32223468993 — each parsed by the shipped code
rather than by a fixture.

The acceptance's second clause is met in the sense the measurement
allows: no *reported* duration is silently shorter than a command it
provably ran, because the report now names every one that is. Making the
number itself impossible-proof would need a timestamp BuildStream does
not emit at sub-second resolution, and is not something a wrapped log
can be made to yield.
