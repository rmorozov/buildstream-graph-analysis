# UX-581: a direction has no status, so a tail goes silent

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-231 (the Serves line every direction carries) | **Serves:** the reader deciding what is still open at direction level | **Topic:** docs

## Motivation

Every direction's decomposition landed (every id 🟢), and the
declines that were stated are stated well. What the round found is
the tails that were neither landed nor declined and say nothing:

```text
D8  directions.md:976-978   "explain-path for compare"             git grep "evidence chain" scenarios → 0
D9  directions.md:1025-1031 queue seam · capacity model · cost translation    greps → 0 files (cost translation: UX-234 only)
D10 directions.md:1562      item 5 "a tag"                          git tag | wc -l → 0
D11 directions.md:1641-1645 four "yes" rows for bga:distribution    schemas.py: one site
D1  directions.md:188-206   "None of it is currently printed"       no Done callout; phrases absent from report/text.py
```

`test_every_direction_names_its_reader.py` walks the `## Direction`
headings for a Serves line; no line says whether a direction is
landed, partial or declined, so a partial one reads as landed.

## Required Fix

A `**Status:**` line per direction — `landed` / `partial — <what
remains, as a filed id or a stated decline>` / `declined — <why>` —
held by extending the Serves guard's section walk; the five above
resolved into that vocabulary (the D8/D9 tails filed or declined, the
tag either cut or the item retired, D11's table corrected).

## Out of Scope

- Re-arguing any direction — the status line records the state; the argument stays as written.

## Acceptance Test

Mutation: remove a direction's Status line — red; write `partial`
without an id or a decline — red.
