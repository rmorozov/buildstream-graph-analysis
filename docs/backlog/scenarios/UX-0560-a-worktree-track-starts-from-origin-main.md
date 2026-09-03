# UX-560: a worktree track starts from `origin/main`, whatever base its brief names

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-510 (which made the brief name its base) | **Found by:** round 81's two parallel tracks, independently | **Serves:** every round that runs a track | **Topic:** tooling

## Motivation

`UX-510` closed "a track's brief names the base it will actually get".
Round 81 named it — `0527217`, correct at launch — and both tracks
still opened at a different commit:

```text
$ git reflog show worktree-agent-a1652da2e53f0bc02 | tail -2
0527217 ...@{2}: reset: moving to 0527217
cd52125 ...@{3}: branch: Created from origin/main
$ git reflog show worktree-agent-ad210313e9a10d92b | tail -2
0527217 ...@{1}: reset: moving to 0527217
cd52125 ...@{2}: branch: Created from origin/main
```

`cd52125` is `origin/main`, **34 commits behind** the session's branch.
The brief was right; the worktree is created from `origin/main`
regardless of what the session has checked out. So on any branch with
unmerged work — which is every round — a track's base is wrong by
construction, and `UX-510`'s fix cannot help because the brief is not
what decides it.

Both tracks found it the same way and for the same reason: the brief
said *every file cited below exists at that base; if one does not, stop
and say so rather than guessing*, and both had cited files missing.
Both recovered with `git reset --hard <base>` because the commit was in
the object store, and both reported it first. Rounds 75 and 76 hit the
same shape without that instruction and guessed.

## Required Fix

The instruction is a mitigation, not a fix — it depends on the brief
citing a file the base lacks, which is luck. Either the worktree is
created from the session's `HEAD`, or the track is told to reset to its
named base as its first act and a guard asserts it did.

Naming the base is worth keeping either way: it is what let both tracks
detect the mismatch rather than build on it.

## Out of Scope

- `UX-510` itself, which is closed and correct: the brief *should*
  name the base. This row is that naming it is not sufficient.
- The recovery route. `reset --hard` worked twice here because the base
  was already fetched; a track whose base is not in its object store
  needs a fetch, and that is the same fix.

## Acceptance Test

A track launched from a session whose branch is ahead of `origin/main`
opens at the session's commit, or reports the mismatch before its first
edit.
