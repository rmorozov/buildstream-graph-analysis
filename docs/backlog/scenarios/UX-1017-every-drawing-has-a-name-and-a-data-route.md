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

Every `svg[role=img]` drawn by `bga/viewer/` carries its §6 sentence as its name, and either `aria-details` pointing at the table it draws or a named twin route (the section's table) one control away.

## Out of Scope

Sonification; a new table for a drawing whose data no table holds (file it).

## Acceptance Test

`tests/unit/test_every_drawing_has_a_name_and_a_data_route.py`, booted on both fixtures: every `svg[role=img]` has a non-empty accessible name and a resolvable data route. Mutation: drop the name from the density strip, and the guard reds.

## Outcome

Not started.
