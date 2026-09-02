# UX-510: a parallel track starts from a base the orchestrator has left behind

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** `UX-504` | **Found by:** round 75, three tracks in flight | **Serves:** the track told to read a file that does not exist in its copy | **Topic:** guards

## Motivation

All three of round 75's `implementer` worktrees were created from
`8585e7d` — round 74's last commit — while the orchestrator was nine
commits further on:

```text
worktree agent-aaa...  base 8585e7d   Round 74: the workflow measured
worktree agent-aea...  base 8585e7d
worktree agent-af3...  base 8585e7d
orchestrator HEAD      c5c8d75        round 75: the tail's decomposition
```

Two tracks reported the same consequence unprompted: the brief told
them to read `docs/contributing/rules.md` and
`docs/audits/round-75.md`, and **neither file existed in their copy**
(`UX-505` and this round's own audit are among the nine). One of them
noticed the second-order version too — the worktree's `CLAUDE.md` and
the orchestrator's had diverged, so the two copies of the same
instruction file disagreed about which document is the rule.

The merge cost is measured rather than argued: three cherry-picks, one
conflicted (`tools/dev_close_task.py` and
`tests/unit/test_the_loop_stays_fast.py`, both edited by `UX-501` and
`UX-506` inside the nine commits). The conflicts were additive and
resolved by keeping both sides, but a track that had *read* the round-74
version of `dev_close_task.py` was reasoning about a file the round had
already changed.

## Required Fix

- A track's copy starts from the orchestrator's HEAD, or the brief
  states the base it will actually get and stops naming files that
  postdate it.
- Whichever it becomes, the `implementer` brief carries it, so the
  agent can check rather than discover — `git log --oneline -1` against
  what the brief claims.
- `decompose`'s track section says what the merge costs: three picks,
  one conflict, over nine commits, is this round's number and the only
  one on file.

## Out of Scope

- Where the Agent tool puts the worktree, which is `UX-509`.
- Rewriting the tracks' work. It merged; the cost is the brief's, not
  the diffs'.

## Acceptance Test

A track launched against a HEAD with an uncommitted-at-launch document
in it, reading that document, from the base the brief names.

## Outcome

_Not started._
