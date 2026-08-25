"""UX-304: the palette validator, as an instrument rather than a
transcript.

Round 41 ran "the categorical validator" on the viewer's tokens and
reported two failures in prose - three of four dark tokens above the
mark-lightness band, and amber/green failing CVD separation in light.
Neither the tool nor its numbers were committed, so the next person to
change a token had a claim and no way to re-run it. This is the tool.

Everything here is standard and citable, so a disagreement is about
the values rather than about the arithmetic:

- **relative luminance** and **contrast ratio**: WCAG 2.1, the
  `(L1 + 0.05) / (L2 + 0.05)` definition, over linearised sRGB.
- **L\\***: CIE 1976 L*a*b* against D65, which is what "lightness band"
  means - a perceptual axis, not `#rrggbb` arithmetic.
- **ΔE2000**: CIE Delta E 2000, the current standard difference
  metric. Round 41's prose quotes ΔE 3.6 for the light amber/green
  pair under protanopia and this reads 6.5; the model and the metric
  it used are not recorded, so the number here is the one this
  repository can reproduce, and the finding - that the pair fails - is
  the same.
- **dichromat simulation**: Viénot, Brettel & Mollon (1999), the LMS
  projection, applied in linear light.

No dependencies: this runs in the same interpreter as every other
guard, and a validator that needed a wheel would be a validator nobody
runs.
"""
import math
import re

# D65, 2-degree observer.
WHITE = (0.95047, 1.0, 1.08883)


