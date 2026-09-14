# UX-848: a compile-bound example is the jobserver's evaluation

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-843, UX-846 | **Found by:** round 117, Direction 20 | **Serves:** R4 (the number round 112 asked for) | **Topic:** capture | **Area:** tools | **Shape:** judgement

## Motivation

Round 112 declined the mode because examples/06's wall did not move
(30.25 s → 30.46 s) while its under-utilised share fell fourfold: that
project's bound is a six-deep chain, and no jobserver shortens a chain.
The mode is supported when a compile-bound capture's wall moves, and
no example in the tree is compile-bound.

## Required Fix

`examples/07-jobserver/`: four independent autotools and cmake
elements, each compiling 64 generated C files and linking one binary,
behind one `all.bst`, small enough for CI's examples job; the job
captures it twice (static `max-jobs`, then `--jobserver auto`) and
`bga compare` prints the envelope and the wall side by side; the
README of the example carries the two numbers from the machine that
wrote it, dated. The mode's `Status` in Direction 20 is decided on
that row.

## Decomposition

Input classes: cold cache both ways (the artifact keys equal per
`UX-844`, so the second capture must be run with the cache cleared);
the journey it extends is R4's first capture with the mode on.

## Out of Scope

A project with a real link-bound tail - `UX-846`'s fixture; remote
execution (`UX-680`).

## Acceptance Test

`bst-examples` in CI builds 07 both ways and `tests/unit/test_the_examples_build.py`
(or the job's own step) asserts `bga compare` prints a wall for each;
mutation: point the second capture at the first's run - the compare
refuses two identical runs (red).

## Outcome

**Gap measured:** no example in the tree was compile-bound (Motivation).
`examples/10-jobserver` (07-09 were already taken by later examples;
07-jobserver would have collided with `07-declared-vs-used-
dependencies`) has four independent elements, two `autotools` two
`cmake`, each generating 64 C files in-sandbox and linking one binary.
`bga compare` had no refusal for two runs pointed at the same directory,
confirmed live: `bga compare tests/fixtures/macro_micro/run{,}` printed
`Verdict: NO SIGNIFICANT CHANGE`, exit 0.

**Close measured**, `python3 -m pytest tests/unit/test_the_examples_build.py -v`:

```text
tests/unit/test_the_examples_build.py::test_the_ci_step_captures_both_modes_from_a_cold_cache PASSED
tests/unit/test_the_examples_build.py::test_the_ci_steps_own_wall_assertion_matches_real_compare_output PASSED
tests/unit/test_the_examples_build.py::test_a_capture_pointed_at_its_own_run_is_refused PASSED
tests/unit/test_the_examples_build.py::test_a_capture_pointed_at_its_own_run_via_a_relative_path_is_also_refused PASSED
tests/unit/test_the_examples_build.py::test_a_comparable_pair_is_unaffected PASSED
5 passed in 1.46s
```

Real captures, this 4-core box, 2026-09-14, cold cache both times,
`bst build all.bst` (default `--builders`/`--max-jobs`):

```text
bga capture run --run-dir run-off  --jobserver off  examples/10-jobserver plane2-off.json  -- bst build all.bst   -> Total Duration 21.62s
bga capture run --run-dir run-auto --jobserver auto examples/10-jobserver plane2-auto.json -- bst build all.bst   -> Total Duration 22.83s
bga compare run-off run-auto -> Verdict: REGRESSED (+1.22s, +5.6%)
```

All four elements grew, `cmake` (not yet joined - `UX-843`) by as much
as `autotools` (joined today) - both runs already ran all four elements
concurrently at the host's own `-j4` each (16-way oversubscribed before
the mode adds anything), so there were no idle cores this capture found
to redistribute; see the example's own README for the full reading.

**Mutation table:**

| Guard | Mutation | Reddened | Count |
|---|---|---|---|
| `bga/cli.py`'s identical-run refusal (`_execute_compare_and_write`) | `if False and Path(args.baseline)...` | `test_a_capture_pointed_at_its_own_run_is_refused`, `test_a_capture_pointed_at_its_own_run_via_a_relative_path_is_also_refused` | 2 of 5 tests in the file |
