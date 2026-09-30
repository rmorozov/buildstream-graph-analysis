# UX-1190: table sort is keyboard-reachable, shows its state, and ranks the whole population

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-157 data-exploration review (`/mnt/project-files/view-ui-review/data-exploration/review.md`) of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`, Plane 2 rewritten by heavy.py to 5,849 processes and at most 81 binaries per element) at `cbc739b0`, Chromium 1440x900 and 390x844 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Finding: 8 of the review.

0 of 68 header cells across 29 tables are focusable. No `aria-sort` at rest, although the element table opens sorted descending. The first click sorts ascending and reorders only the 25 already shown, so row 1 reads 8.8 s rather than the fastest element. Controls that differ from their label: a header click on "Element durations" shows ▲ ascending and re-sorts the 25 mounted, not the population. Breaks §6e.8 and §6d.

## Decomposition

Input classes: the 1,202-element two-plane page, the heavy-binary page (`UX-1182`'s, heavy.py's until it lands), `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

Rule, "a sortable header is a button": it shows its resting direction, the first press on a quantity sorts descending, and sorting re-ranks the population before the bound.

## Decision

Class: product.

## Out of Scope

Multi-column sort; the opening ranking itself (`UX-1185`).

## Acceptance Test

`tests/unit/test_a_sortable_header_is_a_button.py`: every header in a table of more than 10 rows is focusable, the opening sort shows its glyph and `aria-sort`, and after one press on a quantity row 1 is the population's maximum. Mutation: remove the `button`; the guard reds.

## Outcome

Open.
