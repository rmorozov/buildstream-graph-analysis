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

One landed bound per size class, in one currency, held by one guard;
§3c's prose derives its figures from the guard's constants
(`test_the_styleguide_names_its_guards.py`'s derived-count pattern)
rather than restating them.

## Out of Scope

Moving any bound's value.

## Acceptance Test

Changing `CHAPTER_HEADING_SCREENS` without §3c reds a guard.
Mutation: set it to 9.5, and the derived clause reds.

## Outcome

Not started.
