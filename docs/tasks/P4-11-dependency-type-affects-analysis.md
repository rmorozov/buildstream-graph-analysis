# P4-11: `dependency_type` (build vs. runtime) doesn't affect analysis anywhere

**Priority:** P4 | **Status:** 🟢 Fixed & Verified (2026-08-14) | **Depends on:** `P4-10` (done - the real ingestion pipeline that can now supply genuine `dependency_type`-carrying input to test against, not only synthetic fixtures)

## Spec Reference
Part 5.1 (`build`/`runtime` dependency scope, explicit in the graph model), Part 32.2 (`graph/v9`'s `dependency_type` field), Part 7 (ready-time gating), Part 24/25 (leaf/deferrability, blast radius - structural analysis).

## Background
Filed while building `P4-10` (real ingestion pipeline). `bst_show_to_graph.py` (`P4-08`) correctly populates `DependencyEdge.dependency_type` (`"build"` or `"runtime"`) from a real project's `%{build-deps}`/`%{runtime-deps}`, but grepping `bga/` shows every consumer of the dependency graph treats every edge identically, regardless of type - `dependency_type` is stored but never read as a genuine tri-state anywhere in the analysis pipeline. See `docs/ingestion-pipeline.md`'s "`dependency_type`'s effect on analysis" section for the full context.

Per BuildStream's own semantics (confirmed via its docs while researching `P4-08`): a `build`-type edge genuinely gates the successor's build start (the dependency's product must be staged first, before the successor's own build can begin). A `runtime`-only edge does not - "an element's runtime dependencies are not available to the element at build time," so a runtime-only dependency's build finishing has no causal bearing on when the successor's build can start.

## Current Broken Behavior
- `bga/normalize/timestamps.py::compute_ready_times`/`_element_build_finish`: every dependency edge (`graph.dependencies`) gates the successor's BUILD-kind readiness on the predecessor's BUILD finish, regardless of `dependency_type` - a pure `runtime`-only edge over-constrains ready time (the successor is being made to wait for something it doesn't actually need until runtime, after its own build).
- `bga/graph/edg.py`'s structural algorithms (depth, reachability, critical path, dominators) treat every edge as a plain graph edge - not wrong for structural analysis in general (Part 24/25 wants reachability/blast-radius over the *full* dependency graph, both types), but means there's no way to separately ask "what's the critical path considering only build-gating edges" vs. "full structural reachability."
- `bga/attribution/blame_chain.py`/`bga/replay/scheduler.py`: same BUILD-to-BUILD gating assumption, same over-constraint risk for runtime-only edges.

## Required Fix
1. Scope ready-time/critical-path gating (Part 7, `compute_ready_times`, replay's readiness check) to `build`-type (and BuildStream's default `all`, which `bst_show_to_graph.py` already collapses to `"build"` per `P4-08`) edges only - a `runtime`-only edge should not force the successor's BUILD to wait for the predecessor's BUILD to finish.
2. Keep `runtime`-only edges fully counted for structural analysis (reachability, blast radius, leaf/deferrability, Part 24/25) - only the *gating* semantics change, not the graph's structural shape.
3. Determine whether this changes any of the flagship fixtures' (`tests/fixtures/synthetic_multi_subproject/`, `tests/fixtures/topologies.py`) results - they currently synthesize `dependency_type: "build"` for every edge (confirmed: `build_model.py` hardcodes `"dependency_type": "build"`), so this fix should be a no-op for them unless a new runtime-only-edge test fixture is added.

## Out of Scope
- Don't invent a third dependency-type-related category or spec concept not already in Part 5.1/32.2 - `build`/`runtime` is the full tri-state (a dependency not of type `build` is `runtime`, no `all` value is ever stored - `P4-08` already collapses `all` to `"build"` at ingestion).
- Don't change `bst_show_to_graph.py`'s own `dependency_type` extraction (`P4-08`) - that part is already correct and verified.

## Acceptance Test
A fixture with two elements: A is a `runtime`-only dependency of B, with A's BUILD finishing *after* B's BUILD would otherwise be ready to start (e.g. no other constraint). B's BUILD must NOT be gated on A's BUILD finish (ready_us should not be pushed back by A), while a structural query (e.g. `is_reachable(A, B)`) must still return true. A parallel fixture with A as a `build`-type dependency of B under the same timing must show the existing gating behavior unchanged (regression).

## What was built
Filtered every ready-time/ordering/critical-path *gating* consumer to `build`-type edges only, while deliberately leaving every purely-structural consumer (reachability, blast radius, leaf/deferrability, `unweighted_depth`/`weighted_depth`, dominators - Part 24/25) reading the full, unfiltered graph:

- `bga/normalize/timestamps.py::compute_ready_times`/`validate_ordering`/`clamp_task_starts` - the predecessor maps and `NormalizedTask.dependencies` now skip `dependency_type == "runtime"` edges.
- `bga/analyzer.py`'s `explicit_predecessors` construction (feeds the blame-chain's "responsible predecessor" selection, Part 7.1) - same filter.
- **`bga/graph/edg.py::compute_critical_path`/`compute_slack`** (Part 14.1, T∞,observed): found and fixed a **more severe issue than the task's original ready-time-only scope** while verifying the acceptance-test fixture - `compute_critical_path` was summing a `runtime`-only edge's duration into the "critical path" as if it gated ordering, which directly contradicts Part 14.1's own certification claim ("no schedule with unlimited relevant capacity can complete faster than this value" - false if the value counts a non-gating edge as gating; a real schedule could beat it by simply not waiting on that edge). Added an `exclude_dependency_types` parameter to `build_element_graph`/`compute_in_out_degree` (default `None` = unfiltered, preserving every other call site's behavior exactly) and passed `{"runtime"}` from `compute_critical_path`/`compute_slack` (which must stay mutually consistent - `compute_slack` consumes `compute_critical_path`'s output) and from `bga/diagnostics/analyzer.py`'s Monte-Carlo criticality-probability sampling (Part 26, the same critical-path concept under perturbation - would otherwise disagree with the analyzer's own single observed critical path over what "the critical path" means).
- Confirmed via `tests/fixtures/synthetic_multi_subproject/`'s own model (hardcodes `dependency_type: "build"` for every edge) that this is a genuine no-op for every existing pinned fixture - byte-identical results.
- Verified against **real typed input** from the completed `P4-10` pipeline: `tests/fixtures/bst_show_project/` already has a genuine `runtime`-only edge (`subproj-junction.bst:libfoo.bst -> app.bst`) - a real end-to-end run (`bst_extract_run.py` + `bga analyze`) completes with no errors and no ordering-violation false positives.

## Verification Log
```
$ PYTHONPATH=. python3 -m pytest tests/unit/test_dependency_type_gating.py -v
10 passed   # direct unit tests on compute_ready_times/validate_ordering/
            # clamp_task_starts/compute_critical_path/compute_reachability,
            # plus one end-to-end test via analyze_run

$ PYTHONPATH=. python3 -m pytest tests/test_synthetic_multi_subproject.py -q
16 passed   # flagship fixture unaffected - every edge is dependency_type:
            # "build" there, confirming the filter is a genuine no-op

$ PYTHONPATH=. python3 -m pytest tests/ -q
324 passed (with bst on PATH) / 320 passed, 4 skipped (without)   # was 314/310+4

# Real end-to-end run against tests/fixtures/bst_show_project's genuine
# runtime-only edge (subproj-junction.bst:libfoo.bst -> app.bst):
$ bst -C tests/fixtures/bst_show_project build app.bst > real_build.log 2>&1
$ PYTHONPATH=. python3 tools/bst_extract_run.py tests/fixtures/bst_show_project real_build.log /tmp/extracted_run
$ PYTHONPATH=. python3 -m bga.cli analyze /tmp/extracted_run
# full report produced, no crash, no false-positive ordering violations

$ PYTHONPATH=. python3 tests/test_e2e.py
Results: 7 passed, 0 failed

$ make check-clean
OK: no ignored files are tracked
```
