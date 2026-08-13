# P3-05: Phase overlap + occupancy edge-case tests

**Priority:** P3 | **Status:** 🔴 Not Started | **Depends on:** `P3-01`

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
_(append real command + output here once run, before marking 🟢)_
