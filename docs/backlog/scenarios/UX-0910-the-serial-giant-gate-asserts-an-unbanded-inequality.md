# UX-910: the serial-giant gate asserts an unbanded inequality the jobserver cannot satisfy

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-857, UX-905 | **Found by:** round 132 — `bst-examples` is red on `main` at `395ebdc0` and at `6e410ab7`, both times on the same step, so every branch inherits it; `UX-857`'s own step comment pre-authorised the remedy | **Serves:** every round whose CI is red for a reason its diff did not cause | **Topic:** guards | **Area:** tools | **Shape:** mechanical

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
run 35564652560    (a14ba0c1, #246)  off=218.52s  auto=215.46s  -1.4%  IMPROVED
run 35572266477    (2f17171b, #246)  off=212.40s  auto=214.43s  +1.0%  no significant change
```

Six fail the step and two pass it, with nothing in the
workflow or the example different between them. The deltas run from
-1.4% to +2.2% and sit around zero, and the step asserts a strict
inequality over one sample of that with no band — so whether CI is
green is decided by which side of zero the run lands on.

The last two rows are the sharpest pair in the table: `a14ba0c1` and
`2f17171b` differ only by `UX-911`'s change to a unit test, which the
examples do not run, and they land on opposite sides of the assertion.
`a14ba0c1` also carries the `jobserver-auth: fd` annotation `UX-913`
added, and `peak` stayed at 2 with it, so the two arms are still the
same configuration - the inequality is asserted between a thing and
itself, and the sign of the noise decides the build.

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

**Replace the assertion, do not remove it.** The step's defect is not
only that its inequality is unbanded; it is that it asserts on **wall**,
which is a proxy for the thing the step names. That is the instrument
shape `CLAUDE.md` warns about, and it is why eight pairs taught nothing.
Width is an integer read off process overlap, so it carries a direction
a 218-second wall cannot.

`examples/11-serial-giant/check_jobserver_width.py`, a committed module
because `UX-354` refuses a `run:` block that subscripts this
repository's own JSON, takes both `plane2.json` reports and the `auto`
capture's own log. Three assertions, each able to fail only on
something real:

1. **the `auto` capture named no scrubbed auth.** `UX-883`'s
   `lto_preflight_warnings` line is what `UX-913` was found by, and it
   printed four times a run under all eight pairs while the step
   asserted a wall instead of reading it;
2. **`off` held its resolved width**, so the baseline is a baseline;
3. **`auto` was never narrower than `off`.**

And one **reading, printed and not asserted**: whether `auto` exceeded
the resolved width. That is `UX-913`'s second gate, and asserting it
today would red `main` on a question this row does not own. The step
prints it every run so the state is visible instead of implied.

`UX-848`'s wall check survives unchanged - both walls are still
computed, echoed as `off=…s auto=…s`, and uploaded. Only the ordering
`awk` goes, and with it the three guards that exercised it: a guard
over a removed assertion is not a guard.

## Out of Scope

Diagnosing why the giant stays at width 2 with the auth kept - that is
`UX-913`'s second gate, and this row's printed reading is what makes it
visible. Changing any jobserver default. Touching `10-jobserver`'s or
`12-junctioned`'s steps. Banding a wall, which remains unavailable and
is no longer wanted: the same-sha pair moved `auto` 0.99% with nothing
changed, so a ±1% band sits inside the noise it would be drawn from.

## Acceptance Test

`bst-examples` is green on a branch whose only change is this one, with
`off=…s auto=…s` still in the log and both runs still uploaded.

`python3 -m pytest tests/unit/test_the_examples_build.py -q` is green,
and six mutations redden six distinct guards: dropping each of the
three assertions, dropping the `UX-913` reading, reading a row for an
element neither arm carries, and removing the script's call from the
step.

The step must **pass** on today's real reading - `peak 2` under both
arms with the auth kept - and say in its own output that the width was
not granted. A check that greens silently on that reading would repeat
the defect this row is about in the other direction.

## Outcome

**The gap, measured.** Eight off/auto pairs on the CI runner, three
branches, unchanged workflow code: -1.4%, +0.6%, +0.0%, +0.0%, +0.5%,
+0.04%, +2.2%, +1.0%. Six failed the step. The load-bearing one is the
same-sha pair, two runs of an identical tree: `off` moved 0.52% and
`auto` 0.99% with nothing differing, so a +-1% band sits inside the
noise it would be drawn from. `peak_work_concurrency` read **2** on
every one of the eight, so the example never granted the width whose
effect the step asserted. `UX-883`'s `scrubbed to recipe -jN` line
printed four times per run through all of it, unread - that line is
what `UX-913` was eventually found by, and the step that existed to
catch this defect was reading a wall instead.

**The close, measured.** `examples/11-serial-giant/check_jobserver_width.py`
replaces the ordering `awk`: three assertions (no scrubbed auth in the
`auto` capture, `off` within its resolved width, `auto` never narrower
than `off`) and one printed reading (whether `auto` exceeded the
resolved width - `UX-913`'s second gate, deliberately not asserted).
`UX-848`'s wall grep, the `off=...s auto=...s` echo and both uploads are
untouched. The three guards over the removed `awk` are gone and eight
replace them: `python3 -m pytest tests/unit/test_the_examples_build.py
-q` reads **20 passed in 1.70s**, against 15 before.

**The printed reading is two shapes, not one,** and the second was
missed in the first draft. The `auto` arm has been seen publishing no
resolved width at all (`req ?` in its per-element table), and the
first version folded that into `did not exceed its resolved width` -
which would have reported an `auto` peak of 4 against `off`'s 2 as a
pool going undrawn. The width is the real denominator, so it leads
when it is there; `off`'s measured peak is a labelled fallback only
when it is not, because a peak under its own width says nothing.

**The mutation table.** Nine applied, nine distinct guards red, no
collateral:

| mutation | guard reddened |
|---|---|
| `if scrubbed:` never fires | `test_the_width_check_refuses_a_scrubbed_auth` |
| `if auto_peak < off_peak:` never fires | `test_the_width_check_refuses_auto_narrower_than_off` |
| `if ... off_peak > width:` never fires | `test_the_width_check_refuses_an_off_arm_over_its_resolved_width` |
| a missing row reads as absent | `test_the_width_check_refuses_an_element_neither_arm_carries` |
| the `UX-913` reading is not printed | `test_the_width_check_accepts_a_granted_pool`, `..._passes_the_reading_on_record_and_says_so` |
| the step's call to the script removed | `test_the_ci_step_11_goes_through_the_committed_width_check` |
| a missing width reads as a width nothing exceeded | `test_the_width_check_says_so_when_no_resolved_width_is_published` |
| `off`'s peak stands in for the resolved width | `test_the_width_check_passes_the_reading_on_record_and_says_so`, `..._does_not_read_a_peak_under_its_width_as_a_draw` |
| the fallback comparison is read backwards | `test_the_width_check_says_so_when_no_resolved_width_is_published` |

**Deviations, two.**

The Required Fix this row was filed with asked for the assertion to be
**removed**, and said in its own Out of Scope that removal is the
unblock and never the fix. Ruslan chose replacement on 2026-09-21, and
the row above was rewritten to it before any code was written. The
earlier text is in `git log`; nothing here silently reinterprets it.

The Acceptance Test's first clause - `bst-examples` green on a branch
carrying only this change - is CI's to report, not this container's.
There is no BuildStream sandbox here and the example is a ~218s build
on a machine class this box is not. The six mutations and the guard
count above are this box's; the step's own green is the CI run's.
