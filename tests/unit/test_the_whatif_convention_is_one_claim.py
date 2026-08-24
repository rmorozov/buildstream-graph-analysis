"""UX-244: what "fixed" means is published in three places and must
mean the same thing in all three.

`bga whatif` publishes a projected makespan, and a figure travels
further than its payload - into a slide, a ticket, a meeting. What
"fixed" means is the difference between a bound and a lie, so the
convention is carried by the answer itself (`bga/whatif.py`'s
`CONVENTION`), stated in the guide a reader learns the command from
(`docs/guides/cli.md`), and *reasoned about* in the architecture. Three
hand-maintained copies of one claim is exactly the shape this
repository keeps finding drifted.

The guard normalises whitespace before matching, and that is not
tidiness. `UX-244` was filed on this measurement:

```text
git grep -l "upper bound, not a forecast" docs/    -> (nothing)
```

which was a **false negative**: the guide had carried the sentence
since the commit that shipped `UX-230`, hard-wrapped as

```text
durations, with nothing else assumed to change - an upper bound, not a
forecast. The convention travels in every answer.
```

`git grep` is line-oriented and this repository's prose is hard-wrapped
at 72 columns, so any phrase long enough to matter can wrap and read as
absent. A guard that repeated that mistake would report the convention
missing on the day someone reflowed a paragraph.
"""
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
GUIDE = REPO / "docs/guides/cli.md"
ARCHITECTURE = REPO / "docs/design/architecture.md"

# Each claim, and the phrases that carry it. Phrases rather than one
# sentence, because the three copies are deliberately in three
# registers - the payload's, the guide's and the architecture's - and a
# guard that demanded one wording would force them to become one
# wording, which is the copy-paste this repository argues against.
CLAIMS = {
    "fixed means instant": ("fixed", "instant"),
    "over this run's measured durations": ("measured durations",),
    "a bound and not a forecast": ("upper bound", "not a forecast"),
}


def _flat(text):
    """One line, lower case, dashes normalised.

    The three things that differ between the copies and must not:
    where the line breaks, whether the dash is `-` or an em dash, and
    the capital on "Fixed" at the start of a sentence.
    """
    return re.sub(r"\s+", " ", text).replace("—", "-").lower()


def _convention():
    from bga import whatif

    return _flat(whatif.CONVENTION)


def _guide_section():
    """The `whatif` section of the guide, not the whole guide.

    The whole guide names `whatif` in a dozen places; the claim has to
    be where the command is taught."""
    text = GUIDE.read_text(encoding="utf-8")
    marker = "### Choosing the fixes"
    assert marker in text, f"{GUIDE.name} has no {marker!r} section"
    return _flat(text.split(marker, 1)[1].split("\n### ", 1)[0])


class TestTheClaimTravelsWithTheNumber:
    @pytest.mark.parametrize("claim", sorted(CLAIMS))
    def test_the_payload_carries_it(self, claim):
        """The convention is published with every answer, so a consumer
        that never reads a document still has it."""
        missing = [p for p in CLAIMS[claim] if p not in _convention()]
        assert missing == [], (
            f"`bga/whatif.py`'s CONVENTION no longer carries "
            f"{claim!r}: {missing} absent")

    @pytest.mark.parametrize("claim", sorted(CLAIMS))
    def test_the_guide_carries_it(self, claim):
        """And the reader who learns the command from the guide has it
        before they ever run it."""
        missing = [p for p in CLAIMS[claim] if p not in _guide_section()]
        assert missing == [], (
            f"docs/guides/cli.md's whatif section no longer carries "
            f"{claim!r}: {missing} absent")


class TestTheReasoningHasAHome:
    """The guide states the convention; the architecture is where a
    reader finds out *why* it is a bound, which is the half that cannot
    be reconstructed from the output."""

    def _chapter(self):
        text = ARCHITECTURE.read_text(encoding="utf-8")
        marker = "## What a projection is, and why it is a bound"
        assert marker in text, (
            "architecture.md records no reasoning behind the what-if bound")
        return _flat(text.split(marker, 1)[1].split("\n## ", 1)[0])

    def test_it_says_a_sum_is_wrong(self):
        chapter = self._chapter()
        assert "never a sum" in chapter or "not a sum" in chapter, (
            "the chapter does not say the projection is not a sum of "
            "per-element savings")

    def test_it_gives_both_directions(self):
        """One direction is a rule of thumb; two is the reason the
        simulation exists. `UX-74` measured both on one capture, and
        they are the opposite of the intuition: same chain adds,
        different chains take a maximum."""
        chapter = self._chapter()
        for phrase in ("same chain", "different chains", "maximum"):
            assert phrase in chapter, (
                f"the chapter omits {phrase!r} - it states one direction "
                f"of the joint-saving arithmetic, not both")

    def test_it_is_measured_rather_than_asserted(self):
        """`UX-74`'s figures, because a claim about arithmetic that
        carries no numbers is the kind a reader has to take on faith."""
        chapter = self._chapter()
        for figure in ("1569.8", "2605.8"):
            assert figure in chapter, (
                f"the chapter argues the arithmetic without {figure}s, "
                f"the measurement UX-74 made")


class TestTheGuardDoesNotRepeatTheFilingsMistake:
    def test_a_wrapped_phrase_is_still_found(self):
        """The whole reason `_flat` exists. This is the exact shape the
        item was filed on - `git grep` for the phrase returned nothing
        while the guide carried it, hard-wrapped."""
        wrapped = "with nothing else assumed to change - an upper bound, not a\nforecast."
        assert "upper bound, not a forecast" not in wrapped, (
            "the fixture is no longer wrapped, so it tests nothing")
        assert "upper bound, not a forecast" in _flat(wrapped)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
