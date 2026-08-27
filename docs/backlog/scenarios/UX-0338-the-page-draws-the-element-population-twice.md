# UX-338: the page draws the element population twice

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-289 (one element table, many presets — this is its unfinished half), UX-215 (the join that added the second table), UX-329 (which made it visible) | **Serves:** R1 — whoever reads the page | **Topic:** viewer

## Motivation

`UX-289` settled it: **one element table, many presets.** `UX-215`
then published `element_join` — the two-plane join, same rows — and the
page draws it as its own table. On any run with a Plane 2 report that
is the whole element population, twice:

```text
tests/fixtures/macro_micro, through `bga view`:
  elements in the run                     11
  signals element table                   11 rows
  element_join table                      11 rows
```

**This is not new, and that is the point.** `bga view` has attached the
sibling `plane2.json` since `UX-203`, so every real viewer of a
two-plane snapshot has seen both tables since `UX-215`. Measured on the
tree *before* `UX-329`:

```text
BEFORE UX-329, through `bga view`: element_join present = True | rows = 11
```

`UX-289`'s guard did not see it because its fixture reaches the page
through `bga analyze` **without** `--plane2` — the one configuration a
real viewer never has. `UX-329` made `analyze` attach the sibling, and
the guard went red on its first run.

So this is the same shape as `UX-329` itself: an instrument pointed at
a configuration nobody uses.

## Required Fix

The join becomes a **preset of the one element table** rather than a
second table — `UX-289`'s own answer, applied to the columns `UX-215`
added — or the two are given populations that differ on purpose and the
rule is restated. Whichever, `test_one_table_many_views.py` runs its
page fixture **with Plane 2 attached**, because that is what a viewer
has; the exemption this round added is removed in the same change.

## Out of Scope

- `structural.batch_opportunities.serialized_pairs` against
  `structural.sensitivity.top_opportunities` — the pre-existing,
  measured exemption in that guard, which is a different pair.
- The `analyze/v2` payload. `element_join` is right to be published
  (`UX-215`); this is about how the page draws it.

## Acceptance Test

With Plane 2 attached, no two tables on the page carry the same element
population, and the whole-population table count is 1 (both asserted by
the existing clauses, with the `element_join` exemption gone); the join's
columns are reachable from the one element table.
