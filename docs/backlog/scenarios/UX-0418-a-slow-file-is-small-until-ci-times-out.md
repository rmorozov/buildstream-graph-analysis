# UX-418: a slow file is small until CI times out

**Priority:** Medium | **Status:** 🟢 Done | **Found by:** UX-403's guard census | **Serves:** the edit-run loop | **Topic:** guards

## Motivation

`UX-403`'s census mutated one guard per family and watched it go red.
Ten of eleven did. The one that did not was
`test_the_tiers_are_a_partition.py`, under the mutation "a large file
demoted to no tier":

```text
tier partition               GREEN    14 passed in 0.58s
```

Deleting a **50-second** entry from `LARGE` changed nothing. Every
clause in that file reads the two lists against each other or against
the filesystem — *listed files exist*, *no file is in two tiers*,
*every file is in at most one* — and `small` is the default, so a file
that belongs in a tier and is absent from both lists is "small on
purpose" and nothing says otherwise. The module's own docstring names
this escape for the *stale* direction ("a renamed file leaves its line
behind… the file it names silently becomes small") and never covers
the missing one.

`UX-403` fixed the half that is legible without measuring: a file that
boots a real Chrome says so in its imports, and four were doing it from
the small tier. What is left needs a measurement, and the file is right
that timing a suite from inside itself goes flaky and then gets muted.

Today the missing half is caught by CI's small-tier timeout — which
fails as *"the small tier took longer than `SMALL_TIER_BUDGET_S`"*,
naming a budget rather than the file that blew it, on a step that
already runs after every push.

## Required Fix

The measurement exists; nothing reads it. `pytest --durations=0`
prints per-test setup/call/teardown, which is exactly what
`tests/tiers.py`'s figures are derived from by hand.

- A CI step (or a `tools/dev_*.py` helper) that sums `--durations=0`
  per file after the full run and compares each file against the floors
  in `tests/tiers.py`, failing with **the file's name and its measured
  cost** when an unlisted file is over `MEDIUM_FLOOR_S`.
- It runs where a full run already happens, so it costs a parse rather
  than a second suite.
- The floors stay the authority; this only reads them.

## Out of Scope

- A wall-clock assertion inside a test. That is the shape
  `test_the_tiers_are_a_partition.py` rejects and this item agrees
  with it.

## Acceptance Test

- Deleting a large entry from `tests/tiers.py` fails the new step,
  naming the file and its measured seconds.
- Falsification: the same deletion with the step removed passes, which
  is the state this item is filed on.

## Outcome (round 65, 2026-08-30) — 🟢 Done

### The gap, measured

`UX-403`'s mutation, re-run against the committed tree — a large,
non-browser file deleted from `LARGE`, which is the exact shape the
census used:

```text
-- the partition guard --
16 passed in 0.60s
```

Still green, still silent, with a **35.8-second** file in the default
tier.

### After

The same mutation, with the new step reading the suite's own report:

```text
1 file(s) measured above the tier tests/tiers.py lists them in:
  tests/unit/test_process_spine.py  36.4s  listed small, measured large
exit=1
```

The file's name and its measured seconds, which is what
`SMALL_TIER_BUDGET_S`'s timeout — the only thing catching this today —
cannot say.

On the committed tree, against a real full run:

```text
tiers ok: 367 file(s) measured, none above the tier it is listed in
(floors: medium 1.0s, large 15.0s, x1.35 slack)
```

### What it found on its first run, which is the point

Three files listed **medium** had grown past the large floor and
nothing said so. Re-measured single-process to confirm:

```text
                                             -n auto   single
test_the_chain_folds_and_clicks_are_counted    26.2s    24.5s
test_any_element_can_be_inspected              18.1s    16.6s
test_the_handoff_has_a_fixture                 16.2s    15.5s
```

All three are in `LARGE` now with their measurements. The instrument
paid for itself on the run that landed it.

### `--junitxml`, not `--durations=0`

The Required Fix names `pytest --durations=0`. Its output cannot be
summed:

```text
(30 durations < 0.005s hidden.  Use -vv to show these durations.)
```

A file of two hundred fast tests reads as nothing at all. The junit
report carries every test's total (setup + call + teardown) with no
threshold — the same measurement without the hole — and pytest already
writes it on request, so the step still costs a parse. `make test`
gained a `PYTEST_ARGS` hook and CI passes `--junitxml`; the drift step
is the next line in the same job.

### The step was wrong on its first CI run, and how

**It reddened, and nothing had drifted.** `test (3.11)` on the head
that landed it:

```text
5073 passed, 140 skipped in 306.20s
3 file(s) measured above the tier tests/tiers.py lists them in:
  tests/unit/test_report_stays_readable_at_scale.py  21.5s  listed medium, measured large
  tests/unit/test_one_table_many_views.py            20.8s  listed medium, measured large
  tests/unit/test_marginal_efficiency_gate.py        20.4s  listed medium, measured large
```

Re-measured single-process on the machine the tiers were taken on, all
three are comfortably medium:

```text
                                      CI (-n auto)   here (1 proc)  ratio
test_report_stays_readable_at_scale        21.5s          13.5s     1.59
test_one_table_many_views                  20.8s          12.4s     1.68
test_marginal_efficiency_gate              20.4s          11.3s     1.81
```

**The floors are seconds on one clock and the report came from
another**, and the step compared them directly. `PARALLEL_REPORT_SLACK`
— the constant added below for the parallel-vs-single spread — was
sized at 1.35 on this container and was wrong by a factor on the first
foreign clock it met. That is what a constant standing in for a
measurement does, and this file already knew better: `SMALL_TIER_BUDGET_S`
keeps CI and local numbers apart for exactly this reason, with the
ratio written down.

**The fix is to calibrate rather than to widen.** For every listed file
the report also measured, `measured / recorded` is one reading of this
runner's clock against the tiers' own; the **median** of those readings
scales the floors. `tiers.recorded()` reads the reference off each
entry's own trailing `# N.Ns` — the lists have carried that number since
`UX-238`, so the calibration cannot drift away from the tiers it
calibrates, and there is no second copy to disagree. A median, not a
mean, so no single file can talk the scale up.

`TIER_DRIFT_MARGIN = 1.15` covers the residual: files do not all scale
by the same factor (1.59–1.81 across the three above). The scale is
printed on every run, drift or not, so the number that decides is
visible before the run that reddens.

Reproduced and re-checked, per the fixing guide's rule for a CI fix —
the same report both ways:

```text
the shipped rule (fixed x1.35), on a slower clock:   9 files flagged
the calibrated rule, on the same report:             tiers ok, x1.59
                                                     (large floor 27.5s)
```

Bumping the constant would have been the other option, and it is the
one this item's own filing warns about: *"a step that reds on an
ordinary run is one somebody mutes."* A number that has to be re-sized
for every machine is a mute switch with extra steps.

### The fourth file, and the number this needed

A fourth file was flagged and should not have been:

```text
test_the_order_the_page_has   15.2s (-n auto)   11.9s (single)   1.28x
```

CI's full run is `-n auto`, and a test's wall clock **inside a worker
carries its neighbours' contention**, while `tests/tiers.py`'s figures
are measured single-process (that is the `measure` skill's recipe). So
a parallel report over-reads, by 5–28% on these four.

Without a number for that, the step reds on an ordinary run — and a
step that reds on an ordinary run is one somebody mutes, which is the
failure mode this item was filed to avoid rather than to reproduce.
This is the observation the first version answered with a constant and
the second answers with a measurement — the section above is the whole
story. `--exact` compares against the floors as they stand, for a
report taken on the tiers' own clock.

**The cost is stated rather than hidden**, in the margin's own comment
and in a clause: a file 15% over its floor *on the report's own clock*
is not reported. It is a ratchet against drift, not a re-measurement —
and `test_a_real_drift_still_shows_through_a_slow_runner` holds the
other end.

### `test_the_report_has_chapters.py`, caught the same hour

`UX-414` gave that file a second fixture and the step read it at
**15.9s**, over the large floor, for fifteen clauses booting the same
two documents. One export and one node boot per fixture now, cached:
**4.9s**. Found by this step within an hour of it existing, which is
the shortest feedback this item was asking for.

### Mutations verified red and reverted (3)

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| F1 | `test_the_journey_has_an_answer_key.py` deleted from `LARGE` (the Acceptance Test) | the step, naming the file and `107.8s`; exit 1 |
| F2 | `test_process_spine.py` deleted from `LARGE` — `UX-403`'s exact mutation shape, on a file that boots no browser | the step, naming it and `36.4s`; the partition guard stayed at 16 passed, which is the filed state |
| F3 | `PARALLEL_REPORT_SLACK` raised to 100.0, so nothing can ever drift | `test_the_message_carries_the_name_and_the_seconds`; 1 failed, 18 passed |
| G1 | one medium file really triples, on a 1.5x-slower simulated clock | the step, naming it at 64.8s against a calibrated 27.5s floor; exit 1 |
| G2 | `test_process_spine.py` deleted from `LARGE`, on the same slower clock | the step, naming it at 53.7s; exit 1 |

G1 and G2 are the calibration's own falsification: the fix must not
become an excuse, so both are run on a clock slow enough that the
uncalibrated rule flagged nine innocent files. F3 named a constant that
no longer exists; its successor is
`test_one_file_cannot_move_the_scale`, which is the same question about
the mechanism that replaced it.

F2 is the falsification the filing asks for — *the same deletion with
the step removed passes* — measured both ways in one run. F3 is the
direction that matters most for a step with a tolerance in it: a
tolerance nothing guards is a mute switch.

### Deviation from the Required Fix

- **`--junitxml` instead of `--durations=0`**, for the measured reason
  above. Same run, same cost, no threshold.
- **The clock calibration is new**, and the filing did not anticipate
  it — it assumes the report and the floors share a clock, and they do
  not. It is a deviation in the direction of the filing's own warning
  ("goes flaky and then gets muted"): the alternative was a constant
  re-sized per machine, which is a mute switch with extra steps. Its
  cost is written into `TIER_DRIFT_MARGIN` and asserted by clauses
  rather than left implicit.
- **`tests/tiers.py` gained `recorded()`**, which reads each entry's
  own trailing seconds. Not asked for, and load-bearing for the above:
  a step that compares two clocks needs the numbers the floors were
  taken with, and they were already there as comments.
- The rest as specified: it reads the floors and never sets them, it
  runs where a full run already happens, and it fails naming the file
  and its measured seconds. The Out of Scope — *a wall-clock assertion
  inside a test* — is honoured: nothing here times anything; it parses
  a report.
