# UX-442: one slow sample reddens CI, and nothing asks it to repeat

**Priority:** High | **Status:** 🟢 Done | **Found by:** round 69, the third `test (3.11)` red on a branch whose diff could not cause any of them | **Serves:** every contributor whose PR the drift gate stops for a number that will not reproduce | **Topic:** guards

## Motivation

`test (3.11)` went red on `279900f`, a commit whose diff is one backlog
file and one index row. The suite passed:

```text
=========== 5217 passed, 140 skipped, 1 warning in 280.20s (0:04:40) ===========
```

What failed was the drift step:

```text
371 file(s) measured against ci_reference.json (…), this run x1.16 from 114 file(s) over 1s, IQR 0.37
1 file(s) slower than CI's own record of them:
  tests/unit/test_the_page_has_a_reader.py  13.9s  against 7.1s recorded, x1.67 after this run's x1.16 shift
```

**The same file across four CI runs of this branch**, read from the
`--record -` documents those runs printed:

```text
run   reader file   run's shift   run's spread max
 1        7.13            —              —
 2        7.13            —              —
 3        7.53          1.227          5.87
 4       13.85          1.18           4.872
```

Three samples at 7.1-7.5 and one at 13.9. **The outlier run was not a
contended run**: its shift was x1.18 and its spread max x4.87, both
unremarkable and both *lower* than run 3, which passed. One file
excursed; the machine did not.

Both gates tripped, and only just:

```text
ratio/shift  1.69  against CI_DRIFT_FACTOR 1.5
seconds      5.66  against CI_DRIFT_SECONDS 5.0
```

`UX-418` set two gates so a small file could not trip on a ratio and a
big one could not trip on seconds. `UX-423` then measured the run's
**dispersion**, so a globally slow runner would not be read as drift.
Both were right and neither covers this: **the shift's dispersion is
measured and a single file's excursion is not.** A file that boots a
browser can swing six seconds once in four runs, and one such swing is
a red PR.

The cost is not hypothetical. This branch has now been stopped three
times by `test (3.11)`, every one of them at this step, none of them by
a test, and none of them by anything the diff could reach. That is the
habit `UX-426`'s CI-first loop is trying to build being taxed by the
gate meant to protect it — and a gate that reddens on noise is one
people learn to re-run without reading, which is `UX-427`'s "an alarm
nobody reads" arriving from the other direction.

## Required Fix

- **Require the excursion to repeat, or to be large enough that one
  sample settles it.** Two consecutive runs over the bound, a
  best-of-two, or a second much higher factor for a single-run trip —
  the item picks one and states the arithmetic.
- **Whatever is chosen, say what it costs**: a rule needing two runs
  finds real drift one run later, and that delay is the price being
  paid for not crying wolf. Write it down where the next round reads it.
- **A guard driven by a series, not a run.** The present clauses feed
  `dev_tier_drift` one junit document; this needs a fixture of several,
  with one file excursing once and another excursing twice, asserting
  only the second reddens.
- Consider bounding by the file's own history rather than one record —
  `7.13, 7.13, 7.53` is a tight distribution and `13.9` is far outside
  it, which is a stronger statement than a ratio against a single
  number.

## Out of Scope

- **Re-recording the reference to make this green**: the file is not
  slower — three of four samples say 7.1-7.5 — and recording 13.9 would
  bake a contended sample into the document `UX-427` exists to keep
  true.
- **Making `test_the_page_has_a_reader.py` faster**: it boots a browser
  because that is what it measures, and its normal cost is already in
  the reference.
- **Both gates' constants**: `UX-418` measured them and this item adds
  a repetition rule rather than retuning either.
- **The log readability that made this hard to diagnose** — `UX-441`.

## Acceptance Test

Feed `tools/dev_tier_drift.py` a series in which one file exceeds the
bound in a single run and another exceeds it in two consecutive runs:
only the second is reported. A mutation removing the repetition rule
must redden the guard.

## Outcome (round 70, 2026-08-30) — 🟢 Done

### The rule chosen, and its arithmetic

**Two consecutive runs of the same branch must find a file over both
gates before it is reported.** `CI_DRIFT_RUNS = 2` in
`tools/dev_tier_drift.py`, next to the two gates it qualifies. Neither
gate moved — `UX-418` measured them, and this item's Out of Scope keeps
them.

The memory is a **carry** file: `--carry PATH` holds the names the runs
behind this one found, at most `CI_DRIFT_RUNS - 1` of them. CI restores
it before the step and saves it after, keyed by `github.ref` so a branch
reads its own series and not another branch's. Every `--against` run
rewrites it, including the runs that find nothing — a file that excurses,
recovers and excurses again has not drifted twice in a row, and the empty
run between is what says so.

**What it costs, stated because the Required Fix asks for it.** Real
drift is reported one run later than before, and a branch's first run
cannot report at all — there is nothing for it to agree with. A cache
that fails to restore lands in the same state and is treated as an
absent history rather than an error, because failing the build over a
missing cache is a worse alarm than the one this item removes.

**Why not a second, higher bound that trips on one sample**, which the
Required Fix also offered: it would need a number, and the only series
anybody has is the four runs in the Motivation. Sizing a constant from
one excursion is the mistake `UX-420` paid three red CI rounds for. A
hang is already caught by the small tier's `timeout 120` backstop
(`UX-421`); drift, by definition, repeats.

### The acceptance test, run

