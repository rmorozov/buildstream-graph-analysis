"""UX-185: a capture that slept must know it slept.

Field feedback: *"there also can be scenario with computer going to
sleep during the capture — well known pattern on ubuntu is
`systemd-inhibit --what=sleep:shutdown gnome-session-inhibit --inhibit
idle ./my_long_script.sh` — maybe something like that can be embedded
into some command line switch."* A multi-hour capture on a laptop meets
the lid.

**Why it is worse than a slow build.** Round 20 ground-truthed the two
clocks. The hook and the spine stamp `CLOCK_MONOTONIC` (`hook.c:324`,
`spine.c:198`), which **does not advance while the machine is
suspended**; Plane 1's wrapper stamps wall-clock time. So a suspend
mid-capture makes the two planes disagree about the same build - Plane
2 spans crossing the suspend under-report (the sleep vanishes), Plane 1
spans over-report (the sleep counts as build time), `UX-110`'s
timestamp-agreement check sees a drift it has no name for, and every
duration-derived number, verdicts included, is quietly wrong.

Two halves, and the second one is the load-bearing one:

1. **Prevention** is opt-in. `--inhibit` takes a lock on the user's
   power management, and doing that uninvited is not `bga`'s call.
2. **Detection is not.** A capture records a monotonic/wall pair at
   each end whether or not the flag was passed; the difference between
   how much wall time and how much monotonic time elapsed is how long
   the machine was asleep. Beyond a threshold the run declares itself
   incomplete and `UX-156`'s existing grammar does the rest - analyze
   banners it, compare refuses the verdict.

**Not** an attempt to correct the spans. Which processes were mid-flight
at the suspend is not recorded anywhere, so there is nothing to correct
them *with*; refusal is the honest output, and `UX-129` is the standing
lesson about the alternative.
"""
import shutil
import time
from typing import Optional

# How much wall-minus-monotonic drift counts as "the machine slept".
#
# Not a tuning knob: the two clocks are read microseconds apart at each
# end, so on a machine that did not sleep the difference is dominated by
# NTP corrections - which `adjtime` slews at up to 500ppm, or 1.8s per
# hour of build. Five seconds is comfortably above that for any
# plausible capture and far below the shortest suspend a laptop lid
# produces (a lid closes for at least the time it takes to open it
# again). A capture that trips this really did lose time.
DRIFT_THRESHOLD_S = 5.0

_WHY = "bga capture"
_WHO = "bga"


def clocks() -> dict:
    """The pair, read as close together as the interpreter allows."""
    return {"wall": time.time(), "monotonic": time.monotonic()}


def drift_seconds(start: Optional[dict], end: Optional[dict]) -> Optional[float]:
    """Wall seconds elapsed minus monotonic seconds elapsed, or None.

    Positive means wall time ran ahead of the monotonic clock, which on
    Linux means the machine was suspended for that long. Negative is
    possible (a backwards wall-clock step from NTP) and is not a
    suspend, so it is not reported as one.
    """
    if not start or not end:
        return None
    try:
        wall = end["wall"] - start["wall"]
        monotonic = end["monotonic"] - start["monotonic"]
    except (KeyError, TypeError):
        return None
    return wall - monotonic


def slept(start: Optional[dict], end: Optional[dict],
          threshold: float = DRIFT_THRESHOLD_S) -> Optional[dict]:
    """`{"suspended_seconds": float}` if the machine slept, else None."""
    drift = drift_seconds(start, end)
    if drift is None or drift < threshold:
        return None
    return {"suspended_seconds": round(drift, 1)}


def available() -> dict:
    """Which inhibitors this machine has."""
    return {
        "systemd-inhibit": shutil.which("systemd-inhibit"),
        "gnome-session-inhibit": shutil.which("gnome-session-inhibit"),
    }


def inhibit_argv(command: list[str]) -> list[str]:
    """`command`, wrapped in whatever inhibitors are installed.

    The field's own incantation:
    `systemd-inhibit --what=sleep:shutdown gnome-session-inhibit
    --inhibit idle <command>`. Each layer is added only if present, so a
    headless runner with `systemd-inhibit` and no GNOME gets the half
    that applies, and a machine with neither gets its command back
    unchanged - the caller says so in one line and runs it anyway.
    """
    found = available()
    argv = list(command)
    if found["gnome-session-inhibit"]:
        argv = [found["gnome-session-inhibit"], "--inhibit", "idle"] + argv
    if found["systemd-inhibit"]:
        argv = [found["systemd-inhibit"], "--what=sleep:shutdown",
                f"--why={_WHY}", f"--who={_WHO}"] + argv
    return argv


def unavailable_notice() -> Optional[str]:
    """One line when `--inhibit` was asked for and cannot be honoured."""
    if any(available().values()):
        return None
    return ("--inhibit: neither `systemd-inhibit` nor `gnome-session-inhibit` "
            "is installed, so this capture cannot stop the machine from "
            "sleeping. Running anyway - a suspend mid-capture is detected "
            "either way and the run will say so.")


def describe(suspension: dict) -> str:
    """What analyze banners and compare refuses with.

    Names the fix, because a user reading this has a three-hour capture
    they cannot use and the next question is what to do differently.
    """
    seconds = suspension.get("suspended_seconds", 0)
    minutes = seconds / 60
    span = f"{minutes:.0f} minutes" if minutes >= 2 else f"{seconds:.0f} seconds"
    return (f"This capture spans a suspend: the machine slept for about "
            f"{span} while it ran. Plane 1 counts that sleep as build time "
            f"and Plane 2 does not, so the durations here are not "
            f"measurements. Re-run with `--inhibit`, or on mains power with "
            f"the lid open.")
