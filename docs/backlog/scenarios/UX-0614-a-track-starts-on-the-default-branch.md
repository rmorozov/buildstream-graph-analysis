# UX-614: a track starts on the default branch, not the round's

**Priority:** High | **Status:** 🔴 Open | **Depends on:** UX-510 (a track's brief names the base it will get) | **Found by:** round 84, by three of seven tracks independently | **Serves:** every round that runs tracks in parallel | **Topic:** guards

## Motivation

A worktree-isolated track is branched from the **default branch**, not
from the round's branch. Three of round 84's seven tracks reported it
without being asked:

```text
track's `git log --oneline -1`   0bc5aff   CI: adopt the touching map (main)
the round's branch tip           d4a3d04   24 commits ahead
```

Every file those briefs cited was missing — the task file itself, the
module the item extends, the guard it was told to follow. Two tracks
recovered by merging the tip; one was blocked by a permission classifier
and had to find `merge --ff-only` instead. All three spent turns on it.

`UX-510` made a brief *name* its base. That was the right fix for a
brief that lied; it does not help when the base handed to the worktree
is simply not the one the round is on.

The failure is silent in the worst way: a track that does **not**
notice writes its item against a tree missing the round's other work,
and the merge is where that surfaces — which is exactly the position
this round's cross-item catches came from.

## Required Fix

A track begins on the round's branch, or — if the harness cannot be
told which branch that is — the brief's first instruction is a
measured check that fails loudly rather than a request to report the
base. The orchestrator's own launch step names the tip it expects, and
a track whose `git log` disagrees stops instead of proceeding.

## Out of Scope

- The permission classifier that blocked `git reset --hard` — declined:
  `merge --ff-only` is the better instruction anyway, and the
  classifier is not this repository's.

## Acceptance Test

A track launched while the round's branch is ahead of the default,
reporting the round's tip rather than the default branch's.
