# UX-185: a capture that slept must know it slept

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-156 (the incompleteness grammar this reuses), UX-110 (the timestamp-agreement machinery) | **Topic:** capture

## Motivation

Field feedback: *"there also can be scenario with computer going to
sleep during the capture — well known pattern on ubuntu is
`systemd-inhibit --what=sleep:shutdown gnome-session-inhibit
--inhibit idle ./my_long_script.sh` — maybe something like that can be
embedded into some command line switch."* A multi-hour capture on a
laptop meets the lid.

Ground truth, round 20: the hook and the spine stamp
`CLOCK_MONOTONIC` (`hook.c:324`, `spine.c:198`) — which **does not
advance during suspend** — while Plane 1's wrapper stamps wall-clock
time. A suspend mid-capture therefore makes the two planes disagree
about the same build: Plane 2 spans crossing the suspend under-report
(the sleep vanishes), Plane 1 spans over-report (the sleep counts as
build time), the timestamp-agreement check (UX-110) sees a drift it
has no name for, and every duration-derived number — verdicts
included — is quietly wrong. Nothing detects it today.

Two halves, prevention and honesty:

## Required Fix

1. **`bga snapshot --inhibit`** (and `capture run`): when
   `systemd-inhibit` exists, wrap the build in
   `systemd-inhibit --what=sleep:shutdown --why="bga capture" --who=bga`
   (adding `gnome-session-inhibit --inhibit idle` when present); when
   neither exists, say so in one line and run anyway. Not the default
   — taking a lock on the user's power management uninvited is not
   bga's call — but named in the phase output when active, and
   suggested by doctor on machines where a sleep policy is detected.
2. **Detection regardless of the flag**: the capture records a
   monotonic/wall pair at start and end; a wall−monotonic drift beyond
   a threshold means the machine slept, and the run records
   `incomplete_reason: suspended` with the drift — feeding UX-156's
   existing grammar, so analyze banners it and compare refuses the
   verdict the same way it does for a failed build ("this capture
   spans a suspend; its durations are not measurements").
3. The suspend note names the fix: re-run with `--inhibit`, or plug
   in.

## Out of Scope

- Correcting the spans (unknowable — which processes were mid-flight
  at suspend is not recorded; refusal is the honest output).
- Non-Linux suspend detection.

## Acceptance Test

Suspend is simulated, not performed: a seam lets the test inject a
wall−monotonic drift, and the run then carries
`incomplete_reason: suspended`, analyze banners it, compare refuses
with the suspend sentence (all three asserted). `--inhibit` on a
machine with `systemd-inhibit` present wraps the build (argv asserted
through a fake binary on PATH); absent, the one-line notice appears
and the capture proceeds. Doctor's suggestion appears only when a
sleep policy is detectable.

## What was built

`bga/suspend.py`, and the wiring that makes a slept capture refuse
itself.

**Detection, which is not optional.** The wrapper records both clocks at
both ends of the build, as a line in the log rather than a side file -
so a log a user kept still carries the answer when it is extracted
later. Wall time running ahead of monotonic time *is* how long the
machine slept.

The threshold is 5 seconds, and it is derived rather than tuned: the
two clocks are read microseconds apart, so on a machine that did not
sleep the difference is dominated by NTP, which `adjtime` slews at up
to 500ppm - 1.8s per hour of build. Five seconds sits comfortably above
that and far below the shortest suspend a lid can produce. A *backwards*
wall-clock step (NTP can do that too) is not sleep and is not reported
as sleep; both directions are asserted.

**It feeds `UX-156`'s grammar rather than growing its own.**
`RunContext.incomplete_reason` gained a third answer, `"suspended"`,
beside `"failed"` and `"interrupted"` - the accessor `UX-157` created
precisely so a consumer cannot handle one reason and forget another.
The analyzer raises the same `build_failed` violation, so the analyze
banner, compare's refusal and the CI gate all handle it without
learning about it separately. Measured end to end: `bga analyze` on a
suspended run banners it, `bga compare` answers `not comparable (the
candidate capture spans a suspend (2700s of sleep))`, and the gate
exits **6**.

The sentence names the fix, because the reader has a three-hour capture
they cannot use and the next question is what to do differently:

```text
This capture spans a suspend: the machine slept for about 45 minutes
while it ran. Plane 1 counts that sleep as build time and Plane 2 does
not, so the durations here are not measurements. Re-run with
`--inhibit`, or on mains power with the lid open.
```

**Prevention, which is.** `--inhibit` on `bga snapshot` and `bga capture
run` wraps the build in the field's own incantation - `systemd-inhibit
--what=sleep:shutdown` plus `gnome-session-inhibit --inhibit idle` when
present, each layer added only if installed. With neither, one line and
the capture proceeds. Not the default: taking a lock on the user's
power management uninvited is not `bga`'s call.

The inhibitors wrap what is **launched**, never what is recorded -
`Executing command:` stays the real `bst` invocation, because `UX-29`
recovers `--max-jobs` from it and a line reading `systemd-inhibit ...
bst build` would break that. There is a guard.

`bga doctor` gained a `sleep-policy` check that warns only where the
question arises (a machine with `systemctl` and an unmasked
`sleep.target`), so it is silent on the CI runners most captures run on.

Tests: 21 new (`tests/unit/test_a_capture_that_slept.py`). Suspend is
simulated through the clock-pair seam rather than performed. Five
mutations, each red - including the two over-reach directions (no
threshold, and treating a backwards clock step as sleep), because
refusing a good capture is this feature's failure mode.

**A defect the guards found in the fix itself:** `bga/findings.py`
hardcoded *"THIS BUILD FAILED: N element(s) ended in FAILURE"* for the
`build_failed` violation whatever its reason - so a suspended capture
read as a failure with zero failed elements. That was already true of
an **interrupted** capture: `UX-157` fixed the wording in the report
and this second site kept it, for four rounds. Both now say what
actually happened.

## Deviation from the Required Fix

The item names `incomplete_reason: suspended` as a field the *run*
records. It is recorded on disk as `build_outcome.suspended`
(`{"suspended_seconds": …}`) beside `interrupted`, and
`incomplete_reason` is the *accessor* that answers `"suspended"` - which
is the shape `UX-156`/`UX-157` already established, and reusing it is
what gives the banner, the refusal and the gate for free. The number of
seconds is kept rather than a bare flag, because "the machine slept for
about 45 minutes" is actionable and "the machine slept" is not.

