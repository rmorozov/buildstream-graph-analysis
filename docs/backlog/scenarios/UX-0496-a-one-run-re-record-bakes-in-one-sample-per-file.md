# UX-496: a wholesale re-record samples every file once, and the drift factor has never been sized against that

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** `UX-488` did the re-record; `UX-494` let the gate speak; `UX-458` closed the factor with a starting value | **Found by:** round 73, driving PR #191 to green | **Serves:** the round whose gate is red on a file nobody touched, and cannot tell a stale reference entry from a real regression | **Topic:** guards

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

_Not started._
