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
        if self.total:
            body = f"{self.label}: {self._count}/{self.total}"
        else:
            body = f"{self.label}: {self._count}"
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
