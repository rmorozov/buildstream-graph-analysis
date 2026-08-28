"""UX-304: dark first, two grades of token, and a validator that runs.

The page was authored light-first with a dark media override, and the
reader it was built for reads dark. Round 41 ran a palette validator
and reported two failures in prose — three of four dark tokens above
the mark-lightness band, and amber↔green failing CVD separation in
light — but neither the tool nor its numbers were committed, so the
next person to touch a token had a claim and no way to re-run it.

`tests/palette.py` is that tool now: WCAG relative luminance and
contrast, CIE L*, ΔE2000, and the Viénot/Brettel/Mollon dichromat
projection, all from the standards and with no dependency. What it
measures on the tokens as committed:

```text
dark surface #161616                 L*   contrast   band 45..70
  --warn-mark   #c5922f            63.9       6.49   in
  --bad-mark    #db6868            58.0       5.34   in
  --good-mark   #4dae6b            64.1       6.53   in
  --accent-mark #6c97d9            61.9       6.09   in
  (before, the text-grade values did the filling)
  --warn        #d9a441            70.7       8.05   over
  --good        #6fcf8a            76.0       9.45   over
  --accent      #8ab4f8            72.8       8.59   over
  --bad         #e06c6c            59.6       5.63   in

light surface #ffffff                L*   contrast   band 35..60
  --warn-mark   #9a6400            47.0       5.00   in
  --bad-mark    #aa1111            36.0       7.51   in
  --good-mark   #176b2c            39.4       6.61   in
  --accent-mark #2b5797            37.0       7.21   in
```

**Three of four dark tokens over the band, one inside** — round 41's
finding, reproduced here by a tool that is in the repository. The
light set needed no change at all, which is the argument for
validating per surface instead of flipping one palette into the other:
the light values had been looked at and the dark ones had not.

The CVD numbers this palette actually has, as ΔE2000 between adjacent
status hues under each dichromacy (round 41's prose says ΔE 3.6 for
the light amber/green pair; its model and metric are not recorded and
this reads 6.5 — the finding is the same and the number here is the
reproducible one):

```text
light   warn/good   protan   6.5      dark   good/accent  tritan  2.4
        bad/good    deutan   8.2             bad/good     deutan  9.5
        warn/bad    tritan   2.3             warn/bad     tritan  4.1
```

Which is *why* §4.3 exists rather than a thing to fix by picking
better hues: no ordering of four status hues clears every dichromacy,
so a status tone never travels alone.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tests"))
import palette                                          # noqa: E402

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")
CSS_PATH = REPO / "bga" / "viewer" / "style.css"
CSS = CSS_PATH.read_text(encoding="utf-8")
SETS = palette.token_sets(CSS)

STATUS = ("warn", "bad", "good", "accent")

# The band, per surface. Stated here and in `style.css`'s own comment
# because it is the rule a token change is measured against: a fill
# must clear its surface (WCAG 1.4.11's 3:1) and must not climb into
# the range where it reads as text, which is what round 41 measured
# going wrong.
BANDS = {"root": (45.0, 70.0), "light": (35.0, 60.0), "print": (35.0, 60.0)}
MARK_CONTRAST = 3.0                                     # WCAG 1.4.11
TEXT_CONTRAST = 4.5                                     # WCAG 1.4.3


class TestDarkIsTheDesignSurface:
    def test_root_carries_the_dark_set(self):
        """Not "there is a dark block somewhere" — the *base* is dark.

        Read as a property of the value rather than of the block's
        position, so moving the declarations around cannot pass it.
        """
        assert palette.lightness(SETS["root"]["bg"]) < 20, (
            f'`:root` --bg is {SETS["root"]["bg"]}, L* '
            f'{palette.lightness(SETS["root"]["bg"]):.1f} — that is a light '
            f"surface, and this item made dark the base")
        assert palette.lightness(SETS["root"]["fg"]) > 80

    def test_light_is_the_override_and_holds_every_token(self):
        assert set(SETS["light"]) == set(SETS["root"]), (
            "the light override and `:root` declare different tokens: "
            f"{set(SETS['root']) ^ set(SETS['light'])}")
        assert palette.lightness(SETS["light"]["bg"]) > 90

    def test_an_unset_browser_still_gets_light(self):
        """`prefers-color-scheme: light` matches a reader who expressed
        no preference, so the default did not move when the base did.
        Guarded on the media query's spelling, because
        `prefers-color-scheme: dark` here would silently flip every
        unset browser to the new base."""
        assert "@media (prefers-color-scheme: light)" in CSS
        assert "@media (prefers-color-scheme: dark)" not in CSS

    def test_print_renders_light_on_white(self):
        """Dark-first, not dark-only: the export is printed, and a dark
        page prints as a black rectangle or as nothing."""
        assert "@media print" in CSS
        assert set(SETS["print"]) == set(SETS["root"])
        assert SETS["print"] == SETS["light"], (
            "print and light disagree on a token value: "
            + str({k: (SETS['print'][k], SETS['light'][k])
                   for k in SETS['print']
                   if SETS['print'][k] != SETS['light'][k]}))


class TestTheTwoGradesAreValidated:
    """The item's central clause, and the reason `tests/palette.py`
    exists: every value is measured against the surface it is used on,
    and the numbers are in the failure message so a change is a
    measurement rather than an argument."""

    @pytest.mark.parametrize("theme", ["root", "light", "print"])
    @pytest.mark.parametrize("name", STATUS)
    def test_mark_grade_sits_in_its_band(self, theme, name):
        tokens = SETS[theme]
        value = tokens[f"{name}-mark"]
        low, high = BANDS[theme]
        star = palette.lightness(value)
        assert low <= star <= high, (
            f"{theme} --{name}-mark {value} is L* {star:.1f}, outside the "
            f"{low}..{high} band for that surface")
        ratio = palette.contrast(value, tokens["bg"])
        assert ratio >= MARK_CONTRAST, (
            f"{theme} --{name}-mark {value} is {ratio:.2f}:1 against "
            f"{tokens['bg']}, under WCAG 1.4.11's {MARK_CONTRAST}:1")

    @pytest.mark.parametrize("theme", ["root", "light", "print"])
    @pytest.mark.parametrize("name", STATUS)
    def test_text_grade_is_readable(self, theme, name):
        tokens = SETS[theme]
        value = tokens[name]
        ratio = palette.contrast(value, tokens["bg"])
        assert ratio >= TEXT_CONTRAST, (
            f"{theme} --{name} {value} is {ratio:.2f}:1 against "
            f"{tokens['bg']}, under WCAG 1.4.3's {TEXT_CONTRAST}:1")

    def test_the_band_would_have_caught_the_old_dark_values(self):
        """The clause that proves the band discriminates.

        These are the four dark tokens as they stood before this item —
        the text-grade values, which were also the fill values. Three
        are over the band's ceiling, which is round 41's finding; if
        this passed, the band would be a range that forbids nothing.
        """
        low, high = BANDS["root"]
        before = {"warn": "#d9a441", "bad": "#e06c6c",
                  "good": "#6fcf8a", "accent": "#8ab4f8"}
        over = {name: round(palette.lightness(value), 1)
                for name, value in before.items()
                if palette.lightness(value) > high}
        assert over == {"warn": 70.7, "good": 76.0, "accent": 72.8}, over

    def test_the_two_grades_are_not_the_same_colour_on_dark(self):
        """Otherwise the split is a rename. Light's grades *are* equal,
        deliberately — its values already validated — so this is asked
        of the surface the item retuned."""
        same = [name for name in STATUS
                if SETS["root"][name] == SETS["root"][f"{name}-mark"]]
        assert same == ["", ][:0] or not same, (
            f"dark --{same} and its mark grade are the same value")


class TestNoColourLivesOutsideTheStylesheet:
    """§4.5: a new color is a token with a stated job, in `style.css`,
    or it does not exist."""

    HEX = re.compile(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b")

    def _sources(self):
        for path in sorted((REPO / "bga" / "viewer").iterdir()):
            if path.suffix in {".js", ".html"}:
                yield path
        for path in sorted((REPO / "tools").glob("*.py")):
            yield path
        for path in sorted((REPO / "bga").glob("*.py")):
            yield path

    def test_no_hex_literal_outside_style_css(self):
        found = []
        for path in self._sources():
            for line in path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped.startswith(("#", "//", "*", '"""', "'''")):
                    continue    # a comment or a docstring, not a value
                for match in self.HEX.findall(line):
                    found.append(f"{path.relative_to(REPO)}: {match}")
        assert not found, (
            "hex color outside `bga/viewer/style.css` — it must be a "
            "token with a stated job:\n  " + "\n  ".join(found))


