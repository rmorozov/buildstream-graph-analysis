# UX-615: the scratchpad is shared between tracks

**Priority:** Low | **Status:** 🔴 Open | **Depends on:** UX-614 (the same launch step) | **Found by:** round 84, by the track it happened to | **Serves:** a round running tracks in parallel | **Topic:** guards

## Motivation

Tracks run in isolated worktrees and share one scratchpad directory.
One of round 84's tracks had its mutation harness overwritten by
another track mid-session:

```text
another agent overwrote my mutate.py mid-session. My matrix had
already run and my tree was verified reverted
```

It cost nothing that round because the timing was lucky — the matrix
had finished. Had it not, the track would have run a *different
track's* mutations against its own tree and reported the results as
its own, which is a fabricated mutation table and the one thing the
`falsify` discipline cannot tolerate.

The worktrees are isolated precisely so two tracks cannot write each
other's files. The scratchpad is the hole in that.

## Required Fix

Each track gets its own scratchpad path, named for the track, and the
brief says so. The isolation the worktree provides for the repository
extends to the working files the track builds beside it.

## Out of Scope

- Anything about the worktrees themselves — they worked.

## Acceptance Test

Two tracks writing the same filename, and neither seeing the other's.
