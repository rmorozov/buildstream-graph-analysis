# UX-161: the stale casd everyone suspects is checkable before the build, and nobody looks

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-147 (whose item 2 this completes), UX-149 (the probe with the structural blind spot) | **Topic:** capture | **Area:** tools

## Motivation

UX-147 deferred its stale-daemon detection (recorded as a deviation),
and the round-16 review established that the gap is now the sharpest
edge left on the field failure:

- The zero-invocation summary *names* `buildbox-casd` reuse as a
  cause (`tools/bst_native_build_tracer.py:4188-4194`) — after the
  build, as one of three possibilities, with no way to tell whether it
  is the live one.
- `bga doctor --capture` **structurally cannot reproduce it**: the
  probe isolates `HOME` (`tools/bga_doctor.py:626-629`), which starts
  a fresh casd with the shim already on PATH. Doctor's chain passing
  therefore does not imply the user's real capture reaches the shim —
  the exact assurance the command exists to give.
- The user's real sessions make the miss likely, not exotic: any plain
  `bst build` (or `bst show`) before `bga snapshot` leaves a casd
  running with a pre-shim PATH, and bga's own census runs `bst show`
  — meaning **the capture itself can start the stale daemon it then
  falls victim to** if the census ordering ever precedes the PATH
  assembly.

The fix is cheap because the question is answerable from `/proc`
before the build: a `buildbox-casd` process whose command line names
this cache directory (`--bind=... <cachedir>` are its own argv), with
a start time earlier than the capture.

## Required Fix

1. **A pre-build check in the capture path**: before `bst` runs,
   look for a running `buildbox-casd` serving this build's cache
   directory (resolve it the way bst does: `XDG_CACHE_HOME` /
   `~/.cache/buildstream`, or the configured `cachedir`). If one
   predates the capture, say so *up front*, with the ten-second
   remedy: `A buildbox-casd started before this capture is running
   (pid 4132, started 2h ago); it will not see the capture's PATH.
   Stop it first: bst shutdown / kill 4132 - bst restarts it
   automatically.` Under `--diagnose`, record pid + start time in the
   fingerprint line.
2. **The zero-invocation summary upgrades from possibility to
   verdict** when the check fired: "a stale buildbox-casd was detected
   at capture start (and warned about)" replaces the three-way guess.
3. **Doctor tells the truth about its own blind spot**: `doctor
   --capture` reports the host's running casd state (age, whether it
   predates doctor) alongside its isolated-HOME probe result, so a
   passing chain is not read as "your next real capture will work"
   when a stale daemon is sitting right there.

## Out of Scope

- Killing the daemon automatically (a daemon bga did not start is not
  bga's to kill; the remedy is one command and stays the user's).
- Whether reuse actually bypasses the shim on every bst version — the
  check reports what is running and lets the wording of the verdict
  stay evidence-shaped, per UX-147's own caution.

## Acceptance Test

Live, on `examples/06`: run `bst show` (starts a casd), then
`bga snapshot` — the pre-build warning names the pid and age; the same
capture's fingerprint records it; stop the daemon, snapshot again — no
warning. `doctor --capture` run with that stale casd present reports
it next to a passing chain. A capture on a quiet machine (no casd)
prints nothing new — the check is silent when there is nothing to say.

---

## What was built

Detection keys on what casd's argv actually carries, measured on a live
daemon: `... --jobs=16 /tmp/x/cache/buildstream`, the cache directory as
its last positional. The capture warns up front with pid, age and the
one-command remedy; `--diagnose` records pid and age in the fingerprint;
the zero-invocation summary promotes that possibility to the leading
explanation when the check fired, and says the check found nothing when
it did not.

Doctor gained `casd-fresh`, which exists mainly to state doctor's own
blind spot: `--capture` isolates `HOME` (`UX-84`), so its chain probe
starts a *fresh* daemon and structurally cannot reproduce this.

Verified live: with a casd on the build's cache directory the warning
names it (pid 7464, started 14s ago) and the fingerprint records it;
doctor reports it beside a passing chain; stopped, a capture prints
nothing new. A daemon on a *different* cache directory produces no
warning and the shim still ran 9/9 - specific, not a blanket alarm.

### Deviation, recorded

The acceptance asks for the stale daemon to be produced by running
`bst show` first. On BuildStream 2.7.0 here **casd does not outlive its
bst** - measured twice, no daemon survives `bst show` or `bst build`
exiting - so it was started directly instead, which is what a shared or
persistent-daemon setup looks like and what the check matches on. The
"tasks ran but the shim was never called" branch is therefore covered by
test rather than by a live reproduction: 2.7.0 could not be made to reuse
a foreign daemon at all.

A `proc_root` seam makes the matching rules testable - a process's `comm`
cannot be faked otherwise.
