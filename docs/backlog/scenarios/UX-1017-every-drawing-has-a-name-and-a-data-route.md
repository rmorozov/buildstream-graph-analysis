# UX-1017: every drawing has an accessible name and a route to its numbers

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the styleguide audit (2026-09-26, PR #294), styleguide §6e.9 | **Serves:** R1, R4 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical

## Motivation

Measured on `main` at `98ab850`: `python3 -m tools.bga_view <run> --export` on `macro_micro` and `golden`, booted in Chromium at 1440x900 and 390x844.

```text
svg[role=img] with no accessible name   20 of 23 (macro_micro), 8 of 11 (golden)
```

A screen reader hears "image" for every density strip and the sparkline.

## Decomposition

Input classes: every drawing kind (density strip, sparkline, decomposition, interval, chains); both fixtures. The journey extends reading a drawing's sentence into reaching the numbers it draws.

## Required Fix

Every `svg[role=img]` drawn by `bga/viewer/` carries its §6 sentence as its name, and a route to its values, by kind:

| kind | drawn in | route |
|---|---|---|
| density strip | `drawings.js` | its §2f table twin in the same figure |
| decomposition, interval | `drawings.js` | their table twin in the same figure |
| sparkline | `drawings.js`, `element.js` | `aria-details` on the values it sits beside |
| comparison band | `views.js` `renderBand` | none today: this row draws its twin |
| store trend | `views.js` | none today: this row draws its twin |

A kind found during the work with no route gets its twin here too.

## Out of Scope

Sonification.

## Acceptance Test

`tests/unit/test_every_drawing_has_a_name_and_a_data_route.py`, booted on both fixtures: every `svg[role=img]` has a non-empty accessible name and a resolvable data route. Mutation: drop the name from the density strip, and the guard reds.

## Outcome

Not started.
