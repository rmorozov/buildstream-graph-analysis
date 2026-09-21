# UX-910: the serial-giant gate asserts an unbanded inequality the jobserver cannot satisfy

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-857, UX-905 | **Found by:** round 132 — `bst-examples` is red on `main` at `395ebdc0` and at `6e410ab7`, both times on the same step, so every branch inherits it; `UX-857`'s own step comment pre-authorised the remedy | **Serves:** every round whose CI is red for a reason its diff did not cause | **Topic:** guards | **Area:** tools | **Shape:** mechanical

## Motivation

`UX-857` added an ordering check to the `11-serial-giant` CI step: run
the project with `--jobserver off`, again with `--jobserver auto`, and
fail the step unless `auto`'s wall is strictly under `off`'s. Six
pairs on the CI runner, over three branches, on unchanged workflow
code:

```text
run 35511368643    (6e410ab7, main)  off=170.94s  auto=174.76s  +2.2%  REGRESSED
run 35536366563    (395ebdc0, main)  off=173.41s  auto=174.54s  +0.6%  no significant change
run 35541259164 #1 (d64d67f2, #245)  off=219.02s  auto=220.15s  +0.5%  no significant change
run 35541259164 #2 (d64d67f2, #245)  off=217.88s  auto=217.98s  +0.0%  no significant change
run 35542312865    (PR #246)         off=218.41s  auto=218.42s  +0.0%  no significant change
run 35545829617    (9679d398, #246)  off=218.69s  auto=216.09s  -1.2%  IMPROVED
```

Five fail the step and the sixth passes it, with nothing in the
workflow or the example different between them. The deltas run from
-1.2% to +2.2% and sit around zero, and the step asserts a strict
inequality over one sample of that with no band — so whether CI is
green is decided by which side of zero the run lands on.

The two rows for run `35541259164` are its two attempts, the same sha
re-run, so they measure the noise directly rather than by inference:
`off` moved 219.02s → 217.88s and `auto` moved 220.15s → 217.98s, a
0.5% and a 1.0% swing with nothing changed at all. The four ~218s
pairs are one machine class and the two ~172s pairs another, so the
+2.2% outlier is not drawn from the same population as the rest;
within the ~218s class alone the deltas still span +0.5% to -1.2% and
still straddle zero. That cuts two ways and both matter. The outlier
is bad evidence for how wide the noise is, because reading it that way
pools two populations — but it is fair evidence for what a band would
have to survive, because the step runs on whichever runner it draws
and cannot choose its class.

`bga compare`, which the step itself calls, already applies the band
(`_SIGNIFICANCE_PCT = 1`) and the step discards its verdict to
re-derive a cruder one by `awk`. Four of the six pairs are inside that
band; the two outside it point in opposite directions.

The element's own measured concurrency is flat across every one of the
six, including the improved run:

```text
  element                  peak  req  achieved     span work
  giant.bst                   2    2      100%   43.53s  530
```

`peak 2` against a ceiling of 4, on all six. So the measured width
does not move under `auto`, while the wall moves either way by up to
three seconds — in the improved run `giant.bst` itself went 213.25s to
210.20s with the same peak of 2. Whatever the wall is doing here, this
example does not show the jobserver widening the element, and it does
not separate an effect from variance either.

Whether `peak 2` is a real ceiling on the mechanism or an artefact of
how width is measured is a separate question, and it is the one
`11-serial-giant` was built to answer. It cannot answer it while the
answer arrives as a coin-flipping pipeline.

## Required Fix

Drop the ordering check from the step; keep the wall assertion
(`UX-848`'s), the `off=…s auto=…s` line and the uploaded artifacts, so
every run still records both numbers for a reader. The three guards in
`tests/unit/test_the_examples_build.py` that exercise the extracted
`awk` fragment go with it — a guard over a removed assertion is not a
guard — replaced by one holding that the step still prints both walls.
`10-jobserver`'s step (`UX-848`) is the shape to match: it greps for
the walls and asserts no ordering.

Banding it instead is not available today, and the same-sha pair is
why: a bare re-run of `d64d67f2` moved `auto` by 1.0% with nothing
changed, so ±1% is already inside this example's idle variance on one
machine class, before the other class is considered at all. `bga
compare`'s own ±1% would also still fail the +2.2% pair, which the
step cannot decline to run on. A band has to be chosen against a
measured spread, and the six pairs above are the only ones there are.

Removing the gate is not a verdict that the jobserver is fine, and this
task must not be read as one. The six readings say nothing about the
jobserver in either direction: their deltas are the example's own
run-to-run spread, and `peak 2` holds on every one of them, so the
example never granted the width whose effect the step was asserting.
What the task decides is only that a strict inequality over two
unbanded runs, in a step that already calls `bga compare` and then
discards its banded verdict, cannot carry a result of any sign — it
reports a coin flip as a broken pipeline, and blocks every unrelated
round while it does.

The `peak 2` reading needs its own root cause: either the wrapper never
rewrote the giant's `-j`, or it did and `make` declined the tokens, or
`giant.bst`'s own `max-jobs: 2` caps the element below the ceiling of 4
before the jobserver is consulted at all. That is not this task, and it
must be filed before this one closes, because it is the question
`11-serial-giant` was built to answer and it is currently answering
nothing in a red pipeline nobody reads as a measurement. It belongs
beside `UX-905`'s compile-bound project at scale and the three off/auto
pairs on a 16-core host that Direction 20 already requires before the
mode goes on by default.

## Out of Scope

Diagnosing why the giant stayed at width 2 (its own row). Changing any
jobserver default. Touching `10-jobserver`'s or `12-junctioned`'s steps.

**And, explicitly: removing or banding the assertion is not the fix.**
It is the unblock, and it is all the Required Fix above asks for today.
A closed row whose subject is the jobserver reads, to a round with no
other context, as "this was measured and found fine" — which is not
what the six pairs say either. They say the example cannot tell. So
this row does not close on a green job.

## Acceptance Test

Two parts, and the second is what lets the row close.

**The unblock.** `bst-examples` is green on a branch whose only change
is this one, with `off=…s auto=…s` still in the step's log and both
runs still uploaded; `python3 -m pytest
tests/unit/test_the_examples_build.py -q` green, and a mutation
removing the `off=`/`auto=` echo reddens the guard that replaces the
three.

**The close.** Either `11-serial-giant` reads `peak > 2` under `auto`
on the runner — the fixture granting width, which is what the example
was built to show — or a filed row establishes that it never could at
`max-jobs: 2` and replaces the example with one that can. A band is
not an alternative to either: choosing one needs the example's own
spread measured on one sha, and the two attempts of `35541259164` are
the only such pair on record. Until one of
those, this row stays open with the assertion removed, which is the
honest state: the tree is unblocked and the question is unanswered.

## Outcome
