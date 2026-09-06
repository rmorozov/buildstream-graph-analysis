# UX-730: a derived figure over the whole test tree has no refresh route

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-716 (the same class, in the timing mechanism), UX-662 (which retires the map's readers), UX-336 (the selector) | **Serves:** every round that adds a test file, and the branch that pays for it | **Topic:** guards | **Shape:** bounded | **Area:** tools

## Motivation

Round 98 went red on CI across four Pythons and three shas, with the
suite otherwise green (7441 tests recorded, 2 failures):

```text
FAILURE test_the_cost_row_is_derived_from_the_selector
        TestTheDocumentsCarryTheComputedFigure::test_each_cost_line_carries_the_figure
        docs/contributing/fixing-guide.md: 0 line(s) price the loop at
        '13-127 of 490 test files, median 19', expected 2
```

The cause is two new guard files:

```console
$ python3 tools/dev_touching.py --spread --write
13-127 of 491 test files, median 19          # the guide said 489
```

**The selector cannot reach it.** `select()` greps every test file for
each *changed path*, so this guard is chosen when
`tools/dev_touching.py` or `docs/contributing/fixing-guide.md` changes.
Its verdict, though, depends on the size of `tests/`, and adding
`tests/unit/test_an_aliased_import_is_refused.py` is not a change to
anything the guard names. The `selector-before-commit` hook therefore
passed on all four commits that invalidated it, and CI paid.

This is `UX-716`'s class in a second mechanism. There it is *recorded
seconds* decaying as a population grows; here it is a *derived figure*.
Same shape, different currency, and neither `UX-662`'s retirement of
the map's readers nor the census floor covers it.

## Required Fix

The census floor (`tests/tiers.py`'s `CENSUS`, the 13 files that run
under every mapped module) is the obvious home, and the judgement is
whether it is the *right* one: `select(census=False)`'s docstring says
the census is "which guards a grep can never reach", and this guard is
reachable by grep — for its readers, not for its population. Either
the census's definition widens to "a grep cannot reach it *for every
input it has*", stated where `CENSUS` is declared, or a guard declares
the population it derives from and a run that changes that population's
size selects it — which is `UX-716`'s first candidate route and would
serve both rows with one mechanism.

Decide with the measurement `UX-716` asks for: how many guards are in
the class. If the two rows have the same members, build the mechanism
once and close both.

## Out of Scope

- The figure re-derived in this round to unblock CI (489 → 491).
  Declined as the fix for the same reason `UX-716` declined its own
  hand-refresh: it buys one round, not the property.
- Making `make test-touching` run everything. `UX-336` sized the
  selector against exactly that, and `UX-605` bounded it.

## Acceptance Test

A commit that adds a test file and nothing else selects the guards
whose figures are derived from the test-file population. Mutation: add
an empty test file, run the selector — the cost-row guard is in the
selection and reds before the commit lands.