def _rules():
    """Every CSS rule, as `(selector, declarations)`, comments removed."""
    body = re.sub(r"/\*.*?\*/", "", CSS, flags=re.S)
    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", body):
        yield " ".join(match.group(1).split()), " ".join(match.group(2).split())


class TestFillsUseMarkGradeAndTextUsesTextGrade:
    """The split has to reach the rules, or it is two tokens and one
    habit. Read off the stylesheet: a declaration that *fills* (fill,
    background, stroke) must name a mark-grade token, and one that
    *reads* (color) must name a text-grade one."""

    FILLING = re.compile(r"(?:^|;\s*)(fill|background|background-color|stroke)\s*:")

    def test_every_fill_names_a_mark_token(self):
        loose = []
        for selector, decls in _rules():
            for piece in decls.split(";"):
                property_, _, value = piece.partition(":")
                if property_.strip() not in {"fill", "background",
                                             "background-color", "stroke"}:
                    continue
                bare = re.findall(r"var\(--(warn|bad|good|accent)\)", value)
                if bare:
                    loose.append(f"{selector} {{ {piece.strip()} }}")
        assert not loose, (
            "a fill using a text-grade token — that is the failure "
            "round 41 measured:\n  " + "\n  ".join(loose))

    def test_every_text_colour_names_a_text_token(self):
        loose = []
        for selector, decls in _rules():
            for piece in decls.split(";"):
                property_, _, value = piece.partition(":")
                if property_.strip() != "color":
                    continue
                if re.search(r"var\(--(warn|bad|good|accent)-mark\)", value):
                    loose.append(f"{selector} {{ {piece.strip()} }}")
        assert not loose, (
            "text wearing a mark-grade token:\n  " + "\n  ".join(loose))


