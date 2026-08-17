# UX-64: the sandbox correlation matches on a start *instant*, so 18 of 25 real sandboxes are ambiguous when four builders overlap

**Priority:** High | **Status:** 🟢 Done | **Depends on:** `UX-56` (done — which built the correlation this sharpens)

## Motivation

`UX-56` recovered element identity for a real `freedesktop-sdk` capture
by correlating each bwrap sandbox against Plane 1's BUILD spans. Round 7
ran it on a real project and it works — **19,024 processes relabelled**
across 6 correctly-identified elements, and `unmatched: 0`, which
confirms the clock alignment holds at real scale.

It does not reach far enough:

```
certain 6, deduced 0, ambiguous 18, conflicting 1, unmatched 0
```

Six of twenty-five sandboxes resolved. `deduced: 0` is the diagnosis: the
elimination never cascaded, because there were too few single-candidate
sandboxes to start a chain. With `--builders 4`, four BUILD spans overlap
continuously, so a start *instant* falls inside several of them and the
constraint propagation has nothing to force.

The consequence is that `bga correlate` still refuses the join (correctly
— 14.9% of processes carry a real element name), so declared-vs-used,
per-element parallelism, CPU time and peak memory remain attributed to a
`buildstream-build` bucket for 85% of a real build's processes.

## The information is already in the capture

The correlation matches on the invocation's **start time only**, because
the shim `execv`s and cannot record an end.

But the end is already recorded, twice over. Every traced process carries
`inv=` (`UX-56`), so a sandbox's own window is
`[min(start_ts), max(end_ts)]` over its processes — in the hook's
`CLOCK_MONOTONIC`. The shim's `started_at` is wall-clock. One anchor pair
converts between them.

That turns each sandbox from an instant into an **interval**, and
requiring the whole interval inside a BUILD span is a far stronger
constraint. It should bite hard on this capture specifically, because the
25 elements' build durations differ by orders of magnitude —
`cmake-stage1.bst` ran for many minutes while several elements took
seconds, so a long sandbox cannot belong to a short element no matter how
their starts overlap.

## The `conflicting` sandbox is a second, separate finding

One sandbox came back `conflicting` — two sandboxes forced onto the same
element. `UX-56` reports that separately from ambiguity precisely because
it invalidates the premise rather than limiting the reach: **an element
does not always host exactly one sandbox on a real project.**

BuildStream can run more than one sandboxed command for one element (an
integration command, a separate staging step). Until that is understood,
the one-sandbox-per-element assumption that drives the elimination is not
safe to lean on harder than it already is — so this must be settled
*before* the interval matching is tightened, not after.

## Required Fix

1. **Anchor the clocks.** Record one `CLOCK_MONOTONIC`/`CLOCK_REALTIME`
   pair at capture start, so the hook's stamps and the shim's are
   convertible. Do not infer the offset per sandbox from its own first
   process — that bakes the very thing being measured into the answer.
2. **Match on the interval.** A sandbox whose whole window lies inside
   exactly one BUILD span is that element's. Keep the elimination pass on
   top; it becomes far more effective once most sandboxes start with a
   single candidate.
3. **Settle the conflict first.** Find out why one element hosted two
   sandboxes, and either model it (an element may host N sandboxes, which
   weakens elimination but keeps it sound) or exclude the case explicitly.
4. **Keep refusing what is still ambiguous.** The point of `UX-56` is
   that a mis-attributed read set is worse than a missing one, and a
   tighter constraint must not become a licence to guess the remainder.

## Out of Scope

- Any change to what happens *after* attribution succeeds. The consumers
  (`UX-46`, `UX-32`, `UX-45`, `UX-63`) are already correct; they are
  starved of correct names, not wrong about what to do with them.
- Asking BuildStream upstream for an element-identifying field in the
  sandbox invocation. That is the real long-term fix and is a different
  kind of task.

## Acceptance Test

1. On a re-capture of `freedesktop-sdk` at the same commit, `certain +
   deduced` covers substantially more than 6 of 25 sandboxes, and
   `ambiguous` shrinks correspondingly.
2. `unmatched` stays 0 — the interval must not push sandboxes out of
   every span, which would be the clock anchoring being wrong.
