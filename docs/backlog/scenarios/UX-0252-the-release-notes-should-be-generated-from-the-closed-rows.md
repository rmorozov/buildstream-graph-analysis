# UX-252: the release notes should be generated from the closed rows

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-251 (the ledger the notes live in) | **Serves:** R8, reading what landed; and the maintainers, who should not write it a third time | **Topic:** docs

## Motivation

Every closed backlog row already carries a one-line statement of what
was wrong and a summary of what shipped, with its measurement — 789
lines of them, written at the moment the work was verified, which is
the only moment anyone knows the detail.

Hand-writing release notes would make a **third** copy of those facts,
after the task file's Outcome and the closed row. This repository's
most-repeated defect, by a wide margin, is two hand-maintained copies
of one fact drifting; a third would be a choice to reproduce it
knowingly.

So the notes' body is generated from `closed.md` between two release
markers, and the only writing per release is the head: the theme, the
contract delta, and what a consumer has to do about it.

## Required Fix

1. A generator — a `tools/` program, aliased like the rest — that takes
   two closed-row markers and emits the rows between them, grouped by
   topic, each linking its task file.
2. The head is hand-written and stays hand-written: what this release
   is *about*, the contract delta in a sentence, and the upgrade note
   when there is one. A generated theme would be a summary of summaries
   and worth nothing.
3. A guard that the generated half is generated — regenerating it
   produces no diff, the way `tests/test_golden.py` holds the golden
   snapshot.

## Out of Scope

- Generating the head. Stated above and worth stating twice: the
  judgment half is the half that makes notes worth reading.
- Rewriting closed rows into release-note prose. They are history and
  `UX-232` keeps them verbatim.

## Acceptance Test

The generator run over release 0.2.0's marker range reproduces that
release's body byte-for-byte, and the guard reddens when a closed row
is added without regenerating.
