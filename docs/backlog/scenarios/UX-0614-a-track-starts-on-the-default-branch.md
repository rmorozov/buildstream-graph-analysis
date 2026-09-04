# UX-614: a track starts on the default branch, not the round's

**Priority:** High | **Status:** 🟢 Done Open | **Depends on:** UX-510 (a track's brief names the base it will get) | **Found by:** round 84, by three of seven tracks independently | **Serves:** every round that runs tracks in parallel | **Topic:** guards

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

## Outcome (round 85, 2026-09-04) — 🟢 Done

**Premise:** half-held. The mechanism is confirmed and now has a
one-line reading; the harm did not recur this round.

### The gap, measured

```text
$ git reflog show worktree-agent-a4b6a45b499adfdc3
5343bd6 …@{0}: branch: Created from origin/main
$ git rev-parse --short origin/main main
5343bd6                     ← what the worktree was branched from
0d288eb                     ← the local default branch, 187 behind
```

The harness branches from `origin/main` and nothing consults the
round. This round `origin/main` *was* the named base, so the distance
was 0 and no file was missing — the premise's three-of-seven harm is
round 84's reading, not re-measured here. What is re-measured is that
the choice is not the round's to make.

Two premises of the brief did **not** survive. `git reset --hard HEAD`
ran unrefused in this worktree, so "the classifier blocks it" is
argument- or environment-dependent, not a property. And the classifier
refused `git -C <main-checkout> …`, so a track cannot inspect the tree
it was copied from at all.

### After

The instruction is `git merge --ff-only <base>`, and the argument for
it is no longer the classifier: **behind, it is the same command as the
reset; diverged, it stops instead of discarding.** The guards run it
rather than reading it — the command is lifted out of `implementer.md`
and executed against both shapes.

```text
$ python -m pytest …TestATrackTakesTheBaseItWasNamed…reaches_the_round_s_tip -q
1 passed in 0.48s
```

### Mutations verified red and reverted (3)

| # | mutation | reddened |
|---|---|---|
| B1 | fenced command back to `git reset --hard` | refusal (`assert 0 != 0`, the track's commit gone) + agreement; **"reaches the tip" stayed green** — that is the distinction |
| B2 | fenced command to `git reset --soft` | all 3, acceptance included: "moved the branch without the working tree" |
| B3 | `git rev-parse HEAD` dropped from the skill | agreement only, 1 failed 2 passed |

`UX-560`'s `test_the_implementer_takes_its_base_rather_than_stopping`
**stopped discriminating** under B1/B2: it asserts the literal
`git reset --hard` is somewhere in the body, and that stayed true when
the fenced instruction changed. Rewritten to the pair the wording
cannot drop — "then take the base", and the object-database reason —
with the command itself moved to a clause that executes it.

### Deviation from the Required Fix

The second option was taken: the harness chooses the branch, so "a
track begins on the round's branch" is not in this repository's gift.
Not done: nothing makes a track *stop*. The brief's first instruction
is the check and its remedy, and the remedy is the one that refuses
when taking the base would cost work.

```text
$ make test-touching   18 file(s) selected · 577 passed, 3 skipped in 18.36s
$ make lint            All checks passed!
```
