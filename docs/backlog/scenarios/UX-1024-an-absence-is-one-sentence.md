# UX-1024: an absence is one sentence, and no separator stands beside an empty value

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the styleguide audit (2026-09-26, PR #294), styleguide §6e.12 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical

## Motivation

Measured on `main` at `98ab850`: `python3 -m tools.bga_view <run> --export` on `macro_micro` and `golden`, booted in Chromium at 1440x900 and 390x844.

With the reader "anyone", the header ends in an orphan "—" before an empty span. §1 says absence is stated; nothing says what the statement holds, though the CLI already has the shape (`bga/plane2.py` `absence()`).

## Decomposition

Input classes: each reader, including "anyone"; Plane 2 present, declined and absent. The journey extends meeting an empty value into knowing the command that fills it.

## Required Fix

Every empty state in `bga/viewer/` says what is missing, why, and the command that fills it; separators are drawn only between two non-empty nodes.

## Out of Scope

The CLI's absence sentences, which already hold.

## Acceptance Test

`tests/unit/test_an_absence_is_one_sentence.py`, booted with each reader: no separator beside an empty node. Mutation: restore the header's unconditional "—", and the guard reds.

## Outcome

Not started.
