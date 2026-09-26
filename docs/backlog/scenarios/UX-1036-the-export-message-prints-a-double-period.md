# UX-1036: `bga view --export` prints a double period before its timeline hint

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the styleguide audit (2026-09-26, PR #294), styleguide §4g | **Serves:** R1 | **Topic:** cli | **Area:** tools | **Shape:** mechanical

## Motivation

`tools/bga_view.py:1926` formats `No Perfetto timeline in it: {omitted}. ` and `omitted` is a sentence from `bga/plane2.py` that already ends in a period, so the export prints "goes missing.. `bga timeline` renders one".

## Required Fix

`tools/bga_view.py` strips the trailing period of `omitted` or drops its own.

## Out of Scope

The absence sentences' wording.

## Acceptance Test

`tests/unit/test_the_export_message_is_punctuated.py` exports a run with Plane 2 but no raw log and asserts no `..` in stderr. Mutation: restore the format string, and the guard reds.

## Outcome

Not started.
