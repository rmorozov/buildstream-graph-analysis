# P3-09: Per-module unit test split

**Priority:** P3 | **Status:** 🟢 Fixed & Verified (2026-08-13) | **Depends on:** none, but naturally absorbs pieces of `P3-03` through `P3-06` — coordinate to avoid duplicate test files; check what those tasks already created before adding new files with overlapping names

## What was done

Added the four module test files this task names, none of which existed yet (checked first, per this task's own coordination note):

- `tests/unit/test_normalize.py` (11 tests): quantization determinism and transitive equality, ready-time computation, small-gap-absorbed-by-quantization vs. genuine ordering violation, start-clamp preserves finish, and a direct regression test for `P1-26`'s dependency-mapping fix.
- `tests/unit/test_edg.py` (11 tests): depth/in-out-degree/reachability/dominators/critical-path/slack on a hand-built diamond and linear chain, with exact hand-computed expected values (not "key exists" checks - the class of check that would have caught the M6 `max_depth: 0` bug, `P1-18`), plus a cycle-detection test.
- `tests/unit/test_replay.py` (5 tests): dependency-chain scheduling correctness, capacity-forced serialization vs. parallelism, capacity-sweep monotonicity (endpoints match hand-computed serial/parallel makespans), and a regression guard for the sweep's first-sample NaN bug (`P1-14`-adjacent).
- `tests/unit/test_utilisation.py` (9 tests): CPU bucket routing (useful/retry/rebuild/idle), max-observed-concurrency tracking, and the oversubscription-evidence contract (Part 30.3) - config-only oversubscription (`builders * max_jobs > effective_cpus`) alone only ever produces `evidence=LOW`, never one of the two stronger evidence strings, which require real observed corroboration.

CPU reconciliation (I9) is `P3-06`'s file, not duplicated here; attribution identity is `P3-03`'s.

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

```text
$ PYTHONPATH=. python3 -m pytest tests/unit/test_normalize.py tests/unit/test_edg.py tests/unit/test_replay.py tests/unit/test_utilisation.py -v
36 passed

$ time PYTHONPATH=. python3 -m pytest tests/unit/ -q
202 passed in ~11s
# The 4 new files here each run in ~0.2-0.3s (fast, hermetic, no I/O
# beyond in-memory objects) - the directory total is dominated by
# pre-existing slower tests (test_graph_performance.py's timing
# assertions, test_determinism.py's n=100 full-scale check, which this
# repo's pytest config runs by default rather than gating behind -m slow).

$ PYTHONPATH=. python3 -m pytest tests/ -q
231 passed

$ PYTHONPATH=. python3 tests/test_e2e.py
Results: 7 passed, 0 failed

$ make check-clean
OK: no ignored files are tracked
```
