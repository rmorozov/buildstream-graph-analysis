# UX-632: the touching figure is the sample its own round disproved

**Priority:** Low | **Status:** 🔴 Open | **Depends on:** UX-606 (which replaced it in the guard), UX-336 (which measured it) | **Found by:** architecture review 15 | **Serves:** anyone budgeting the inner loop | **Topic:** docs

## Motivation

**Corrected round 86, re-measured before the fix; the filing as sent is
kept below.**

**Four** places price `make test-touching` at **4s on a one-module
diff** — `docs/contributing/fixing-guide.md:59` and `:74` (both from
`bc15935`, 2026-08-28), `CLAUDE.md:17` (from `de20309`, 2026-08-30, not
`bc15935`) and `.claude/skills/verify/SKILL.md:25`, which adds "7
files, 123 tests". The figure is one sample: `bga/store_aggregate.py`.

`UX-606` closed in this same window by deleting exactly that sample
from the guard and putting a distribution over the mapped population
in its place. The prose beside the fixed guard still quotes the
sample. Re-measured at `d8dfc46`, after `UX-624` changed the selector:

```text
$ dev_touching.select(['bga/store_aggregate.py'])   24 of 461 test files
$ dev_touching.select(['bga/cli.py'])              124 of 461 test files
$ over all 85 mapped modules   min 11 · median 17 · p90 40 · max 124
```

`cli.py` was filed at 118 and is 124; `store_aggregate` holds at 24.

A reader budgeting the loop from `CLAUDE.md` is told the best case and
called it the case.

<details><summary>the filing as sent</summary>

Three places price `make test-touching` at **4s on a one-module
diff** — `docs/contributing/fixing-guide.md:59` and `:74`, and
`CLAUDE.md:17`. The figure was entered on 2026-08-28 (`bc15935`) from
one sample: `bga/store_aggregate.py`.

```text
$ dev_touching.select(['bga/store_aggregate.py'])   24 of 461 test files
$ dev_touching.select(['bga/cli.py'])              118 of 461 test files
```

</details>

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

## Outcome (round 86, 2026-09-04)

**Premise:** held for the defect, falsified for two of its figures —
`cli.py` is 124 and not 118, there are four sites and not three, and
`CLAUDE.md`'s copy came from `de20309`, not `bc15935`. Motivation
corrected above with the filing kept.

### The gap, measured

```text
$ over all 85 mapped modules, at d8dfc46
min 11 · median 17 · p90 40 · max 124        the guard's own numbers
$ the documents, same tree
fixing-guide.md:59   measured at 4s on a one-module diff
fixing-guide.md:74   | **4s** on a one-module diff |
CLAUDE.md:17         ...your diff touched (~4s)
```

The guard `UX-606` fixed and the prose beside it disagree by the whole
population: 4s is `bga/store_aggregate.py`, the narrowest name in the
tree, on one machine.

### Where the figure now comes from, and why not seconds

Seconds have no local instrument — `UX-551`, and
`test_the_loop_stays_fast.py`'s own docstring, which declines to guard
wall clock because it is a property of the machine. The **selection**
is a property of the tree, is what determines the cost, and is already
computed. So `tools/dev_touching.py` gained `spread()`, `figure()` and
`--spread [--write]`: one function computes it, one option writes every
site, one guard holds the sites to it. Re-typing better values would
have been `UX-501`'s defect with fresher numbers, and a derived figure
no tool writes drifts just as far, only slower.

### After

```text
$ python3 tools/dev_touching.py --spread
11-124 of 462 test files, median 17
$ python3 -m pytest tests/unit/test_the_cost_row_is_derived_from_the_selector.py -q
11 passed in 4.47s
```

The guard's first run was red: its own file moved the population
461 → 462, and `--spread --write` closed it — the loop that replaces a
typed number.

### Mutations verified red and reverted (6)

| # | mutation | reddened |
|---|---|---|
| B1 | the table row drifted to the filing's pre-`UX-624` figures | 2 — the count clause and the rewriter clause |
| B2 | `~4s` back in `CLAUDE.md`'s row | 2 — the seconds clause and the defers clause |
| B3 | `figure()` returns today's string as a constant | 1 — the interpolation clause |
| B4 | `write_figure` rewrites nothing | 1 — the rewriter clause |
| B5 | `SITES` emptied | 2 red, **2 skipped** — the floor caught what the skips could not |
| B6 | the spread reads `store_aggregate` alone, as `UX-336` did | 3 — the population floor, naming `modules: 1` |

B4 is the pair worth keeping: with a no-op rewriter the drift clause
`test_the_document_is_what_the_tool_would_write` stays **green**, because
a document with no figure is one the rewriter leaves alone. The
declared per-site count is what sees that, and neither clause is
sufficient alone. B5 is the over-broad exclusion: the parametrized
clauses collected nothing and reported as skips, which is why
`test_the_sites_are_real_and_price_the_loop` asserts the population
before anything reads it.

### Deviation from the Required Fix

**Two.** `CLAUDE.md` carries no figure: `UX-471`'s guard there forbids a
count the tree changes under it — `test_no_line_carries_a_count_that_a_close_makes_wrong`
reddened on `462 test files` — so that row prices the loop in nothing
and points at the guide, which is what its own `make test` row already
does. Held by `test_a_deferring_document_states_no_figure_of_its_own`.
And `.claude/skills/verify/SKILL.md:25` is the fourth site and was left
alone: outside this track's declared surface. It still says 4s.

Tier: **medium**, 4.54s single-process. `tests/tiers.py` not edited
here — a merge hotspot; the measurement is this line.
