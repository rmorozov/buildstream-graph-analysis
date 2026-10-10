# UX-1354: layout-free browser checks read the DOM shim instead of Chrome

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** round 173 (UX-1349 Decision) | **Serves:** R8 | **Topic:** guards | **Area:** tests | **Shape:** judgement | **Reading:** runner:test

**Guard:** none — open, no guard named yet

## Motivation

UX-1349's Decision measured browser tests at 59% of CI test seconds and
named the larger cost: 559 Chrome drives, 971 s. It rejected moving the
layout-free checks to the DOM shim for that row, as a per-test judgement
over about 150 files that three arms cannot take from one brief, and left
it for its own row.

## Required Fix

Move checks that need no layout from a Chrome drive to the DOM shim, file
by file. Each moved check keeps its claim: the assertion is unchanged, and
a check that reads layout, computed style or scroll stays in Chrome.

## Out of Scope

Checks that need layout. Rewriting the DOM shim. The browser tier's
selection in `tests/tiers.py`.

## Acceptance Test

Browser share of CI seconds measured before and after on a refreshed
`tests/ci_reference.json`, with the command and the numbers pasted in the
Outcome.

## Outcome
