# UX-662: the adopted touching map made the selector guard a hundred times dearer

**Priority:** High | **Status:** 🔴 Open | **Depends on:** UX-524 (the adoption mechanism), UX-420 (the drift gate that caught it), UX-605 (the cap on what a map may select) | **Found by:** round 89, by CI going red on a PR whose own diff did not touch the selector | **Serves:** anyone whose branch goes red for a cost the base branch introduced | **Topic:** guards | **Shape:** judgement

## Motivation

`8751a7e` on `main` — *"CI: adopt the touching map this run measured
(UX-524)"* — added `tests/touch_map.json`, 340 lines, by the mechanism
built for it. The next branch to merge `main` went red on the drift
gate:

```text
473 file(s) measured against ci_reference.json (github-actions
ubuntu-latest, test (3.11), -n auto), this run x0.82 from 162 file(s)
over 1s, IQR 0.41, and 2 file(s) slower than ci_reference.json records:
  tests/unit/test_the_loop_stays_fast.py 25.3s against 4.4s recorded, x6.99
  tests/unit/test_the_order_the_page_has.py 25.1s against 18.6s recorded, x1.63
```

The junit for that run records **7165 tests, 0 failures, 0 errors** —
no test failed. The gate did.

The cost is the map, measured by removing it and putting it back:

```console
$ python3 -m pytest tests/unit/test_the_loop_stays_fast.py -q \
      -k TestTheSelectorStillSelects --durations=3
4.82s call  ...::test_the_selection_is_a_fraction_of_the_suite
4.64s call  ...::test_the_wide_modules_are_named_and_not_merely_tolerated
0.11s call  ...::test_the_floor_is_under_every_module[bga/store_aggregate.py]
15 passed, 35 deselected in 10.00s

$ mv tests/touch_map.json /tmp/ && python3 -m pytest ... --durations=3
0.10s call  ...::test_the_floor_is_under_every_module[bga/store_aggregate.py]
0.09s call  ...::test_the_floor_is_under_every_module[bga/cli.py]
0.06s call  ...::test_a_one_module_change_selects_a_handful_not_the_suite
2 failed, 13 passed, 35 deselected in 0.55s
```

**10.00s against 0.55s** for the class, and the two clauses that read
the map go from about 0.05s each to 4.7s each. (The two failures
without the map are the clauses that require one — they are what makes
the removal a control rather than a shortcut.)

The same branch measured at the base commit `933de24`, before the map
was on `main`, and at its own head: **17.34s → 18.10s** for the whole
file. This branch added 4%. The map added the rest, and it arrived from
`main`.

That the reference still says 4.4s is not a second defect: `933de24`'s
own CI run measured 4.4s with the gate green, because the map did not
exist in that tree. The reference is exactly as true as it was; the
tree under it changed.

## Required Fix

Two halves, and the first is a decision this row is not entitled to
take alone.

**Is the map's cost meant?** `UX-605` capped what a map may *select*
after a merge made a one-module diff select 180 of 449 files. Nothing
caps what reading one costs the guard that reads it. If ~4.7s per
clause is the price of a coverage-derived map, the drift reference is
refreshed from a CI run's `ci-reference-candidate` artifact and the
figure is stated where a reader meets it. If it is not, the two clauses
read the map once between them rather than once each, or sample it.

**And the adoption should not be able to do this silently.** The job
that commits a map runs on `main` and no gate stands between it and the
next branch that merges: the first branch to pay is the one that goes
red, for a diff that never touched the selector. Whatever the decision
above, the adopt job measures the guard it is about to make dearer and
refuses — or refreshes the reference in the same commit.

## Out of Scope

- `test_the_order_the_page_has.py` at ×1.63, the second row in the same
  gate line. Declined because ×1.63 on an 18.6s file is within what one
  runner's afternoon explains, and this row is about the ×6.99 whose
  cause is measured.
- Reverting `8751a7e`. The map is the mechanism `UX-524` built and
  `UX-605` capped, and it works; what is missing is the price being
  visible when it is adopted.
- The drift gate's thresholds — `CI_DRIFT_FACTOR` and
  `CI_DRIFT_SECONDS` were sized from a measured run by `UX-420`, and
  this row is evidence they work rather than a case against them.

## Acceptance Test

The two selector clauses' cost with a map present is measured and
either bounded or recorded as the reference; and adopting a map that
makes a guard cross the drift gate reddens something in the adopting
commit rather than in the next branch that merges it.
