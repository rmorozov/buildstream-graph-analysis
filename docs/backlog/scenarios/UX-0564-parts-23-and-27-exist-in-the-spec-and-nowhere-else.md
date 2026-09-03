# UX-564: Parts 23 and 27 exist in the spec and nowhere else

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Serves:** the maintainer deciding the spec's edge | **Topic:** analysis

## Motivation

```text
$ git grep -il "resource_mix\|CACHE_IO\|wait_to_execution\|wait_share" -- bga tests docs/backlog
(none — `largest_wait_share` in findings.py is a different quantity)
specification.md:1175-1202   Part 23, wait-to-execution ratio
specification.md:1338-1370   Part 27, resource mix
specification.md:1619-1625   both listed as `signals` keys of analysis/v9
bga/analyzer.py:1434         never writes either
```

No row, tracker line or comment records a decision to drop them; the
progress tracker's "backlog complete" line does not mention them.
They are the only two analysis Parts with nothing behind them.

## Required Fix

Decide, and record it in Part 32: implemented (two `signals` keys,
an addition under `UX-190`, with the guard the spec's 36.x pattern
gives every other Part) or declined (a registry note naming both
Parts as not published, so the next spec review does not find them
again).

## Out of Scope

- The other `signals` keys — verified present.

## Acceptance Test

The registry says which, and a guard reads the `signals` key set
against the registry's list.
