"""UX-1140: a duration, percent or count as the page prints it.

Mirrors `bga/viewer/format.js` `duration` / `quantity`, so a finding's
title and the pair drawn beside it read one string for one value.
"""


def duration(microseconds) -> str:
    """`471 ms`, `78.3 s`, `1.2 min`, `2.0 h` - the viewer's `duration`."""
    if microseconds is None:
        return "none"
    if microseconds < 0:
        return "-" + duration(-microseconds)
    s = microseconds / 1e6
    if s < 1:
        return f"{round(microseconds / 1000):.0f} ms"
    if s < 90:
        return f"{s:.1f} s"
    m = s / 60
    if m < 90:
        return f"{m:.1f} min"
    return f"{m / 60:.1f} h"


def seconds(value) -> str:
    """`duration` of a value held in seconds."""
    return "none" if value is None else duration(value * 1e6)


def share(fraction) -> str:
    """`42.4%` for a 0..1 fraction - the viewer's `share`."""
    return "none" if fraction is None else f"{fraction * 100:.1f}%"
