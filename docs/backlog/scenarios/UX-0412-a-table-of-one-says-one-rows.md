# UX-412: a table of one says "1 rows"

**Priority:** Medium | **Status:** 🟢 Done | **Found by:** UX-400's sweep, first run | **Serves:** every reader of a run small enough to have one of something | **Topic:** viewer | **Area:** bga/viewer

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

## Outcome (round 65, 2026-08-30) — 🟢 Done

### The gap, measured

`UX-400`'s sweep at a single row, before — nine badges, every one of
them wrong:

```text
badges over one row: {'readers': ['1 rows'], 'next_steps': ['1 rows'],
 'critical_path_detail': ['1 rows'], 'optimization_horizon': ['1 rows'],
 'latent_heavies': ['1 rows'], 'serialization_point_risks': ['1 rows'],
 'restructuring': ['1 rows'], 'binary_cost': ['1 rows'],
 'provenance': ['1 rows']}
```

### After

Both ledgers empty, and two clauses added:

```text
tests/unit/test_every_population_at_zero_one_and_many.py
17 passed in 1.39s
```

### One helper, where the count is written

```js
export function plural(count, noun) {
  return `${count.toLocaleString("en-US")} ${noun}${count === 1 ? "" : "s"}`;
}
```

Read by `badgeText` and by the copy control's label, which is the two
call sites the filing names. The `N of M` form is untouched: a
denominator is always a population, so `1 of 12` was already right.
`boundCards`' own control goes through it too, so `Show all 120
findings` is written the same way as everything else.

### The sweep reads the copy control now

The acceptance test's second clause — *a one-row table's copy control
reads `Copy 1 row`* — had no instrument: `UX-400` read badges only. It
reads both now, with a companion clause asserting the reading is not
empty, which is the shape `UX-403`'s census exists to catch.

### A mutation that did not discriminate, and what it bought

`C3` deleted the agreement test from `plural` itself — the helper
returns `${count} ${noun}` for any count — and **all sixteen clauses
passed**. Every clause in `TestOne` asserts the *singular* case, and
`1 row` is what a helper with no agreement produces; the many leg's
badge is the `N of M` form, which does not use `plural` at all.

So the guard proved the singular and nothing proved the plural. Fixed
with `TestMany::test_no_control_singularises_a_population`, which
reads the many leg's badges and copy labels for a count above one
followed by a bare `row`. Recorded rather than quietly fixed, because
"the mutation passed" is the finding: **agreement is two claims and
only one of them was being made.**

### Mutations verified red and reverted (3)

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| C1 | `badgeText` writes `${n(total)} rows` again | `test_no_badge_pluralises_a_single_row`; 1 failed, 15 passed |
| C2 | only the copy control's label reverts | `test_no_copy_control_pluralises_a_single_row`; 1 failed, 15 passed |
| C3 | `plural` drops the agreement entirely | nothing, until the many-leg clause existed; then `test_no_control_singularises_a_population`; 1 failed, 16 passed |

C1 and C2 are separate on purpose: one edit could have fixed the badge
and left the label, which is the state the filing describes.

### Deviation from the Required Fix

- **None.** One helper, used by both call sites named. The Out of
  Scope — *any other sentence over a population of one* — is honoured:
  the sweep reads badges and copy labels, both of which are controls
  that carry a count, and no prose was touched. Three other sites do
  write a bare `N rows` (`statedOnce`'s uniform-column note, the
  column strip's label, the density strip's sentence); the first is
  gated on `total > SERIES_MIN_POINTS` and cannot say `1 rows`, and
  the other two are the wider prose sweep this item deliberately
  leaves to its own instrument.