class TestStatusToneIsNeverAlone:
    """§4.3, page-wide. Every rule that tints something with a status
    tone is listed here with the non-color channel that travels with
    it, and the list is checked in both directions — a new toned rule
    reddens, and so does an entry whose rule is gone."""

    CHANNELS = {
        # The block's own `<h2>` says what the verdict is, and
        # `data-incomplete` / `data-warning` carry it as data.
        ".verdict.refused": "the heading names the state",
        ".verdict.warn": "the heading names the state",
        ".verdict.good": "the heading names the state",
        # `data-severity` is the channel, and `.badge` prints it.
        '.finding[data-severity="critical"], .finding[data-severity="high"]':
            "data-severity, printed in the badge",
        '.finding[data-severity="warning"], .finding[data-severity="medium"]':
            "data-severity, printed in the badge",
        '.finding[data-severity="info"], .finding[data-severity="low"]':
            "data-severity, printed in the badge",
        # `UX-356`: the join's own advice, at the same grade and with
        # the same channel - `data-severity` on the block, the word
        # printed in the badge beside the sentence.
        '.advice[data-severity="critical"], .advice[data-severity="high"]':
            "data-severity, printed in the badge",
        '.advice[data-severity="warning"], .advice[data-severity="medium"]':
            "data-severity, printed in the badge",
        '.advice[data-severity="info"], .advice[data-severity="low"]':
            "data-severity, printed in the badge",
        # `UX-305`: the tone moved off the value and onto the marker
        # beside it (§4.4). The glyph is the channel, and the value
        # still carries its sign.
        '.delta-mark[data-direction="better"]': "the marker glyph, and "
                                                "the signed value",
        '.delta-mark[data-direction="worse"]': "the marker glyph, and "
                                               "the signed value",
        # `UX-212`'s markers, from the schema.
        ".trend-point.aliased": "data-marker",
        ".trend-point.incomplete": "data-marker",
        ".trend-point.verdict-regressed": "data-marker",
        ".trend-point.verdict-improved": "data-marker",
        '.band[data-disputed="true"] .candidate': "data-disputed, and the "
                                                  "band's own sentence",
        # `UX-304` gave this one its channel: it had only the tone.
        "th .th-filter.unparsed": "border-style: dashed, aria-invalid, title",
    }

    def _toned(self):
        """A rule is *status-toned* if it paints with good/warn/bad, or
        if it keys off `data-severity` at all.

        The second half matters: the lowest severity is drawn in the
        one accent rather than in a status hue, and a reader still has
        to be able to tell an `info` finding from a `high` one without
        seeing the border.
        """
        toned = {}
        for selector, decls in _rules():
            if (re.search(r"var\(--(warn|bad|good)(-mark)?\)", decls)
                    or "data-severity" in selector):
                toned[selector] = decls
        return toned

    def test_every_toned_rule_names_its_channel(self):
        unlisted = sorted(set(self._toned()) - set(self.CHANNELS))
        assert not unlisted, (
            "a rule tints with a status tone and names no non-color "
            "channel (§4.3):\n  " + "\n  ".join(unlisted))

    def test_the_list_has_no_dead_entries(self):
        gone = sorted(set(self.CHANNELS) - set(self._toned()))
        assert not gone, (
            "listed as toned, but no such rule any more:\n  "
            + "\n  ".join(gone))

    def test_the_dashed_border_is_really_there(self):
        """The one channel this item added, asserted on the rule rather
        than on the promise above."""
        rule = dict(_rules())["th .th-filter.unparsed"]
        assert "border-style: dashed" in rule, rule


