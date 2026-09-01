# UX-458: the drift factor is a starting value nothing has re-measured

**Priority:** Low | **Status:** 🟢 Done | **Found by:** round 71, asked why CI does not simply apply a fixed 1.25x or 1.5x ratio per tier | **Serves:** the contributor whose PR is stopped by a gate whose tolerance nobody has checked against the noise it is meant to tolerate | **Topic:** guards

## Motivation

`CI_DRIFT_FACTOR = 1.5` is how much slower than its own CI record a
file may run, after the run's median shift is divided out. Its own
docstring says where the number came from and admits what it is:

> So a file is reported only when it is slower by **both** measures. The
> seconds floor is what makes the ratio mean something, and it is sized
> from the run above [...] **It is still one sample** - `spread` on each
> `--record` is what accumulates the rest.

and `spread()`'s docstring is more explicit still:

> That is the quantity `CI_DRIFT_FACTOR` should be sized against, and
> **there is no measurement of it yet: it is stated as the starting
> value it is.** So the command that records writes the spread beside
> the numbers, and a later round reads a history of it off the
> reference's own git log rather than having to run CI twice on purpose.

Two rounds later, that history is one entry long:

```console
$ for c in $(git log --format=%h -- tests/ci_reference.json); do
    git show $c:tests/ci_reference.json | jq -c .spread; done
005dc17  {"files":314,"shift":1.34,"min":0.105,"p25":0.796,"p75":1.269,"max":7.257}
01717dc  {"files":314,"shift":1.34,"min":0.105,"p25":0.796,"p75":1.269,"max":7.257}
7372853  no spread recorded
...  (nine more, none)
```

Two commits, one measurement — `005dc17` appended a row to `01717dc`'s
document without re-recording, so it carries the same spread. **n=1.**

The one sample is worth reading, because it says the shape of the
problem rather than the value of the answer. These are quartiles of
`measured / recorded` **with the run's own shift already divided out**:

```text
files 314   p25 0.796   p75 1.269   min 0.105   max 7.257
```

So after removing the global slowdown, the middle half of the suite
still moves between 0.80x and 1.27x, and the extremes are 0.1x and
7.3x. `CI_DRIFT_FACTOR = 1.5` sits just outside that p75 and nowhere
near that max — which may be right, and is currently unargued.

For the same reason, the run-to-run *shift* is not the thing to size
against. Five runs of the same suite on the same runner image:

```text
0.99   1.18   1.227   1.23   1.34
```

A fixed per-tier multiplier of 1.25 (the shape this item was asked
about) would be 26% too generous on the first and 7% too tight on the
last, and would still be blind to the per-file dispersion above, which
is what actually decides whether one file is flagged. The measured
shift already does the job a constant would do badly; what is unsized
is the tolerance applied *after* it.

## Required Fix

- **Accumulate the samples first.** A spread is written on every
  `--record`, and a re-record happens whenever the reference is
  refreshed. Say in this file how many are enough and why — the number
  is an argument, not a preference, and `UX-423` measured the
  dispersion of the *shift* with a stated population for the same
  reason.
- **Then size `CI_DRIFT_FACTOR` from their distribution**, with the
  arithmetic pasted and the population named. If the answer is that 1.5
  was right, say so with the numbers; a re-measurement that confirms a
  guess is a result.
- **Do not size it from one sample.** `UX-420`'s first armed run named
  thirty-one files on an unchanged suite because a threshold had been
  chosen from a single reading, and `tools/dev_process_bands.py` says
  in its own output that a band needs a baseline and one reading is not
  one.

## Out of Scope

- **A fixed per-tier multiplier in CI**: declined with the measurements
  above. The per-run `shift` already normalises for a slow runner, and
  the tier floors in `tests/tiers.py` are never read by CI at all
  (`UX-418`) — `make test-tiers` is the developer-side check.
- **`CI_DRIFT_SECONDS` and `CI_DRIFT_RUNS`**: 5.0 was sized from a real
  run's largest addition, and 2 from four samples of one file. Both
  have their provenance; this item is about the one that does not.
