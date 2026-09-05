# UX-665: the page's census is a tool, so a walk reads it instead of driving it

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-359 (the page fixture every browser guard measures), UX-532 (the nested-row class a census would have caught) | **Serves:** the orchestrating session paying for a walk | **Topic:** guards | **Shape:** bounded

## Motivation

Every walk since round 63 has re-derived the same census by driving
the page: sections, rail entries, controls grouped into classes with
counts, tables with folded cells, planes present. Round 77's control
walk cost 336k tokens and most of it was that census; round 82's
five researchers rebuilt the trace and contract inventories the same
way. The `walk` skill fixes the report's shape; nothing yet makes the
census a two-kilobyte artifact a walker reads.

## Required Fix

`tools/dev_page_census.py <export.html>`: boots the export through
`tests/browser.py` once and prints JSON — sections (id, chapter,
depth), rail entries, controls by class (selector, label, count, one
example section), tables with nested tables, drawings with twins,
planes present, and the page's counters the volume guard already
takes. Two consumers:

- the `walk` and `design-review` skills read it first and drive one
  instance per class the census names — a class the census does not
  know is the finding;
- a guard holds the class registry: every control class on the
  golden and macro_micro pages is declared (selector, label pattern,
  the § that owns it) — a new control lands with its row, and a table
  whose cells fold is enumerated so `UX-532`'s shape cannot hide
  behind a fixture that has none.

## Out of Scope

- Driving controls in the tool — a census counts; the walker drives.
- Screenshots — the `design-review` skill's step, not the census.

## Acceptance Test

The census of the round-90 export lists the classes round 77
counted (193) within ±5 and names every table with a nested table;
mutation: add an undeclared button to a fixture page — the registry
guard reds naming its selector.
