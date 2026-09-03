# UX-560: a worktree track starts from `origin/main`, whatever base its brief names

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-510 (which made the brief name its base) | **Found by:** round 81's two parallel tracks, independently | **Serves:** every round that runs a track | **Topic:** guards

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

## Outcome (round 81, 2026-09-03) — 🟢 Done

### The gap, measured

```text
$ git reflog show worktree-agent-a1652da2e53f0bc02 | tail -2
0527217 ...@{2}: reset: moving to 0527217
cd52125 ...@{3}: branch: Created from origin/main
$ git log -1 --format='%h %s' cd52125
cd52125 CI: adopt the tier rows this run measured (UX-503)
```

`cd52125` is `origin/main`; the brief named `0527217`, 34 commits on.
Both of round 81's tracks, independently.

### The decision

The Required Fix offered two routes. The first — create the worktree
from the session's `HEAD` — is not available from inside the
repository: the Agent tool creates it. So the second: **the track
takes its base rather than stopping at it.**

That is only safe because the reset cannot fail, and the reason is
measurable:

```text
$ git -C .claude/worktrees/agent-a1652da2e53f0bc02 rev-parse --git-common-dir
/home/user/buildstream-graph-analysis/.git
$ git -C .claude/worktrees/agent-a1652da2e53f0bc02 cat-file -t 7e39251
commit
```

A linked worktree shares the main checkout's object database, so a
commit made *after* the worktree existed is already reachable from it.
No fetch, no network, no "unreachable base" to improvise around —
which is why `implementer.md` now states that reason and not just the
command.

### After

`.claude/agents/implementer.md` says to report the mismatch and then
`git reset --hard <the commit your brief names>`, with the shared
object database as the reason. `test_the_implementer_takes_its_base_
rather_than_stopping` holds both halves.

### Mutations verified red and reverted (3)

| # | mutation | reddened |
|---|---|---|
| M1 | the `git reset --hard` line replaced with `git status` | `..._takes_its_base_rather_than_stopping` — 1 failed, 5 passed |
| M2 | "object database" reworded away | the same clause — 1 failed, 5 passed |
| M3 | "Never recreate a file the brief cites" inverted | `..._is_told_to_report_rather_than_work_around` — 1 failed, 5 passed |

### A guard this change had to re-pin

`UX-510`'s `..._is_told_to_report_rather_than_work_around` asserted the
literal sentence "stop looking for the files the brief cites", which
this item retires. It now pins the two properties that survive — the
mismatch is *reported*, and a missing file is *never recreated* — so
`UX-510`'s claim is intact and its wording is not frozen. M3 is the
evidence it still discriminates.

### Deviation from the Required Fix

**One, forced.** "The worktree is created from the session's `HEAD`" is
outside this repository's reach. The row said "either ... or", and the
half that is reachable is the half taken.
