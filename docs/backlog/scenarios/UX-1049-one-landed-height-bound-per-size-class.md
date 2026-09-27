# UX-1049: the landed page has one bound per size class, written once

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the second styleguide audit (2026-09-27), styleguide §3c, §3e, §6e.10 | **Serves:** R1, R4 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement

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

Not started.
