# UX-1019: one concept is one word and one control on every bga surface

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the styleguide audit (2026-09-26, PR #294), styleguide §6e.2 | **Serves:** R1, R4 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** bounded

## Motivation

Measured on `main` at `98ab850`: `python3 -m tools.bga_view <run> --export` on `macro_micro` and `golden`, booted in Chromium at 1440x900 and 390x844.

- each top action shows two "why" affordances side by side: a `why` link and a "▶ Why #1" disclosure;
- run / build / capture, element / task, chain / critical path are used interchangeably across chapters;
- the page, `perfetto.html`, `sql.html` and `describe()` name the same things with no shared list.

## Decomposition

Input classes: the page, `perfetto.html`, `sql.html` and `describe()`; top actions and their why controls. The journey extends reading one chapter into recognising the same thing in the next surface.

## Required Fix

A terminology matrix in `docs/design/styleguide.md` §6e.2: each reader noun, the one word for it, and the surfaces that print it. One "why" control per top action.

## Out of Scope

Renaming schema keys.

## Acceptance Test

The reader-strings guard (§4g) reads the matrix and reds on a listed synonym in rendered text or `describe()` output; booted, one "why" control per top action. Mutation: print "build" for a run in one heading, and the guard reds.

## Outcome

Not started.
