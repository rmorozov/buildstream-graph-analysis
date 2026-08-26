# UX-318: the rabbit hole announces its depth

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-277 (the nesting cap), UX-205 (the tables), styleguide §3a | **Serves:** R1, R2 | **Topic:** viewer

## Motivation

Three field reports, one mechanism. Tables nest several levels deep
and "it is unknown for user how deep rabbit hole is" — a fold says
nothing about what is behind it beyond a label. The resource blast
table "became scrollable, but nested doesn't work if I try to look
through all rows" — a nested table's scroll inside a scrolling
parent, the exact interaction §3a abolishes rather than repairs.
And the user asks for "a separate button to enlarge table to occupy
more space" — the same mechanism from the other end. §3a's three
rules: depth announced (levels and row counts on every fold), one
nested level inline, and **table focus** — the nested or capped
table takes the content column's full width as a plain in-flow
section with a breadcrumb back, the enlarge affordance entering the
same state. Deliberately not an overlay (round 24's
export-survivability argument stands); focus is served-mode state
like UX-222's, and the export keeps folds with counts.

## Required Fix

Fold labels gain depth and row counts (computed from the published
value being folded — counting is not analysis); the second nesting
level stops rendering inline and routes to focus; every capped or
nested table gets the expand control entering focus; nested
scrollboxes are removed (a table scrolls only when it is the widest
thing on screen); focus state travels in the URL fragment like the
rest of the view state (`UX-211`/`UX-225`).

## Out of Scope

- Overlays, drawers, modals — declined again with the round-24
  argument.
- Changing the nesting cap itself (`UX-277`'s number stands; this
  changes what happens at it).

## Acceptance Test

On the 1,202-element page: every fold's label states levels and
rows equal to the folded value's actual shape (walk); no table's
scroll container sits inside another (asserted from the booted
DOM); the blast table's second level opens in focus, full column
width, breadcrumb resolving back, and every row is reachable by
plain page scroll (the field defect's repro, inverted into the
guard); focus round-trips through the fragment; export shows folds
with counts and no focus machinery.
