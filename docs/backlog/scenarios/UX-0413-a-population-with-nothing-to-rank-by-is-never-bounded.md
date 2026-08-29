# UX-413: a population with nothing to rank by is never bounded

**Priority:** High | **Status:** 🔴 Not Started | **Found by:** UX-400's sweep, first run | **Serves:** anyone whose run is big enough for the page to be long | **Topic:** viewer

## Motivation

`UX-367` set the volume budget and `UX-262` made a long table open
bounded. Both are enforced by one branch in `buildTable`:

```js
if (total > TABLE_OPENS_BOUNDED_ABOVE) {
  const [column] = presets;
  preset.value = `25:${column}`;
  ...
}
```

`presets` is the list of numeric columns worth ranking by. A table
with none has no preset control at all, so `[column]` is `undefined`
and the bound is never applied. The bound is therefore a *side effect*
of having something to rank by, which is not what either filing meant.

`UX-400`'s sweep at 120 rows, showing rows a reader can actually see:

| population | rows | shown | badge |
|---|---|---|---|
| `critical_path_detail` | 121 | 26 | `25 of 120` |
| `optimization_horizon` | 121 | 26 | `25 of 120` |
| `latent_heavies` | 121 | 26 | `25 of 120` |
| `serialization_point_risks` | 121 | 26 | `25 of 120` |
| `binary_cost` | 121 | 26 | `25 of 120` |
| `readers` | 121 | **121** | `120 rows` |
| `next_steps` | 121 | **121** | `120 rows` |
| `restructuring` | 121 | **121** | `120 rows` |
| `provenance` | 121 | **121** | `120 rows` |

And `findings`, which `renderFindings` draws as one `<article>` per
finding rather than as a table, draws **120 cards** - a shape the row
bound cannot see at all.

`restructuring` is the one that makes this urgent: `UX-407` published
it this round, it is a list of never-read dependency edges, and on a
real monorepo it is the population most likely to be long. Nothing
about it is rankable, so nothing bounds it.

## Required Fix

Bound by count, not by the existence of a ranking:

- when a table is over `TABLE_OPENS_BOUNDED_ABOVE` and has no numeric
  column, fold to the first `TABLE_OPENS_BOUNDED_ABOVE` rows with the
  same `N of M` badge and the same one-click expansion the preset
  gives - the order is the payload's, which is already the order the
  emitter chose;
- give `renderFindings` the same bound over its cards.

## Out of Scope

- Choosing an order for an unrankable population. Publication order is
  the emitter's decision and this item does not reopen it.

## Acceptance Test

- `UX-400`'s `TestMany::test_a_long_population_opens_bounded` goes
  green with an empty ledger, and the ledger entry is deleted in the
  same commit as the fix.
- `UX-360`'s volume budget, measured on a run with a long
  `restructuring`, is inside its ceiling.
