# P3-01: Shared synthetic topology fixture library

**Priority:** P3 | **Status:** 🔴 Not Started | **Depends on:** none — build this first, nearly every other P3 task reuses it

## Spec Reference
Read only: `sed -n '1903,2132p' docs/specification.md` (Part 36 — Testing Strategy) — lists the required synthetic topologies: linear chain, diamond, fan-in, fan-out, multiple equal predecessors, deep unequal predecessors, independent branches, terminal tasks, requested/non-requested targets.

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
_(append real command + output here once run, before marking 🟢)_
