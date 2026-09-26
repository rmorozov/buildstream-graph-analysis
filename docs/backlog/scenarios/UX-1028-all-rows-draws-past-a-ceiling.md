# UX-1028: "All rows" draws the whole table past any ceiling

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the styleguide audit (2026-09-26, PR #294), styleguide §3k | **Serves:** R1, R4 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** bounded

## Motivation

Measured on the 4,002-element run (`bga gen-synthetic --seed 1 --layers 20 --width 200 --store --runs 30`), exported, 1440x900, every chapter open, then every step control pressed.

```text
largest table at rest     40 rows (TABLE_OPENS_BOUNDED_ABOVE)
after "All rows"          4,002 rows (elements)
DOM, every step pressed   62,995 (8.9x rest)
```

## Decomposition

Input classes: tables at 11, 40, 41 and 4,002 rows. The journey extends reading the bounded table into walking the rest a page at a time.

## Required Fix

"All rows" in `bga/viewer/tables.js` is offered only under a ceiling the table states; past it the step replaces the mounted window with the next bound of rows, the position shown ("rows 41-80 of 4,002"), or opens table focus. It never appends.

## Out of Scope

Virtual scrolling.

## Acceptance Test

The §3k census (UX-1032) presses every step at 4,002 elements, each paging step 10 times: mounted rows stay at the bound after every press. Mutations: offer "All rows" unconditionally, or append the next page, and the census reds.

## Outcome

Not started.
