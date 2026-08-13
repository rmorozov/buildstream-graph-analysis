# P1-03: Attribution identity (I4) violated on resource-constrained chains

**Priority:** P1 (highest-value open item — this breaks the tool's core promise) | **Status:** 🔴 Not Started (newly discovered 2026-08-13) | **Depends on:** none, but do after `P1-02` if convenient since that may share root cause

## Spec Reference
Read only: `sed -n '840,868p' docs/specification.md` (Part 13 — Task Horizon and Invariant I1) and `sed -n '1720,1780p' docs/specification.md` (Part 34 — Core Invariants, esp. I4: "for the selected horizon, `Σ attribution_duration == H` exactly").

## Current Broken Behavior — reproduce it yourself first
This was found by actually running the CLI, not by reading code. Reproduce with the fixture in `docs/fixing-guide.md` §7 (a 3-task linear chain, single `PROCESS` resource pool, capacity 1):

```
python3 -m bga.cli analyze /tmp/bga_test_run
```

Observed output (2026-08-13): `Total Duration: 0.5s`, `T∞ (observed critical path): 0.45s`, but the Attribution Breakdown is:
```
Execution On Chain Us  0.15s ( 33.3%)
Dependency Wait Us     0.00s (  0.0%)
Resource Wait Us       0.00s (  0.0%)
Scheduler Wait Us      0.00s (  0.0%)
Idle / Retry / Untracked  all 0.00s
```
Only the *first* task's execution (150000µs) is attributed; the chain's other two tasks (also 150000µs execution each, serialized on the same single-capacity `PROCESS` resource, so genuinely dependency/resource-blocked for 300000µs combined) are missing entirely. **Σ attribution = 150000µs, H = 450000µs — a 66% shortfall.** This directly violates invariant I4.

Note this is *different* from the passing `tests/test_e2e.py::test_invariants` case — that fixture's tasks apparently don't attach `resources` the same way, or don't hit whatever code path drops coverage here. Your first job is root-causing why the two scenarios diverge.

## Required Fix
1. Instrument/trace `compute_full_attribution` and `_build_flattened_timeline` (`bga/attribution/blame_chain.py:581-646`, and the orchestration in `bga/analyzer.py:230-321`) against the reproduction fixture above to find exactly where coverage is dropped. Likely suspects to check (don't assume — verify): the blame-chain backward walk may be stopping after one hop when a resource-wait or scheduler-wait branch is taken; `explicit_predecessors` construction (`bga/analyzer.py:262-280`, flagged separately as `P1-16` for its O(tasks²)/one-task-per-element assumptions) may be mis-mapping predecessors for this fixture's shape.
2. Fix root cause so the flattened timeline / attribution sum covers every task's full duration, not just the first hop of the blame chain.
3. This task and `P1-04` (multi-terminal timeline coverage) are related but distinct: `P1-04` is about graphs with independent branches / multiple terminals; this task is about a single linear chain still under-attributing. Fix this one first — it's the simpler, more fundamental case.

## Out of Scope
- Don't implement the "raise a violation on undercount" reporting behavior — that's `P1-05`. This task is about making the sum correct in the first place.
- Don't rewrite the O(N²)/O(tasks²) algorithms for performance — that's `P1-16`. If you need to touch that code to fix correctness, keep the algorithmic complexity the same and only fix the logic bug, unless the bug *is* the complexity shortcut (verify before assuming).

## Acceptance Test
1. Re-run the exact reproduction fixture: `python3 -m bga.cli analyze /tmp/bga_test_run` — the Attribution Breakdown must sum to `0.45s` (450000µs = H), matching `T∞ (observed critical path)`.
2. Add a permanent regression test (in `tests/test_e2e.py` or a new `tests/unit/test_attribution_identity.py`) that builds this exact 3-task single-resource-pool scenario programmatically and asserts `sum(attribution values) == H` exactly (integer equality, not approximate).
3. Re-run `PYTHONPATH=. python3 tests/test_e2e.py` — all 7 existing tests must still pass (no regression).

## Verification Log
_(append real command + output here once run, before marking 🟢)_
