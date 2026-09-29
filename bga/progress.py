"""UX-183: a moving number inside the phases that take minutes.

Field feedback, first deployment on big captures: *"some bga commands
can take considerable time... progress bar and progression status
messages would be great — but it definitely can break some scenarios
with passing tool output into something through unix pipe."* Both
halves are the requirement, and the second one decides the design.

`UX-159` gave the long phases an announcement line each, so a user
knows *which* step is running. On a 200k-process trace one of those
lines holds the terminal for minutes, and silence-within-a-phase is the
same problem one level down.

**The rules, in the order they bind.**

1. `stdout` is never touched. It carries the report, and a pipeline
   reading `--format json` must see the same bytes whether or not
   anything is drawing a progress line. There is a guard.
2. Progress writes to `stderr`, and **only when `stderr` is a TTY**. A
   redirected stderr is a log file or a pipe, and a carriage return in
   a log file is a line somebody has to clean up later. Piped, the
   output is exactly what it was before this module existed: the phase
   lines, whole, and nothing else.
3. `BGA_NO_PROGRESS=1` turns it off on a TTY too - for the user who
   wants stillness, and because it makes the enabled path testable
   without a pty.

The implementation is a carriage return and a string. A progress bar
library would be a dependency, a rendering mode to configure, and a
second thing that writes to the terminal; one `\\r` line is the whole
requirement.
"""

import os
import sys
import time
from contextlib import contextmanager, suppress
from typing import Optional

# How often the line may be redrawn. A build phase can iterate hundreds
# of thousands of times, and a terminal write per iteration is itself a
# measurable cost - this is a progress indicator, not a frame counter.
_MIN_INTERVAL_S = 0.1

# Longest line drawn. Narrower than any real terminal, so the line never
# wraps - a wrapped `\r` line leaves its first row behind on screen and
# the "self-overwriting" property quietly stops holding.
_MAX_WIDTH = 72


def enabled(stream=None) -> bool:
    """Whether in-phase progress may be drawn at all.

    Read fresh each time rather than cached at import: tests redirect
    `sys.stderr`, and a value captured at import would describe the
    process's original stderr forever.
    """
    if os.environ.get("BGA_NO_PROGRESS"):
        return False
    stream = sys.stderr if stream is None else stream
    if os.environ.get("BGA_FORCE_PROGRESS"):
        # `UX-197`: draw even onto a pipe. This exists so a test can run
        # a real subprocess with progress genuinely *on* and compare its
        # stdout against a run with it off - the comparison `UX-183`
        # claimed to make and did not, because without this there is no
        # way to turn progress on without a terminal, so both sides of
        # that assertion were progress-off.
        #
        # Documented (`UX-630`) as what it is rather than as a switch: it makes
        # `bga ... 2>file` write control characters into that file, and
        # the one thing `UX-183` is about is that nothing does. It loses
        # to `BGA_NO_PROGRESS` above, so the documented off-switch stays
        # absolute.
        return True
    try:
        return bool(stream.isatty())
    except (AttributeError, ValueError):
        # A closed handle, or something file-like that does not answer.
        # Not a TTY is the safe reading: it costs a progress line and
        # cannot corrupt a log.
        return False


