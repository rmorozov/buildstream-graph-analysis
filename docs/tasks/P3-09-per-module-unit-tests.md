# P3-09: Per-module unit test split

**Priority:** P3 | **Status:** 🔴 Not Started | **Depends on:** none, but naturally absorbs pieces of `P3-03` through `P3-06` — coordinate to avoid duplicate test files; check what those tasks already created before adding new files with overlapping names

## Spec Reference
No single spec section — this is a structural test-suite improvement covering `bga/normalize/`, `bga/occupancy/`, `bga/graph/`, `bga/replay/`, `bga/utilisation/` in isolation (the modules not already given a dedicated test file by another P3 task).

## Current State
Only `tests/test_e2e.py` exists — a single full-pipeline test against one fixture. No module gets isolated, fast, pure-function-level testing.

## Required Fix
Create, for each module lacking dedicated coverage after the other P3 tasks have landed their pieces (check the tracker first — don't duplicate `test_attribution_identity.py`, `test_tie_break.py`, `test_resource_wait.py`, `test_phase_and_occupancy.py`, `test_cpu_reconciliation.py`, `test_cold_floor.py`, `test_criticality_montecarlo.py`):
- `tests/unit/test_normalize.py` — quantization determinism (`quantize_timestamp` applied once, not pairwise, per Part 3.2), ready-time computation, ordering-violation detection (small gap absorbed by quantization vs. genuine violation, Part 3.3), start-clamp preserves finish (Part 3.4).
- `tests/unit/test_edg.py` — depth/reachability/dominators/critical-path/slack computation on small hand-built graphs with known-correct expected values (not just "key exists" — this is the exact class of check that would have caught the M6 `max_depth: 0` bug).
- `tests/unit/test_replay.py` — deterministic replay scheduler basic correctness, capacity sweep monotonicity where spec says it should be monotonic.
- `tests/unit/test_utilisation.py` — CPU bucket computation, oversubscription-warning evidence requirements (Part 30.3 — must require corroborating evidence, not just `builders × max_jobs > effective_cpus` alone).

Each should be fast, hermetic (no filesystem/network I/O beyond in-memory fixture construction), and use `pytest.mark.parametrize` where testing the same logic across multiple small inputs.

## Out of Scope
- Don't re-test things already covered by other P3 tasks' dedicated files — check the tracker before writing a new test, to avoid duplicate/conflicting coverage.

## Acceptance Test
`PYTHONPATH=. python3 -m pytest tests/unit/ -v` — all module-level unit tests pass, and collectively they should be fast (this whole directory should run in well under a few seconds — if any single test takes long, it probably belongs in a `slow`-marked integration file instead).

## Verification Log
_(append real command + output here once run, before marking 🟢)_
