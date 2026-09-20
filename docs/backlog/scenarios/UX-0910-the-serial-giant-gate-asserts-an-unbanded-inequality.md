# UX-910: the serial-giant gate asserts an unbanded inequality the jobserver cannot satisfy

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-857, UX-905 | **Found by:** round 132 — `bst-examples` is red on `main` at `395ebdc0` and at `6e410ab7`, both times on the same step, so every branch inherits it; `UX-857`'s own step comment pre-authorised the remedy | **Serves:** every round whose CI is red for a reason its diff did not cause | **Topic:** guards | **Area:** tools | **Shape:** mechanical

## Motivation

`UX-857` added an ordering check to the `11-serial-giant` CI step: run
the project with `--jobserver off`, again with `--jobserver auto`, and
fail the step unless `auto`'s wall is strictly under `off`'s. It is red
on `main` twice running, and on every branch that inherits it:

```text
run 35511368643 (6e410ab7, main)  off=170.94s  auto=174.76s  +2.2%  REGRESSED
run 35536366563 (395ebdc0, main)  off=173.41s  auto=174.54s  +0.6%  no significant change
run 35542312865 (PR #246)         off=218.41s  auto=218.42s  +0.0%  no significant change
run 35541259164 (PR #245)         off=217.88s  auto=217.98s  +0.0%  no significant change
```

Four pairs on the CI runner, over three branches, and `auto` is never
faster. Once it is significantly slower by `bga compare`'s own rule
(`_SIGNIFICANCE_PCT = 1`); the other three are ties. This is not a gate
tripping on noise; it is a gate failing because the thing it asserts is
not true here.

The fourth is the sharpest, because in it the element the example
exists to measure **improved** and the step failed anyway:

```text
Which Elements Changed:
  3 grew, 1 shrank (per-element deltas are not noise-banded)
  leaf-a.bst: +0.10s (3.20s -> 3.30s)
  leaf-b.bst: +0.10s (3.20s -> 3.30s)
  leaf-c.bst: +0.10s (3.20s -> 3.30s)
  giant.bst: -0.05s (212.25s -> 212.20s)
```

`giant.bst` went 212.25s to 212.20s. The whole +0.11s that failed the
run is three leaves off the critical path, each +0.10s. A gate that
rejects a run in which its own subject got faster is measuring the
wrong thing.

Why it is not true is the finding. From the `auto` capture's own report
in run 35536366563, taken with a ceiling of 4:

```text
Per-element native parallelism (real compiler/assembler/linker processes only):
  element                  peak  req  achieved     span work
  giant.bst                   2    2      100%   45.07s  530
```

`peak 2` against a ceiling of 4. The element ran exactly as wide under
`auto` as the recipe's own `max-jobs: 2` already made it, so the
jobserver granted no width and there was nothing for the wall to
convert. What it did add is visible in the regressed run's leaves,
which do no compiling worth parallelising:

```text
  leaf-a.bst: +1.80s (1.90s -> 3.70s)
  leaf-b.bst: +1.80s (1.90s -> 3.70s)
  leaf-c.bst: +1.80s (1.90s -> 3.70s)
```

Cost without benefit, on this example, on this runner. That is a real
result about the intervention, and the assertion's job was to surface
it — which it has, by staying red.

`UX-857`'s step comment states what to do with exactly this:

```text
# This box read auto over off twice at load 7-13; the assertion
# stands on the CI runner's own quiet reading - if it reds there,
# the reading is the finding, drop the assertion, keep the walls.
```

The condition is met, on the runner, three times.

## Required Fix

Drop the ordering check from the step; keep the wall assertion
(`UX-848`'s), the `off=…s auto=…s` line and the uploaded artifacts, so
every run still records both numbers for a reader. The three guards in
`tests/unit/test_the_examples_build.py` that exercise the extracted
`awk` fragment go with it — a guard over a removed assertion is not a
guard — replaced by one holding that the step still prints both walls.
`10-jobserver`'s step (`UX-848`) is the shape to match: it greps for
the walls and asserts no ordering.

Removing the gate is not a verdict that the jobserver is fine, and this
task must not be read as one. The three readings say the opposite: on
this runner `auto` buys no width and costs the leaves about 1.8s each.
What the task decides is only that a strict inequality over two
unbanded runs, in a step that already calls `bga compare` and then
discards its banded verdict, is the wrong instrument for carrying that
result — it reports a real finding as a broken pipeline, and blocks
every unrelated round while it does.

The `peak 2` reading needs its own root cause: either the wrapper never
rewrote the giant's `-j`, or it did and `make` declined the tokens.
That is not this task, and it must be filed before this one closes,
because it is the question `11-serial-giant` was built to answer and it
is currently answering "nothing happened" in a red pipeline nobody
reads as a measurement. It belongs beside `UX-905`'s compile-bound
project at scale and the three off/auto pairs on a 16-core host that
Direction 20 already requires before the mode goes on by default.

## Out of Scope

Diagnosing why the giant stayed at width 2 (its own row). Changing any
jobserver default. Touching `10-jobserver`'s or `12-junctioned`'s steps.

**And, explicitly: removing or banding the assertion is not the fix.**
It is the unblock, and it is all the Required Fix above asks for today.
A closed row whose subject is the jobserver reads, to a round with no
other context, as "this was measured and found fine" — which is the
opposite of what the four pairs say. So this row does not close on a
green job.

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
`max-jobs: 2` and replaces the example with one that can. Until one of
those, this row stays open with the assertion removed, which is the
honest state: the tree is unblocked and the question is unanswered.

## Outcome
