# P2-07: Timestamp quantization uses floating-point division instead of integer arithmetic

**Priority:** P2 (low practical risk for realistic BuildStream timestamps - int64 microseconds stay well within float64's exact-integer range - but an avoidable, spec-adjacent precision hygiene issue) | **Status:** 🟢 Done | **Depends on:** none

## Spec Reference
Part 3.1: "All internal timestamps and durations use int64 microseconds... No floating-point arithmetic is used for timeline accounting" (`docs/spec/specification.md:193-215`). Part 3.2: quantization is defined conceptually as `round(ts / epsilon) * epsilon`, but "the implementation must use a documented deterministic rounding rule" (`docs/spec/specification.md:219-245`) - the conceptual formula is not itself a license to use real floating-point division.

## Background
Raised by an external review; independently verified against the current code before filing.

`quantize_timestamp` (`bga/normalize/timestamps.py:50-66`):
```python
return round(ts_us / epsilon_us) * epsilon_us
```
`ts_us / epsilon_us` is Python 3 true division - a float result - before `round()` (which uses round-half-to-even/banker's rounding for exact `.5` ties) and multiplication back into an integer. This works correctly for realistic BuildStream timestamps (microsecond values well under float64's 2^53 exact-integer boundary), so this is not a currently-observed correctness bug - but it's real, avoidable floating-point arithmetic in a code path Part 3.1 explicitly says should have none, and the tie-breaking behavior (`round()`'s banker's rounding) isn't explicitly documented anywhere as the chosen deterministic rounding rule Part 3.2 requires.

## Required Fix
1. Replace the float division + `round()` with pure integer arithmetic, e.g. `((ts_us + epsilon_us // 2) // epsilon_us) * epsilon_us` for round-half-up, or an equivalent integer formulation for whatever tie policy is chosen.
2. Explicitly choose and document the tie policy (e.g. round-half-up vs round-half-to-even) in the function's own docstring, satisfying Part 3.2's "must use a documented deterministic rounding rule" requirement directly rather than implicitly inheriting Python's `round()` default.
3. Verify the new integer formula produces identical results to the current float-based one across the full existing timestamp-normalization test suite (`P3-05`) - this should be a behavior-preserving refactor for every currently-tested case, with the tie-policy documentation being the only externally-visible change.

## Out of Scope
- Don't change `epsilon_us`'s default value or how it's configured.
- Don't touch any other timestamp-handling code outside `quantize_timestamp` itself unless the tie-policy change requires it.

## Acceptance Test
1. Exact-tie cases (`ts_us` exactly halfway between two epsilon-grid points) produce the documented, chosen rounding behavior, not silently-inherited Python float `round()` behavior.
2. Every existing timestamp-normalization test (`tests/unit/test_normalize.py`, `P3-05`'s occupancy/phase edge-case tests) passes unchanged.
3. `bga/normalize/timestamps.py` contains no float division in the quantization path (a simple, verifiable grep-level check as part of this task's own verification).
4. Full suite green.

## Verification Log
`quantize_timestamp` (`bga/normalize/timestamps.py`) now uses `((2 * ts_us + epsilon_us) // (2 * epsilon_us)) * epsilon_us` - pure integer floor division, no float arithmetic anywhere in the path. Documented tie policy: round-half-up (exact ties round to the higher grid point) - a deliberate choice, replacing the previous docstring's inaccurate claim that Python's `round()` "rounds toward zero" (it actually performs round-half-to-even/banker's rounding, which the fix removes entirely).

New tests (`tests/unit/test_normalize.py`, 3 new): an exact-tie case (125000, exactly halfway between 100000/150000 at epsilon=50000) resolves to the documented round-up behavior, not banker's rounding; a bytecode-level check (via `dis`) that the compiled function contains a `//` operator and no `/` operator, immune to docstring-prose false positives a source-grep would hit; a cross-check against an independent reference round-half-up implementation across a wide range of timestamps/epsilons. Confirmed no existing test relied on exact-tie behavior (none used a value exactly at an epsilon/2 boundary), so this is a behavior-preserving change for every previously-tested case.

```
$ python3 -m pytest tests/unit/test_normalize.py -v
22 passed
$ python3 -m pytest -q   # full suite
430 passed, 11 skipped
$ make lint
All checks passed!
```
