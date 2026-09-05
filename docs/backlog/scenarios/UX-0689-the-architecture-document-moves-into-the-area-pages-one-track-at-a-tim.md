# UX-689: the architecture document moves into the area pages, one track at a time

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-688 (the pages), UX-569 (the prose its guards do not read), UX-568 (the spec's Part→guard index) | **Serves:** the reader pricing a change; the session restructuring without losing a sentence | **Topic:** docs | **Shape:** judgement

## Motivation

```text
docs/spec/specification.md     3,051 lines · 16 guards · frozen outside Part 32 by rule · Part→guard index landed (UX-568)
docs/design/architecture.md    1,648 lines · 19 guards · guarded skeletons exact, prose drifting (UX-569, round 82)
```

The brief proposes restructuring both. The spec should not be
restructured: it is layered — the Part 32 registry, the Part→guard
index, the advisory-Parts note — and its five edge decisions are
taken (`UX-564`..`UX-568`); a rewrite would re-open them for no
reader. The architecture document is the one whose *prose* has
drifted, and the area pages (`UX-688`) are where each chapter's prose
belongs — beside the derived tables that keep it honest.

## Required Fix

A planned round of tracks, not a rewrite: one area per track under
the `decompose` skill's merge rules; each track moves the chapter's
mechanism prose into the area page, leaves a one-paragraph pointer in
`architecture.md`, and keeps the guarded skeletons (CLI table,
contract inventory, viewer table, verification log) where the guards
read them. The acceptance figure is the round-82 review's method run
before and after: no sentence lost, every link resolving, the 19
guards green throughout.

## Out of Scope

- The specification's body — layered, not moved (§3.12 stands).
- `directions.md` — the history of the arguments; it is read as
  history.

## Acceptance Test

After the last track: `architecture.md` under 400 lines of pointers
and skeletons; every former chapter's sentences found in exactly one
area page; the 19 guards green; the link guard green.
