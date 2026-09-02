# UX-496: a wholesale re-record samples every file once, and the drift factor has never been sized against that

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-488` did the re-record; `UX-494` let the gate speak; `UX-458` closed the factor with a starting value | **Found by:** round 73, driving PR #191 to green | **Serves:** the round whose gate is red on a file nobody touched, and cannot tell a stale reference entry from a real regression | **Topic:** guards

## Motivation

`UX-488` refreshed `tests/ci_reference.json` wholesale from one CI run,
which is the documented route (`UX-447`: the runner's own clock, never
a local `--record`). The route is right and the document is one
coherent measurement. What nothing in it says is that **each of its 397
entries is a single sample**, so the refresh freezes whichever end of
each file's range that one run happened to hit.

Measured, on the file that caught it —
`tests/unit/test_why_bga_believes_what_it_believes.py`:

| run | head | reading |
|---|---|---|
| 33540660861 | `08490f5` | 12.8 (the gate named it: *"12.8s against 7.1s recorded, x1.73"*) |
| 33544888654 | `3dd6e03` | **8.19** — the run `UX-488` re-recorded from |
| 33552128782 | `5705840` | 12.81 |
| 33554592057 | `3ab9e76` | 13.62 |

Four of five sit at 12.8–13.6; 8.19 is the outlier, and it is the one
now in the reference. The gate did exactly what it should: `3ab9e76`
put the file in `waiting` (one run), `2bee296` agreed, and the second
run confirmed it. The build went red on a documentation-only commit,
correctly, against a reference entry that was never representative.

The same shape, less severe, in three browser guards on one run —
`test_emphasis_is_a_budget.py` 15.66 / 15.52 / **36.34** / 15.22 — and
that one *was* an excursion, which is how `UX-495` came to be filed.
Both cases have one cause: nothing in the pipeline distinguishes "this
file has a wide range" from "this file changed".

`CI_DRIFT_FACTOR = 1.5` has never been sized against that. `UX-458`
closed with it as a starting value and said so; the second distinct
`spread` `UX-488` produced is the first data that could size it, and
sizing wants the *per-file* range the table above shows, not the
suite-wide one.

## Required Fix

- **A reference entry that is more than one sample.** A median over the
  last N candidates, or a recorded range per file — the shape is the
  decision, and the pipeline already keeps a carry across runs, so the
  samples exist.
- **`CI_DRIFT_FACTOR` sized against the per-file range**, once there is
  one. A factor below a file's own spread makes the gate an alarm
  nobody reads (`UX-418`); a factor above it makes the gate blind to a
  real regression of that size. Both failure modes are now observed.
- Whatever it becomes, the two cases above are its test set: a file at
  12.8–13.6 whose reference said 8.19 must read as a bad entry, and a
  file at 15.2–15.7 that spiked once to 36.3 must read as an excursion.

## Out of Scope

- `UX-495`, which measures the browser family's spread. This row is
  about the reference and the factor; that one is about whether that
  family is unstable for a reason worth fixing. They meet at the
  numbers and are separate questions.
- The wholesale-refresh route itself (`UX-447`, `UX-488`), which is
  correct about *whose clock* to use and is not what this row disputes.
- Re-recording individual entries by hand, which is what round 73 did
  to get green and is a patch, not an answer — `UX-488`'s Motivation
  already explains why hand-appends do not accumulate into anything.

## Acceptance Test

The per-file readings for at least five CI runs, pasted, with the
distribution stated; and `CI_DRIFT_FACTOR` either re-derived from that
distribution with the derivation shown, or left where it is with the
reason written down.

## Outcome

**Round 75, 2026-09-02.** `UX-495` measured the range first; this is
the shape decided against it.

**The shape.** The reference gains `samples: {file: [readings]}`, the
last `CI_REFERENCE_SAMPLES = 5` on that document's clock, newest last,
and `files` becomes their **`median_low`**. Two rules follow:

- **A carried reading is rebased** by the shift between the documents,
  so the list is one clock — mixing two runners is `UX-418`'s defect
  inside a key. Under `SHIFT_MIN_FILES` they are **dropped**: a list
  nobody can rebase is worse than one reading.
- **A file must beat the top of its own readings** as well as the two
  gates — the distinction the Motivation says nothing made. It can only
  widen the gate, never narrow it, since `files` is that list's median.

**Where the samples come from.** `--record` has run wholesale **twice
in the reference's entire history** (`git log tests/ci_reference.json`:
18 commits, 16 one-row adopts). So `--adopt`, which runs on the default
branch after every merge, now leaves a reading on every file it
measured. `added` still means "names the reference lacked", and the
value is still nobody's decision, because it joins a list.

**The test set, both cases, pasted from the guards:**

```text
test_why_bga_believes_what_it_believes.py  samples [12.8, 8.19, 12.81, 13.62]
                                           files   12.8      (was 8.19)
