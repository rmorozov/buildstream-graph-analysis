"""UX-596: build seconds in the unit the reader argues in.

R8 funds infrastructure and argues in engineer-hours or in currency;
every price `bga` prints is in build seconds. The conversion is one
multiplication, which is why this is an item about honesty rather than
about arithmetic.

**No default rate.** A made-up rate presented as a figure is the
anecdote this replaces, so with nothing supplied the report is
unchanged and the block is absent rather than empty or zeroed.

**Every converted figure names the rate that converted it**, inline. A
converted figure travels alone - pasted into an issue, screenshotted
into a deck - and one that arrived without its rate reads as something
this tool measured.

**Not in the payload.** The rate is the reader's input, not this run's
measurement, so writing it into `analyze/v5` would put an input inside a
schema-described record of what was observed. The seconds are published;
the multiplication is a rendering.

**Supplied through the environment.** `bga analyze --help` is at the
45-line cap `UX-158` measured, so a flag would have had to move that
budget; `BGA_RATE` costs no help line and is set once in a CI config.
"""
import os
import re
from typing import Optional

ENV_VAR = "BGA_RATE"

# `<amount> <unit>/<denominator>`. Two denominators, both an hour of
# this build's wall clock, kept apart because they are different
# arguments: what the runner cost, and what the wait cost.
DENOMINATORS = ("machine-hour", "build-hour")

_GRAMMAR = re.compile(
    r"^\s*(-?[0-9]+(?:\.[0-9]+)?)\s+([^/\s]+)\s*/\s*([a-z-]+)\s*$")

_EXAMPLE = "90 USD/machine-hour"


def parse(text: str) -> dict:
    """The supplied string, or an `error` saying why it was not used.

    A malformed rate is **named, not swallowed**: silence here is
    indistinguishable from no rate at all, and a reader who set one and
    got the unconverted report would have no way to learn why.
    """
    match = _GRAMMAR.match(text or "")
    if not match:
        return {"error": f"{ENV_VAR}={text!r} is not "
                         f"`<amount> <unit>/<{'|'.join(DENOMINATORS)}>` "
                         f"(for example `{_EXAMPLE}`)"}
    amount, unit, per = match.group(1), match.group(2), match.group(3)
    if per not in DENOMINATORS:
        return {"error": f"{ENV_VAR}={text!r} is per {per!r}; this converts "
                         f"build seconds, so the denominator has to be one "
                         f"of {', '.join(DENOMINATORS)}"}
    if float(amount) <= 0:
        return {"error": f"{ENV_VAR}={text!r} is not a positive rate"}
    return {"amount": float(amount), "unit": unit, "per": per,
            "text": f"{amount} {unit}/{per}"}


def supplied(environ=None) -> Optional[dict]:
    """The reader's rate, or `None` when they supplied none."""
    raw = (environ if environ is not None else os.environ).get(ENV_VAR)
    return parse(raw) if raw else None


def convert(duration_us: float, rate: dict) -> float:
    return duration_us / 3_600_000_000 * rate["amount"]


def _amount(value: float) -> str:
    return f"{value:,.2f}" if abs(value) >= 0.01 else f"{value:.3g}"


def phrase(duration_us: float, rate: dict) -> str:
    """The converted figure with the rate that converted it, welded on.

    One function, so no surface can print half of it - which is the
    whole guard this item asks for.
    """
    return (f"{_amount(convert(duration_us, rate))} {rate['unit']} "
            f"at {rate['text']}")


def preamble(rate: dict) -> str:
    return (f"rate: {rate['text']} - an input you supplied ({ENV_VAR}), not "
            f"anything this run measured")
