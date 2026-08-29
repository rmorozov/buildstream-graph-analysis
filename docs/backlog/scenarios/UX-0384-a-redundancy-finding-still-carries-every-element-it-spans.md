# UX-384: a redundancy finding still carries every element it spans

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-375 (the cap that made this the remaining term) | **Serves:** anyone whose store holds a monorepo's captures | **Topic:** contracts

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