_PROBE = r"""
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;
globalThis.document = { createElement: _makeNode,
                        createElementNS: (_n, t) => _makeNode(t),
                        getElementById: () => null };
const app = await import("./tests/viewer.mjs");

// The findings block and a delta cell, built directly - the two toned
// controls a golden run really renders.
const findings = app.renderFindings([
  { severity: "critical", title: "Serial chain", detail: "three deep" },
  { severity: "low", title: "Small", detail: "noted" },
]);
// `renderPairs` is what draws a signed change: the direction hint is
// declared on the *object*, which is how `compare/v1` publishes its
// deltas.
const deltasBlock = app.renderPairs("deltas",
  { total_duration_us: 4000, build_us: -2000 },
  { "bga:direction": "lower_is_better", "bga:quantity": "duration_us" });

const all = (n, pred, out = []) => {
  if (pred(n)) out.push(n);
  for (const c of n.children ?? []) all(c, pred, out);
  return out;
};
const text = (n) => !n ? "" : ((n.children ?? []).length
  ? (n._text ?? "") + n.children.map(text).join("") : (n._text ?? ""));

const toned = all(findings, (n) => (n.attrs.class || "").includes("finding")
                                   && n.attrs["data-severity"]);
// The value cells, not the markers inside them.
const deltas = all(deltasBlock, (n) =>
  (n.attrs.class || "").split(/\s+/).includes("delta"));
const marks = all(deltasBlock, (n) => n.attrs["data-direction"])
  .map((n) => [n.attrs["data-direction"], text(n)]);
console.log(JSON.stringify({
  findings: toned.map((n) => ({ severity: n.attrs["data-severity"],
                                text: text(n) })),
  deltas: deltas.map((n) => text(n)),
  marks,
}));
"""


@needs_node
class TestTheChannelsAreOnThePage:
    """And the channels are not only in the stylesheet's comments —
    the rendered elements carry them."""

    @classmethod
    @pytest.fixture(scope="class")
    def rendered(cls):
        result = subprocess.run(
            [node, "--input-type=module", "-e", _PROBE],
            capture_output=True, text=True, cwd=REPO, timeout=60,
            env=dict(os.environ,
                     BGA_DOM_SHIM=str(REPO / "tests" / "dom_shim.mjs")))
        assert result.returncode == 0, result.stderr[-3000:]
        return json.loads(result.stdout)

    def test_a_finding_carries_its_severity_as_data_and_as_text(self, rendered):
        assert rendered["findings"], "no findings rendered"
        for finding in rendered["findings"]:
            assert finding["severity"], finding
            assert finding["severity"].lower() in finding["text"].lower(), (
                f"severity {finding['severity']!r} is a border colour and "
                f"nothing else in: {finding['text'][:120]!r}")

    def test_a_delta_carries_its_sign_and_its_marker(self, rendered):
        """Two channels, neither of them colour: the sign in the value,
        and `UX-212`'s glyph on the marker beside it."""
        assert rendered["deltas"], "no delta cells rendered"
        signs = {value.replace("\u25be", "").replace("\u25b4", "").strip()[0]
                 for value in rendered["deltas"] if value.strip()}
        assert signs == {"+", "-"}, (
            f"a delta's direction is colour only: {rendered['deltas']}")
        assert dict(rendered["marks"]) == {"better": "\u25be",
                                           "worse": "\u25b4"}, rendered["marks"]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
