"""UX-273: the rule that decides how every nested value is drawn is in
the chapter a schema author reads, and its thresholds are named rather
than copied.

Found by review 2 (`UX-241`). Round 36 gave the viewer a rule that
governs every object- or array-valued field in every published schema -
inline, bounded table, or fold, chosen by width - and measured on the
day it was filed it lived in exactly one place:

```text
$ git grep -c "width, not depth" -- docs/
docs/backlog/scenarios/UX-0267-...md:1
```

The architecture's viewer chapter described the *hint* half of
schema-driven rendering in detail and said nothing about what becomes of
a field's value, so a maintainer adding a schema field learned that it
was free and did not learn that its shape decides its rendering.

The second half of this guard is the one with teeth. The chapter must
name the thresholds as **exported constants**, not restate `4`, `6` and
`160`, because a document that repeats a number is a second copy that a
later round moves without it. Both directions are checked: every
constant this rule rests on is named, and every constant named still
exists in the module.
"""
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
ARCHITECTURE = REPO / "docs/design/architecture.md"
APP = REPO / "bga/viewer/app.js"
CHAPTER = "## The viewer axis"

# The three the rule is expressed in. Each decides one of the three
# renderings, so a chapter naming two of them describes a rule with a
# branch missing.
THRESHOLDS = ("OBJECT_INLINE_FIELDS", "ARRAY_INLINE_ITEMS", "CELL_TEXT_CAP")


def _flat(text):
    return re.sub(r"\s+", " ", text).replace("—", "-")


def _chapter():
    text = ARCHITECTURE.read_text(encoding="utf-8")
    assert CHAPTER in text, f"architecture.md has no {CHAPTER!r} chapter"
    return _flat(text.split(CHAPTER, 1)[1].split("\n## ", 1)[0])


def _exported_constants():
    """What `bga/viewer/app.js` actually exports as a number."""
    source = APP.read_text(encoding="utf-8")
    return {name: value for name, value in
            re.findall(r"^export const ([A-Z_]+) = (\d+);", source, re.M)}


class TestTheRuleIsWhereASchemaAuthorReads:
    def test_the_viewer_chapter_states_the_rule(self):
        chapter = _chapter()
        assert "width, not depth" in chapter, (
            "the architecture's viewer chapter describes the view-hints and "
            "not what becomes of a field's value - the rule UX-267 shipped "
            "governs every object- or array-valued field in every schema")

    def test_it_names_all_three_renderings(self):
        """A rule with one branch described is a rule a reader will
        guess the rest of."""
        chapter = _chapter().lower()
        for rendering in ("inline", "table", "fold"):
            assert rendering in chapter, (
                f"the value rule is stated without naming the {rendering!r} "
                f"case")

    def test_it_says_depth_is_not_the_criterion(self):
        """The half a reader gets wrong on their own: nesting looks like
        the obvious criterion and is not the one."""
        assert "Depth is deliberately not the criterion" in _chapter(), (
            "the chapter states the rule without saying what it is a rule "
            "*instead of*")


class TestTheThresholdsAreNamedAndNotCopied:
    @pytest.mark.parametrize("constant", THRESHOLDS)
    def test_the_chapter_names_the_constant(self, constant):
        assert constant in _chapter(), (
            f"the value rule is stated without naming {constant}, so a "
            f"reader cannot find the threshold it rests on")

    @pytest.mark.parametrize("constant", THRESHOLDS)
    def test_the_constant_exists(self, constant):
        """The other direction: a document pointing at a name the module
        no longer exports is worse than one that repeated the number,
        because it reads as checkable and is not."""
        assert constant in _exported_constants(), (
            f"the architecture names {constant}, which bga/viewer/app.js "
            f"does not export as a number")

    def test_the_chapter_does_not_restate_the_numbers(self):
        """The reason clause 2 asked for names: a copied number is a
        second copy of a fact, and this repository has spent whole
        rounds on those (`UX-132`). Checked as a *threshold claim* -
        `4 fields`, `160 characters` - rather than by banning the digits,
        which would fail on `UX-267` and on round 36."""
        chapter = _chapter()
        restated = [
            phrase for phrase in re.findall(
                r"\b(\d+)\s+(?:fields?|items?|entries|characters?|chars?)\b",
                chapter)
            if phrase in set(_exported_constants().values())
        ]
        assert restated == [], (
            f"the chapter restates threshold value(s) {restated} that the "
            f"exported constants already carry - name the constant instead")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
