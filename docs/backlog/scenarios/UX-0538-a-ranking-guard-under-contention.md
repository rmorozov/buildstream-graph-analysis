# UX-538: a guard that ranks a real build's seconds cannot hold under load

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** `UX-489` (the answer key's ranking margin), `UX-455` (the contention artefact, one guard earlier) | **Serves:** the round that runs parallel tracks on one machine | **Topic:** guards

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

_Not started._
