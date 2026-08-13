# P1-04: Flattened timeline undercounts on multi-terminal / independent-branch graphs

**Priority:** P1 | **Status:** 🔴 Not Started — scope now precisely bounded and reproducible (`P1-19` landed 2026-08-13) | **Depends on:** none (`P1-03`, `P1-19` both done)

## `P1-19` is done — this is now a distinct, narrower problem
`P1-19` (intra-element phase sequencing + inter-element predecessor edges for every task kind, not just `BUILD`) turned out to fully resolve flattened-timeline coverage for any **single connected component** — the blame-chain walk's existing tie-break always follows the objectively slowest predecessor, so it naturally traces the graph's true critical path end to end, which by construction spans the full task horizon when everything is reachable from it. See `docs/tasks/P1-19-flattened-timeline-residual-coverage.md` for the full explanation of why an occupancy-sweep approach wasn't needed after all.

What's left, confirmed empirically (not just theorized) via `tests/unit/test_multi_terminal_coverage.py::test_independent_terminal_extending_horizon_is_dropped_p1_04`: two **fully independent** elements (no dependency relationship between them at all) each start their own chain walk only if picked as *the* default terminal (the single task with the overall maximum finish time, per `P1-03`'s fix). Whichever one isn't picked contributes **zero** attribution unless its own time span happens to be nested within the picked terminal's span (in which case it's coincidentally invisible but harmless to the sum - see the sibling passing test in the same file for that case).

## Spec Reference
Read only: `sed -n '788,839p' docs/specification.md` (Part 12 — Flattened Timeline).
Key requirement (quoted): "segments are ordered / segments do not overlap / segments cover the selected horizon." "There is no generic interval-eclipsing engine." No category may "win" by priority.

## Current Broken Behavior
File: `bga/attribution/blame_chain.py`, `compute_full_attribution`'s default `terminal_tasks` (single task, max finish time - see `P1-03`) and `build_blame_chain` (single linear walk from that one task). A second, fully disconnected element/component is never walked at all, so its `task_attributions` (computed for it, like every task, in `compute_full_attribution`'s per-task loop) never becomes a flattened-timeline segment. `reconcile_attribution` sums only from `segments`, so this loss is invisible downstream — nothing flags it (that reporting gap is `P1-05`, not this task).

## Required Fix
1. Identify all **genuine** terminal tasks - tasks belonging to elements that (a) have `requested_target = True` (or, absent that, no successors in the real dependency graph - not the old broken finish-time-matching heuristic `P1-03` removed) and (b) are not reachable from any other terminal's own walk. Reuse `explicit_predecessors`/the graph's real structure for this, not a heuristic.
2. Run the backward blame-chain walk (`build_blame_chain`, already correct after `P1-03`/`P1-19`) from **every** genuine terminal, merging the resulting segments. Since each walk only follows the objectively-slowest-predecessor tie-break through its own connected component, walks from genuinely independent components should never revisit the same task - no dedup logic should be needed if terminal identification (step 1) is correct, but verify this empirically with the two-independent-terminal fixture below rather than assuming it.
3. Confirm the flattened timeline now covers the full task horizon `H` for a graph with genuinely disconnected components.

## Out of Scope
- Don't add the violation-reporting behavior for cases where coverage still comes up short after this fix — that's `P1-05`.
- Don't touch `select_dependency_blame`'s tie-break logic — it's correct and already doing the right thing (see `P1-19`); this task is only about *which terminals get walked*, not how a walk picks its own predecessors.

## Acceptance Test
1. `tests/unit/test_multi_terminal_coverage.py::test_independent_terminal_extending_horizon_is_dropped_p1_04` currently documents the gap with `assert total == 200000` (the buggy shortfall) and an explicit comment: once fixed, change that assertion to `assert total == h` (exact identity) and update the docstring/comment accordingly.
2. `tests/unit/test_multi_terminal_coverage.py::test_independent_terminal_nested_within_the_other_is_invisible_but_harmless` must still pass unchanged (that case already passes today, coincidentally, and should keep passing for the right reason once this is properly fixed).
3. Add a third case with more than two independent components, and one with three-plus elements per component (not just single-task terminals) for broader coverage once the above two are solid.
4. `PYTHONPATH=. python3 -m pytest tests/ -v` — full suite green.

## Verification Log
_(append real command + output here once run, before marking 🟢)_