def channels(value):
    """`#abc` or `#aabbcc` as three 0..1 floats."""
    text = value.strip().lstrip("#")
    if len(text) == 3:
        text = "".join(c * 2 for c in text)
    if len(text) != 6 or not re.fullmatch(r"[0-9a-fA-F]{6}", text):
        raise ValueError(f"not a hex color: {value!r}")
    return tuple(int(text[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _linear(component):
    return (component / 12.92 if component <= 0.04045
            else ((component + 0.055) / 1.055) ** 2.4)


def _encode(component):
    component = min(1.0, max(0.0, component))
    return (12.92 * component if component <= 0.0031308
            else 1.055 * component ** (1 / 2.4) - 0.055)


def luminance(value):
    """WCAG relative luminance."""
    r, g, b = (_linear(c) for c in channels(value))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(one, other):
    """WCAG contrast ratio - 1.0 for identical, 21.0 for black on white."""
    a, b = luminance(one), luminance(other)
    high, low = max(a, b), min(a, b)
    return (high + 0.05) / (low + 0.05)


def _xyz(value):
    r, g, b = (_linear(c) for c in channels(value))
    return (0.4124 * r + 0.3576 * g + 0.1805 * b,
            0.2126 * r + 0.7152 * g + 0.0722 * b,
            0.0193 * r + 0.1192 * g + 0.9505 * b)


def lab(value):
    """CIE L*a*b* against D65."""
    def f(t):
        return t ** (1 / 3) if t > (6 / 29) ** 3 else t / (3 * (6 / 29) ** 2) + 4 / 29

    x, y, z = _xyz(value)
    fx, fy, fz = f(x / WHITE[0]), f(y / WHITE[1]), f(z / WHITE[2])
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def lightness(value):
    """L* alone - the axis the mark band is stated on."""
    return lab(value)[0]


def delta_e(one, other):
    """CIE ΔE2000."""
    l1, a1, b1 = lab(one)
    l2, a2, b2 = lab(other)
    c1, c2 = math.hypot(a1, b1), math.hypot(a2, b2)
    cbar = (c1 + c2) / 2
    g = 0.5 * (1 - math.sqrt(cbar ** 7 / (cbar ** 7 + 25 ** 7))) if cbar else 0.5
    a1p, a2p = (1 + g) * a1, (1 + g) * a2
    c1p, c2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360 if (a1p or b1) else 0.0
    h2p = math.degrees(math.atan2(b2, a2p)) % 360 if (a2p or b2) else 0.0

    dlp = l2 - l1
    dcp = c2p - c1p
    if c1p * c2p == 0:
        dhp = 0.0
    elif abs(h2p - h1p) <= 180:
        dhp = h2p - h1p
    elif h2p - h1p > 180:
        dhp = h2p - h1p - 360
    else:
        dhp = h2p - h1p + 360
    dhp_big = 2 * math.sqrt(c1p * c2p) * math.sin(math.radians(dhp) / 2)

    lbar = (l1 + l2) / 2
    cbarp = (c1p + c2p) / 2
    if c1p * c2p == 0:
        hbar = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hbar = (h1p + h2p) / 2
    elif h1p + h2p < 360:
        hbar = (h1p + h2p + 360) / 2
    else:
        hbar = (h1p + h2p - 360) / 2

    t = (1 - 0.17 * math.cos(math.radians(hbar - 30))
         + 0.24 * math.cos(math.radians(2 * hbar))
         + 0.32 * math.cos(math.radians(3 * hbar + 6))
         - 0.20 * math.cos(math.radians(4 * hbar - 63)))
    theta = 30 * math.exp(-(((hbar - 275) / 25) ** 2))
    rc = 2 * math.sqrt(cbarp ** 7 / (cbarp ** 7 + 25 ** 7)) if cbarp else 0.0
    sl = 1 + (0.015 * (lbar - 50) ** 2) / math.sqrt(20 + (lbar - 50) ** 2)
    sc = 1 + 0.045 * cbarp
    sh = 1 + 0.015 * cbarp * t
    rt = -math.sin(math.radians(2 * theta)) * rc
    return math.sqrt((dlp / sl) ** 2 + (dcp / sc) ** 2 + (dhp_big / sh) ** 2
                     + rt * (dcp / sc) * (dhp_big / sh))


# Viénot, Brettel & Mollon (1999). Hunt-Pointer-Estevez LMS for sRGB
# primaries, the dichromat projection, and back.
_TO_LMS = ((17.8824, 43.5161, 4.11935),
           (3.45565, 27.1554, 3.86714),
           (0.0299566, 0.184309, 1.46709))
_FROM_LMS = ((0.0809444479, -0.130504409, 0.116721066),
             (-0.0102485335, 0.0540193266, -0.113614708),
             (-0.000365296938, -0.00412161469, 0.693511405))
KINDS = ("protan", "deutan", "tritan")


def simulate(value, kind):
    """`value` as a dichromat of `kind` sees it."""
    if kind not in KINDS:
        raise ValueError(f"unknown dichromacy: {kind!r}")
    r, g, b = (_linear(c) for c in channels(value))
    lms = [sum(row[i] * c for i, c in enumerate((r, g, b))) for row in _TO_LMS]
    long, medium, short = lms
    if kind == "protan":
        long = 2.02344 * medium - 2.52581 * short
    elif kind == "deutan":
        medium = 0.494207 * long + 1.24827 * short
    else:
        short = -0.395913 * long + 0.801109 * medium
    out = [sum(row[i] * c for i, c in enumerate((long, medium, short)))
           for row in _FROM_LMS]
    return "#" + "".join(f"{round(_encode(c) * 255):02x}" for c in out)


_DECLARATION = re.compile(r"--([\w-]+)\s*:\s*(#[0-9a-fA-F]{3,6})\s*;")


def token_sets(css):
    """The declared token sets, keyed by the block that declares them.

    Returns `{"root": {...}, "light": {...}, "print": {...}}` - the
    base `:root`, and one per media override. Parsed rather than
    hardcoded, so a block renamed here reddens instead of quietly
    dropping out of validation.
    """
    sets = {}
    head, _, _ = css.partition("* { box-sizing")
    base = head.split(":root {", 1)[1].split("}", 1)[0]
    sets["root"] = dict(_DECLARATION.findall(base))
    for name, marker in (("light", "@media (prefers-color-scheme: light)"),
                         ("print", "@media print")):
        if marker not in head:
            continue
        block = head.split(marker, 1)[1].split(":root {", 1)[1].split("}", 1)[0]
        sets[name] = dict(_DECLARATION.findall(block))
    return sets
