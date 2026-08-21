# UX-206: focused graphs, not a DAG viewer

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-202 (the overview these hang off), UX-199 (the anchors they link to), Direction 7 second iteration

## Motivation

The external review and Direction 7 arrived at the same restraint
independently: a general BuildStream DAG viewer answers no question
anyone asks, and the temptation to build one must lose to the two
graphs that *are* questions:

1. **The critical path, drawn**: the chain the report already prints
   as text, as a horizontal sequence — element boxes sized by
   duration, linked to their sections, the elided middle (UX-187's
   fold) expandable in place. It is the "where did the time go"
   spine, and it is a *list with widths*, not a graph layout
   problem.
2. **The blast tree**: the blast answer as an indented hierarchy —
   direct consumers, then closure by depth, each row carrying its
   kind badge and measured work — the review's own sketch, which is
   a `<details>` tree over data `blast/v1` already carries, not a
   renderer.

Both are DOM and small SVG in the existing no-library discipline;
neither needs layout algorithms. The general DAG stays deferred with
its vendoring decision, as Direction 7 already records.

## Required Fix

The two views, in the UX-196 pattern (published JSON only, no viewer
arithmetic, geometry asserted from data attributes); the critical
path linked from the overview's execution segment (UX-202), the
blast tree from each blast answer and Shared Sources row.

## Out of Scope

- Any general graph rendering, any layout library (the deferral
  stands until a concrete question defeats these two).
- Cross-run diff graphs.

## Acceptance Test

The critical-path view on the 1,202-element synthetic renders the
folded chain with widths proportional to published durations
(asserted from data attributes; mutation: uniform widths reddens)
and expands the fold in place; the blast tree on the monorepo
fixture nests closure depths correctly against the JSON (depth
asserted) and renders kind badges from the declared item shape. No
new files beyond the views module growing; the page-size guard
(`< 80,000 B`) still holds.
