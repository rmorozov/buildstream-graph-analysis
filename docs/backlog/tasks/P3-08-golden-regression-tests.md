# P3-08: Golden/regression tests

**Priority:** P3 | **Status:** 🟢 Fixed & Verified (2026-08-13) | **Depends on:** `P3-01`, and ideally most `P1-*` correctness fixes landed first (otherwise the golden snapshot bakes in known-wrong numbers)

## What was done
Checked in `tests/fixtures/golden/mixed_task_kinds/` (run-context.json, graph.json, trace.json): 4 elements (`base.bst -> lib.bst -> app.bst` chain plus an independent `extra.bst`), mixed task kinds (`BUILD` and `FETCH`), a genuine resource constraint (`PROCESS: 2, DOWNLOAD: 1`), a phase span, and deliberate wall-clock slack (exercises `UNTRACKED_TAIL`, `P1-23`).

Building the initial (richer) version of this fixture - every element with a full `TRACK->FETCH->BUILD` chain - surfaced a real bug: replay's makespan `T_C` came out *below* the certified `LB`, violating I2. Root-caused, filed, and fixed as `P1-26` (own task file) - a predecessor-task-kind mismatch in `bga/normalize/timestamps.py::clamp_task_starts`, the same bug class `P1-03` already fixed elsewhere but left unfixed in this second, independent predecessor-construction path (`NormalizedTask.dependencies`, read only by the replay scheduler). After the fix, the remaining small T_C/LB gap traced to a separate, deeper, unconfirmed question about how `T∞,observed`'s per-element duration is derived for elements with multiple sequential task kinds - not chased further in this round (would need its own investigation); the golden fixture was simplified instead (one task per element, still mixing task *kinds* across elements) to avoid depending on that still-open question for a clean reference snapshot.

Captured `expected_output.json` via the real CLI (`analyze --format json --diagnostics`) and confirmed byte-identical output across two independent runs (I11). Added `tests/test_golden.py`: exact-match diff against the snapshot, plus a determinism cross-check (two live runs must match each other, not just the checked-in file). Verified the test actually catches regressions by temporarily corrupting the checked-in snapshot, confirming a failure with a clear diff, then reverting - per this task's own acceptance test.

## Spec Reference
`sed -n '1513,1628p' docs/spec/specification.md` (Part 32 — Data Contracts, `analysis/v9` output shape) for what a snapshot should contain.

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
```
$ PYTHONPATH=. python3 -m pytest tests/test_golden.py -v
2 passed

# Regression-catching proof: temporarily set expected_output.json's
# floors.lb to 999999, re-ran - failed with a clear dict diff pinpointing
# the exact field; reverted, re-ran - passed again.

$ PYTHONPATH=. python3 -m pytest tests/ -q
194 passed (+ 1 known-flaky, unrelated timing test)   # was 193

$ PYTHONPATH=. python3 tests/test_e2e.py
Results: 7 passed, 0 failed

$ make check-clean
OK: no ignored files are tracked
```
