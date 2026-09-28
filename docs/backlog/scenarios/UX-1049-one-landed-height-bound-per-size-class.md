# UX-1049: the landed page has one bound per size class, written once

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the second styleguide audit (2026-09-27), styleguide §3c, §3e, §6e.10 | **Serves:** R1, R4 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement

**Guard:** test_the_two_capabilities_are_offered.py, test_the_styleguide_names_its_guards.py, test_the_chain_folds_and_clicks_are_counted.py, test_the_page_has_a_volume_budget.py · inferred r149

## Motivation

The same quantity, the height of the page a reader lands on, is bound
in four places at `814a2db8`:

```text
§3c prose        document <= 10 screens; every chapter question within 8 screens
test_the_chain_folds_and_clicks_are_counted.py
                 DOCUMENT_SCREENS = 10.0, CHAPTER_HEADING_SCREENS = 9.0   (8.5 -> 9.0 in UX-1018)
§3e / test_the_page_has_a_volume_budget.py
                 landed <= 7,600 px (8.4 screens at 900)
UX-1023          COMPACT_LANDED_HEIGHT_PX 11,400 on macro_micro (13.5 screens at 844)
```

§3c's "8 screens" is not what its guard holds; §3c's 10 screens and
§3e's 7,600 px bound one number in two currencies; and §6e.10 says
§3c is measured in both size classes while the compact bound is 13.5
screens against §3c's 10.

## Decomposition

Input classes: `golden`, `macro_micro`, the 1,202 and 4,002 runs; both
size classes.

## Required Fix

The landed document's total height and each chapter question's
distance from the top constrain different things and stay two metrics.
Each metric gets one authoritative bound per size class, in one
currency, held by one guard: total height today lives twice (§3c's 10
screens and §3e's 7,600 px) and loses one copy; the chapter-question
bound stays independent of total height. §3c's prose derives its
figures from the guards' constants (`test_the_styleguide_names_its_guards.py`'s
derived-count pattern) rather than restating them.

## Decision

