# UX-262: a long critical path grows a section without bound

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Serves:** R1, on the projects most worth analysing | **Topic:** viewer

## Motivation

The third thing the report asked to recheck, and it is real. `UX-187`
made the report readable at four thousand elements by capping the
tables that scale with *element count*. A table that scales with
**critical-path length** was not capped, and nobody had a run deep
enough to notice.

Measured in Chromium on two runs, same viewport (1440x900):

```text
run                              signals section    rows   document
1,202 elements, shallow path       1884px  2.1 screens   24   19.4 screens
  482 elements, 122-deep path      5539px  6.2 screens  132   24.7 screens
```

The section triples while the run gets *smaller*. The offending table
is the critical-path detail, and the reason is precise: the table has
`Top 10 / Top 25 / All rows` controls and **its default is `All
rows`** — so depth goes straight to the page.

A 122-element critical path is not exotic; it is what a bootstrap
chain looks like. On a real `freedesktop-sdk` build the path is the
thing the reader came for, and it is the thing that buries the rest of
the report.

## Required Fix

1. The critical-path detail table defaults to a bounded top-N, like
   every other table that can grow (`UX-187`), with `All rows` one
   click away. The control already exists; the default is the defect.
2. The bound is stated where the reader can see what they are not
   seeing — a truncated table that does not say it is truncated is
   worse than a long one (`UX-187`'s own rule).
3. A guard that a section's height cannot be driven without bound by
   path depth. What that guard can actually assert is the open
   question `UX-257` names: the harness has no layout engine, so the
   checkable form is the *row count* the renderer emits, not the
   pixels it produces.

## Out of Scope

- Capping the critical path itself, or what the analysis computes. This
  is what the *page* renders by default.
- Paginating. `UX-187` chose top-N plus an opt-out and it works; a
  second interaction model for one table would be worse than either.

## Acceptance Test

On the 122-deep run the critical-path table emits a bounded number of
rows by default and says how many it is not showing; `All rows` still
reaches all 122; and the section's height stops tracking path depth —
measured in a browser and pasted, since that is the claim.
