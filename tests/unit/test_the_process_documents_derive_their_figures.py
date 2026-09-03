"""UX-584: the counted figures in the process layer, read off the tree.

`UX-471` removed `CLAUDE.md`'s file count and `UX-549` derived five
figures in the guides. Neither reached the documents that steer a
session. Measured when this was filed (round 83, `5b4c05f`):

```text
fixing-guide.md:96    analyze/v2, compare/v1, blast/v1   schemas.py: v5/v2/v2
fixing-guide.md:105   Part 32 spans 1515-1788            1515-1888
rules.md:6 · guide:6  the guide is 34 KB                 40,796 B
researcher.md:5,19    421 task files                     589
verify SKILL.md:130   380 files in ci_reference          426
decompose SKILL.md:51 "Three files are shared", four paths listed
release-guide.md:23   twelve independent contracts       23 ids, 14 live
style-guide.md:15     "Two of them are enforced by test" four say so
```

Two instruments: `TestTheFiguresAreDerived` recomputes each figure from
its population (`UX-549`'s shape), and `TestNoBareCountSurvives` bans
the shape across the layer, so the *next* one reddens before a review
finds it. The scan reads **sentences**, and not the word `one` - "one
file per claim" is idiomatic, and banning it bans what these documents
are for.
"""
import functools
import json
import pathlib
import re
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import contracts, schemas  # noqa: E402

RULES = REPO / "docs/contributing/rules.md"
GUIDE = REPO / "docs/contributing/fixing-guide.md"
STYLE = REPO / "docs/contributing/style-guide.md"
DECOMPOSE = REPO / ".claude/skills/decompose/SKILL.md"
SPEC = REPO / "docs/spec/specification.md"

#: How these documents spell a count. `one` is deliberately absent -
#: see the module docstring.
WORDS = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven",
         8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve",
         13: "thirteen", 14: "fourteen", 15: "fifteen", 16: "sixteen",
         17: "seventeen", 18: "eighteen", 19: "nineteen", 20: "twenty"}

_NUMBER = "|".join(WORDS.values())
_NOUN = r"(?:file|test|contract)s?"

#: A count of a population the tree changes. Not `question` - `UX-576`'s
#: sweep already holds every sentence counting the question library, and
#: two guards on one claim is how the two disagree.
COUNT = re.compile(
    rf"(?<!more than )(?<!fewer than )(?<!over )(?<!under )(?<!up to )"
    rf"(?<!at most )\b(\d[\d,]*|{_NUMBER})[\s-]+(?:[a-z]+[\s-]+)?{_NOUN}\b",
    re.I)

#: What makes a count legal without deriving it: it is pinned to a
#: moment, so it was never a claim about now.
PINNED = re.compile(
    r"UX-\d+|\bround(?:s)? \d+|\b\d{4}-\d{2}-\d{2}"
    r"|`(?:make|python3?|pytest|git|bga) [^`]*`", re.I)


@functools.lru_cache(maxsize=1)
def _tracked():
    """`UX-577`: git's list, never a glob - the checkout holds
    `.claude/worktrees/<agent>/`, a second copy of the whole tree."""
    out = subprocess.run(["git", "ls-files"], cwd=REPO, check=True,
                         capture_output=True, text=True).stdout
    return tuple(out.splitlines())


def _population():
    """The documents that steer a session: the skills, the agents and
    the contributing guides."""
    return [one for one in _tracked()
            if (re.fullmatch(r"\.claude/.+\.md", one)
                or re.fullmatch(r"docs/contributing/[^/]+\.md", one))
            and (REPO / one).exists()]


def _sentences(text):
    """Sentences, with the line wraps flattened. Where a wrap falls is
    the author's; the claim is the sentence."""
    for para in re.split(r"\n\s*\n", text):
        flat = " ".join(para.split())
        yield from re.split(r"(?<=[.:!?]) (?=[(\"A-Z*`\-—])", flat)


#: `UX-607`: the width the guide's size is stated at. At `round(B/1024)`
#: the band is 1 KB, so a paragraph over the headroom moved the figure -
#: and the figure is in two documents, one of them another track's file.
#: The figure is for a reading decision (card first, guide by paragraph),
#: which needs an order of magnitude and not a byte.
GUIDE_KB_STEP = 10

#: What a paragraph costs. The width has to be wider than this.
PARAGRAPH = 1024


def _kb(path):
    return round(path.stat().st_size / 1024)


def _bucket(nbytes):
    """The guide's size as it is stated: KB, to `GUIDE_KB_STEP`."""
    return round(nbytes / 1024 / GUIDE_KB_STEP) * GUIDE_KB_STEP


def _band():
    """`(low, high)` bytes over which the guide states the same figure."""
    size = GUIDE.stat().st_size
    stated, low, high = _bucket(size), size, size
    while _bucket(low - 1) == stated:
        low -= 1
    while _bucket(high) == stated:
        high += 1
    return low, high


