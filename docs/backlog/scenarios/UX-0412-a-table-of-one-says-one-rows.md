# UX-412: a table of one says "1 rows"

**Priority:** Medium | **Status:** 🔴 Not Started | **Found by:** UX-400's sweep, first run | **Serves:** every reader of a run small enough to have one of something | **Topic:** viewer

## Motivation

`UX-400`'s zero/one/many sweep renders every published population at a
single row. Nine of them draw a badge, and every one of those badges
reads `1 rows`:

```text
readers                     ['1 rows']
next_steps                  ['1 rows']
critical_path_detail        ['1 rows']
optimization_horizon        ['1 rows']
latent_heavies              ['1 rows']
serialization_point_risks   ['1 rows', '1 rows']
restructuring               ['1 rows', '18 rows', '4 rows']
binary_cost                 ['1 rows']
provenance                  ['1 rows']
```

One helper writes all of them - `badgeText` in
[`bga/viewer/tables.js`](../../../bga/viewer/tables.js):

```js
return shown === total ? `${n(total)} rows` : `${n(shown)} of ${n(total)}`;
```

This is `UX-365`'s class exactly: a sentence written for a population,
read over a single row. It is small, and it is the first thing a
reader sees on the runs most likely to be somebody's first run - one
finding, one next step, one heavy element.

`structured.js` writes the same plural a second time, in the copy
control's label (`${total.toLocaleString("en-US")} rows`), so a
one-row table also offers `Copy 1 rows`.

## Required Fix

Pluralise where the count is written, not at each call site: one
helper that takes a count and a noun and agrees with it, used by
`badgeText` and by the copy control's label. The `N of M` form needs
no change - a denominator is always a population.

## Out of Scope

- Any other sentence over a population of one. `UX-400`'s sweep reads
  badges; the headings and notes came back clean and a wider sweep of
  the page's prose is its own instrument.

## Acceptance Test

- `UX-400`'s `TestOne::test_no_badge_pluralises_a_single_row` goes
  green with an empty ledger, and the ledger entry is deleted in the
  same commit as the fix.
- A one-row table's copy control reads `Copy 1 row`.
