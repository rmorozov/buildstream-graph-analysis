# UX-538: a guard that ranks a real build's seconds cannot hold under load

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-489` (the answer key's ranking margin), `UX-455` (the contention artefact, one guard earlier) | **Serves:** the round that runs parallel tracks on one machine | **Topic:** guards

## Motivation

`test_the_journey_has_an_answer_key.py::test_the_first_thing_to_fix_is_core`
captures a **real `bst` build** of `examples/06` and asserts that
`core.bst` leads the what-if ranking. It does, on a quiet machine.
Round 80 ran four implementer tracks in parallel worktrees on one
container, and the same guard failed three times in a row with three
different answers:

```text
load  ranking, first three                                    verdict
 ~1   core.bst 9.05s · lib-a 7.0s · ...                        green
 ~6   lib-a.bst 7.00s · lib-b 6.0s · lib-c 5.0s                red
~10   lib-a.bst 14.05s · lib-b 13.0s · lib-e 11.0s             red
~12   core.bst 9.05s (leads by too little for `leads`)         red
```

The savings it ranks are measured wall clock inside a sandbox, so
under contention the leader changes. `UX-489` measured this guard's
**margin** and found it thin; this is that margin meeting a loaded
box, and the box is loaded because the round's own workflow now puts
four tracks on it (`UX-510`, `UX-525`).

The failure mode is the expensive one: a red that is not a defect
teaches a session to disbelieve the suite.

## Required Fix

- Measure the guard's margin against load, not in the abstract: the
  same capture at 1, 4 and 8 concurrent workers, ranking pasted for
  each. `UX-489` has the instrument.
- Then one of two, on that number: give the ranking a **floor** the
  measured spread cannot cross, or take the timing out of the
  assertion — rank a *recorded* capture and let a separate, cheaper
  clause hold that a live capture still produces one.
- Whichever it is, the guard says in its docstring what load it was
  measured under, the way `UX-456` names CI's.

## Out of Scope

- The four-track workflow itself, declined: it is `UX-510`'s and the
  round-79 filings' answer to a real cost, and a guard that only
  holds when nothing else runs is the thing to fix.
- `bga what-if`'s ranking, declined: the same run ranks the same way,
  and what moves under load is the capture underneath it.

## Acceptance Test

The guard green at 8 concurrent workers, three runs, all three
rankings pasted. Mutation: shrink the fixture's separation between
`core.bst` and the runner-up below the measured floor — the guard
must red on a quiet machine, not only on a loaded one.

## Outcome

**Round 80, 2026-09-02.** 4-core box, `examples/06` cold, `analyze` on
the result, in two load shapes.

**N concurrent captures.** Eight cannot run here: eight isolated CAS
stores exhaust staging (`OutOfSpaceException` in `merklize`) - the
disk, not the ranking. Four can, with the quota pinned:

```text
load  first in the horizon   core    best (element)      core leads
  1   core.bst              10.0    10.0  core.bst       yes  (wall 56.0s)
  4   lib-c / core / lib-d   18-22   40-42 codegen.bst    no, 0 of 4
```

**One capture, N-1 burners** - the shape round 80's four-track
workflow actually produces:

```text
load  first in the horizon   core    best (element)      core leads
  1   lib-d.bst             14.0    17.05 lib-d.bst      no
  4   lib-c/lib-d/lib-f     16.05   17.0  three-way tie  no
  8   lib-f.bst             14.05   20.0  codegen.bst    no
  8   lib-b.bst             20.35   25.05 codegen.bst    no
  8   lib-f.bst             absent  22.2  lib-f.bst      no
  8   core.bst              21.1    27.05 codegen.bst    no
```

**So `core.bst` led 1 of 1 quiet runs and 0 of 12 loaded ones.** At
four workers `codegen.bst` takes the top saving by about **2x** - an
outright reversal, not a tie `UX-489`'s `leads` absorbs. So a floor is
not available: the leader changes, and no number separates "the fixture
lost its shape" from "the box was busy". One 8-way run dropped
`core.bst` out of the horizon **entirely**, falsifying even the weaker
claim that it is named.

**The close: the second option.** The ranking clause reads
`tests/fixtures/macro_micro/run` - the same build, recorded - so its
input is bytes rather than seconds:

```text
core.bst 12.05s   codegen.bst 7.0s   margin 1.7214,  x3 identical
```

and it now asserts `leads` **plus** `CORE_LEAD_FLOOR = 1.25` - 0.47 to
spare, and above every loaded margin (1.00-1.48). The live capture
keeps one cheaper clause, `test_a_live_capture_still_ranks_something`:
a non-empty horizon, which is all 12 loaded runs agreed on.

**Mutations.** `PYTHONDONTWRITEBYTECODE=1`, `__pycache__` cleared.

| # | mutation | reddened | count |
|---|---|---|---|
| R1 | `core.bst`'s recorded span 19.023s -> 11.0s (saving 4.0 < codegen 7.0) | `leads`, in `test_the_first_thing_to_fix_is_core` | 1 failed, 22 deselected |
| R2 | the same span -> 15.0s: core 8.0 vs 7.0, margin **1.143**, below the floor and still leading | the `CORE_LEAD_FLOOR` clause, by itself | 1 failed, 1 passed |
| R3 | `bga/analyzer.py` publishes an empty `optimization_horizon` | both clauses, recorded and live | 2 failed, 21 deselected |

R2 is the one the Acceptance Test asked for: it reddens the *floor*
rather than `leads`, on a quiet machine.

**Acceptance Test, pasted** - the clause at 8 concurrent workers, x3:

```text
--- run 0, 8 workers, loadavg 14.58 ---   1 passed in 3.96s
--- run 1, 8 workers, loadavg 14.69 ---   1 passed in 3.79s
--- run 2, 8 workers, loadavg 15.68 ---   1 passed in 8.84s
```

Identical ranking all three: `core.bst` 12.05s, `codegen.bst` 7.0s,
margin 1.7214. Whole file alone: `23 passed in 144.47s`.

**A second instance, not fixed.**
`test_the_never_read_edges_are_the_declared_chain` here went red once
under `make test-touching` at `-n auto` (`('lib-b.bst','lib-c.bst')`
missing from the restructuring finding), green alone, at base under
`-n 4`, and on the next run. Needs its own row.

**Deviation:** the 8-worker reading is one capture under 8-way CPU
contention, not 8 concurrent captures - those do not complete here, for
a reason unrelated to ranking.
