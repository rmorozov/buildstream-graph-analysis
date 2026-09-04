# UX-615: the scratchpad is shared between tracks

**Priority:** Low | **Status:** 🟢 Done Open | **Depends on:** UX-614 (the same launch step) | **Found by:** round 84, by the track it happened to | **Serves:** a round running tracks in parallel | **Topic:** guards

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

## Outcome (round 85, 2026-09-04) — 🟢 Done

**Premise:** held, and quantified.

### The gap, measured

```text
$ ls -1 /tmp/claude-0/-home-user-buildstream-graph-analysis/ | wc -l
1                       ← one session key for the whole project
$ ls -1 …/scratchpad | wc -l
1592                    ← Aug 16 → Sep 4, every round of the project
$ ls …/scratchpad | grep -c '^mutate'
33
$ ls -la …/scratchpad | grep ' mutate.py$'
-rw-r--r-- 2378 Sep  3 21:06 mutate.py      ← round 84's, the one overwritten
```

The path is keyed by the **project**, not by the session and not by the
worktree: this track's cwd is
`…/.claude/worktrees/agent-a4b6a45b499adfdc3` and its scratchpad key is
the main checkout's path. Of the 33 `mutate*` files, the ones that
escaped collision carry an item id or an agent id — `mutate595_adf6.py`
— so tracks have been improvising this convention one name at a time.

### After

`implementer.md` fences one recipe and `decompose` puts it in the
brief. The clauses **run** it from two worktrees rather than reading
it, which is the acceptance test:

```text
$ python -m pytest …TestEachTrackHasItsOwnScratchpad…do_not_see_each_other -q
1 passed in 0.07s
```

### Mutations verified red and reverted (3)

| # | mutation | reddened |
|---|---|---|
| C1 | recipe to a constant `…/track` | all 3: "made 1 director(y/ies): ['track']" |
| C2 | recipe to `…/$$` (pid, not the worktree) | the name clause only — **the acceptance clause stayed green** on two distinct pids, which is why the two are separate |
| C3 | `$(basename "$PWD")` dropped from the skill | agreement only, 1 failed 2 passed |

No clause of this item failed to discriminate. C2 is the one that
matters: "two directories" and "the *right* two directories" are
different claims, and a single clause asserting isolation passes on any
unique name — including one the track must be told, which puts the
allocation back on the brief that UX-615 says is silent.

### Deviation from the Required Fix

None. "Each track gets its own scratchpad path, named for the track"
is a convention, not a mechanism — the harness hands the path in and
nothing here can rebind it — so what is guarded is the recipe's
*behaviour*, executed, not the sentence's presence.

```text
$ make test-touching   18 file(s) selected · 580 passed, 3 skipped in 15.76s
$ make lint            All checks passed!
```
