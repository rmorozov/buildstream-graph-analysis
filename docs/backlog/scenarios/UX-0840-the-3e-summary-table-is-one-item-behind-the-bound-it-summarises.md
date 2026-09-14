# UX-840: the §3e summary table is one item behind the bound it summarises

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-367 (the per-class bound table), UX-830 (which last moved it) | **Found by:** review 23 | **Serves:** anyone reading §3e's table for "what is the current bound" rather than its history | **Topic:** viewer | **Area:** bga-viewer | **Shape:** judgement

## Motivation

`docs/design/styleguide.md`'s §3e carries two reference tables ("to 50
elts" at line 603, "to 4,100 elts" at line 630) that every later item's
prose narrates a delta against — each paragraph says "moved the bound
X -> Y", and the table is where a reader who skips the prose looks for
Y. `UX-830` (round 116) is the latest delta and its own paragraph
(lines 733-736) states it: 50-class opened 36,900 -> 38,200; 4,100-class
opened 32,000 -> 36,500, words 9,400 -> 9,600, nodes 5,500 -> 6,000. The
tables were never rewritten to Y:

```text
$ sed -n '603p;630p' docs/design/styleguide.md
budget, to 50 elts             7,300   36,900   12,800        800    7,900
budget, to 4,100 elts          7,000   32,000    9,000        900    5,500
$ grep -n "(50, \|(4_100, " tests/unit/test_the_page_has_a_volume_budget.py
352:    (50, 38_200, 12_800, 800, 7_900),
353:    (4_100, 36_500, 9_600, 900, 6_000),
```

Both tables still show the pre-`UX-830` numbers: opened 36,900 against
the guard's 38,200, and opened/words/nodes 32,000/9,000/5,500 against
the guard's 36,500/9,600/6,000 — the 4,100-class row is three
generations stale (`UX-683`'s words move and `UX-680`'s never landed
in it either).

**The shape is a guard that could not fail.**
`TestTheBudgetIsWrittenWhereItIsRead.test_the_style_guide_states_every_budget`
asserts every number `BUDGETS` carries appears *somewhere* in the whole
§3e section — and `38,200` does appear there, as the tail of `UX-830`'s
own "36,900 -> 38,200" sentence. The guard the reference table's
correctness depends on is satisfied by the delta narrative beside it,
so a table that never catches up to the last delta is invisible to it.

Corrected at filing (round 116's gate): both rows now read the
guard's figures - 38,200 and 36,500 / 9,600 / 6,000. What stays open
is the guard that let them drift.

## Required Fix

Rewrite the two table rows to the guard's current five- and four-value
tuples (`LANDED_HEIGHT_PX` plus `BUDGETS`), and give the guard a second
clause: the *table* row for each class — read structurally, not by
membership-in-section — equals `BUDGETS`'s row for that class. The
narrative paragraphs stay: they are the history the table is a summary
of, not a duplicate to delete.

## Decomposition

Input classes: the 50-element table (opened only stale) and the
4,100-element table (opened, words and nodes all stale) are two
distinct repair sites with different diffs; the journey is a viewer
contributor reading §3e top-down for "what do I budget for," the way
`UX-367`'s original table was written to be read.

## Out of Scope

- Re-deriving the bounds themselves — `UX-830`'s numbers are already
  measured and guarded; this item only makes the table agree with them.
- The historical narrative paragraphs' own numbers (each delta's
  *starting* value, e.g. `36,900` inside "36,900 -> 38,200") — those are
  dated records of what the bound *was*, not a claim about what it *is*.

## Acceptance Test

`python3 -m pytest tests/unit/test_the_page_has_a_volume_budget.py -q`
green with the new structural table clause; mutation: revert one table
cell (`38,200` back to `36,900`) with the narrative paragraph left
alone — the new clause reds by cell, where
`test_the_style_guide_states_every_budget` stays green throughout,
proving which guard the fix depends on.

## Outcome

**Gap measured.** With the two rows already hand-corrected (round 116's
gate), `test_the_style_guide_states_every_budget` was green against a
row that has since drifted again: the 4,100-class row's landed cell
read `7,000`, but `LANDED_HEIGHT_PX` - the one bound shared by every
class (`TestBothBudgetsAreBound.test_the_landed_page_is_short`) - is
`7,300`. The membership clause passed because `7,000` never appears as
a number this file asserts, so nothing checked the cell at all.

**Row moved.** `docs/design/styleguide.md:630`, `budget, to 4,100
elts`: landed `7,000` -> `7,300`. The 50-class row (line 603) already
read the guard's tuple exactly and needed no change. The `4,000`-elt
row inside the round-66 historical block (line 606) is untouched - it
is the pre-`UX-526` reading the narrative right after it supersedes,
not a live summary row, and its class is not in `BUDGETS`.

**Close measured.**
`python3 -m pytest tests/unit/test_the_page_has_a_volume_budget.py -q`

```text
26 passed, 2 skipped in 55.71s
```

New clause alone:

```text
TestTheBudgetIsWrittenWhereItIsRead::test_the_style_guide_states_every_budget PASSED
TestTheBudgetIsWrittenWhereItIsRead::test_the_summary_rows_match_the_budgets_structurally PASSED
TestTheBudgetIsWrittenWhereItIsRead::test_the_size_classes_are_stated_too PASSED
```

**Mutation table.**

| mutation | reddened | old guard |
|---|---|---|
| `docs/design/styleguide.md:603` `38,200` -> `36,900` (narrative paragraph at line 733 left alone) | `test_the_summary_rows_match_the_budgets_structurally`: `"§3e's 'to 50 elts' row reads (36900, 12800, 800, 7900), not this file's (38200, 12800, 800, 7900)"` | `test_the_style_guide_states_every_budget` stayed **PASSED** (1 failed, 2 passed) |

Reverted from the scratch copy (`falsify` step 4), re-ran:

```text
TestTheBudgetIsWrittenWhereItIsRead::test_the_style_guide_states_every_budget PASSED
TestTheBudgetIsWrittenWhereItIsRead::test_the_summary_rows_match_the_budgets_structurally PASSED
TestTheBudgetIsWrittenWhereItIsRead::test_the_size_classes_are_stated_too PASSED
```
