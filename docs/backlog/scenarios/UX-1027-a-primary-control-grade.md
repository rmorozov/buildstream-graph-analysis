# UX-1027: one control per view wears a primary grade

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the styleguide audit (2026-09-26, PR #294), styleguide §6e.5 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical

## Motivation

§6a's "one primary action per view" row was never decided, and §6d's four grades have no primary one. The first command's copy in "What should I run next?" is the page's one next step and looks like every other button.

## Decomposition

Input classes: chapters with no, one and several commands. The journey extends reading the decision into running its first command.

## Required Fix

A fifth grade, `primary` (accent fill), in `bga/viewer/style.css`, worn by at most one control per chapter; the first command's copy wears it.

## Out of Scope

A primary control per section.

## Acceptance Test

§6d's census in `tests/unit/test_static_census.py` gains the grade and a count ≤ 1 per chapter. Mutation: give a second copy button the grade, and the census reds.

## Outcome

Not started.
