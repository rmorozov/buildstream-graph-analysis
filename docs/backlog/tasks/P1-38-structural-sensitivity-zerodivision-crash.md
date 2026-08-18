# P1-38: `compute_sensitivity` crashes with `ZeroDivisionError` on real negative-slack data

**Priority:** P1 (a straight interpreter crash, not a wrong number - worse than most tracked correctness gaps) | **Status:** 🟢 Done | **Depends on:** none

## Spec Reference

Part 34 (Sensitivity Analysis): "Determine how much improving each element would help overall... uses critical path membership and slack as a proxy" - a reporting feature, not expected to ever crash the whole `analyze` run regardless of the input trace's shape.

## Background

Found via real data, not a hand-built fixture: the new `examples/02-deep-chain-mixed-kinds` real BuildStream project (`bst-examples` CI job, see `examples/README.md`) built successfully, but `bga analyze -d` crashed with an uncaught `ZeroDivisionError`, exit code 2:

```text
File "bga/structural/analyzer.py", line 265, in compute_sensitivity
    sensitivity_scores[key] = 0.1 / (1.0 + slack / 1000000.0)
ZeroDivisionError: float division by zero
```

`compute_sensitivity` (`bga/structural/analyzer.py:243-275`) computes, for every element:

```python
slack = slacks.get(key, 0)  # CP elements, line 259
sensitivity_scores[key] = 1.0 / (1.0 + slack / 1000000.0)      # line 261
# or, for non-CP elements:
slack = slacks.get(key, float('inf'))                          # line 264
sensitivity_scores[key] = 0.1 / (1.0 + slack / 1000000.0)      # line 265
```

Both formulas assume `slack >= 0` (a decay function that only makes sense for non-negative slack) but `slack` comes from `_compute_all_slacks()`, which - confirmed by this real crash - can produce negative values. The denominator `1.0 + slack / 1_000_000.0` is exactly `0` when `slack == -1_000_000` (i.e. -1 second, in microseconds) and **negative** whenever `slack < -1_000_000`, which would silently produce a nonsensical negative "sensitivity" score rather than crash - an even less obvious failure mode than the crash itself.

This is not a contrived edge case: `examples/02-deep-chain-mixed-kinds`'s real topology (a depth-4 chain of real, multi-second `sleep`-based elements plus a near-instant `compose` stage) reproduces it on every CI run deterministically. Real negative slack is plausible generally too - this codebase already has a documented precedent for legitimate negative-duration/negative-gap values elsewhere (`P1-27`, `P1-36`), so `_compute_all_slacks()` producing a negative value isn't necessarily itself a bug; `compute_sensitivity`'s formula just doesn't handle it.

## Required Fix

1. `compute_sensitivity` must not crash for any real `slack` value, including negative slack at or below -1,000,000us.
2. Decide and document the intended semantics for negative slack (e.g. clamp to `0` before the decay formula, treat as "maximally sensitive" since negative slack indicates the element is already behind, or some other explicit, documented rule) rather than leaving the current implicit "assumes slack >= 0" assumption unstated.
3. Whatever the chosen fix, it must not silently produce a negative or otherwise out-of-range sensitivity score for any input - if the fixed formula can't guarantee a sane range for pathological slack values, clamp or flag explicitly rather than passing a nonsensical number through to the report.

## Out of Scope

- Don't investigate *why* this specific project produces exactly -1,000,000us slack for one element (that's `_compute_all_slacks`/critical-path-adjacent behavior, not `compute_sensitivity`'s own bug) - this task is scoped to `compute_sensitivity` not crashing or producing nonsense on whatever slack value it's given.
- Don't change `compute_sensitivity`'s CP-vs-non-CP weighting (1.0 vs 0.1 base) or its role in the broader structural analysis report - only the divide-by-zero/negative-denominator handling.

## Acceptance Test

1. `slack == -1_000_000` (exact) → no crash, a defined, in-range sensitivity score.
2. `slack < -1_000_000` → no crash, no negative sensitivity score.
3. `slack >= 0` (the previously-only-tested range) → unchanged behavior/values.
4. Re-run `bga analyze -d` against `examples/02-deep-chain-mixed-kinds`'s real run directory (from a `bst-examples` CI artifact, or a local `tools/bst_extract_run.py` extraction) - exits 0, produces a real structural/sensitivity section.
5. Full suite green.

## Verification Log

Fixed by clamping slack to `max(slack, 0)` before the decay formula in both the CP and non-CP branches of `compute_sensitivity` (`bga/structural/analyzer.py`) - negative slack is treated as maximally sensitive for its tier rather than extrapolating the decay curve backwards, avoiding both the zero-denominator crash and the silent-negative-score case.

New tests (`tests/unit/test_structural_sensitivity.py`, 3 tests): slack exactly -1,000,000us (the real crash value) does not crash and produces non-negative scores; slack well past that point (-2,000,000us) likewise; ordinary non-negative slack produces unchanged, exact expected values (regression guard that the fix doesn't touch the normal-input case).

```text
$ python3 -m pytest tests/unit/test_structural_sensitivity.py -v
3 passed
$ python3 -m pytest -q   # full suite
394 passed, 11 skipped
$ make lint
All checks passed!
```
