# UX-613: the capacity model emits no document

**Priority:** Medium | **Status:** 🔴 Open | **Depends on:** UX-595 (which built it), UX-341 (the quantity rule that blocks it) | **Serves:** R4 and anyone wanting the model's answer in a pipeline | **Topic:** contracts

## Motivation

`UX-595` built the queueing model and `bga snapshot --capacity N,RATE`
prints it. `--format json` is **refused**, with its reason:

```text
a stamped contract needs a `rate` member in schemas.QUANTITIES, which
UX-341's "no two members measure one thing" guard governs, plus the
viewer's quantityFor and four census guards
```

The refusal is right — `UX-190` forbids an output that does not say
what shape it is, and inventing a quantity to dodge that is worse than
declining. But the model's whole value is a number a pipeline can act
on, and today only a human reading a terminal can.

## Required Fix

`capacity-model/v1` as a stamped contract, with the `rate` quantity
argued against `UX-341`'s rule rather than added beside it — a rate is
not a duration and not a count, and the argument for it being its own
member is what this item owes.

## Out of Scope

- The model's arithmetic and its assumption ledger — done and guarded
  in `UX-595`; this publishes what it already computes.

## Acceptance Test

`bga snapshot --capacity 4,400 --format json` emitting a stamped
`capacity-model/v1`, with `--schema` answering for it.
