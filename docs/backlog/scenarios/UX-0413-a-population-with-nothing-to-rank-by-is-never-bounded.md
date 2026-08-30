# UX-413: a population with nothing to rank by is never bounded

**Priority:** High | **Status:** 🟢 Done | **Found by:** UX-400's sweep, first run | **Serves:** anyone whose run is big enough for the page to be long | **Topic:** viewer

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

## Outcome (round 65, 2026-08-30) — 🟢 Done

### The gap, measured

`UX-400`'s sweep at 120 rows, before. Five populations opened bounded
and four drew every row they had — the four with nothing numeric in
them — while `findings`, drawn as cards, drew 120 of them:

```text
drawing every one of 120 at once:
  {'readers': 121, 'next_steps': 121, 'restructuring': 121,
   'provenance': 121, 'findings': 120}
```

### After

The ledger is empty and the sweep is green:

```text
tests/unit/test_every_population_at_zero_one_and_many.py
14 passed in 1.71s
```

`TestMany::test_a_bounded_table_says_what_it_is_bounding` now covers
those four as well, so each of them says `40 of 120` rather than
bounding silently.

### The bound is decided on the total, in one place

The decision moved out of the block that builds the Top-N control and
into `openingBound(presets, total, bound)` in `tables.js`, which
answers with the state to open at:

```js
export function openingBound(presets, total, bound) {
  if (total <= bound) return null;
  const [column] = presets;
  return column
    ? { value: `25:${column}`, top: { n: 25, column } }
    : { value: `${bound}:`, top: { n: bound, column: null } };
}
```

`applyFilters` learned that `top.column` is optional: with a column it
sorts and takes the top n, without one it takes the first n in the
order the payload published them — `UX-413`'s Out of Scope keeps that
order as the emitter's decision. Everything downstream is the same
pass, so the badge, the text filter and the copy control cannot tell
the two apart, and the escape is the same control: the select carries
`All rows` beside `First 40 rows`.

`renderFindings` gets the same bound through `boundCards`, which hides
the cards past it rather than removing them — the rule `foldTheMiddle`
already follows, so Ctrl-F, the export and every `#anchor` into a
finding keep working.

### Two guards this change made wrong, and one harness

- `test_the_report_has_two_panes.py` greps the viewer's source for
  `if (total > TABLE_OPENS_BOUNDED_ABOVE)`. The mechanism moved, so
  the clause was pointed at `openingBound` — and `tables.js` was added
  to `APP_MODULES`, which is the list whose own comment records this
  exact failure mode: *"pointing them at `app.js` alone would have
  quietly stopped seeing the constants they defend."*
- `UX-400`'s sweep counted `<article>` elements rather than *visible*
  ones, so a bounded card list still read as 120. That is the same
  mistake the file's own docstring records for `<tr>`, made a second
  time for cards; it now reads `cards_shown`.

### The page budget moved, with the measurement

`PAGE_BUDGET_B` 284,000 → 286,000. Measured with the module's own
instrument (`export`, then `_embedded`), before and after:

```text
page            282,543 -> 283,964   (+1,421, source)
golden          382,864 -> 384,218
macro_micro     438,227 -> 439,581
```

All of it source. The contract half is 81,623 B either side — no
declaration changed — which is why both totals move by exactly what
the page did.

### Mutations verified red and reverted (3)

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| B1 | `openingBound` returns `null` without a column — the filed defect, exactly | `test_a_long_population_opens_bounded`, `test_a_bounded_table_says_what_it_is_bounding`, `test_the_bound_holds_at_the_threshold_the_viewer_declares`; 3 failed, 11 passed |
| B2 | the `boundCards` call deleted | `test_a_long_population_opens_bounded`, on `{'findings': 120}`; 1 failed, 13 passed |
| B3 | the opposite direction — bound every table however short | `test_no_badge_pluralises_a_single_row`; 1 failed, 13 passed |

B3 is the one that makes the fix a distinction rather than a rename.
It reddens through the *badge* rather than through the bound: a
one-row table bounded to 40 still shows its one row, so "is it
bounded" cannot see it, and what changes is that the badge reads
`1 of 1`. A real consequence, and a narrower guard than B1's.

### Deviation from the Required Fix

- **The Acceptance Test's second clause could not be measured.**
  *"`UX-360`'s volume budget, measured on a run with a long
  `restructuring`, is inside its ceiling."* No fixture has one:

  ```text
  tests/fixtures/golden/mixed_task_kinds: restructuring: NoneType None
  tests/fixtures/macro_micro/run:         restructuring: list 1
  ```

  Golden publishes none at all and `macro_micro` publishes a single
  row, and the volume budget's third fixture is `gen-synthetic`, which
  is Plane 1 only. That absence is the reason this defect survived
  four rounds, and it is why `UX-400`'s synthetic sweep — not a
  fixture — is the instrument that found it. What *was* measured is
  the volume budget on the three runs it does have
  (`22 passed, 1 skipped in 31.16s`) and the drawn-row count at 120,
  which is the quantity the budget is a proxy for.
- Everything else: **none**. The bound folds to the first
  `TABLE_OPENS_BOUNDED_ABOVE` rows, keeps the `N of M` badge, keeps
  one-click expansion, and `renderFindings` gets the same bound.