#: `UX-607`: a size in KB, and a sentence that is about the guide. The
#: layer states other sizes - a 63 KB CI log, a 311 KB snapshot - and
#: those are observations, not a figure two documents have to agree on.
_KB = re.compile(r"~?\d[\d,]*\s*KB\b")
#: Named three ways, and the first draft of this had only two: a third
#: copy writing `the fixing guide is 40 KB` was not seen, because
#: `the guide` does not match `the fixing guide`.
_ABOUT_THE_GUIDE = re.compile(
    r"\bfixing[- ]guide\b|\bthe (?:whole )?guide\b|\bthis file\b", re.I)


def _size_population():
    """`_population()` plus `CLAUDE.md`, which summarises the card and is
    where a third copy of the guide's size would land."""
    return [*_population(), "CLAUDE.md"]


def _shared_paths():
    """The merge-hotspot block in the decompose skill, as its own rows."""
    text = DECOMPOSE.read_text(encoding="utf-8")
    block = text.split("session does, once, at the end", 1)[1]
    block = block.split("```text", 1)[1].split("```", 1)[0]
    return [line.split()[0] for line in block.splitlines() if line.strip()]


def _part_32():
    """`(first, last)` line numbers of the spec's Part 32, from its own
    headings - the range the fixing guide's item 12 quotes."""
    lines = SPEC.read_text(encoding="utf-8").splitlines()
    starts = [n for n, line in enumerate(lines, 1) if line.startswith("# ")]
    first = next(n for n in starts if lines[n - 1].startswith("# Part 32"))
    return first, next(n for n in starts if n > first) - 1


def _live_contracts():
    return [one for one in contracts.ids() if one not in contracts.superseded()]


def _pinning_clause():
    """§3.7's first sentence - what a consumer is told to pin. The rest
    of the item is history and keeps its own (superseded) literals."""
    item = GUIDE.read_text(encoding="utf-8").split(
        "\n7. **If your fix renames", 1)[1]
    return item.split("are what a consumer pins", 1)[0]


def _derived():
    """`{path: [sentence fragment]}` written from the population here and
    nowhere from a literal, so the ban accepts exactly what a clause
    above has already checked (`UX-549`'s shape)."""
    guide_kb = _bucket(GUIDE.stat().st_size)
    shared = WORDS[len(_shared_paths())].capitalize()
    # The rules are the subject; the header above §1 is the argument,
    # and it carries the marker in the sentence stating the count.
    rules = STYLE.read_text(encoding="utf-8").split("\n## 1.", 1)[1]
    enforced = rules.count("**Enforced by test")
    return {
        "docs/contributing/rules.md": [f"it is ~{guide_kb} KB"],
        "docs/contributing/fixing-guide.md": [
            f"{_kb(RULES)} KB against this file's ~{guide_kb} KB",
            f"`{schemas.ANALYZE}`, `{schemas.COMPARE}` and `{schemas.BLAST}`",
            "Part 32 spans {}-{}".format(*_part_32())],
        "docs/contributing/release-guide.md": [
            f"summary of {WORDS[len(_live_contracts())]} live contracts"],
        "docs/contributing/style-guide.md": [
            f"{WORDS[enforced].capitalize()} of the rules below close with"],
        ".claude/skills/decompose/SKILL.md": [f"{shared} files are shared"],
        ".claude/agents/implementer.md": [f"{shared} files are shared"],
    }


class TestTheFiguresAreDerived:
    """Each figure recomputed from what it describes, so a move in the
    population reddens a guard instead of ageing a sentence."""

    @pytest.mark.parametrize("rel", sorted(_derived()))
    def test_the_document_carries_the_derived_sentence(self, rel):
        text = " ".join((REPO / rel).read_text(encoding="utf-8").split())
        missing = [one for one in _derived()[rel] if one not in text]
        assert not missing, (
            f"{rel} does not carry the figure the tree gives: {missing}")

    def test_the_guide_pins_a_version_that_is_not_superseded(self):
        """§3.7 told a consumer to pin `analyze/v2`, which `schemas.py`
        lists as superseded - the rule's own example was three bumps
        behind. Read the pinning clause only; the history after it is
        about `UX-288` and keeps its literal."""
        named = set(re.findall(r"`([a-z][a-z0-9-]*/v\d+)`", _pinning_clause()))
        assert named, "the versioning rule names no contract id"
        stale = named & set(contracts.superseded())
        assert not stale, (
            f"the rule tells a consumer to pin {sorted(stale)}, which "
            f"`bga/schemas.py` lists as superseded")

    def test_the_scan_reads_something(self):
        """Every clause here passes on an empty population."""
        assert len(_population()) >= 10, (
            f"the process layer is {len(_population())} documents")
        # A count, not the count - restating 4 here is the defect above.
        assert len(_shared_paths()) >= 2, _shared_paths()
        assert _live_contracts(), "no live contract ids"


