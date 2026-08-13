# P1-12: No determinism harness; no `bga/validation/` package

**Priority:** P1 | **Status:** 🔴 Not Started | **Depends on:** none (but most valuable once P1-01..P1-05 land, since it will catch any nondeterminism they introduce)

## Spec Reference
Read only: `sed -n '1873,1902p' docs/specification.md` (Part 35 — Determinism Contract) and the I11 entry in `sed -n '1720,1780p' docs/specification.md` (Part 34). Also `sed -n '2261,2331p' docs/specification.md` (Part 39 — Implementation Architecture) for the recommended `bga/validation/determinism.py` module location.
Key requirements (quoted): "No Python hash iteration order, dictionary order, filesystem order, or concurrency-dependent ordering may influence results." Determinism harness: run the same analysis "N >= 100 times" and compare canonical serialized output.

## Current Broken Behavior
- No file anywhere implements this repeated-run comparison.
- No `bga/validation/` package exists (spec Part 39 recommends `invariants.py`, `determinism.py` there).

## Required Fix
1. Create `bga/validation/__init__.py` and `bga/validation/determinism.py`.
2. Implement a `run_determinism_check(run_dir, n=100)` function (or similar) that: runs `BuildEfficiencyAnalyzer(...).analyze()` `n` times against the same input, canonically serializes each `AnalysisResult` (stable key ordering, no floats where ints are expected per Part 3.1 — reuse whatever JSON serialization the CLI's `--format json` path already uses, don't invent a second serializer), and asserts all `n` outputs are byte-identical.
3. Report which specific fields differ if a mismatch is found (don't just say "mismatch" — this is meant to be a diagnostic tool, so pinpoint the differing key path).
4. This is primarily a **test/validation tool**, not user-facing analysis output — it's fine (expected) for it to be slow (100 full pipeline runs); mark it appropriately if you add a pytest marker system (see `P3-*` test tasks for the `@pytest.mark.slow` convention).

## Out of Scope
- Don't move `_compute_confidence` or other invariant-checking logic out of `bga/analyzer.py` into `bga/validation/` as part of this task — that broader architecture move is `P1-15`, done later. This task only adds the new determinism-harness capability; it doesn't have to relocate existing code.
- Don't try to fix any nondeterminism you find as part of *writing* the harness — if it finds a real nondeterminism bug, log it as a new tracker row and let a future task fix it, so this task stays scoped to "build the harness."

## Acceptance Test
1. Run the harness against the existing `tests/test_e2e.py` fixture with `n=100` (or a smaller `n` like 10 for a fast CI-friendly check, with `n=100` reserved for a `slow`-marked test) and confirm it reports full determinism (no mismatches) — if it finds a mismatch, that's a real bug to log separately, not a reason to consider this task's harness itself broken (the harness doing its job by finding a bug is success, not failure).
2. `PYTHONPATH=. python3 tests/test_e2e.py` still passes.

## Verification Log
_(append real command + output here once run, before marking 🟢)_
