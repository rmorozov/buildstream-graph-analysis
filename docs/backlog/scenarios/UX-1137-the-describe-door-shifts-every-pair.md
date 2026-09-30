# UX-1137: the block's `?` door takes a grid cell and shifts every term one cell over

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-1021 | **Found by:** Ruslan's own `bga snapshot` -> `bga view` (2026-09-29), reproduced on a two-plane synthetic store | **Serves:** R1, R2, R8 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_a_pair_list_keeps_its_pairs_on_one_row.py`

## Motivation

`UX-1021`'s `attachBlockDoor` prepends the block's `?` button to the
`dl.pairs` it describes, and `.pairs` is a two-column grid. The button
takes row 1 column 1, so the first `<dt>` lands in column 2 beside it,
its `<dd>` starts row 2 in column 1, and every term after sits beside
the previous term's value. Booted at 1440x900, `dl.pairs` terms not on
their value's row: 169 on `golden`, 259 on `macro_micro`.

## Decomposition

Input classes: a pair list with and without a door - finding evidence, a section's scalars, the run summary; both fixtures. The journey extends reading a term against its value.

## Required Fix

A door that is a `dl.pairs`' child spans the grid's full row, above the
terms, so the pairs keep their cells.

## Out of Scope

Moving the door out of the `dl` (the census and both door guards read
`marker.parentElement` as its block); the door's label.

## Acceptance Test

`tests/unit/test_a_pair_list_keeps_its_pairs_on_one_row.py`, booted on
`golden` and `macro_micro`: every rendered `dt` in a `dl.pairs` shares
its `dd`'s top and sits left of it. Mutation: delete the
`.pairs > button.describe` rule, and it reds on both.

## Outcome

## Outcome (round 153, 2026-09-29) — 🟢 Done

**Premise:** held — every `dl.pairs` with a door had its pairs split across rows.

### The gap, measured

```text
booted at 1440x900, dl.pairs terms whose dd is not on the same row, to the right:
  golden        169
  macro_micro   259
first split keys: category, category_us, share, hint, zero_slack_share
```

`attachBlockDoor` prepends the `?` button to the `dl`; the grid's
auto-placement gave it the first cell.

### After

```text
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_a_pair_list_keeps_its_pairs_on_one_row.py tests/unit/test_one_door_per_block.py tests/unit/test_a_sentence_lives_on_its_door.py -q
25 passed
```

`.pairs > button.describe` spans `1 / -1`, so the door sits on its own
row above the terms and each term shares its value's row.

### Mutations verified red and reverted (1)

| # | mutation | reddened |
|---|---|---|
| A1 | delete the `.pairs > button.describe` rule | `test_every_term_sits_beside_its_value[golden]`, `[macro_micro]`, 2 failed |

Deviation: `test_pointer_travel_is_a_budget.py` re-bases both 390 J3
readings, 3 runs, spread 0: `macro_micro` 18.51 -> 23.76 bits (wheel
50,777 -> 51,692 px), `both_scale` 21.01 -> 30.32 (57,550 -> 60,317).
The pairs now wrap in their own columns, so each chapter button lands
at a different height after its scroll: `chapter time` goes from 14 to
169 px of pointer distance, `believe` 737 -> 1454. An absolutely placed
door read worse (25.27 and 29.10, and J2 at 1440 over), so the row
stays. Moving the door out of the `dl` was declined: both door guards
and the census read `marker.parentElement` as its block.
