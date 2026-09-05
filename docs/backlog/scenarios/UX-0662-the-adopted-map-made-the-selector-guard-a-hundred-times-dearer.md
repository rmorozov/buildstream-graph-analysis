# UX-662: the adopted touching map made the selector guard a hundred times dearer

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-524 (the adoption mechanism), UX-420 (the drift gate that caught it), UX-605 (the cap on what a map may select) | **Found by:** round 89, by CI going red on a PR whose own diff did not touch the selector | **Serves:** anyone whose branch goes red for a cost the base branch introduced | **Topic:** guards | **Shape:** judgement

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

## Outcome

🟢 Done. Both halves, in two rounds.

**The first half, round 89.** The decision the row would not take alone
was taken by measurement: the two clauses were two readings of one
sweep and each ran it. `26b3252` shares it and reads each test file's
text once per process, taking the file **25.3s → 19.8s** in CI (18.62s
→ 14.26s locally, 18% under the base commit) with `--spread`
byte-identical. `28c2071` then refreshed three entries from that run's
own candidate at its stated shift (x0.96): 4.4 → 20.62, 9.96 → 18.54,
6.73 → 15.94. So the cost was cut first and only the remainder
recorded.

**The second half, this round: the adoption stops being silent.**
`--adopt` now retires, in the commit that adds the map, the drift
entries belonging to the map's own readers. Nothing is typed: the map
names them itself, in its row for `tools/dev_touching.py`.

Retiring is not losing. `against` carries a file with no entry out with
`was` None; `repeated` splits those into `recorded`, and the run
returns 0 on them (`dev_tier_drift.py:811,1047`). The next reference
candidate re-records each on that run's own clock, because `--adopt`
adds exactly the names the reference lacks. One run unjudged, instead
of a branch going red for seconds it never spent.

Two things the work found that the filing did not know:

- **The two adopt jobs raced.** Both were `needs: test`, both push to
  `main`, and `tier-reference-adopt` adopts from a candidate `test
  (3.11)` measured *before* this run's map. Landing second it would
  re-add precisely what the retire removed. They are now sequenced, and
  `touch-map-adopt` pulls before it edits so its retire sits on top.
- **Retiring every reader is cheap, and that is measured, not assumed.**
  Six readers lose an entry, three of which are small (0.02s, 0.15s,
  1.74s). The map has changed **3 times in 332 commits** on `main`
  (`git log --follow -- tests/touch_map.json`), so this fires about
  once per hundred commits and the entries rebuild `UX-496`'s sample
  band in between. The asymmetry decides it: over-retiring costs one
  printed row, under-retiring costs a red branch.

### Acceptance

```console
$ python3 tools/dev_touch_map.py --adopt cand.json   # one added edge
87 module(s), 7341 edge(s)
retired 6 drift entries the map's readers own, for the next run to re-record:
  tests/unit/test_a_slow_file_says_which_file.py
  ... four more, then test_the_touching_map_is_measured.py
```

`files` 474 → 468, and each retired name reads `None` after. The gate's
verdict on such a row is `recorded`, held by the clause below.

### Mutations

Seven guards, seven mutations, each reddening its own clause and only
its own.

| mutation | guard |
|---|---|
| `readers` returns a typed list | the readers are the map's own row |
| `READER` names `bga/cli.py` | the named reader reads the map |
| `retire` drops from `files` only | dropped from files *and* samples |
| `retire` reports absent names | a name it lacks retires nothing |
| `retire` leaves the entry in place | retired ⇒ `recorded`, not confirmed |
| `git add` without the reference | the commit carries both |
| `needs: test` alone | adopted after the rows measured without it |

### Deviation

The filing offered "refuses — or refreshes the reference in the same
commit" and this does neither exactly: it *retires* in the same commit
and lets the existing adoption re-record. Refusing would stall the
mechanism `UX-524` built; refreshing from the adopt job's own clock is
the cross-clock write `UX-418` ruled out. Retiring is the third door,
and it needed no new machinery.
