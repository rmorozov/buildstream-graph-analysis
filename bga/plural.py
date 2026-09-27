"""UX-1038: `1 element` / `2 elements` - the count and its noun in one
call, chosen by the count rather than spelled `(s)`.

Moved out of `bga/units.py`, which it shares no dimension with, so
`plural`'s own callers stop paying that module's size budget.
"""
from typing import Optional


def plural(count, noun: str, plural_noun: Optional[str] = None,
           shown: Optional[str] = None) -> str:
    """`shown` overrides how the count itself renders (e.g. a
    `:g`-formatted rate), for a caller whose count is not the plain
    integer to print. Reused from `bga/correlate.py`'s own `_count`
    (kept as an alias there) and named for `bga/viewer/tables.js`'s
    `plural`, the same idiom already in the codebase."""
    word = noun if count == 1 else (plural_noun or f"{noun}s")
    return f"{count if shown is None else shown} {word}"