Total landed height keeps only its §3e copy, in px: `LANDED_HEIGHT_PX` and `COMPACT_LANDED_HEIGHT_PX` in `test_the_page_has_a_volume_budget.py`. Both `DOCUMENT_SCREENS` constants go. `CHAPTER_HEADING_SCREENS` stays in screens in the chain file as the regular bound, and a new `COMPACT_CHAPTER_HEADING_SCREENS` joins it, measured at 390x844 (new, not moved: worst of golden and macro_micro plus the file's headroom, measurement pasted). §3c's landed bullet becomes a pointer to §3e with no number; its chapter bullet states both screen figures, and a clause parses them against the constants (the module-count pattern, `test_the_styleguide_names_its_guards.py:402`). These are distinct metrics (distance vs volume), per Ruslan's review: none is merged into another.

- Rejected: screens as the surviving currency (10 screens = 9,000 px, looser than 7,600, no compact copy, 2 pages against 4); a name-only prose check (CHAPTER_HEADING_SCREENS 9.5 would stay green); the chapter bound in px or in the volume file (it is a distance); a shared `tests/budgets.py` (a third file both tracks edit).
- Files: `tests/unit/test_the_chain_folds_and_clicks_are_counted.py` (delete `DOCUMENT_SCREENS` and `test_the_document_fits_the_budget`, l.358/459-465; `_DISTANCE` divides by the given viewport height, not 900; the compact constant, its 390x844 clause, the §3c clause); `tests/unit/test_the_two_capabilities_are_offered.py` (drop `DOCUMENT_SCREENS` l.47, import `LANDED_HEIGHT_PX`, compare the Perfetto top in px); the volume file l.807 (add `COMPACT_LANDED_HEIGHT_PX.values()` to `numbers`); styleguide §3c l.463-468, index row l.56, one §3e sentence stating 8,500 and 11,400.
- Mutations: (1) `CHAPTER_HEADING_SCREENS` 9.0→9.5 reds the §3c clause; (2) the compact constant +0.5 reds it; (3) "at most **10 screens**" back in §3c's landed bullet reds it; (4) `COMPACT_LANDED_HEIGHT_PX["golden"]` 8,500→8,600 reds the §3e membership clause; (5) delete the landed-height assert: chapter clauses stay green (independence); (6) `LANDED_HEIGHT_PX = 1000` reds the two-capabilities clause (the import is live).
- Stop: the Perfetto clause tightens from 9,000 to 7,600 px; if the Perfetto top exceeds 7,600, stop and report (moving a bound is out of scope).
- Class product; one track, sonnet; parallel with UX-1050 (UX-1050 owns `LABELS`, `BUDGETS` and the constants' values); whichever merges second rebases.

## Out of Scope

Moving any bound's value.

## Acceptance Test

Changing `CHAPTER_HEADING_SCREENS` or the total-height bound without
§3c reds a guard. Mutations: set the first to 9.5, and the derived
clause reds; remove the total-height assertion, and the chapter clause
stays green, showing the two are independent.

## Outcome

**Gap measured.** At `5f967f09`, total landed height was bound twice
(§3c's 10 screens, §3e's 7,600 px) and the chapter-question distance
had no compact copy despite §6e.10's claim. `_DISTANCE`'s `scr()`
divided by a hardcoded 900, so it could not run at 390x844 at all.

**Close measured.** `DOCUMENT_SCREENS` and `test_the_document_fits_the_budget`
removed from the chain file; `_DISTANCE` now divides by
`window.innerHeight`. New `COMPACT_CHAPTER_HEADING_SCREENS`, first
13.5, set to **13.0** after the rail tracks merged (`2fb1524e`), the
next half screen strictly above the worst, as the regular bound's
9.0 sits above 8.6. Measured at 390x844 on both trees alike:

```text
              golden   macro_micro
maxHeadingScr    9.7          12.9
documentScr     10.1          13.3
```

Re-read on the merged tree (`_DISTANCE` via the chain file's `exports`
fixture, two runs, identical):

```text
golden 390x844: worst 9.7 :: change 8.8, time 9, machine 9.2, elements 9.3, believe 9.5, run 9.7
macro_micro 390x844: worst 12.9 :: change 12, time 12.2, machine 12.4, elements 12.5, believe 12.8, run 12.9
```

§3c's landed bullet now points at §3e with no number; its
chapter bullet states 9 and 13 screens, parsed against the constants
by two new tests. `test_the_two_capabilities_are_offered.py` imports
`LANDED_HEIGHT_PX` and compares the Perfetto top in px (5,778 golden,
7,397 macro_micro — both under 7,600). Volume file: only `numbers` at
l.807 touched, adding `COMPACT_LANDED_HEIGHT_PX.values()`.

Beyond the Decision's file list: §7's guard table (`test_the_styleguide_names_its_guards.py`)
required `test_the_chain_folds_and_clicks_are_counted.py` added to the
§3c, §3e and §6e rows, since the new guards' own text cites those
sections and the census checks the table names every citing file.

**Mutation table.**

| # | mutation | reddened | run |
|---|---|---|---|
| 1 | `CHAPTER_HEADING_SCREENS` 9.0→9.5 | `test_3c_states_both_screen_figures` | 1 failed |
| 2 | `COMPACT_CHAPTER_HEADING_SCREENS` 13.0→13.5 (the tree's landed value) | `test_3c_states_both_screen_figures` | 1 failed |
| 3 | §3c landed bullet restated "at most 10 screens" | `test_3c_states_no_landed_height_number` | 1 failed |
| 4 | `COMPACT_LANDED_HEIGHT_PX["golden"]` 8,500→8,600 | `test_the_style_guide_states_every_budget` | 1 failed |
| 5 | deleted `test_the_landed_page_is_short`'s assert | chapter clauses stayed green (independence confirmed) | 6 passed |
| 6 | `LANDED_HEIGHT_PX` 7,600→1,000 | `test_the_section_is_inside_the_document_a_reader_lands_on` (both fixtures) | 2 failed |

All six reverted from the pristine copy and reconfirmed green
(`test_the_chain_folds_and_clicks_are_counted.py` 21 passed;
`test_the_two_capabilities_are_offered.py` 21 passed;
`test_the_page_has_a_volume_budget.py` 30 passed, 2 skipped).

**Deviation.** The track's `13.5` (worst 12.9 + 0.6) was its own
headroom choice; integration set it to 13.0 by the regular bound's
convention; the §7 table rows are an addition the Decision's file list did
not enumerate, forced by an existing guard. Both are flagged for
review rather than assumed correct.

`test_3c_states_both_screen_figures`'s regex took a left word
boundary (`\b`) at `e2435ba2`, so `13` no longer matches inside `113`
or similar; that fix landed before this row closed.
