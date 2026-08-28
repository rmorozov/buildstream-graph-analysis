"""UX-341: one unit per dimension, and the boundaries where that starts.

The payload speaks **microseconds for time, bytes for memory, and 0..1
for a bounded fraction**. It used to speak three spellings of two of
those - `seconds` beside `duration_us`, `megabytes` and `kilobytes`
beside `bytes`, `percent` beside `share` - and every tail was derived
from its own head, usually by a lossy division of a value the tool
already held as an integer:

```text
bga/blast.py       micros / 1e6           an int, made a float, to be printed
bga/correlate.py   peak_rss_kb / 1024     KiB, exact, made a float
```

So the conversions live here, at the two places a figure crosses into
the payload from something that is not one of this tool's documents -
`run-context.json` records the host's RAM in MB, and Plane 2's record
reports `ru_maxrss` in KiB. Both are inputs with their own conventions
(`UX-343` covers what those cost); neither is rewritten by this item.
Everything downstream of these functions is in the payload's units.

The formatting constants are here for the same reason: a terminal line
that says "GB" divides by one number, named once, rather than by
`1024 / 1024` written out at nine call sites.
"""
from typing import Optional

#: Bytes in a kibibyte, mebibyte, gibibyte. Binary, because that is
#: what `ru_maxrss` and `/proc/meminfo` report and what a reader
#: comparing the two would otherwise have to guess.
KIB = 1024
MIB = 1024 * 1024
GIB = 1024 * 1024 * 1024

#: Microseconds in a second, for the terminal lines that still say "s".
US_PER_S = 1_000_000


def mb_to_bytes(value) -> Optional[int]:
    """A capture-side megabyte figure as bytes, or `None`.

    `None` in, `None` out: a host whose RAM was never recorded is not a
    host with no RAM, and the arithmetic downstream refuses on the
    absence rather than on a zero.
    """
    return None if value is None else int(value) * MIB


def kb_to_bytes(value) -> Optional[int]:
    """Plane 2's `ru_maxrss` (KiB) as bytes, or `None`.

    Exact and integral, which the megabyte float this replaced was not.
    """
    return None if value is None else int(value) * KIB


def s_to_us(value) -> Optional[int]:
    """A capture-side seconds figure as microseconds, or `None`.

    Rounded, not truncated: the input is a float of seconds and the
    payload is an integer count of microseconds, so the nearest one is
    the honest answer rather than the one that always reads low.
    """
    return None if value is None else int(round(float(value) * US_PER_S))
