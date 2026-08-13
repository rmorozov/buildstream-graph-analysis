# P1-05: No violation raised when the flattened timeline undercounts

**Priority:** P1 | **Status:** 🔴 Not Started | **Depends on:** none now (`P1-03`/`P1-04`/`P1-19` all done - attribution identity holds exactly on every fixture tested so far, including `IDLE` gap-filling for disconnected components; this task is still valuable as defense-in-depth reporting for any future/untested scenario where a residual reappears, not eliminating a currently-known gap)

## Spec Reference
Read only: `sed -n '1629,1719p' docs/specification.md` (Part 33 — Reconciliation and Confidence) and the I4/I10 entries in `sed -n '1720,1780p' docs/specification.md` (Part 34).
Key principle: the spec's whole design philosophy is "no silent correction" — ordering violations are reported, not hidden (Part 3.3); resource ambiguity is reported (`UNKNOWN`/`ambiguous=true`), not invented; CPU reconciliation residuals are reported as `unaccounted_cpu_s` rather than silently forcing categories to sum. This task extends that same philosophy to attribution-timeline reconciliation, which currently has no equivalent safety net.

## Current Broken Behavior
File: `bga/attribution/blame_chain.py`, function `reconcile_attribution` (around line 648).
- Sums `segments` and compares nothing against `H`. If the flattened timeline (see `P1-04`) undercounts, there is currently no code path that notices — the tool just silently reports a smaller-than-correct set of numbers with no warning.

## Required Fix
1. In `reconcile_attribution`, after summing segment durations, compare the sum against the task horizon `H` (see `bga/occupancy/sweep.py::compute_task_horizon`).
2. If `Σ segments != H` (after `P1-04`'s fix, this should be rare/zero, but must still be checked — defense in depth, and it also catches any future regression), append a structured entry to the existing `violations` field on `AnalysisResult` (check `bga/ingest/models.py:224-241` for the exact shape already defined there — reuse it, don't invent a new field) describing the exact residual in microseconds and which invariant (I4) is affected.
3. This should also reduce the reported `confidence` value (ties into `P1-13`, which implements the broader confidence-gate computation — if that task isn't done yet, just make sure `violations` is populated correctly here; `P1-13` will pick it up).
4. Never silently pad or truncate to force the sum to match — report the true residual.

## Out of Scope
- Don't implement the full confidence-gate formula (`min(provenance_score, coverage_score, model_score, attribution_score)`) — that's `P1-13`. Just make sure this task's violation entry exists so `P1-13` has something to consume.

## Acceptance Test
1. Using the `P1-04` regression fixture (two independent chains) plus a deliberately-broken variant (e.g. temporarily stub one segment out, or construct a fixture that intentionally still doesn't cover full H, such as one with a genuinely untracked gap) — confirm `violations` gets a new entry when `Σ segments != H`, and confirm it does **not** get a spurious entry when the sum is exact.
2. `PYTHONPATH=. python3 tests/test_e2e.py` still passes (this fixture's sum should already be exact after `P1-03`/`P1-04`, so no new violation should appear for it).

## Verification Log
_(append real command + output here once run, before marking 🟢)_
