# UX-632: the touching figure is the sample its own round disproved

**Priority:** Low | **Status:** 🔴 Open | **Depends on:** UX-606 (which replaced it in the guard), UX-336 (which measured it) | **Found by:** architecture review 15 | **Serves:** anyone budgeting the inner loop | **Topic:** docs

## Motivation

Three places price `make test-touching` at **4s on a one-module
diff** — `docs/contributing/fixing-guide.md:59` and `:74`, and
`CLAUDE.md:17`. The figure was entered on 2026-08-28 (`bc15935`) from
one sample: `bga/store_aggregate.py`.

`UX-606` closed in this same window by deleting exactly that sample
from the guard and putting a distribution over the mapped population
in its place. The prose beside the fixed guard still quotes the
sample:

```text
$ dev_touching.select(['bga/store_aggregate.py'])   24 of 461 test files
$ dev_touching.select(['bga/cli.py'])              118 of 461 test files
```

A reader budgeting the loop from `CLAUDE.md` is told the best case and
called it the case.

## Required Fix

The cost row carries a spread over the population — the figures
`UX-606`'s guard already computes — rather than one machine's one
module, in all three places.

## Out of Scope

- `UX-624`'s cap, which changes those numbers and should land first if
  both are in one round.

## Acceptance Test

The three quoted figures derived from the same distribution the guard
reads, reddening when they drift from it.
