# UX-110: Plane 1 under-reports a task whose log lines it flushed late

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — (found by UX-108's ground-truth check)

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
