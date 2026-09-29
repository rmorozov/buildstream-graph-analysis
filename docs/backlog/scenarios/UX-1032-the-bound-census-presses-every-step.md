# UX-1032: the §3k census presses every step control at the largest size class

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the styleguide audit (2026-09-26, PR #294), styleguide §3k | **Serves:** R1, R4 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** bounded

**Guard:** test_every_step_past_a_bound_is_bounded.py · inferred r149

## Motivation

Measured on the 4,002-element run (`bga gen-synthetic --seed 1 --layers 20 --width 200 --store --runs 30`), exported, 1440x900, every chapter open, then every step control pressed. At rest all three §3k violations pass; only pressing the steps finds them.

## Decomposition

Input classes: both fixtures and the 4,002-element run; every step control pressed. The journey extends reading the page at rest into pressing every control it offers.

## Required Fix

A booted census at the largest size class (§3f) in `tests/unit/test_every_step_past_a_bound_is_bounded.py`: open every chapter, press every step control, and read rows mounted per table, names per reveal and characters per text run and per JSON door. The ceilings are literals in the guard (`MOUNTED_ROWS_MAX = 200`, `NAMES_MAX = 60`, `TEXT_CHARS_MAX = 20_000`), never imported from the constants it audits; each paging step is pressed 10 times, not once.

## Out of Scope

Fixing the three violations (UX-1028, UX-1029, UX-1030), which land their own mutations.

## Acceptance Test

The census reds today on the three violations, and each fix row greens its part. Mutations: raise `TABLE_OPENS_BOUNDED_ABOVE` to 10,000, and the at-rest table mounts 4,002 rows past `MOUNTED_ROWS_MAX`; make the page step append instead of replace, and the tenth press reds.

## Outcome

**Gap measured.** Against the unmodified code (production `tables.js`,
`structured.js`, `rawjson.js` at this round's base), the census run
against `bga gen-synthetic --seed 1 --layers 20 --width 200`, 1440x900,
every chapter and `<details>` open, every step pressed 10 times:

```text
tables mounted past MOUNTED_ROWS_MAX (200)   wall_clock_share_us, elements -> 4,002
                                              leaf_analysis.leaves_detail -> 533
reveals past NAMES_MAX (60)                  up to 207 names mounted at once
json doors past TEXT_CHARS_MAX (20,000)      elements -> 3,591,520 characters
```

5 of 10 clauses failed (`pytest -q`), matching the three filed violations.

**Close measured.** With UX-1028/UX-1029/UX-1030 landed in the same
branch: `pytest tests/unit/test_every_step_past_a_bound_is_bounded.py -q`
-> `10 passed`.

**Mutation table** (each reverted after, from a copy per the `falsify`
skill):

| mutation | reddened | count |
|---|---|---|
| `TABLE_OPENS_BOUNDED_ABOVE` 40 -> 10,000 | `TestEveryTableStaysBounded::test_no_table_ever_mounts_past_the_bound` | 1 of 10 |
| paging step appends instead of replacing (`state.top.n` accumulates) | same table clause, at the 5th of 10 presses | 1 of 10 |

Both this file's own two mutations reproduce the census's design intent
(the ceiling is a literal, never imported); UX-1028/1029/1030 reproduce
their own three mutations against the same file (see those files).

Deviation: none from the Required Fix; the guard was tiered medium at 14.7s on the merge (`f71a4831`).
