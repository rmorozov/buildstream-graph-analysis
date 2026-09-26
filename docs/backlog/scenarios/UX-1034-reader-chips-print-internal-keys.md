# UX-1034: reader chips print R1 to R5 inside section headings

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the styleguide audit (2026-09-26, PR #294), styleguide §4g.3 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** bounded

## Motivation

Measured on `main` at `98ab850`: `python3 -m tools.bga_view <run> --export` on `macro_micro` and `golden`, booted in Chromium at 1440x900 and 390x844. Section headings read "What this capture supports **R4**"; §4g.3 says no internal key reaches the reader.

## Decomposition

Input classes: every section heading with a reader chip; each reader. The journey extends reading a heading into knowing who it is for.

## Required Fix

The chip in `bga/viewer/` names the reader in words, or leaves the heading.

## Out of Scope

The R-numbers in the docs, which are for authors.

## Acceptance Test

The reader-strings guard (§4g) reds on `\bR[1-9]\b` in rendered headings. Mutation: restore the chip text, and the guard reds.

## Outcome

Not started.