class Ticker:
    """A single self-overwriting line, for one long phase.

    Disabled instances are not a special case anywhere else in the
    codebase: `step()` and `done()` are cheap no-ops, so a caller writes
    the same three lines whether or not anything will be drawn.
    """

    def __init__(self, label: str, total: Optional[int] = None, stream=None):
        self.label = label
        self.total = total
        self._stream = sys.stderr if stream is None else stream
        self._on = enabled(self._stream)
        self._last_draw = 0.0
        self._width = 0
        self._count = 0

    def step(self, count: Optional[int] = None, suffix: str = "") -> None:
        """Advance to `count` (or by one), redrawing at most a few times
        a second."""
        self._count = self._count + 1 if count is None else count
        if not self._on:
            return
        now = time.monotonic()
        if now - self._last_draw < _MIN_INTERVAL_S:
            return
        self._last_draw = now
        self._draw(self._render(suffix))

    def note(self, text: str) -> None:
        """Redraw the line with arbitrary text instead of a count.

        For a phase whose progress is *elapsed time* rather than items -
        a subprocess this cannot see inside. "Still running, 40s" is a
        weaker signal than "3000/5000", and much stronger than a cursor
        that has not moved in four minutes.
        """
        if not self._on:
            return
        now = time.monotonic()
        if now - self._last_draw < _MIN_INTERVAL_S:
            return
        self._last_draw = now
        self._draw(f"  {self.label}: {text}"[:_MAX_WIDTH])

    def done(self, suffix: str = "") -> None:
        """Erase the line. The phase's own summary, if it has one, is a
        whole line printed by the caller afterwards - this never leaves
        a partial line behind for it to collide with."""
        if not self._on:
            return
        self._erase()

    # -- context manager, so an exception cannot leave the line drawn ---

    def __enter__(self) -> "Ticker":
        return self

    def __exit__(self, *_exc) -> bool:
        self.done()
        return False

    # ------------------------------------------------------------------

    def _render(self, suffix: str) -> str:
        body = f"{self.label}: {self._count}/{self.total}" if self.total else f"{self.label}: {self._count}"
        if suffix:
            body = f"{body} {suffix}"
        return f"  {body}"[:_MAX_WIDTH]

    def _draw(self, text: str) -> None:
        # Pad to the previous width so a shortening line does not leave
        # its own tail on screen.
        padded = text.ljust(self._width)
        self._width = len(text)
        try:
            self._stream.write("\r" + padded)
            self._stream.flush()
        except (OSError, ValueError):
            # The terminal went away mid-phase. Progress is decoration;
            # losing it must never take the analysis with it.
            self._on = False

    def _erase(self) -> None:
        if not self._width:
            return
        try:
            self._stream.write("\r" + " " * self._width + "\r")
            self._stream.flush()
        except (OSError, ValueError):
            pass
        self._width = 0


def phase(message: str, stream=None) -> None:
    """Announce a phase: one whole line on stderr, always.

    This is `UX-159`'s behaviour, unchanged and unconditional - the
    piped case must keep getting these. It exists here so a caller that
    also draws a ticker has one import rather than two conventions.
    """
    print(message, file=sys.stderr if stream is None else stream)


def ticker(label: str, total: Optional[int] = None, stream=None) -> Ticker:
    return Ticker(label, total=total, stream=stream)


# -- UX-1077/UX-1078: one recorder for the tail's phases -----------------
#
# `timed` announces a phase, prints its elapsed seconds and appends a row
# to this ledger; `bga snapshot` writes the ledger as `tail.json`, so the
# printed timings and the stored ones are one list, not two that drift.

_LEDGER: dict = {"build_wall_us": None, "phases": []}
_ON_ROW = None

# UX-1080: subprocess calls (`bst --version`, `bst show`, `bst artifact
# list-contents`) landed by `timed_call`, before the phase they belong to
# has a row of its own - `timed`'s `finally` only appends that row once
# the `with` block exits, so a call made inside it cannot index into
# `_LEDGER["phases"]` yet. Buffered here instead and sliced off by the
# enclosing `timed()` when it closes; a call made outside any phase (the
# doctor's `bst --version`, before `bga snapshot` has one) rides along
# with whichever phase closes first.
_CURRENT_CALLS: list = []


def reset_ledger(on_row=None) -> None:
    """Empty the ledger; `on_row()` is called after every row lands."""
    global _ON_ROW
    _LEDGER["build_wall_us"] = None
    _LEDGER["phases"] = []
    _CURRENT_CALLS.clear()
    _ON_ROW = on_row


def set_on_row(on_row) -> None:
    """Attach (or replace) the write-back callback without discarding
    rows already recorded - UX-1080's doctor call can land before the
    snapshot directory `on_row` writes into even exists."""
    global _ON_ROW
    _ON_ROW = on_row


