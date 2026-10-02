# UX-1293: `design/directions.md` holds the directions in order, and its round history moves to `audits/`

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** none | **Found by:** the docs audit (2026-10-02, findings 8, 11) | **Serves:** contributors | **Topic:** docs | **Area:** unassigned | **Shape:** bounded | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

`directions.md` is 2,781 lines: 20 Directions interleaved with
"Round 24/25/26" chapters (1061-1246), an "Implementation status
(updated 2026-08-16)" (372), a "Round history" (1985) and a
"Verification Log" (2120), with Directions 10-14 after those.
`architecture.md` (~287-300) embeds a table of Done UX rows. A design
page that is also a log cannot be read as the argument it is.

## Required Fix

Directions in numeric order, each its own `##`; round, status and
verification chapters move to `docs/audits/directions-history.md`;
`architecture.md`'s row table becomes a link to the backlog.

## Out of Scope

Rewriting any Direction's argument.

## Acceptance Test

`##` headings of `directions.md` are Directions 1-20 in order and
nothing else; the moved chapters' line count is preserved; link and
anchor guards green.

## Outcome