3. Every element the correlation names is checked against the declared
   graph: a name that is not a declared element uid is a failure, not a
   near-miss. Round 7 found `flit_core` and `expat` as `--dir` segments
   where neither is an element, so this check has already caught
   something once.
4. `bga correlate` produces a real join, and `declared_vs_used` reports
   per-element rather than against one bucket.

## Fix Implemented — and two measured corrections to this task as filed

### 1. The elimination was unsound, not merely weak

This task called the one-sandbox-per-element premise something to
"settle first". Round 7's own data settles it: **false**.

- `components/bison.bst` hosted **two** sandboxes, 4.1 seconds apart —
  which is what the `conflicting` result was reporting.
- In the build's first 54 seconds, **15 sandboxes ran against at most 10
  concurrently-building elements**.

That is not a limitation of reach. `UX-56`'s elimination struck a
resolved element from every other candidate set, so on a real project it
could attribute a sandbox to the **wrong** element. It is removed. What
remains — a sandbox contained in exactly one span is that element's — is
sound, and the two `bison` sandboxes now both resolve to `bison.bst`
correctly, where before one was reported as a contradiction.

### 2. The interval must be matched on its **end**, not its start

The obvious reading of this task was "require the whole interval inside
the span". Measured on a real traced build, that is *worse* than what it
replaced — 2 of 9 sandboxes resolved, 7 unmatched.

The reason is a real skew. Plane 1 timestamps a line when the **wrapper
reads** it, which lags the event, so **every one of 9 sandboxes began
before its element's logged BUILD START**, by 0.18s to 0.46s. The same
lag makes the span systematically *shorter* than the sandbox it
contains, so "no longer than its span" fails too — `app.bst`'s sandbox
ran 2.03s against a 1.62s span.

The **end** is the reliable edge: BuildStream cannot log an element's
terminal status until its sandbox has finished, so a sandbox's last
process must exit before its span ends.

| matching rule | resolved | unmatched |
|---|---|---|
| start instant (`UX-56`, with unsound elimination) | 7 | 0 |
| whole interval inside the span | **2** | **7** |
| **end inside the span** | **8** | **0** |

### The sandbox's end needed no new capture field

`sandbox_durations` derives it from data already recorded: every process
carries `inv=` (`UX-56`), so a sandbox's length is
`max(end_ts) - min(start_ts)` over its own processes. The monotonic
stamps supply only the *delta*, the shim's wall-clock start supplies the
origin, and no clock anchor is needed at all.

The computed interval is very slightly shorter than the true one — bwrap
starts before its first traced process and exits after its last — which
is milliseconds against spans of seconds to minutes, and is stated in
the code rather than assumed away.

### Result on the local reproduction

`examples/06` with `build-root: /buildstream-build`, a real traced build:

| | `UX-56` (start instant) | `UX-64` (end edge) |
|---|---|---|
| sandboxes resolved | 7 of 9, one via unsound elimination | **8 of 9**, all sound |
| processes correctly named | 616 / 822 (75%) | **729 / 822 (88.7%)** |
| distinct real elements | 6 | **8** |
| `declared_vs_used` | — | **24 unused, 8 used** |

The one remaining ambiguous sandbox is genuinely ambiguous: `core.bst`
and `codegen.bst` both start at t=0 and its end falls inside both spans.

Tests: 16 (`tests/unit/test_invocation_correlation.py`), including both
measured corrections above as named cases. Suite: 1024 → 1028.

**Not yet validated at real scale.** Round 7's published capture dropped
its full native trace above 40 MB, and the 4 MB head that survived covers
**17 seconds of a 3584-second build**, so every sandbox duration derived
from it is truncated and proves nothing. Round 8 is the real test.

## Verification Log

Filed and implemented 2026-08-17 (round 7). Every figure is from the real capture
published to `captures/fdsdk-latest` as `df20544`, produced by run
`32044281643`: the correlation counts and `relabelled_processes` are from
its `native-report.json`, the 14.9% figure and the refused join are from
its `element_attribution` and `correlate.txt`, and the `--dir` segment
survey is from its `invocations.jsonl` (25 sandboxes) cross-checked
against `graph-declared.json`.
