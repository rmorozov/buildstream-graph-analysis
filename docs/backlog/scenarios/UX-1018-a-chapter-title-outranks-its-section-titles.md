# UX-1018: a chapter title outranks its section titles in the heading outline

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the styleguide audit (2026-09-26, PR #294), styleguide §6e.1 | **Serves:** R1, R4 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical

## Motivation

Measured on `main` at `98ab850`: `python3 -m tools.bga_view <run> --export` on `macro_micro` and `golden`, booted in Chromium at 1440x900 and 390x844.

```text
h1                        the wordmark "bga"
chapter title             h2, 17px, 700
section title             h2, 17px, 700
```

A chapter and its first section look identical, and the outline has one level where it needs three.

## Decomposition

Input classes: chapter, section and block titles; both fixtures. The journey extends scanning the outline into telling a chapter from its section.

## Required Fix

`h1` the run, `h2` a chapter at `--font-h1`, `h3` a section at `--font-h2`, `h4` a block at body weight 600, in `bga/viewer/chapters.js` and `bga/viewer/style.css`. §4f's four sizes hold.

## Out of Scope

Renaming the wordmark.

## Acceptance Test

`tests/unit/test_the_heading_outline_has_three_levels.py`, booted: the outline skips no level, and every chapter title is strictly larger than every section title. Mutation: render section titles as `h2`, and the guard reds.

## Outcome

Not started.
