# UX-779: the README prints two wall clocks the guide says are not the suite's

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-551 (the rule these two figures predate) | **Serves:** the newcomer budgeting a run from a number measured on someone else's afternoon | **Topic:** docs | **Area:** unassigned | **Shape:** judgement

## Motivation

The README's install block prints two bare durations:

```console
$ sed -n '295,296p' README.md
make test-small           # the tier to run while you work: 21s, measured
make test                 # the whole suite: 5m11s, measured
$ grep -rn "5m11s\|21s, measured" tests/unit/*.py | wc -l
0
```

Written 2026-08-23 by `UX-236`, which deliberately chose one wall
clock "so a reader is deciding on" a fixed figure. `UX-551` later
falsified the premise, and the fixing guide now says so in the same
breath as its own readings:

> **The suite's wall clock is a property of the machine, not of the
> suite** — round 80's 8m52s is not reproducible on the tree that
> produced it: the same commit reads 3m32s on a quiet machine. A
> single dated sample dates the afternoon, not the suite.

The README's two figures carry no date, no load average and no
machine — the three things `UX-551` established are required for a
duration to mean anything, and the three things the guide's own
readings now carry. This session measured `make test` at 333s and
418s on the *same commit* an hour apart, which is the same >2x spread
the guide records, arriving again.

The cost is small and specific: the README is the front door, and its
number is the one a newcomer budgets against. `5m11s` says the suite
is fast; `make test` here has run at seven minutes with three agents
on the box.

## Required Fix

Point at the guide's spread rather than repeating a sample. The
fixing guide already carries a measured table with the load reading
beside each figure — the README should link it, or state a range with
the same three attributes, and not a bare second-count either way.

`UX-236`'s reason for a fixed figure was real: a reader wants to know
roughly what they are in for before running anything. A range serves
that; a wrong point estimate does not. Say in the Outcome which shape
was chosen and why, and annotate `UX-236` — this supersedes its
explanation, which is fixing-guide item 6.

## Out of Scope

- The tier durations in `tests/tiers.py`, which are derived and
  guarded — `UX-503` owns them.
- Re-measuring the suite. Whatever number this round takes would be
  another afternoon's; the point of the row is that a point estimate
  is the wrong shape.

## Acceptance Test

A guard that reads the README's duration claims and reds on a bare
second-count with no date and no machine beside it — the same shape
`UX-511` gave the real-project guide's block.

## Outcome

_Not started._
