# UX-999: a weekly retro turns repeated bookkeeping into automation

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-998 | **Blocks:** — | **Found by:** round 139 — Ruslan in the project thread, 2026-09-23 15:11: "for any kind of bureaucracy automation is always is right way to solve the problem" | **Serves:** every later round, through the bookkeeping it no longer files | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

The run ledger's friction column is free prose: 276 of 350 rows fit none
of the eight recurring themes a keyword sweep finds, and rounds 132, 133,
135 and 137 have no rows at all, so the process cannot read its own cost.
Bookkeeping recurs by class (derived counts, census bounds, slug markers),
and each class has so far been fixed one instance at a time.

## Required Fix

A `retro` skill and a weekly routine that runs it. It reads the
bookkeeping ledger (`UX-998`), the run ledger and CI history, groups
repeated lines by class, and for the top classes proposes the tool, hook
or derivation that removes the class. The proposals go to the `architect`
as optimization rows (exempt from `UX-994`'s cap). Its one metric is
bookkeeping lines filed per week, which should fall.

## Out of Scope

Implementing any proposal the retro makes.

## Acceptance Test

To be named by the `architect`'s Decision.
