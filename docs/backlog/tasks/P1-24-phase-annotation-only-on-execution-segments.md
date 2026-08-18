# P1-24: Phase annotations silently dropped on every segment category except EXECUTION_ON_CHAIN

**Priority:** P1 | **Status:** 🟢 Fixed & Verified (2026-08-13) | **Depends on:** none

## Spec Reference
Part 10.2 (`sed -n '674,733p' docs/spec/specification.md`): worked examples explicitly show phase annotations on non-execution categories - `IDLE / phase=cache_cleanup` and `SCHEDULER_WAIT / phase=load`.

## How this was found
Discovered while building `P3-05`'s required test cases ("phase overlapping DEPENDENCY_WAIT/RESOURCE_WAIT/IDLE - each must keep its original category" - the spec's own examples imply a phase tag too, matching the EXECUTION_ON_CHAIN case).

## Current Broken Behavior (before this fix)
`BlameChainAnalyzer._build_flattened_timeline` (`bga/attribution/blame_chain.py`) only ever set `phase=` on `EXECUTION_ON_CHAIN` segments, via `attribution.phase_annotations[0] if attribution.phase_annotations else None`. The wait-gap segments (`DEPENDENCY_WAIT`/`RESOURCE_WAIT`/`SCHEDULER_WAIT`, built from `node.wait_breakdown`) and the IDLE-fill segments never called `annotate_phases` (or anything equivalent) at all - `phase` stayed `None` on every one of them regardless of any actual overlapping `PhaseSpan`, directly contradicting Part 10.2's own worked examples.

Confirmed with a real reproduction: a `cache_cleanup` phase span exactly overlapping a `DEPENDENCY_WAIT` segment produced `phase=None` on that segment before the fix.

## What was fixed
- Extracted the overlap-check logic shared by both cases into `BlameChainAnalyzer._overlapping_phases(start_us, end_us) -> List[str]`; `annotate_phases(task)` now just calls it on `[task.start_us, task.finish_us)`.
- Added `_first_overlapping_phase(start_us, end_us) -> Optional[str]`, matching the existing single-phase-field convention (`phase_annotations[0]`).
- `_build_flattened_timeline` now calls `_first_overlapping_phase` for every wait-gap segment (`DEPENDENCY_WAIT`/`RESOURCE_WAIT`/`SCHEDULER_WAIT`) and both IDLE-fill code paths (the gap-between-segments case and the final-tail case), not just the EXECUTION_ON_CHAIN case.

## Out of Scope
- The flattened timeline's `phase` field is still a single `Optional[str]` (first overlapping phase only), not a list of every simultaneously-overlapping phase - Part 12.1 calls the flattened timeline "a presentation view," and the underlying `annotate_phases`/`_overlapping_phases` computation already returns the complete list; only the single-field presentation layer picks one. Not changed here - out of this fix's scope (it's about categories getting phase-tagged *at all*, not about a data-model change to carry multiple simultaneous tags through to the timeline).

## Acceptance Test
`PYTHONPATH=. python3 -m pytest tests/unit/test_phase_and_occupancy.py -v` (P3-05, this fix's own regression coverage) plus the full suite and e2e test.

## Verification Log
```
$ PYTHONPATH=. python3 -m pytest tests/unit/test_phase_and_occupancy.py -v
13 passed

$ PYTHONPATH=. python3 -m pytest tests/ -q
231 passed   # cumulative, after all of this round's P3 work

$ PYTHONPATH=. python3 tests/test_e2e.py
Results: 7 passed, 0 failed

$ make check-clean
OK: no ignored files are tracked
```
Manual reproduction before/after: a `cache_cleanup` PhaseSpan [20000,50000) exactly
overlapping a DEPENDENCY_WAIT segment [20000,50000) - `phase=None` before,
`phase='cache_cleanup'` after, category unchanged (DEPENDENCY_WAIT) in both cases.
