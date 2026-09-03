# UX-605: the touching map adopted a selection that is everything

**Priority:** High | **Status:** 🟢 Done Open | **Depends on:** UX-524 (the map), UX-336 (the bound it broke) | **Found by:** round 84, CI red on the merge commit and green on both parents | **Serves:** every session running `make test-touching` | **Topic:** guards

## Motivation

`0bc5aff` on `main` — CI adopting the map its own run measured — turned
`test_the_loop_stays_fast.py` red for every Python version, and did it
on the *merge* commit, so both parents were green and neither branch's
own run showed it:

```text
E   AssertionError: a one-module diff selected 180 files. The point is
    to be faster than the tier; selecting everything is not.
```

`--cov-context=test` records which test executed which module *line*,
and a module's top-level lines run at **import**. So every test that
imports anything from `bga` "touches" `bga/progress.py`. Measured on
the adopted map:

```text
modules mapped                85       total edges  6,702
entries naming 100+ of 449    38
largest    bga/progress.py   200   bga/ingest/models.py  198
           bga/schemas.py    189   bga/findings.py       174
```

`bga/store_aggregate.py` maps to 165 files. With the census and the
grep that is 180 — 40% of the suite, slower than `make test-small`,
for a one-module diff.

Coverage is a **proxy** for "this test is about this module" (fixing
guide §5), and at import time it is a very bad one.

The second finding is the guard's own shape. Re-measured with the map
removed entirely, `18 of 85` mapped modules still select more than 25
from the **grep** half alone — `bga/cli.py` matches 112. So the ≤25
bound was never a property of the selector; it is a property of
`store_aggregate`, the one distinctive name the guard samples.

## Required Fix

A map entry naming more test files than the selector's own bound is
not a selection: it is ignored, and `--why` says which entries were
ignored and how wide they were. The bound is `25` because that is
what `test_a_one_module_change_selects_a_handful_not_the_suite`
asserts — derived from the guard, not chosen.

The guard says it samples one module, and a second clause holds the
map's own shape so a future adopt cannot re-poison it silently.

## Out of Scope

- Making coverage attribute import-time lines correctly — declined:
  that is `coverage.py`'s semantics, not this repository's, and the
  cap does not need it.
- The 18 modules whose *grep* half exceeds 25 — filed as `UX-606`,
  because widening or narrowing that bound is a separate measurement.

## Acceptance Test

A map with one over-wide entry, and the selector ignoring it while
still using the narrow ones in the same map.

## Outcome

**Round 84**, 2026-09-03. The cap, and the second finding underneath it.

### The gap, measured

Reproduced on the merge of `origin/main` into this branch — CI's
number, character for character, on a tree neither parent had:

```text
$ python3 -m pytest tests/unit/test_the_loop_stays_fast.py -q -k selects_a_handful
E   AssertionError: a one-module diff selected 180 files. The point is
    to be faster than the tier; selecting everything is not.
1 failed, 29 deselected in 0.10s
```

180 = 165 map + 13 grep (deduped) + 11 census. The map's shape:

```text
modules mapped              85     total edges  6,702
entries over 100 of 449     38     over 25      48
largest   bga/progress.py  200     bga/ingest/models.py  198
```

### The close, measured

```text
$ python3 -m pytest tests/unit/test_the_loop_stays_fast.py -q
33 passed in 3.65s
$ python3 -c "...; print(len(dt.select(['bga/store_aggregate.py'])[0]),
              len(dt.wide_entries()), len(dt.touch_map()))"
24 48 85
```

24 against the same map. 48 entries ignored, 37 still used — the cap
is not "ignore the map", which is what the second guard holds.

### Mutations

| mutation | result |
|---|---|
| `MAP_ENTRY_CAP = 10**9` (the defect restored) | 2 red |
| `MAP_ENTRY_CAP = 0` (the map ignored) | 1 red — the narrow-entry clause |
| the comparison inverted (wide kept, narrow dropped) | 3 red |
| `wide_entries()` reports nothing | 1 red |
| `wide_entries()` reports everything | 1 red |

### A guard of mine that did not discriminate

`test_the_map_in_the_tree_says_which_entries_it_cannot_use`, written
as *"every entry reported is over the cap"*, **stayed green** when the
reporter was made to report nothing — the loop iterated an empty dict
and both clauses held vacuously. The fourth mutation is what found it.
Rewritten to compare the reporter against the set derived in the test,
it reddens in both directions and still says the honest thing (zero)
on a clean map.

### The second finding

Re-measured with the map removed entirely, **18 of the 85** mapped
modules still select over 25 from the grep half alone — `bga/cli.py`
matches 112. So `test_a_one_module_change_selects_a_handful_not_the_suite`
never held a property of the selector; it held one of
`store_aggregate`, a distinctive two-word name. That is `UX-606`, and
the guard's docstring now says it samples one module.

### Deviation from the Required Fix

**None.** The cap is at read time rather than adopt time, which the
Required Fix leaves open and which is the stronger of the two: the
poisoned map is already on `main`, and a read-time cap fixes every
checkout of it without waiting for CI to re-adopt.

### Tier and suite

`test_the_loop_stays_fast.py` small; 33 tests in 3.65s. Full suite at
the round's gate.