def ledger() -> dict:
    """A copy of the ledger: `build_wall_us` and one row per phase."""
    return {"build_wall_us": _LEDGER["build_wall_us"], "phases": [dict(row) for row in _LEDGER["phases"]]}


def tail_us(phases) -> int:
    """What the *post-build* phases cost together - derived, never
    stored (UX-996). `stage: "before"` phases (the readiness check
    ahead of the build) are timed but excluded: they are not part of
    "bga's own time after the build" (review, pull request 300)."""
    return sum(row.get("wall_us") or 0 for row in phases or () if row.get("stage") != "before")


def _reset_peak_rss() -> bool:
    # VmHWM per phase; `ru_maxrss` is the whole process's high-water mark.
    try:
        with open("/proc/self/clear_refs", "w") as handle:
            handle.write("5")
        return True
    except OSError:
        return False


def _peak_rss_bytes() -> Optional[int]:
    try:
        with open("/proc/self/status", encoding="ascii") as handle:
            for line in handle:
                if line.startswith("VmHWM:"):
                    return int(line.split()[1]) * 1024  # VmHWM is in kB
    except (OSError, ValueError, IndexError):
        return None
    return None


def _say(text: str, stream) -> None:
    with suppress(OSError, ValueError):
        print(text, file=sys.stderr if stream is None else stream, flush=True)


@contextmanager
def timed(name: str, say: Optional[str] = None, stream=None, before_build: bool = False):
    """One phase: announced, timed, and recorded - also when it raises.

    A TTY (or `BGA_FORCE_PROGRESS`) gets the announcement and an elapsed
    line; a pipe keeps the one announcement line; `BGA_NO_PROGRESS`
    prints neither. The row lands whichever was chosen.

    `before_build=True` marks the row `stage: "before"` - recorded like
    any other phase, but excluded from `tail_us` and everything built
    on it: the readiness check ahead of the build is not part of "bga's
    own time after the build" (review, pull request 300).
    """
    loud = enabled(stream)
    if not os.environ.get("BGA_NO_PROGRESS"):
        _say(say or f"{name}...", stream)
    measured = _reset_peak_rss()
    start = time.monotonic()
    try:
        yield
    finally:
        wall = round((time.monotonic() - start) * 1e6)
        # UX-1080: every call buffered since the previous phase closed -
        # including one made before any phase existed at all, like the
        # doctor's `bst --version` ahead of the first snapshot phase.
        calls = list(_CURRENT_CALLS)
        _CURRENT_CALLS.clear()
        _LEDGER["phases"].append(
            {
                "name": name,
                "wall_us": wall,
                "peak_rss_bytes": _peak_rss_bytes() if measured else None,
                "calls": calls,
                "stage": "before" if before_build else "after",
            }
        )
        if loud:
            _say(f"  {name}: {wall / 1e6:.1f}s", stream)
        if _ON_ROW is not None:
            _ON_ROW()


@contextmanager
def timed_call(argv):
    """One BuildStream subprocess call, recorded as a `calls` row under
    the phase it ran inside of (UX-1080). Yields a mutable row the
    caller sets `exit` on before the block ends; a call that raised (or
    timed out) keeps `exit: null`, which is the honest reading of "never
    returned" rather than a made-up code.
    """
    start = time.monotonic()
    row = {"verb": " ".join(argv), "wall_us": None, "exit": None}
    try:
        yield row
    finally:
        row["wall_us"] = round((time.monotonic() - start) * 1e6)
        _CURRENT_CALLS.append(row)


@contextmanager
def timed_build():
    """The build's own wall, around its subprocess - no line printed."""
    start = time.monotonic()
    try:
        yield
    finally:
        _LEDGER["build_wall_us"] = round((time.monotonic() - start) * 1e6)


def total_line(stream=None) -> None:
    """The tail's last line, printed whatever the progress setting."""
    line = f"bga's own time after the build: {tail_us(_LEDGER['phases']) / 1e6:.1f}s"
    if _LEDGER["build_wall_us"] is not None:
        line += f" (the build: {_LEDGER['build_wall_us'] / 1e6:.1f}s)"
    _say(line, stream)
