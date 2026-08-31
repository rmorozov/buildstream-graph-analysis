# UX-444: the page budget and the data ratio have converged

**Priority:** High | **Status:** 🔴 Not Started | **Found by:** round 70, landing `UX-434` — the corrected query did not fit | **Serves:** every later round, which cannot add a sentence to the page without choosing between two ceilings nobody has compared | **Topic:** guards

## Motivation

Two numbers bound the page half of an export, and after round 70 they
are 112 bytes apart.

```text
page, as tests/unit/test_the_report_you_can_attach.py measures it   285,928 B
PAGE_BUDGET_B                                                       286,000 B   (+72)
the ceiling test_the_data_dwarfs_the_page implies                   286,040 B   (+112)
```

The second is not written down anywhere. `test_the_data_dwarfs_the_page`
asserts the scale run's data is at least **2.4x** the page budget, and
`test_only_one_number_bounds_the_page` exists precisely to catch the two
disagreeing — so the ratio, divided into the scale run's 686,497 B of
data, is a second ceiling that moves whenever the fixture's data moves.

`UX-434` met both. Its corrected `graph-levels` query — a subquery,
because the old one grouped by a name the `slice` table also defines —
took the page to 286,195 B, over both. It was landed by trimming prose
and whitespace, which bought 267 B and will not be available twice.

**The next source addition of any size trips both guards**, and the
person who meets it will be in the middle of an unrelated item, with two
numbers and no argument for either.

## Required Fix

- **Decide which number is the budget**, and say so where a later round
  reads it. Three candidates and each needs its own case: `PAGE_BUDGET_B`
  is `UX-360`'s judgement about what a reader downloads; the 2.4x ratio
  is Direction 7's rule that the data is what an export weighs; and a
  third answer is that the page is simply too big and should shrink.
- **If the ratio wins**, `PAGE_BUDGET_B` becomes derived rather than
  written, so the two cannot drift apart again.
- **If the budget wins**, the ratio needs a number that is not
  coincidentally adjacent to it, argued from what an export is for.
- **If the page should shrink**, name where. The page half has grown
  283,964 → 285,928 over rounds 69 and 70 alone, and every step was a
  sentence somebody wanted.

## Out of Scope

- **Raising either number to unblock one item.** That is what this item
  exists to stop, and round 70 declined to do it — see the note above
  `PAGE_BUDGET_B`.
- **`UX-360`'s volume budget for the rendered page**, which is about
  what a reader scrolls rather than what they download.

## Acceptance Test

One number bounds the page, derived or stated, with the other expressed
in terms of it; `test_only_one_number_bounds_the_page` reads that
relation rather than comparing two constants. A mutation that moves
either without the other must redden the guard.

## Outcome

_Not started._
