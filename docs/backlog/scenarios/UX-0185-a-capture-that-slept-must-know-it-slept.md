# UX-185: a capture that slept must know it slept

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-156 (the incompleteness grammar this reuses), UX-110 (the timestamp-agreement machinery)

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
