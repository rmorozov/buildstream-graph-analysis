# UX-644: main is red — a map entry under the cap widened a module

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-524 (the adopted touching map), UX-605 (an over-wide map entry is not a selection), UX-624 (the last module to join the set) | **Found by:** round 87, by CI on the round's first commit | **Serves:** anyone whose branch cannot go green through no fault of its own | **Topic:** guards

## Motivation

`main` is red. `b7cdd5f` — "CI: adopt the touching map this run
measured (`UX-524`)" — adopted a map in which `bga/report/rate.py`
crossed the selector's width bound, and the guard that exists to make
exactly that loud went red on the next commit to touch the repository:

```text
FAILURE tests.unit.test_the_loop_stays_fast
        ::TestTheSelectorStillSelects
        ::test_the_wide_modules_are_named_and_not_merely_tolerated
AssertionError: joined: ['bga/report/rate.py']; left: []
```

The round's own first commit is documentation only — six task files
and two derived counts — so the failure is inherited, not caused.

Measured:

```text
bga/report/rate.py selects 36 files      (HANDFUL bound: 25)
   23  from the coverage map    entry is 23, MAP_ENTRY_CAP is 25
   11  census guards            tree-sweeping, a floor under every module
    4  named directly
```

The guard is right to fire, and the one-line fix is wrong. Its
docstring argues the set has one shape:

> These 22 are wide because their names are what a test says to
> invoke them — 116 files name `bga.cli` because they run the CLI

Four files name `rate.py`. Its width is **map** width from an entry
that sits one file under the cap, not naming width. Adding it to the
set and leaving that sentence in place would make the set's stated
argument false for one of its members — which is the thing the guard's
own name refuses ("named and not merely tolerated").

Under the cap is not a bug: `MAP_ENTRY_CAP` exists for the `UX-605`
shape, entries like `bga/progress.py`'s 209, which the cap already
discards. A 23-file entry is a real one. So the module is honestly
wide; the set's sentence is what has gone stale.

## Required Fix

`bga/report/rate.py` joins `WIDE` carrying its own argument inline, in
the shape `UX-624` set for `bga/contracts.py` — the measurement that
put it there, in three lines, beside the name.

The docstring stops claiming one shape for the whole set and names
both: naming width, where the module's name is what a test says to
invoke it (`bga/cli.py`, 116 files), and map width, where a coverage
entry under the cap carries a module a test never names
(`bga/report/rate.py`, 23 of its 36). The bound does not move.

## Out of Scope

- Re-measuring the adopted map. `UX-524` adopted what a real CI run
  measured, and the entry is inside the cap the repository already
  argues for.
- Whether the census floor of 11 should count toward a module's width
  at all. It is the same 11 for every module in the map, so it changes
  no module's *relative* width — but it does consume 44% of the bound
  before a module's own tests are counted, and no row has ever argued
  it. Filed as the question this one declined: **UX-645**.

## Acceptance Test

`test_the_wide_modules_are_named_and_not_merely_tolerated` green with
`rate.py` named. Removing the name reddens it; a mutation that drops
another member's name reddens it too, so the clause still guards the
whole set rather than one entry.

## Outcome

**The gap.** `main` red at `b7cdd5f`; the round's documentation-only
first commit inherited it. `bga/report/rate.py` at 36 selected files
against a bound of 25, absent from `WIDE`.

**The close.** The name joins the set carrying its measurement inline,
in the shape `UX-624` set for `bga/contracts.py`, and the docstring
stops claiming one shape for the whole set:

```text
before   these 22 are wide because their names are what a test says to invoke them
after    width is honest in two shapes - by name (bga/cli.py, 116 files name it)
         and by map (bga/report/rate.py, 23 of its 36, entry one under the cap)
```

```text
tests/unit/test_the_loop_stays_fast.py    45 passed in 38.78s
make lint                                 All checks passed!
```

**Mutations.**

| mutation | expected | got |
|---|---|---|
| drop `bga/report/rate.py` from `WIDE` | red | red |
| drop `bga/cli.py` from `WIDE` | red | red |
| revert both | green | 45 passed |

The second is the one that matters: it proves the clause still guards
the whole set and not only the entry this row added.

**Deviation.** The census floor — 11 of the 36, the same 11 under
every module — was measured here and not touched. It consumes 44% of
the bound before a module's own tests count, which is a question about
what the bound means rather than about this module. Filed as
**UX-645** rather than folded in.
