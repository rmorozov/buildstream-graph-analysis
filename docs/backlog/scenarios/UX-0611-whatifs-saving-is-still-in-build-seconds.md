# UX-611: what-if's saving is still in build seconds

**Priority:** Low | **Status:** 🔴 Open | **Depends on:** UX-596 (which built the converter) | **Serves:** the team deciding whether a fix is worth a day | **Topic:** report

## Motivation

`UX-596` converted the headline and the plan into the team's units.
`bga whatif`'s projected saving was outside its declared surface and
still reads:

```text
the top 3 are worth 23.1s
```

One renderer, `bga/whatif.py`, left in the unit the tool measures
rather than the one a reader decides in — which is the whole of
`UX-234`'s cost-translation argument, applied everywhere but here.

## Required Fix

`bga/whatif.py` uses `bga/report/rate.py`, the same converter, so
there is one rule and not two.

## Out of Scope

- The rate's arrival via `BGA_RATE` rather than a flag — `UX-596`
  measured the `--help` budget that decides it, and this item does not
  reopen it.

## Acceptance Test

`bga whatif` under a set rate, showing the converted figure; and the
converter removed from it — red.
