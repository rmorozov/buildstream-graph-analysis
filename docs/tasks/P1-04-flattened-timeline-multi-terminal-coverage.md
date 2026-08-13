# P1-04: Flattened timeline undercounts on multi-terminal / independent-branch graphs

**Priority:** P1 | **Status:** 🟢 Fixed & Verified (2026-08-13) | **Depends on:** none (`P1-03`, `P1-19` both done)

## What was fixed
`P1-19` resolved flattened-timeline coverage for any single connected component. This task closed the remaining gap: graphs with genuinely independent terminals (no dependency relationship between them at all - e.g. two unrelated requested targets in one CI run).

Three pieces, all needed together:

1. **Identify every genuine terminal, not just the single max-finish one.** `bga/analyzer.py::_compute_attribution` now computes `terminal_element_uids` (elements with `requested_target = True`, or with no successor in `graph.dependencies`) and passes the corresponding task keys to `compute_full_attribution` as `terminal_tasks`, instead of relying on the single-max-finish default (`P1-03`'s fix, still the correct default when the caller doesn't know its terminals explicitly).
2. **Walk all terminals deterministically, without re-visiting shared tasks.** `compute_full_attribution` now sorts `terminal_tasks` (finish time descending, task key ascending - Part 35 determinism) and threads a shared `already_covered: Set[str]` through every `build_blame_chain` call, so if two terminals' walks converge on shared upstream lineage, the second walk stops there instead of re-adding it.
3. **Prevent overlapping segments when independent terminals run concurrently in wall-clock time.** This was the subtle part: two tasks with *no dependency relationship at all* can still temporally overlap (e.g. both scheduled to run at the same time using separate capacity). Task-identity dedup (`already_covered`) doesn't catch that. New `covered_intervals: List[Tuple[int, int]]`, also threaded through every walk: before a node is added to a chain, its own `[wait_start or execution_start, execution_end)` span is checked against every interval a higher-priority walk (processed first, by the same finish-time-descending order) already claimed; on overlap, the walk stops there rather than double-claiming that wall-clock window. Verified with a fixture where two independent terminals genuinely overlap in time (`tests/unit/test_multi_terminal_coverage.py::test_independent_terminals_running_concurrently_do_not_double_count`).
4. **Fill genuinely uncovered gaps with `IDLE`, not silence.** Discovered while fixing this: no code anywhere in the pipeline ever produced an `IDLE` segment - `idle_us` was structurally always `0`. `_build_flattened_timeline` now walks the final sorted segment list and fills any gap (before the first segment, between two segments, after the last) with an `AttributionSegment(category=IDLE)`, spanning `[min_start, max_finish)` of the task horizon. This is what makes exact identity (`Σ == H`) hold even when there's genuine dead time between disconnected components, not just when everything happens to be covered.

## Spec Reference
`sed -n '788,839p' docs/specification.md` (Part 12 — Flattened Timeline). "Segments are ordered / segments do not overlap / segments cover the selected horizon." `Σ segment_duration == H` exactly.

## Out of Scope (unchanged)
- The reporting behavior for cases where coverage still comes up short (`P1-05`) - not needed here since coverage is now exact, but the violation-reporting mechanism itself is still a separate task for other scenarios.
- `select_dependency_blame`'s tie-break logic - untouched, already correct.

## Acceptance Test — as executed
1. `tests/unit/test_multi_terminal_coverage.py::test_independent_terminal_extending_horizon_now_covered` (renamed from `..._is_dropped_p1_04`) - now asserts exact identity (`Σ == H`) and `idle_us == 100000` for the genuine gap, replacing the old "documents the known shortfall" assertion.
2. `tests/unit/test_multi_terminal_coverage.py::test_independent_terminal_nested_within_the_other` (renamed, no longer "harmless coincidence" - now correct because `covered_intervals` actually prevents double-counting the nested case).
3. New: `test_independent_terminals_running_concurrently_do_not_double_count` (the overlap case) and `test_three_independent_terminals_all_covered` (3+ components, per the original acceptance test's request).
4. Full suite: `PYTHONPATH=. python3 -m pytest tests/ -v` — 45 passed, 0 xfailed.

## Verification Log
```
$ PYTHONPATH=. python3 -m pytest tests/unit/test_multi_terminal_coverage.py -v
4 passed

$ python3 -c "... synthetic_multi_subproject attribution ..."
idle_us: 0   # correctly unaffected - single connected component, no real gaps

$ PYTHONPATH=. python3 -m pytest tests/ -v
45 passed, 0 xfailed
```