A series of three reports against one reference and one carry. `FLAKY`
(`test_the_page_has_geometry.py`, recorded 61.7s) is doubled on run 1;
`STEADY` (`test_the_journey_has_an_answer_key.py`, recorded 50.0s) on
runs 2 and 3.

```console
$ for n in 1 2 3; do
    python tools/dev_tier_drift.py $T/run$n.xml --against $T/ref.json \
      --carry $T/carry.json --source "a series, one runner"; echo "exit $?"
  done
=== run 1 ===
1 file(s) over both gates on this run only, and 2 consecutive runs are what reports (UX-442):
  tests/unit/test_the_page_has_geometry.py  123.4s  against 61.7s recorded, x2.00 after this run's x1.00 shift
tiers ok: 141 file(s) measured against ref.json (unknown), this run x1.00 from 141 file(s) over 1s, IQR 0.00
exit 0
=== run 2 ===
1 file(s) over both gates on this run only, and 2 consecutive runs are what reports (UX-442):
  tests/unit/test_the_journey_has_an_answer_key.py  100.0s  against 50.0s recorded, x2.00 after this run's x1.00 shift
tiers ok: 141 file(s) measured against ref.json (unknown), this run x1.00 from 141 file(s) over 1s, IQR 0.00
exit 0
=== run 3 ===
141 file(s) measured against ref.json (unknown), this run x1.00 from 141 file(s) over 1s, IQR 0.00
1 file(s) slower than CI's own record of them:
  tests/unit/test_the_journey_has_an_answer_key.py  100.0s  against 50.0s recorded, x2.00 after this run's x1.00 shift

Make it faster, or - if it is meant to cost this - re-record with --record and commit, which is how the reference stays true rather than becoming an alarm nobody reads.
exit 1
```

The single-run excursion exits 0 and the two-run one exits 1. Before
this item both runs exited 1, which is the red on `279900f`.

**The first sample is not swallowed.** A gate that says nothing on run 1
would leave run 2 red with no history a reader can see, so the run that
sees an excursion once prints it and marks it unconfirmed.

### The guard, and the ten mutations

`TestAnExcursionMustRepeat` (six clauses, driven by a **series** — every
clause calls `main` several times over one carry, which is what CI does
with its cache) and `TestCiSuppliesTheMemoryTheRuleNeeds` (four clauses,
tying the workflow to it).

```text
R1  no repetition rule at all         red: two_runs_agree, clean_run_between,
                                           only_saw_it_once, no_history,
                                           every_run_behind
R2  one run is enough to confirm      red: two_runs_agree, only_saw_it_once,
                                           no_history
R3  agreement with any past run       red: every_run_behind_this_one_must_agree
R4  the carry accumulates every run   red: the_history_is_bounded_by_the_constant
R5  a clean run does not break it     red: a_clean_run_between_them_breaks_the_chain
R6  the single excursion is swallowed red: the_run_that_only_saw_it_once_says_so
R7  CI passes no carry                red: the_drift_step_is_given_a_carry,
                                           the_carry_is_restored_and_saved
R8  nothing restores the carry        red: the_carry_is_restored_and_saved
R9  the save is gated on green        red: the_save_runs_when_the_step_reported
R10 one carry for every branch        red: a_branch_reads_its_own_series
```

**Three of these did not discriminate on the first pass**, and each was
a different mistake worth writing down:

- **R3** (`all` → `any` over the history) passed, because with
  `CI_DRIFT_RUNS = 2` the history is one run long and the two are the
  same function. The clause that catches it calls `repeated()` directly
  with a two-run history — no series the tool writes today can tell them
  apart, so the contract had to be asserted rather than exercised.
- **R5** (the carry written only on runs that found something) passed,
  because the series in the acceptance clause has an excursion on *every*
  run. The case needs a run with nothing over the gates in the middle,
  which is now its own clause.
- **R9** (the cache save gated on green) passed, because the clause read
  the whole step *block* for `always()` and the block runs on to the
  comment introducing `UX-427`'s step, which says "`always()`". It now
  reads the step's own `if:` line. This is the tenth sighting of a guard
  that reads a proxy for what it names — a text scan that cannot tell
  code from prose.

The clauses that decide are the six in `TestAnExcursionMustRepeat`; the
four workflow clauses are text about YAML and are named as such in the
class docstring, because a text scan alone would be exactly the
instrument `docs/contributing/fixing-guide.md` §5 forbids.

### Documents this changed

`.claude/skills/verify/SKILL.md` §3 describes the CI drift step, so it
now states the two-run rule and its price. The rule's own reasoning —
the four-run series, the two costs, why no single-sample bound — is in
`CI_DRIFT_RUNS`'s docstring, which is where the other two constants keep
theirs.

### Deviation from the Required Fix

None on the rule. Two of the four bullets were answered by choosing
against them, with the reason recorded: the higher single-run bound
(above), and bounding by the file's own history rather than one record —
the reference holds one number per file and giving it a distribution is
a change to the recorded document that this item does not need, since
agreement between runs already answers the case that was filed. Left as
a note here rather than a new row, because nothing is now blocked on it.

### The suite

```console
$ make test-touching
299 passed in 5.34s

$ make lint
All checks passed!

$ make test
5347 passed, 26 skipped, 1 warning in 286.93s (0:04:46)
```

### What CI has not shown yet

The rule is verified against a synthetic series, which is the only place
a controlled one exists. What this branch's own runs will show is the
first half only — that the step still passes a green suite — because
confirming an excursion needs two runs that have one.
