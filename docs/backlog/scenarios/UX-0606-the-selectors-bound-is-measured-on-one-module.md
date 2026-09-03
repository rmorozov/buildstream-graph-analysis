# UX-606: the selector's bound is measured on one module

**Priority:** Medium | **Status:** 🔴 Open | **Depends on:** UX-605 (which measured it), UX-336 (which set the bound) | **Serves:** the session whose one-module edit runs a third of the suite | **Topic:** guards

## Motivation

`UX-605` capped the touching map and, measuring what remained, found
the bound it was restoring is a claim about one module:

```text
mapped modules whose selection exceeds 25, map ignored entirely   18 of 85
worst   bga/cli.py   112 files, from the grep half alone
```

`test_a_one_module_change_selects_a_handful_not_the_suite` calls
`select(["bga/store_aggregate.py"])` — a distinctive two-word name that
appears in 13 files because those 13 are about it. `cli`, `models`,
`loader` and `analyzer` are not that kind of name, and the guard has
never asked about them.

So the sentence "a one-module diff selects a handful" is true of the
sample and unmeasured for half the tree. Not a defect in the selector:
a defect in what is known about it.

## Required Fix

The bound is measured across every module the map names, not one, and
whatever the measurement says becomes the guard — a per-module ceiling
with the modules that exceed it named and argued, or a distribution
with a stated percentile. `store_aggregate` stays as the worked
example; it stops being the whole evidence.

## Out of Scope

- Narrowing `tokens_for`'s stem rule — declined: `UX-522` measured
  that rule and it is the reason `findings` is excluded already;
  changing it needs its own measurement, not this one's.
- The map's cap (`UX-605`) — done there.

## Acceptance Test

The guard reports a figure over the whole mapped population, and a
module added to that population with a selection over the ceiling
turns it red.
