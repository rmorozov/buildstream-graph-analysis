# P3-08: Golden/regression tests

**Priority:** P3 | **Status:** 🔴 Not Started | **Depends on:** `P3-01`, and ideally most `P1-*` correctness fixes landed first (otherwise the golden snapshot bakes in known-wrong numbers)

## Spec Reference
`sed -n '1513,1628p' docs/specification.md` (Part 32 — Data Contracts, `analysis/v9` output shape) for what a snapshot should contain.

## Required Fix
1. Pick one or two of the larger/more realistic topologies from `P3-01`'s fixture library (or a hand-built more elaborate fixture resembling a real small BuildStream project — several elements, mixed task kinds, at least one resource constraint) and check it into `tests/fixtures/golden/<name>/` (run-context.json, graph.json, trace.json).
2. Run the full pipeline once (after confirming `P1-*` fixes are in place — check the tracker), capture the resulting `analysis/v9` JSON output, and check it in as `tests/fixtures/golden/<name>/expected_output.json`.
3. Write `tests/test_golden.py`: run the pipeline against each golden fixture and diff the output against the checked-in expected JSON — exact match (or a documented, narrow tolerance only for genuinely non-deterministic fields, if any legitimately exist — there shouldn't be any per I11).
4. Document in a comment at the top of `tests/test_golden.py` how to regenerate the expected output when a deliberate behavior change is made (e.g. a script or one-liner command), so future intentional changes don't look like mysterious regressions.

## Out of Scope
- Don't use this as your primary correctness-testing mechanism — golden tests catch *regressions*, they don't explain *why* something changed. Keep the targeted unit/invariant tests (`P3-03` through `P3-07`) as the primary correctness signal; this is a coarse safety net on top.

## Acceptance Test
`PYTHONPATH=. python3 -m pytest tests/test_golden.py -v` — passes against the checked-in snapshot. Also confirm intentionally breaking something (temporarily) causes this test to fail with a clear diff, then revert — proving it actually catches regressions.

## Verification Log
_(append real command + output here once run, before marking 🟢)_
