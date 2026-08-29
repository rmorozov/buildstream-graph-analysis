# UX-418: a slow file is small until CI times out

**Priority:** Medium | **Status:** 🔴 Not Started | **Found by:** UX-403's guard census | **Serves:** the edit-run loop | **Topic:** guards

## Motivation

`UX-403`'s census mutated one guard per family and watched it go red.
Ten of eleven did. The one that did not was
`test_the_tiers_are_a_partition.py`, under the mutation "a large file
demoted to no tier":

```text
tier partition               GREEN    14 passed in 0.58s
```

Deleting a **50-second** entry from `LARGE` changed nothing. Every
clause in that file reads the two lists against each other or against
the filesystem — *listed files exist*, *no file is in two tiers*,
*every file is in at most one* — and `small` is the default, so a file
that belongs in a tier and is absent from both lists is "small on
purpose" and nothing says otherwise. The module's own docstring names
this escape for the *stale* direction ("a renamed file leaves its line
behind… the file it names silently becomes small") and never covers
the missing one.

`UX-403` fixed the half that is legible without measuring: a file that
boots a real Chrome says so in its imports, and four were doing it from
the small tier. What is left needs a measurement, and the file is right
that timing a suite from inside itself goes flaky and then gets muted.

Today the missing half is caught by CI's small-tier timeout — which
fails as *"the small tier took longer than `SMALL_TIER_BUDGET_S`"*,
naming a budget rather than the file that blew it, on a step that
already runs after every push.

## Required Fix

The measurement exists; nothing reads it. `pytest --durations=0`
prints per-test setup/call/teardown, which is exactly what
`tests/tiers.py`'s figures are derived from by hand.

- A CI step (or a `tools/dev_*.py` helper) that sums `--durations=0`
  per file after the full run and compares each file against the floors
  in `tests/tiers.py`, failing with **the file's name and its measured
  cost** when an unlisted file is over `MEDIUM_FLOOR_S`.
- It runs where a full run already happens, so it costs a parse rather
  than a second suite.
- The floors stay the authority; this only reads them.

## Out of Scope

- A wall-clock assertion inside a test. That is the shape
  `test_the_tiers_are_a_partition.py` rejects and this item agrees
  with it.

## Acceptance Test

- Deleting a large entry from `tests/tiers.py` fails the new step,
  naming the file and its measured seconds.
- Falsification: the same deletion with the step removed passes, which
  is the state this item is filed on.
