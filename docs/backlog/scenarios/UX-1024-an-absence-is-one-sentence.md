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

Gap: `wireReaderControl` (`decision.js`) always appended `" — "`
between the reader `select` and its question span. "anyone" (the
landed choice) has no question, so the header read "I am anyone — "
with nothing after the dash.

Close: the dash is now its own `span`, hidden together with the
question whenever there is none, set both at build and on `change`.
New `tests/unit/test_an_absence_is_one_sentence.py` drives every
option the picker offers and asserts no separator is visible beside
an empty question:

```text
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_an_absence_is_one_sentence.py -q
2 passed in 1.24s
```

Mutation table:

| mutation | reddened | count |
|---|---|---|
| restore the unconditional `" — "` text node | `test_no_separator_beside_an_empty_question` | 1 failed |

The guard's first draft only checked element children for a visible
dash and missed the mutation (a bare text node has no `hidden`); it
now treats any child's `—` as shown unless an element wrapping it is
hidden. Other empty-state sentences in `bga/viewer/` (the finding
fold, `Show all`, empty `dl`s) were read by hand and already state
what is missing and why; not re-swept here.