class TestNoBareCountSurvives:
    """The shape, not the eight instances. A count of files, tests or
    contracts is legal three ways: a clause above derives it, it names
    the round or item it was taken in, or it carries a command."""

    def test_every_count_is_derived_or_pinned(self):
        derived, bare = _derived(), []
        for rel in _population():
            allowed = derived.get(rel, ())
            text = (REPO / rel).read_text(encoding="utf-8")
            for sentence in _sentences(text):
                found = COUNT.search(sentence)
                if not found or PINNED.search(sentence):
                    continue
                if any(one in sentence for one in allowed):
                    continue
                bare.append(f"{rel}: {found.group(0)!r} in {sentence[:90]!r}")
        assert not bare, (
            "these count a population the tree changes, and nothing "
            "derives or dates them:\n" + "\n".join(bare))

    def test_the_ban_reads_a_non_empty_population(self):
        """A scan over nothing bans nothing. The corpus is the claim."""
        sentences = [one for rel in _population()
                     for one in _sentences(
                         (REPO / rel).read_text(encoding="utf-8"))]
        assert len(sentences) > 400, f"the corpus is {len(sentences)} sentences"
        assert sum(bool(COUNT.search(one)) for one in sentences) > 5, (
            "the pattern matches nothing in the corpus it is meant to read")


class TestTheGuidesSizeCostsOneFile:
    """`UX-607`: the derived size is in two documents, so a paragraph
    over the headroom is a two-file change across two tracks. Twice in
    round 84. The width is the fix - `round(B/1024)` left 33 B - and a
    scan keeps a third copy from appearing."""

    def test_a_paragraph_does_not_move_the_stated_figure(self):
        """The acceptance: 1 KB added to the guide, and no second
        document red."""
        size = GUIDE.stat().st_size
        _low, high = _band()
        assert high - size >= PARAGRAPH, (
            f"the guide is {size:,} B and states ~{_bucket(size)} KB; the "
            f"figure moves at {high:,} B, so only {high - size:,} B of "
            f"prose fit before docs/contributing/rules.md must change too")

    def test_the_band_is_what_bought_the_headroom(self):
        """Not the current size - the width. At `round(B/1024)` the band
        is 1024 B, so a 1 KB paragraph crosses it wherever it lands and
        the headroom above is luck."""
        low, high = _band()
        assert high - low > PARAGRAPH, (
            f"the guide states one figure over [{low:,}, {high:,}) B, a "
            f"{high - low:,} B band a paragraph can cross by accident")

    def test_no_third_document_states_the_guides_size(self):
        """The shape, not the two instances. A size claim about the
        guide is a copy that has to move when a paragraph lands, and the
        two that exist are derived above."""
        derived, copies = _derived(), []
        for rel in _size_population():
            allowed = derived.get(rel, ())
            for sentence in _sentences(
                    (REPO / rel).read_text(encoding="utf-8")):
                if not (_KB.search(sentence) and _ABOUT_THE_GUIDE.search(
                        sentence)):
                    continue
                if any(one in " ".join(sentence.split()) for one in allowed):
                    continue
                copies.append(f"{rel}: {sentence[:90]!r}")
        assert copies == [], (
            "these state the fixing guide's size and nothing derives it, "
            "so a paragraph in the guide becomes an edit here too:\n"
            + "\n".join(copies))

    def test_the_scan_finds_the_copies_that_do_exist(self):
        """A scan matching nothing bans nothing. The two derived
        sentences are what it has to see."""
        found = {rel for rel in _size_population()
                 for sentence in _sentences(
                     (REPO / rel).read_text(encoding="utf-8"))
                 if _KB.search(sentence) and _ABOUT_THE_GUIDE.search(sentence)}
        assert found == {"docs/contributing/rules.md",
                         "docs/contributing/fixing-guide.md"}, sorted(found)

    def test_the_scan_reaches_the_day_one_summary(self):
        """`CLAUDE.md` is the third copy this is guarding against - it
        summarises the card - and it is in neither `.claude/` nor
        `docs/contributing/`, so the population above does not reach it."""
        assert "CLAUDE.md" in _size_population()


class TestTheCountNoDecisionReadsIsGone:
    """`UX-471`'s other shape: a figure no decision reads is removed, not
    kept true by a test somebody has to edit each round."""

    def test_the_verify_skill_no_longer_counts_the_reference(self):
        rows = len(json.loads(
            (REPO / "tests/ci_reference.json").read_text())["files"])
        text = (REPO / ".claude/skills/verify/SKILL.md").read_text(
            encoding="utf-8")
        assert str(rows) not in text, (
            f"the verify skill states the reference's row count ({rows}); the "
            f"default branch adopts a new row on its own (`UX-503`), so the "
            f"figure moves without anyone deciding anything")

    def test_the_researcher_no_longer_counts_the_backlog(self):
        files = [one for one in _tracked()
                 if one.startswith("docs/backlog/scenarios/UX-")]
        text = (REPO / ".claude/agents/researcher.md").read_text(
            encoding="utf-8")
        assert str(len(files)) not in text, (
            f"the researcher states the backlog's size ({len(files)}); it "
            f"moves on every filing and steers no decision (`UX-471`)")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
