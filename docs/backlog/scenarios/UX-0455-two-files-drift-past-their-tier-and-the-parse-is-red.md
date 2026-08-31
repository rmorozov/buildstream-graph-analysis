# UX-455: two files have grown past the tier they are listed in

**Priority:** Low | **Status:** 🔴 Not Started | **Found by:** round 71, running `make test-tiers` while closing `UX-451` | **Serves:** the contributor whose `make test-medium` quietly costs a minute more than the tier says | **Topic:** guards

## Motivation

`make test-tiers` is red, and not on anything `UX-451` touched.
Measured single-process on a developer machine, against the unmodified
tree:

```console
$ for f in test_the_page_moves_between_runs \
           test_a_command_renders_as_a_command \
           test_the_agent_configuration_holds; do
    PYTEST_XDIST= python3 -m pytest tests/unit/$f.py --durations=0 -q ...
  done
test_the_page_moves_between_runs   18.39s   listed medium at 13.5s
test_a_command_renders_as_a_command 1.36s   listed small
test_the_agent_configuration_holds  0.74s   listed small
```

Two are real drift. `test_the_page_moves_between_runs.py` is past
`LARGE_FLOOR_S` (15.0s) and listed medium at 13.5s;
`test_a_command_renders_as_a_command.py` is past `MEDIUM_FLOOR_S`
(1.0s) and listed small.

The third is **not** drift and is the reason this row says so: the
parallel run reported it as medium, and measured on its own it is
0.74s - under the floor. Under `-n auto` a file waits on a worker, and
the drift parse reads a report from a contended run. That is worth
knowing before someone moves it.

`UX-418` filed exactly this shape for three other files and fixed them;
this is the same finding one round on, which is what the parse is for.

## Required Fix

- Re-measure all three single-process and move the two that really
  drifted, each with its seconds, the way `UX-418` did.
- Decide what to do about the contention artefact: either the drift
  parse reads a single-process report, or it states that a file within
  one worker-slot of a floor is not evidence. A parse that reports a
  file nobody should move is a parse people learn to skim.

## Out of Scope

- **`test_the_handoff_box_is_measured_served.py`**: `UX-451` moved it
  to large with its own before/after measurement, in that commit.
- **The floors themselves**: `tests/tiers.py`'s 1.0s and 15.0s are
  settled, and `UX-418` re-argued them last round.

## Acceptance Test

```bash
make test-tiers
```

exits 0, with each moved file's new seconds in `tests/tiers.py`'s
comment beside it, and the contention decision recorded here.

## Outcome

_Not started._
