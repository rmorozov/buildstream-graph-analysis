# UX-609: the invariants docstring lists five of six gates

**Priority:** Low | **Status:** 🔴 Open | **Depends on:** UX-602 (which fixed the same defect one layer out) | **Serves:** the reader opening the module to find what it enforces | **Topic:** guards

## Motivation

`UX-602` found Part 33.1 naming four of the six published hard gates
and gave the spec a derived table. The same omission is one layer in:

```text
bga/validation/invariants.py   module docstring lists 5 of 6
missing                        run_identity_consistent
```

`UX-602`'s guard reads the spec against the registry and passes,
because the docstring is neither.

## Required Fix

The docstring's list is derived from the registry, or it stops being a
list — a docstring that enumerates a set nothing checks is the shape
`UX-602` just removed from the spec.

## Out of Scope

- `§32.7.5` and Part 33.1 — done in `UX-602`.

## Acceptance Test

A seventh gate registered — red naming the docstring.
