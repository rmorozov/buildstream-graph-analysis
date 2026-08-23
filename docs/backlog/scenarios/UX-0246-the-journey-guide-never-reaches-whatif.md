# UX-246: the journey guide never reaches what-if

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-230 (the command it should reach) | **Serves:** R1 — the local optimizer the guide is written for | **Topic:** docs

## Motivation

Found by review 1 (`UX-241`).

[`docs/guides/real-project.md`](../../guides/real-project.md) is the
end-to-end journey — capture → read → go inside → join → **act** →
gate — and it is the document `README.md` points at six times. The act
step is where a reader decides what to fix. `bga whatif`, which prices
exactly that decision, is named nowhere in it:

```text
subcommands absent from docs/guides/real-project.md:
  whatif, cache-trend, diagnostics, floors, graph, utilisation
```

Five of those six are correct absences: the guide is a journey and
`floors`/`graph`/`utilisation`/`diagnostics` are `analyze`'s own
sections, with `cli.md` as their reference. `whatif` is not — it is a
step in the journey the guide walks, and the guide walks past it.

## Required Fix

1. The act step gains `bga whatif <element>…`: what it answers, and
   the one thing that makes the number safe to quote — *fixed* means
   the element becomes instant over this run's measured durations, an
   upper bound and not a forecast (`UX-244` is the same convention's
   other home).
2. Real output, as every other step in that guide has.

## Out of Scope

- The other five absences, which are correct — a journey is not a
  reference, and `cli.md` names all of them (checked).
- A guard that every subcommand appears in every guide. That would be
  wrong: it would force `ci-comment.md` to name `sweep`.

## Acceptance Test

The act step names `bga whatif` with output from a real run, and the
convention is stated in the guide's own register rather than quoted
from the docstring.
