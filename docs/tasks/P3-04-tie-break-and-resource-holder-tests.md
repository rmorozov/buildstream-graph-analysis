# P3-04: Tie-break + resource-holder tests

**Priority:** P3 | **Status:** 🔴 Not Started | **Depends on:** `P3-01`, `P1-01` (resource-holder tests need the real implementation to test against, not the stub)

## Spec Reference
`sed -n '534,649p' docs/specification.md` (Part 7 — Dependency Gate incl. 7.1 tie-breaking, and Part 8 — Resource Wait Model).

## Required Fix
Create `tests/unit/test_tie_break.py` and extend/create `tests/unit/test_resource_wait.py`:

**Tie-break tests** (Part 7.1):
1. Two predecessors finishing at the exact same normalized time → the one with greater longest-path-to-source depth wins.
2. Depths also equal → smallest task key (lexicographic) wins.
3. Regression test: build a base graph, record the tie-break winner, then add an unrelated, disconnected graph node elsewhere and re-run — assert the winner is unchanged (spec explicitly calls this out: "adding an unrelated graph node must not change the result").
4. Confirm out-degree is never used as a tie-breaker (construct a case where using out-degree would pick a different winner than the spec's actual rule, and assert the spec's rule wins).

**Resource-holder tests** (Part 8, depends on `P1-01` being done):
1. Single identifiable holder → correct holder in `blocking_tasks` with weight 1.0.
2. Multiple simultaneous holders → time-weighted split matches expected proportions.
3. Holder changes mid-wait → both holders appear with correct time-weighted shares.
4. No identifiable holder → `blocking_tasks == "UNKNOWN"`, `ambiguous == True` — explicitly assert no holder is ever fabricated in this case.

## Out of Scope
- Don't test scheduler-wait here — that's implicitly covered by `P1-02`'s own acceptance test; if you want a dedicated broader test suite for it, add it as a new tracker row rather than folding it into this task.

## Acceptance Test
`PYTHONPATH=. python3 -m pytest tests/unit/test_tie_break.py tests/unit/test_resource_wait.py -v` — all cases pass.

## Verification Log
_(append real command + output here once run, before marking 🟢)_
