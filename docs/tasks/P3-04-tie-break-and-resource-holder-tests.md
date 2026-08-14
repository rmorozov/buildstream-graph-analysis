# P3-04: Tie-break + resource-holder tests

**Priority:** P3 | **Status:** 🟢 Fixed & Verified (2026-08-13) | **Depends on:** `P3-01`, `P1-01` (resource-holder tests need the real implementation to test against, not the stub)

## What was done
`tests/unit/test_tie_break.py` (7 tests): `BlameChainAnalyzer.select_dependency_blame` is a pure function of its arguments (never reads `self`), so every tie-break rule (finish desc, depth desc, key asc, out-degree never used) is tested directly against it, plus one full-pipeline test using `P3-01`'s `multiple_equal_predecessors()` fixture (built exactly for this) proving an unrelated, fully disconnected graph node added elsewhere doesn't change the tie-break winner.

`tests/unit/test_resource_wait.py` (7 tests): `BlameChainAnalyzer.classify_resource_wait` tested directly against hand-built `NormalizedTask` lists - single holder (weight 1.0), multiple simultaneous holders (time-weighted split matching the spec's own 70/30 worked example), a holder that only overlaps part of the wait window (partial explanation still marked `ambiguous`), holder changing mid-wait, no identifiable holder (`UNKNOWN`/`ambiguous=True`, never fabricated), and two negative controls (no wait, no resources).

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
```
$ PYTHONPATH=. python3 -m pytest tests/unit/test_tie_break.py tests/unit/test_resource_wait.py -v
14 passed

$ PYTHONPATH=. python3 -m pytest tests/ -q
176 passed   # was 162

$ make check-clean
OK: no ignored files are tracked
```
