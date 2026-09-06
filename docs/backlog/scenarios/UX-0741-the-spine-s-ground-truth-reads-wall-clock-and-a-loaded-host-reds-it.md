# UX-741: the spine's ground truth reads wall clock, and a loaded host reds it

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-108 (the guards), UX-731 (the same swap, done once), UX-110 | **Serves:** R8 reading a red gate on a file nobody touched | **Topic:** guards | **Shape:** judgement | **Area:** tools

## Motivation

`tests/unit/test_spine_ground_truth.py` checks Plane 2 against
arithmetic on `examples/01-resource-contention`, which runs `sleep 3`
eight times. Two of its clauses assert wall-clock readings against
fixed tolerances:

```python
SLEEP_TOLERANCE_S = 0.5      # "generous on the upper side because a
                             #  loaded runner delays teardown"
PLANE_AGREEMENT_S = 1.0
```

Both blew through those tolerances in round 102's gate, on a green
tree, with four implementer tracks running beside the suite:

```console
$ uptime
 18:18:48 up  3:13,  0 user,  load average: 16.14, 29.37, 25.20

E   AssertionError: work-c.bst: 3.917s for a `sleep 3`
E   assert 0.9167175330003374 < 0.5
E   AssertionError: work-a.bst: Plane 2 3.506s against Plane 1 7.284s
E   assert 3.777534432891116 < 1.0
```

**The tree is not at fault, and CI is the discriminator.** The same
commit's CI run named four failures and neither of these was among
them - GitHub's runner is quiet, and there both clauses pass. So this
is a property of the instrument, not of the spine: a `sleep 3` really
does take 3.9s of wall clock on a host at load 16, and Plane 1's
wrapped-log stamp really does drift 3.8s from Plane 2's when the
scheduler is that contended.

This is the shape `UX-731` already closed once, one file over:
**an instrument that reads a proxy for the thing it names.** There the
proxy was elapsed time standing in for algorithmic work, and the fix
was to count line events instead. Here the guard's subject genuinely
*is* elapsed time - `sleep 3` is a claim about the clock - so the same
answer does not transfer, which is why this is filed rather than
fixed in place.

## Required Fix

The judgement first, because the routes differ:

- **Widen the tolerances.** Rejected on sight and recorded here so a
  later round does not re-propose it: 0.5s -> 4s to admit this reading
  would stop the clause discriminating between a `sleep 3` and a
  `sleep 6`, which is the whole claim.
- **Skip on a loaded host.** The clause states what it needs -
  a load average under some measured figure - and skips with that
  reason when the host cannot supply it. `UX-213`'s rule (a guard
  that only guards one machine) is the tension: a clause that skips
  on every developer box guards CI alone.
- **Read something the load cannot move.** The spine records
  `/proc/<pid>/stat`; a `sleep`'s *CPU* time is ~0 under any load,
  and `IDLE_CPU_US` already asserts that and did not red. Whether the
  wall-clock half can be re-expressed against a monotonic reading the
  contention does not stretch is the real question, and it needs
  measuring before it is chosen.

Measure before choosing: run the two clauses at several load averages
and record where each starts to red, so whichever route is taken has a
number under it rather than an adjective.

## Out of Scope

- `PLANE_AGREEMENT_S`'s underlying disagreement, which is `UX-110`'s
  axis - this row is about the guard reading, not the lag.
- The other clauses in the file. `IDLE_CPU_US` and the
  eight-elements-measure-identically clauses held at load 16.

## Acceptance Test

The two clauses give the same verdict on a quiet host and a host at
load 16 - either both pass, or the loaded one skips with the load it
measured named in the reason. Mutation: state a `sleep 6` in the
fixture and confirm the clause still reds on a quiet host.
