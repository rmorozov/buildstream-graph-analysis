# UX-510: a parallel track starts from a base the orchestrator has left behind

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-504` | **Found by:** round 75, three tracks in flight | **Serves:** the track told to read a file that does not exist in its copy | **Topic:** guards

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

## Outcome (round 76, 2026-09-02)

### Which branch of the Required Fix

The second. Where the Agent tool puts a worktree's base is not the
brief's to choose — round 75's three worktrees were all created at
`8585e7d` with the orchestrator at `c5c8d75`, and nothing in the brief
caused that. So the track is told to *read* its base and to report a
disagreement rather than work around it, which is the outcome the two
tracks that hit it reached on their own and which the brief now asks for
in the first sentence.

### The close

`implementer.md` gains **Where your copy starts**, before the loop: the
measurement, the one command that answers (`git log --oneline -1`), and
what to do when it disagrees — say so and stop looking for the files the
brief cites, because a missing file is the brief being wrong about the
base, not a file to recreate.

`decompose` §3 gains the two sentences its orchestrator-side reader
needs: the brief names the base, and what the merge cost the one round
that measured it — three tracks over nine commits, **three cherry-picks,
one conflicted**, in `tools/dev_close_task.py` and
`tests/unit/test_the_loop_stays_fast.py`, resolved additively. 1.33
commits per task against 1.0 serial.

### Mutations

| # | mutation | result |
|---|---|---|
| M1 | the base-check command removed from the brief | 1 failed |
| M2 | the command kept, the comparison dropped | 2 failed |
| M3 | "three cherry-picks" → "several picks" in the brief | 1 failed |
| M4 | the same in `decompose` | 1 failed |
| M5 | the distance dropped from `decompose`'s sentence | 1 failed |
| M6 | the distance dropped from the brief's sentence | 1 failed |

M5 and M6 took three attempts and the first two were **mutations that
did not mutate**. The clause first read `"nine commits" in body`, which
both files satisfy from a paragraph that says it for a different reason;
widening to a ±320-character window around the count did not help,
because that paragraph is 299 characters away in `decompose`. The
offsets were measured (`-801/+144` and `-299/-16/+139`) and the window
set to `-40/+200`, which is the count's own sentence in both files. The
first two forms are recorded rather than deleted: a window chosen by
eye is how a clause ends up reading the file's other paragraph.

### The acceptance test, run

*A track launched against a HEAD with an uncommitted-at-launch document
in it, reading that document, from the base the brief names.* Run on
real work rather than an errand: an `implementer` on `UX-507`, briefed
with base `44a948cf3d334d0d62ada3c897a7e63482e27d9a` and two cited
documents that differ on purpose — `docs/audits/round-76.md`, committed
at `49a8c62`, and this section, written and uncommitted at launch.

**It reproduced.** The track's first sentence:

```text
git log --oneline -1   ->   96970dc CI: adopt the tier rows this run measured
```

**Seven commits behind** the declared base, not nine, and a different
seven — round 75's number was `8585e7d` against `c5c8d75`. So the
defect is not a one-off of that round: the worktree starts at some
earlier commit both times, and the brief is what makes it visible. Of
the two cited documents it could read **neither** at its arrival base —
`round-76.md` did not exist there — and it did not recreate this
section, which is what the brief asks for.

The cost was not cosmetic, and the track named it: two of the seven
commits (`98e50bb`, `0e0db74`) edit `UX-0092` and `UX-0096`, both inside
its own 223-file range. Working from the stale base would have rewritten
two files this round had already changed. It fast-forwarded — its HEAD
was a strict ancestor and its tree clean, so lossless — and worked from
`44a948c`, which is the outcome the brief's "say so and stop" is for.

Tests: 81 → 84 in `tests/unit/test_the_agent_configuration_holds.py`.
