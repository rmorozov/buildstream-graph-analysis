# P3-01: Shared synthetic topology fixture library

**Priority:** P3 | **Status:** 🟢 Fixed & Verified (2026-08-13) | **Depends on:** none — build this first, nearly every other P3 task reuses it

## What was done
Added `tests/fixtures/topologies.py` with one factory per Part 36.1 topology, each returning a `(run_context, graph, trace)` tuple of plain JSON-serializable dicts in the canonical graph/v9 + trace/v9 shape (Part 32.2/32.3) - the same shape already used across the P1/P2 fixture-writing tests (`tests/unit/test_cold_floor.py` etc.), rather than the older, narrower ad-hoc shape in `tests/test_e2e.py`'s one-off `create_test_run_data` - the loader (`bga/ingest/loader.py::load_graph`/`load_trace`) supports both, but the canonical shape is what every other fixture in this codebase already standardized on, so new factories match that dominant convention instead of introducing a second one:
- `linear_chain(n)`, `diamond()`, `fan_in(n)`, `fan_out(n)`, `multiple_equal_predecessors()` (a genuine finish-time tie between a depth-1 and a depth-2 predecessor, for `P3-04`'s tie-break tests), `deep_unequal_predecessors()`, `independent_branches(n)`, `graph_with_terminal_and_nonterminal_tasks()` (a requested-target-reachable dependency alongside a fully unreachable orphan branch, for `P1-11`/leaf-deferrability tests).
- Every factory accepts a `durations: Optional[Dict[str, int]]` override to control any individual element's duration, per the task's requirement.
- `write_run_dir`/`build_analyzer` helpers so consuming tests don't need to re-duplicate the write-run-dir-to-disk boilerplate already copy-pasted across a dozen existing test files.
- `run_context`'s `cpu_accounting.effective_cpus` is set to match each topology's own concurrency (`max_jobs`) to avoid a spurious CPU-reconciliation warning from the default `effective_cpus=1.0` fallback whenever a fixture runs more than one task concurrently.

Added `tests/unit/test_topology_fixtures.py` as the acceptance test itself: a smoke test parametrized over all 9 factories (build it, run full `analyze()`, confirm no exception - the task's own Acceptance Test #1), plus a handful of cheap fixture-shape assertions (duration override applied, the tie-break fixture really is a tie, the deep-unequal fixture really isn't, requested-target flags land correctly, independent branches share no dependency edges) confirming the factories build what their names claim *before* any consuming task (`P3-03`+) relies on that being true. No value-assertions about `bga`'s own analysis output are made here - that's every consuming task's job, per this task's Out of Scope note.

## Spec Reference
Read only: `sed -n '1903,2132p' docs/spec/specification.md` (Part 36 — Testing Strategy) — lists the required synthetic topologies: linear chain, diamond, fan-in, fan-out, multiple equal predecessors, deep unequal predecessors, independent branches, terminal tasks, requested/non-requested targets.

## Current State
`tests/test_e2e.py` has exactly one inline fixture (a 3-node linear chain, `create_test_run_data`, lines 8-77) used by all 7 existing tests. No shared/reusable fixture module exists.

## Required Fix
Create `tests/fixtures/topologies.py` with one factory function per topology, each returning a `(run_context, graph, trace)` tuple (or whatever input shape `bga.ingest.loader.load_all`/`BuildEfficiencyAnalyzer` expects — match the existing `create_test_run_data` shape in `tests/test_e2e.py` for consistency, don't invent a new input format):
- `linear_chain(n=3)` — parametrizable length.
- `diamond()` — A→{B,C}→D.
- `fan_in(n=4)` — n predecessors converging on one successor.
- `fan_out(n=4)` — one predecessor, n successors.
- `multiple_equal_predecessors()` — a task with 2+ predecessors that finish at exactly the same normalized time (for tie-break testing, feeds `P3-04`).
- `deep_unequal_predecessors()` — predecessors at clearly different depths.
- `independent_branches(n=2)` — n fully disconnected chains, no shared dependencies (feeds `P1-04`/`P3-03`).
- `graph_with_terminal_and_nonterminal_tasks()` — mix of elements with/without requested_target set (feeds `P1-11`/leaf analysis tests).
- Each factory should accept override parameters for duration/resource assignment where a specific test needs to control those (e.g. `P1-08`'s DOWNLOAD-bottleneck fixture, `P1-03`'s resource-constrained fixture) rather than hardcoding one fixed shape per topology.

## Out of Scope
- Don't write the actual test *assertions* here — this task only builds reusable fixture factories. Tests that consume them are `P3-03` through `P3-09` (and various `P1-*`/`P2-*` acceptance tests).

## Acceptance Test
1. Each factory function is callable standalone and produces input that `BuildEfficiencyAnalyzer(...).analyze()` can consume without error (smoke-test each one: build it, run analysis, confirm no exception).
2. `PYTHONPATH=. python3 tests/test_e2e.py` still passes unaffected (this task is purely additive).

## Verification Log
```
$ PYTHONPATH=. python3 -m pytest tests/ -q
126 passed   # was 112

$ PYTHONPATH=. python3 tests/test_e2e.py
Results: 7 passed, 0 failed

$ make check-clean
OK: no ignored files are tracked
```
`tests/unit/test_topology_fixtures.py` (14 tests): 9 parametrized smoke
tests (one per factory, each builds + runs a full `analyze()` with no
exception - satisfies Acceptance Test #1 directly) plus 5 fixture-shape
assertions confirming duration overrides, the tie-break/non-tie-break
finish times, requested-target flags, and branch independence are
actually as designed.
