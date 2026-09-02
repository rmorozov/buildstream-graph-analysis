# UX-543: a second clause of the answer key ranks under contention

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** `UX-538` (the same species, one clause over), `UX-489` (the margin instrument) | **Found by:** `UX-538`, fixing its sibling | **Serves:** the implementing session, which must be able to believe a red | **Topic:** guards

## Motivation

`UX-538` took the timing out of `test_the_first_thing_to_fix_is_core`.
While it did, a second clause in the same file went red the same way:

```text
test_the_never_read_edges_are_the_declared_chain
  make test-touching, -n auto   red — ('lib-b.bst','lib-c.bst') missing
                                      from the restructuring finding
  alone                         green
  at base, -n 4                 green
  the re-run                    green
```

Same species, different clause: a real capture's output compared
against an expected set, where what the capture produces depends on
what the machine was doing. `UX-538`'s Motivation says why that is the
expensive failure — a red that is not a defect teaches a session to
disbelieve the suite — and one clause of a file being fixed does not
fix the file.

## Required Fix

The same two options `UX-538` weighed, on this clause's own
measurement: the margin at 1, 4 and 8 concurrent workers, pasted; then
either a floor the measured spread cannot cross, or the declared chain
read from a **recorded** capture with a cheaper live clause beside it.

Whichever it is, the docstring says what load it was measured under.

## Out of Scope

- Re-opening `UX-538`'s decision for the clause it already fixed.

## Acceptance Test

The clause green three times at 8 concurrent workers with the load
average pasted, as `UX-538`'s is.
