# UX-1057: the decomposition bar's aria-details twin table drops the certified lower-bound mark

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** round 143's walk (`10cde1d2`) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** bounded

## Motivation

Measured on `10cde1d2`, `drawings.js`'s decomposition bar
(`drawing-route-0`): the SVG plots a certified lower-bound mark
(`data-mark="lb"`) with an `aria-label` stating it. The `aria-details`
twin table styleguide Rule 9 requires (every value the SVG plots also
readable as a row) has no row for that mark - a screen-reader user
reading the table sees every segment's value but not the certified
floor the picture shows.

## Decomposition

Input classes: a route with a lower-bound mark, a route without one,
multiple marks on one route.

## Required Fix

`drawings.js`'s twin-table builder gains a row per `data-mark="lb"`
element, stating the same value and label the SVG's `aria-label`
carries, in `bga/viewer/drawings.js`.

## Out of Scope

Any other twin-table gap this pass did not measure; `columnStrip`
(kept out of the value route, `round-142`'s note).

## Acceptance Test

A route with a lower-bound mark: the twin table has a row whose text
equals the SVG mark's `aria-label`. Mutation: drop the row-emission
call, and the guard reds.
