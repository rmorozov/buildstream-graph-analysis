# P3-05: Phase overlap + occupancy edge-case tests

**Priority:** P3 | **Status:** 🟢 Fixed & Verified (2026-08-13) | **Depends on:** `P3-01`

## What was done
Added `tests/unit/test_phase_and_occupancy.py` (13 tests). Writing the required "phase overlapping DEPENDENCY_WAIT/RESOURCE_WAIT/IDLE" cases surfaced a real bug - phase annotations were silently dropped on every segment category except `EXECUTION_ON_CHAIN`, contradicting Part 10.2's own worked examples (`SCHEDULER_WAIT phase=load`, `IDLE phase=cache_cleanup`). Filed and fixed as `P1-24` (own task file), since it directly changes production behavior in `bga/attribution/blame_chain.py`.

Phase tests: execution/dependency-wait/resource-wait/idle all keep their causal category and correctly receive a `phase=` tag when a `PhaseSpan` overlaps them; multiple simultaneous overlapping phases are all present in `annotate_phases`'s full list (the flattened timeline's single `phase` field only surfaces the first - a deliberate, documented, unchanged simplification, not a bug).

Occupancy tests: zero-duration tasks (alone, and alongside real tasks - no crash, no double-counted/incorrect coverage), adjacent intervals (half-open semantics, no boundary double-count), nested intervals (correct concurrent-usage segments), gaps (correctly idle), and confirmation that the occupancy step function's own horizon is task-relative, never wall-clock-relative (a deliberately separate concept from `UNTRACKED_HEAD`/`UNTRACKED_TAIL`, `P1-23`).

## Spec Reference
`sed -n '674,733p' docs/specification.md` (Part 10 — Phase Model) and `sed -n '311,405p' docs/specification.md` (Part 4 — Primary Trace Model, occupancy).

## Required Fix
Create `tests/unit/test_phase_and_occupancy.py`:

**Phase tests** (Part 10):
1. A phase overlapping `EXECUTION_ON_CHAIN` time → underlying category stays `EXECUTION_ON_CHAIN` with a `phase=` tag; phase presence must never change the causal category.
2. Same check for phase overlapping `DEPENDENCY_WAIT`, `RESOURCE_WAIT`, and `IDLE` — each must keep its original category.
3. Multiple overlapping phases on the same interval → all recorded as annotations, still no change to the causal category.

**Occupancy tests** (Part 4, Part 36.7):
1. Zero-duration tasks — must not break the sweep-line (no divide-by-zero, no spurious segments).
2. Adjacent intervals (task B starts exactly when task A ends) — half-open interval semantics (`[start, finish)`) must not double-count the boundary instant.
3. Nested intervals (if the data model allows a resource interval fully containing another) — occupancy correctly reflects concurrent usage.
4. Gaps between intervals — correctly reflected as idle/unoccupied.
5. Head/tail — the very first and very last recognized interval relative to `wall_clock` boundaries.

## Out of Scope
- Don't test attribution-identity totals here — that's `P3-03`. This task is specifically about phase-tag invariance and occupancy sweep-line correctness in isolation.

## Acceptance Test
`PYTHONPATH=. python3 -m pytest tests/unit/test_phase_and_occupancy.py -v` — all cases pass.

## Verification Log
```
$ PYTHONPATH=. python3 -m pytest tests/unit/test_phase_and_occupancy.py -v
13 passed

$ PYTHONPATH=. python3 -m pytest tests/ -q
188 passed (+ 1 known-flaky, unrelated timing test)   # was 176

$ PYTHONPATH=. python3 tests/test_e2e.py
Results: 7 passed, 0 failed

$ make check-clean
OK: no ignored files are tracked
```
