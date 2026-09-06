# UX-738: a build that could not write reports as a clean run and exit 255

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-156 (a failed build must not verdict as if it finished), UX-324, UX-148 | **Serves:** anyone whose disk fills mid-capture, and the round that then reads the report | **Topic:** capture | **Shape:** judgement | **Area:** tools

## Motivation

Round 100's gate went red with eighteen fixture errors in
`tests/unit/test_the_journey_has_an_answer_key.py`. The assertion
prints `stdout[-4000:] + stderr[-4000:]`, and what it printed was a
**complete, normal-looking analysis**:

```text
Attribution Breakdown:
  Execution On Chain            0.00s (  0.0%)
  Dependency Wait               0.00s (  0.0%)
  Idle                          8.95s ( 76.5%)
  Untracked Head                2.58s ( 22.0%)
Critical Path Length: 4 elements
  Path: toolchain.bst → core.bst → app.bst → all.bst
...
This snapshot: 167.6K. …/.bga/runs: 167.6K over 1 snapshot(s).

assert 255 == 0
```

Nothing in four thousand characters of either stream says what went
wrong. The only signal is the exit code, and the report beside it
reads as a build that ran and was simply idle — the one shape
`UX-156` exists to stop.

The cause, found by elimination and then confirmed:

```console
$ du -sh /tmp/pytest-of-root
4.4G    /tmp/pytest-of-root
$ rm -rf /tmp/pytest-of-root/*
$ pytest tests/unit/test_the_journey_has_an_answer_key.py -q
25 passed in 42.11s
```

The build could not write. Two things about the diagnosis are the
finding, not the anecdote:

- It reproduced **identically at a commit whose `make test` was fully
  green an hour earlier**, which is what ruled the round's own diff
  out. Nothing in the tool said so; that took a checkout and a re-run.
- `df` reported 13 G available throughout. Whatever ran out, it was
  not the figure a human or a guard would check first, so "check the
  disk" is not the lesson — "say which write failed" is.

`UX-156` made a *failed* build refuse to verdict. This is the same
class one layer down: a build whose sandbox could not write produces
a report of a build that did nothing, and the tool passes the exit
code up without a sentence.

## Required Fix

`bga snapshot` must say why it is exiting non-zero, in the stream the
reader is already looking at. At minimum, when the wrapped command
exits non-zero:

- the last line of output names the wrapped command's exit code and
  that the analysis below describes a build that **did not complete**;
- an analysis with zero execution on the chain and a non-zero wrapped
  exit is refused rather than printed as a verdict, the way `UX-156`
  refuses one for a failed element;
- where the failure is a write, the path that could not be written is
  named. `bst`'s own diagnostics carry it; the wrapper discards it.

Decide and say in the Outcome whether 255 should survive as the tool's
exit code or be mapped — `UX-114`'s exit-code table is the contract
this joins, and an undocumented 255 is itself a finding.

## Out of Scope

- The container's disk allowance. That is an environment fact; this
  row is about the tool's silence, which would be the same on any
  machine that filled up.
- The journey guard's own fixture. It reported the failure correctly
  as far as it could see — the four-thousand-character window was
  full of report because the report is what the tool produced.

## Acceptance Test

A capture whose sandbox cannot write exits non-zero **and** the last
line of its output says the build did not complete, naming the wrapped
exit code; no attribution verdict is printed for it. Mutation: make
the wrapped command exit non-zero after producing a partial trace —
the clause reds if a verdict is printed anyway.
