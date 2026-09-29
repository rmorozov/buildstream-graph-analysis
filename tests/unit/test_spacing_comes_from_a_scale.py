"""UX-1026: 23 distinct margin/padding/gap lengths in `style.css`, none
of them a token - type has four steps and drawings seven, spacing had
none.

Styleguide §6e.6's fix is an 8-step 4px scale (`--space-1` 4px to
`--space-8` 32px); every `margin`, `padding` and `gap` declaration now
resolves to one of those tokens (`var(--space-N)`, a `calc()` built
from them) or `0`. This file is the guard: read the source, not the
page - a bare length anywhere fails it.
"""

import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[2]
STYLE = REPO / "bga/viewer/style.css"

#: `margin`/`padding`/`gap` and their longhands (`margin-top`, ...).
PROP = re.compile(r'\b((?:margin|padding|gap)(?:-[a-z]+)?)\s*:\s*([^;]+);')

#: A bare length: a number followed by a CSS unit, not inside `var(...)`.
BARE_LENGTH = re.compile(r'(?<!--space-\d)\b\d*\.?\d+(?:rem|em|px)\b')


def _declarations():
    text = STYLE.read_text()
    return PROP.findall(text)


def _split_components(value):
    """Split a shorthand value on spaces outside any `(...)` group."""
    parts, depth, current = [], 0, ""
    for ch in value:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch.isspace() and depth == 0:
            if current:
                parts.append(current)
                current = ""
        else:
            current += ch
    if current:
        parts.append(current)
    return parts


def test_every_spacing_value_is_a_token_or_zero():
    offenders = []
    for prop, value in _declarations():
        for part in _split_components(value.strip()):
            if part in ("0", "auto"):
                continue
            if "var(--space-" in part and not BARE_LENGTH.search(part):
                continue
            offenders.append(f"{prop}: {value}")
    assert not offenders, f"non-token spacing values: {offenders}"


def test_the_scale_has_eight_four_pixel_steps():
    text = STYLE.read_text()
    for n, rem in enumerate(
        [".25rem", ".5rem", ".75rem", "1rem", "1.25rem", "1.5rem", "1.75rem", "2rem"],
        start=1,
    ):
        assert f"--space-{n}: {rem};" in text
