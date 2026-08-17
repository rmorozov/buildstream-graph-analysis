# UX-62: a task's terminal status is known at extraction and discarded, so attribution cannot tell work that succeeded from work that was thrown away

**Priority:** Medium | **Status:** 🔴 Open | **Depends on:** `UX-54` (done — which recorded the failure at run level)

## Motivation

`UX-54` made a failed build visible, and deliberately did so at the
*run* level: `build_outcome.failed_elements` in run-context, a
`build_failed` violation, and a gate that fails closed. Its Out of Scope
named what that leaves:

> **Per-span status in trace/v9.** Recording each task's terminal status
> on the span itself is the more complete model, and would let
> attribution treat a failed task's time differently from useful work.

and, separately:

> Whether a failed task's duration should count as `EXECUTION_ON_CHAIN`
> at all. It currently does. Arguably it is closer to waste than to work.

Both are still true. On the failed real capture, four failed builds
contributed 5.3 seconds of `EXECUTION_ON_CHAIN` — time the build spent
producing nothing.

## Why now rather than with `UX-54`

`UX-54` was about a hazard: a broken build passing a CI gate. Fixing that
needed a run-level fact and nothing more, and widening it would have
delayed a fix to a live problem for a schema change touching every
fixture.

What remains is not a hazard but an accuracy question, and it has a
second use `UX-54` did not need: **retries**. `--retry-failed` and real
CI re-runs produce a first attempt that failed and a second that
succeeded, and today those are two spans of identical shape. `UX-19`'s
retry classification infers them from ordinal position; a status field
would make it a fact.

## Required Fix

1. Carry the End event's `Status` onto the span in trace/v9 — additive
   and optional, so every existing capture stays valid and absent keeps
   meaning "not recorded".
2. Decide, explicitly, what a failed task's duration is in attribution.
   It moves `I4`'s identity, so it is a decision with a proof obligation,
   not a re-bucketing.
3. Use it where an inference exists today — retry detection first.

## Out of Scope

- The run-level signal, which `UX-54` shipped and which stays the thing
  the CI gate keys on.
- `CACHED` / `SKIPPED` as span statuses: a cached element produces no
  span at all, and `UX-55` handles that at run level.

## Acceptance Test

1. A real capture of a failing build carries `FAILURE` on the failed
   spans, and every existing fixture is unchanged.
2. Attribution's treatment of failed time is stated in the report rather
   than implied, and `I4` still reconciles.
3. Retry classification uses the recorded status where present, and falls
   back to today's ordinal inference where absent.

## Verification Log

Filed 2026-08-17. Both quotations are verbatim from `UX-54`'s Out of
Scope. The 5.3-second figure is from the real failed capture's
`analyze.txt`, published to `captures/fdsdk-latest` by run
`32026123204`.
