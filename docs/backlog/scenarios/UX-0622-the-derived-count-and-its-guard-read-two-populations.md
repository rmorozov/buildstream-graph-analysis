# UX-622: the derived count and its guard read two populations

**Priority:** Medium | **Status:** 🔴 Open | **Depends on:** UX-617 (the widening), UX-501 (the derivation) | **Found by:** round 85, in UX-617's own Deviation section | **Serves:** the session filing a row | **Topic:** guards

## Motivation

`UX-617` widened `dev_close_task.py`'s population to the index **plus**
`git ls-files --others --exclude-standard`, so `--check` sees a row
that is written but not staged. The guard that reads the figure it
writes did not move:

```text
tools/dev_close_task.py::_backlog_counts       index + untracked
tests/unit/test_a_counted_figure_is_derived.py::_backlog_files   index
```

So `--write` now writes a count the guard rejects until the new file
is staged. `UX-617` recorded this rather than fixing it, on the
argument that the red is the loud direction — which is true and is not
the same as the two agreeing.

The cost is a workflow with a trap in it: run `--check --write` before
staging and the suite goes red on a figure the helper just called
clean. That is the shape `UX-617` exists to remove, one level over.

## Required Fix

Decide which population is the contract and make both sides read it,
or state in one place why they differ and have a guard assert the
difference is the intended one.

`architecture.md`'s sentence is what a reader reads; whichever
population is chosen, the sentence must say which.

## Out of Scope

- `UX-617`'s widening itself — closed, and the direction is right.
- The count's arithmetic (`UX-501`).

## Acceptance Test

A written-but-unstaged task file, `--check --write`, then the guard —
green, or red with a sentence saying it is red on purpose.
