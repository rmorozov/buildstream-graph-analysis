"""UX-242 + UX-243: the two numbers that answer "can `--builders` go up"
are documented, including when they decline.

`UX-237` filed the rule these two came from, and round 28 was its first
application: three mechanisms whose only documentation was a docstring
or a payload note. Measured when they were filed:

```text
git grep -l capacity_recommendation docs/  -> three backlog files
git grep -l memory_envelope docs/          -> four backlog files
```

Both are the `--builders` question, and both are worth nothing to a
reader who cannot tell a *declined* answer from an absent feature: with
no Plane 2 report the lines are simply not printed, which looks
identical to a tool that has no such advice.

The guard checks three things a docstring cannot: that the guide names
each field, that it says under what conditions each declines, and that
the numbers it pastes are the ones the tool produces from the committed
run. The last is the half that rots — `UX-132` named it — and the run is
in the tree, so it is checkable rather than historical.
"""
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
GUIDE = REPO / "docs/guides/cli.md"
README = REPO / "README.md"
CHAPTER = "## How many builders, and what stops you"
SNAPSHOT = REPO / "examples/06-macro-micro-optimization/.bga/runs/20260821T170127Z"


def _flat(text):
    """`UX-244`: this repository hard-wraps prose, so any phrase worth
    checking can wrap and read as absent to a line-oriented search."""
    return re.sub(r"\s+", " ", text).replace("—", "-").lower()


def _chapter():
    text = GUIDE.read_text(encoding="utf-8")
    assert CHAPTER in text, f"docs/guides/cli.md has no {CHAPTER!r} chapter"
    return text.split(CHAPTER, 1)[1].split("\n## ", 1)[0]


def _section(name):
    """One field's subsection, so a claim about the memory envelope
    cannot be satisfied by a sentence about the capacity block."""
    chapter = _chapter()
    heads = [line for line in chapter.splitlines() if line.startswith("### ")]
    matching = [h for h in heads if name in h.lower()]
    assert len(matching) == 1, (
        f"expected one {name!r} subsection in {CHAPTER!r}, found {matching}")
    return chapter.split(matching[0], 1)[1].split("\n### ", 1)[0]


@pytest.fixture(scope="module")
def measured():
    """`bga analyze --plane2` on the committed snapshot, both fields."""
    import json
    from types import SimpleNamespace

    from bga.analyzer import BuildEfficiencyAnalyzer
    from bga.cli import _attach_plane2_capacity

    run = SNAPSHOT / "run"
    analyzer = BuildEfficiencyAnalyzer(verbose=False)
    analyzer.load(run)
    result = analyzer.analyze(run)
    _attach_plane2_capacity(
        SimpleNamespace(plane2=str(SNAPSHOT / "plane2.json")), analyzer, result)
    assert json  # the import is the reason the snapshot is readable at all
    return result


class TestTheFieldsAreNamedWhereTheQuestionIsAsked:
    @pytest.mark.parametrize("field", ["capacity_recommendation", "memory_envelope"])
    def test_an_instructional_document_names_the_field(self, field):
        """The acceptance test both items wrote: not a backlog file."""
        candidates = list((REPO / "docs/guides").glob("*.md")) + [README]
        instructional = sorted(
            path.name for path in candidates
            if field in path.read_text(encoding="utf-8"))
        assert instructional, (
            f"`{field}` is named in no instructional document - only in the "
            f"backlog and the source, which is what UX-237 filed the rule "
            f"about")

    def test_the_readme_sentence_about_peak_memory_points_somewhere(self):
        """`UX-243`: the README says peak memory "is what decides whether
        `--builders` can go up" and used to name no field, so a reader
        who believed the sentence had nowhere to go next."""
        text = _flat(README.read_text(encoding="utf-8"))
        where = text.index("decides whether `--builders`")
        assert "memory_envelope" in text[where:where + 400], (
            "the README's peak-memory sentence still names no field")


class TestEachOneSaysWhenItDeclines:
    """The failure mode both items name: a missing block is
    indistinguishable from a missing feature."""

    @pytest.mark.parametrize("name,needed", [
        ("capacity recommendation", ("--plane2", "declines")),
        ("memory envelope", ("--plane2", "declines")),
    ])
    def test_the_subsection_states_the_condition(self, name, needed):
        section = _flat(_section(name))
        missing = [phrase for phrase in needed if phrase not in section]
        assert missing == [], (
            f"the {name} subsection does not say {missing} - a reader "
            f"cannot tell a declined answer from an absent feature")

    def test_the_envelope_says_what_it_is_an_envelope_of(self):
        """`UX-243` clause 2: concurrent peak, not a sum of peaks, and
        why summing would be the wrong bound."""
        section = _flat(_section("memory envelope"))
        for phrase in ("largest measured per-element peaks", "upper bound",
                       "never held at the same moment"):
            assert phrase in section, (
                f"the memory-envelope subsection omits {phrase!r}")

    def test_the_envelope_names_its_unit(self):
        """Megabytes. A memory figure without a unit is a number."""
        assert "megabytes" in _flat(_section("memory envelope"))

    def test_the_recommendation_says_it_tries_no_configuration(self):
        """The caveat that makes it safe to quote: one capture in, one
        recommendation out."""
        section = _flat(_section("capacity recommendation"))
        for phrase in ("no configuration is tried", "does not model contention"):
            assert phrase in section, (
                f"the capacity-recommendation subsection omits {phrase!r}")


class TestThePastedFiguresAreTheToolsOwn:
    def test_the_snapshot_the_chapter_quotes_exists(self):
        assert (SNAPSHOT / "run").is_dir() and (SNAPSHOT / "plane2.json").is_file(), (
            f"the chapter quotes {SNAPSHOT}, which is not a dual-plane snapshot")

    def test_the_binding_constraint_is_what_the_tool_computes(self, measured):
        recommendation = measured.capacity_recommendation or {}
        assert recommendation, (
            "the committed snapshot no longer produces a capacity "
            "recommendation, so the chapter's worked example is stale")
        binding = recommendation["binding_constraint"]
        allows = recommendation["recommended_builders"]
        chapter = _flat(_chapter())
        assert f"{binding} binds at {allows}" in chapter, (
            f"the chapter's example does not say what the tool says today: "
            f"{binding} binds at {allows}")

    def test_every_constraint_line_is_one_the_tool_prints(self, measured):
        """Line for line, against the renderer's own reasons."""
        reasons = {c["reason"] for c in measured.capacity_recommendation["constraints"]}
        chapter = _flat(_chapter())
        stale = sorted(r for r in reasons if _flat(r) not in chapter)
        assert stale == [], (
            f"constraint reason(s) the tool prints and the chapter does not: "
            f"{stale}")

    def test_the_envelope_figures_are_the_tools_own(self, measured):
        envelope = measured.memory_envelope or {}
        assert envelope, (
            "the committed snapshot no longer produces a memory envelope")
        section = _flat(_section("memory envelope"))
        for key in ("host_memory_mb", "elements_measured"):
            assert str(envelope[key]) in section, (
                f"the memory-envelope subsection quotes no current value for "
                f"{key} ({envelope[key]})")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