test_emphasis_is_a_budget.py               samples [15.66, 15.52, 36.34, 15.22]
                                           files   15.52     (was 36.34 if last)
```

and read back: a run that spikes that file to 36.0 again verdicts
**ok** (inside its own range), while a file whose four readings sit
within a per cent and then runs 2.2x verdicts **drift** and is named.

**`CI_DRIFT_FACTOR`, sized rather than assumed — and left at 1.5.**
Two measurements bound it. Over the reference's own history the
per-file residual with the shift divided out has p90 **1.49** and
**1.21** on the two real re-record pairs (n=116, 136 files ≥ 1s), max
1.82; over `UX-495`'s six runs the stable browser files never leave
**1.06**. So 1.5 is above the bulk of the suite's noise and *below* the
swinging group's 1.60–2.45 — and raising it to 2.5 to cover them would
blind the gate to a real 2x regression everywhere else. The answer is
not a bigger number: it is `samples`, and `CI_DRIFT_RUNS = 2`, which
`UX-495` found held by exactly one run.

**Mutations.** `PYTHONDONTWRITEBYTECODE=1`, `__pycache__` cleared;
122 passed reverted.

| # | mutation | reddened | count |
|---|---|---|---|
| Q1 | `files` is the last run, not the median | `..._is_the_median_not_the_last_run`, `..._does_not_set_the_entry` | 2 failed, 120 passed |
| Q2 | `median` instead of `median_low` | `..._does_not_set_the_entry`, and `UX-503`'s `..._is_never_rewritten` | 2 failed, 120 passed |
| Q3 | the recorded-range clause removed | `..._repeating_its_own_range_is_not_reported` | 1 failed, 121 passed |
| Q4 | the window is unbounded | `..._the_window_is_bounded` | 1 failed, 121 passed |
| Q5 | carried readings are not rebased | `..._put_on_this_runs_clock` | 1 failed, 121 passed |
| Q6 | a thin population rebases anyway | 5 clauses, and 60 more | 65 failed, 57 passed |
| Q7 | `adopt` stops leaving a reading | `..._leaves_a_reading_on_a_file_it_did_not_add` | 2 failed, 120 passed |

Q2 is the informative one: swapping `median_low` for `median` also
reddens an **existing** `UX-503` guard, because with two readings the
mean of the middles moves an entry the reference already holds. Q6 is
deliberately over-broad and reddens far more than its clause; it is
listed as what it is.

**What it made wrong (§3.10).** `UX-503`'s
`test_nothing_new_writes_nothing` asserted `adopt` returns the document
untouched when nothing is new. That is the contract this row changes,
so it is now `test_nothing_new_adds_no_row`: `added` is still empty,
and a reading is still left. The `note` inside the document and the
tool's module docstring both said "one CI run's per-file totals"; both
now say what `files` is.

**Deviation from the Required Fix:** the factor was sized and **not
changed**. The row allowed either; the measurement says a different
number is worse than the mechanism.

**Live from the next adopt.** The committed reference has no `samples`
yet, so every entry reads exactly as it did until CI writes one — a
file with no readings recorded falls through to the factor alone, which
is today's rule.
