# UX-583: the round history is typed, and three rounds are missing from it

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Serves:** the reader tracing a decision to the round that made it | **Topic:** docs

## Motivation

```text
docs/audits/round-81.md exists          directions.md: 0 mentions
rows 25 and 26                          link to round-24.md; no round-25/26 files exist
planted-defect-walk-round-72.md, guard-census-round-64.md   no row
Verification Log (directions.md:1444)   link text "optimization-walkthrough-06.md" for case-study-06-macro-micro.md
docs/README.md audits list              maintained by hand, same omissions (rounds 75-79 added by round 79 in passing)
```

The table is the one place the arguments and the rounds meet, and it
is hand-typed by whichever session remembers.

## Required Fix

A guard that holds the round-history table and the `docs/README.md`
audits list to `docs/audits/`: every `round-*.md` and named walk has
a row that links to it, every row links to a file that exists, and
link text matches the file; the missing rows written (the sibling's
rounds are summarised from their own first paragraphs).

## Out of Scope

- Rewriting existing rows — they are the record of what each round claimed; only missing rows and broken links change.

## Acceptance Test

Mutation: add `round-99.md` — red; point a row at a missing file —
red.
