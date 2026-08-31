# UX-338: the page draws the element population twice

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-289 (one element table, many presets — this is its unfinished half), UX-215 (the join that added the second table), UX-329 (which made it visible) | **Serves:** R1 — whoever reads the page | **Topic:** viewer

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

## Outcome (round 49, 2026-08-27) — 🟢 Done

### The gap, measured

`macro_micro` through `bga view`, every table on the page:

```text
before   signals       table=elements       rows=11
         element_join  table=element_join   rows=11

after    signals       table=elements       rows=11
```

The whole element population, twice, for every reader of a two-plane
snapshot since `UX-215`.

### The shape of the fix

The join's columns merge into the row each element already has, and
`Plane 2 (sandbox)` is a **view of that one table**: element,
duration, cores busy, jobs asked for, peak RSS. Two rules bound the
merge, and neither is reachable on the committed fixture - which is
why both needed a payload built to reach them:

* **Only onto rows Plane 1 put in play.** *"`element_join` never
  introduces an element"* is `views.js`'s own statement of what the
  join is; a row for an element the schedule does not carry would make
  this table a population it does not claim to be.
* **Plane 1 wins a name collision.** A join field shadowing an
  existing column would change what a column means without changing
  its heading - the reader sees `Rebuilds: 999` with no way to know
  which plane said so.

`element_join` no longer renders as a section. `DRAWN_ELSEWHERE` is
not a skip list: each entry names *where the content went*, which is
what stops it becoming somewhere to hide a section nobody wants to
fix.

### The defect the work turned up

Served without its `plane2.json`, the fixture offered the new preset
anyway and drew **two columns under a heading promising five** - the
dead-button defect `UX-194` removed everywhere else, reintroduced at
the level of a view.

Inferring the answer from the run was tried first and is wrong:

```text
rule                                    without Plane 2
"some named column is carried"          offered  (element_durations is)
"every named column is carried"         too strict for the other presets
```

`Plane 2 (sandbox)` also names `element_durations`, which every run
has. So the preset **declares its subject** - `requires` - because
"which of my columns make me this view" is a question only its author
can answer. The schema validates it (a preset cannot require a column
it does not draw), and `presetTable` drops a preset whose subject is
absent:

```text
with plane2      All elements … Latent heavies, Plane 2 (sandbox)
without plane2   All elements … Latent heavies
```

### Mutations verified red and reverted (6)

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| M1 | `element_join` is drawn as a section again (the filed defect) | 2: `the_element_table_is_drawn_once`, `no_two_tables_carry_the_same_elements` |
| M2 | the join stops merging into the element table | 1: `every_declared_view_is_offered` |
| M3 | the join overwrites a Plane 1 column | 2 |
| M4 | the join introduces an element Plane 1 never scheduled | 1 |
| M5 | the preset stops declaring its subject | 1 |
| M6 | `presetTable` ignores `requires` | 1 |

**M3, M4 and M5 all reddened nothing on their first run**, and each
bought a clause. M3 and M4 are unreachable on the committed fixture -
its join carries no field Plane 1 also owns and no element Plane 1 did
not schedule - so `TestTheJoinMergesWithoutOverwriting` drives the
merge on a payload built to reach both. M5 is unreachable because the
fixture *has* Plane 2, so the same class holds the dead-control rule
against a run with none.

Writing that third clause turned up one more thing worth keeping: with
only one usable view, `presetTable` renders no control at all, so
"the sandbox view is gone" first passed against a control that had
vanished entirely. The synthetic signals carry enough Plane 1 for two
views to survive, and a bounding assertion says so.

### Deviation from the Required Fix

- The Required Fix offers "or the two are given populations that
  differ on purpose and the rule is restated". Taken the first branch:
  they are the same eleven elements by construction, and no restatement
  makes that two populations.
