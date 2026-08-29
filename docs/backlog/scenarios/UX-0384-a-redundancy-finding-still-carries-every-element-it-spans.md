# UX-384: a redundancy finding still carries every element it spans

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-375 (the cap that made this the remaining term) | **Serves:** anyone whose store holds a monorepo's captures | **Topic:** contracts

## Motivation

`UX-375` capped `redundant_operations` at 40 findings and cut the
section from 278,510 B to 32,728 on a 40-element capture. Of what
remains, **64% is the `elements` list each finding carries** — 20,400 B
— and that list is the one part still `O(elements)`:

```text
capped rows                          40
bytes                            32,728
of which `elements` lists        20,400   (64%)
projected at 1,200 elements        ~600 kB
```

`correlate.py` is the only consumer of a redundancy finding in this
repository, and it reads `worst_element` and the durations. Nothing
reads `elements`. `UX-375` added `element_count` beside it, which is
what a consumer wants; the list itself is carried and never read.

## Required Fix

`elements` is replaced by `element_count` (already published) and
`worst_element` (already published). Removing a published key bumps
`plane2/v2` to `plane2/v3` — `bga/plane2.py`'s `SCHEMA`/`LEGACY_SCHEMA`
chain, `bga/schemas.py`, the Part 32.5 registry and the architecture
inventory, on the precedent `UX-297` set when it removed the
per-process record list for the same reason.

## Falsification

A capture at 40 elements publishes a `redundant_operations` section
whose byte count does not grow when the same signatures are spread over
400 elements. It fails today: the rows are bounded and the names inside
them are not.

The other direction: `bga correlate` on `tests/fixtures/macro_micro`
produces the same `redundancy_count` and `worst_redundancy` for every
element as it does now, because neither was ever read from `elements`.

## Out of Scope

- The row cap and the coverage counts. Those are `UX-375` and they
  landed; this is the term that was left, named with its measurement so
  a later round does not have to re-derive it.
- The display floor. `UX-375` measured why it stays in the renderer and
  that decision is not reopened here.

## Outcome (round 62, 2026-08-29) — 🟢 Done

### The gap, measured

Re-measured rather than taken from the filing, with `UX-375`'s cap in
place throughout and only the element count varied:

```text
 elements  rows  section B  elements B   share
       40    40     36,901      28,840   78.2%
      400    40    296,221     288,040   97.2%
     1200    40    880,341     872,040   99.1%
```

The rows are bounded and the names inside them were not: a capped
section that is 99% element names at 1,200 elements is not a capped
section.

### After

```text
 elements  rows  section B  names B   vs 40
       40    40      7,581      600   1.00x
      400    40      7,701      600   1.02x
     1200    40      7,821      600   1.03x
```

23.8x → 1.03x across the same range. The residual is not a leak: each
row publishes `element_count` and `occurrence_count`, and `1200` is two
characters longer than `40`. That is `O(log elements)` over a fixed row
count. The term that *was* linear is pinned separately — one element
name per row (`worst_element`), so the bytes spent on names are 600 at
every population.

`element_count` and `worst_element` were already published and are what
a consumer reads. Removing a published key is what makes this a version
rather than an addition, so `plane2/v2` → **`plane2/v3`**, with the
retired shape inventoried as read-and-never-written on the precedent
`UX-297` set: `bga/plane2.py`'s chain, `bga/schemas.py`,
`docs/spec/specification.md` 32.5, the architecture inventory,
`docs/README.md`, and the release ledger's recorded contract state.

### Falsification

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| M1 | `elements` is published again — the original defect | 3 of 15 |
| M2 | `element_count` dropped, so the width is unpublished | 1 of 15 |
| M3 | the contract does not move (`SCHEMA` stays `plane2/v2`) | 2 of 15 |
| M4 | `correlate` stops reading the older shape's list | 1 of 15 |
| M5 | the "other elements" count goes negative on a lone element | 2 of 15 |
| M6 | the retired shape is dropped from the inventory | 2 of 15 |

Baseline: 15 passed. `make lint` clean; small tier 2,640 passed.

**One of my own clauses did not discriminate, and the sweep is what
found it.** `test_a_row_names_exactly_one_element_whatever_the_
population` counted string values only, and the defect it guards puts
the names in a *list* — so M1 reddened two clauses and walked past the
one written for it. Counting names at one level of nesting as well took
M1 from 2 to 3.

### Deviation from the Required Fix

- **The Motivation's premise was false and is corrected here.** It says
  "`correlate.py` ... reads `worst_element` and the durations. Nothing
  reads `elements`." `bga/correlate.py` did read it, at one site, to
  write "it pays 20.4s for an operation *3 other elements* also run".
  It used the list for `len()` alone, and the row is keyed by
  `worst_element`, so that length is exactly `element_count - 1` and
  the sentence is preserved rather than dropped. A helper
  (`_other_element_count`) still falls back to the list when a report
  carries it and no count — a store is full of captures written before
  `UX-375` added the count, and `tests/fixtures/macro_micro` is one, so
  the Falsification's "same output on that fixture" needed it.