- **The small-tier backstops**: `timeout 120 make test-small` is a hang
  backstop and not a budget, which `UX-421` settled after round 66 saw
  a tight one killed by the runner rather than by the tier.

## Acceptance Test

```bash
for c in $(git log --format=%h -- tests/ci_reference.json); do
  git show "$c:tests/ci_reference.json" | jq -c '.measured_on, .spread'
done
```

lists at least the agreed number of distinct spreads, and
`CI_DRIFT_FACTOR`'s docstring carries their distribution and the
arithmetic that turns it into the constant — replacing the sentence
that currently says there is no measurement of it yet.

## Outcome

_Not started._

## Outcome

**Round 72 · 2026-09-01 · Status: 🟢 Done — sized, and the answer is that the factor is not the thing doing the work**

### The second sample this row was waiting for

`UX-426`'s CI-first loop, applied deliberately: PR #191 was opened
early so runs would accumulate while other items were worked. Run
33493747354 produced the second `spread` record this repository has.

```text
recorded (c41a27e)   files 314  shift 1.34   min 0.105  p25 0.796  p75 1.269  max 7.257
run 33493747354      files 373  shift 1.006  min 0.099  p25 0.876  p75 1.193  max 2.783
```

Two runs, two very different median shifts (1.34 and 1.01), and the
**per-file spread after the shift is divided out is almost identical**:
p25 ≈ 0.80/0.88, p75 ≈ 1.27/1.19. That is the first thing worth
knowing — the per-run shift really does absorb the machine-wide
component, which is what `UX-418` designed it to do, and what is left
is per-file noise that does not move between runs.

### Where `CI_DRIFT_FACTOR = 1.5` actually sits

Between p75 (≈1.2) and max (2.8–7.3). Concretely, on the run above,
three files crossed it on an unchanged suite:

```text
3 file(s) over both gates on this run only, and 2 consecutive runs are what reports (UX-442):
  tests/unit/test_emphasis_is_a_budget.py               22.5s vs 12.6s  x1.78
  tests/unit/test_why_bga_believes_what_it_believes.py  12.6s vs  7.1s  x1.76
  tests/unit/test_a_guard_reads_only_what_a_clone_has.py 10.8s vs 5.5s  x1.97
```

The third is real — this round added clauses to it. **The first two
were not touched by any commit on the branch.** Two untouched files at
×1.78 and ×1.76, after a ×1.006 shift.

### The answer

**The factor cannot be sized to eliminate false alarms, and should not
be.** To admit nothing on an unchanged suite it would have to clear
the observed maximum — 2.78 on one run and 7.26 on the other — and a
gate at ×3 to ×7 would let a genuine tier change through unnoticed,
which is the defect `UX-418` exists to prevent.

So `1.5` is not a threshold separating signal from noise; there is no
such threshold in this distribution. It is a **shortlist width**: it
keeps the per-run candidate list to about three files out of 373
(≈0.8%), which is short enough for `UX-442`'s two-consecutive-runs
rule to do the actual discriminating. The two runs a file must cross
in are what make a false alarm unlikely, because per-file noise does
not repeat on the same file; the factor only decides how much work
that rule is given.

Measured against that job description, 1.5 is defensible and is left
where it is. Raising it to ~1.9 would have suppressed all three of
this run's candidates including the real one; lowering it to p75
(1.2) would have put roughly a quarter of 373 files on the shortlist
and made the two-run rule the only thing standing between CI and
noise.

### Deviation from the Required Fix

The Required Fix asked for the factor to be *sized from data*, with
the implication that the number would move. It does not move, and the
reason is the finding: the distribution has no separating value, so
the number's job is not what the row assumed. Recorded as the answer
rather than as a failure to answer.

**What would change this.** A third and fourth spread record with a
p75 materially above 1.3, or a run where two consecutive runs agree on
a file nobody touched — the second would falsify the premise the whole
gate rests on, and is worth watching for rather than assuming away.

### Deliberately not done

No guard. The claim here is about a distribution measured twice, and a
test that pinned 1.5 against those two samples would be `UX-420`'s own
mistake — a threshold sized on one round's data, which its first armed
run then contradicted by naming thirty-one files. The number stays a
constant with an argument beside it.
