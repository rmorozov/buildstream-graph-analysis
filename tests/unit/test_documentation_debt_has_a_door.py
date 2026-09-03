"""UX-237: documentation a change needs and does not get has a door.

The fixing guide had two escape valves for work a session cannot do:
`§2.5` turns an unrelated bug into a tracker row, and `§3`'s item 10
(`UX-233`) makes a document your change falsified a same-commit fix.
Neither covers the commonest shape - *this needs a proper explanation
and writing it well is half a session's work* - so that thought became
a comment, or nothing.

Round 28 produced three instances (`capacity_recommendation`,
`memory_envelope`, `bga/whatif.py`'s convention) and all three survived
only because someone said so out loud in a review. Measured when this
was filed:

```text
git grep -l capacity_recommendation docs/  -> 3 backlog files, no guide
git grep -l memory_envelope docs/          -> 4 backlog files, no guide
git grep -l "upper bound, not a forecast" docs/  -> nothing
```

The judgment half of the rule cannot be tested - no guard knows which
mechanism deserves a page. The mechanical half can: **a filing that
says its documentation is coming later must name where it went.**

holds: rules.md#documentation-you-are-not-writing-now-file-the-row-first
"""
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
SCENARIOS = REPO / "docs/backlog/scenarios"
FIXING_GUIDE = REPO / "docs/contributing/fixing-guide.md"
STYLE_GUIDE = REPO / "docs/contributing/style-guide.md"

# The three instances `UX-237` cites, and the filing each one became.
# Naming the pairing rather than grepping every filing is deliberate:
# the mechanisms are also named in `UX-237`'s own Motivation and in
# each other's Out of Scope sections, so a search over all filings
# stays green when one of the three is deleted - measured, twice.
ROUND_28_INSTANCES = {
    "capacity_recommendation": "242",
    "memory_envelope": "243",
    "whatif": "244",
}

# The rule lands where it is written; `UX-232`'s sweep of the history
# was a one-time job and mining 235 closed filings is `UX-241`'s.
FIRST_FILING = 237

# Phrasings that defer documentation. Each is a real sentence shape a
# filing in this repository has used, not a guess at what someone might
# write - the check is worth exactly as much as this list is honest.
DEFERRALS = (
    r"document(?:ed|ation)?\s+(?:it\s+)?later",
    r"needs?\s+(?:a\s+)?proper\s+document",
    r"to\s+be\s+documented",
    r"will\s+be\s+documented",
    r"documentation\s+(?:is\s+)?(?:still\s+)?(?:a\s+)?(?:filing|task)\s+waiting",
    r"a\s+filing\s+waiting\s+to\s+happen",
    r"undocumented\s+for\s+now",
)
_DEFERRAL = re.compile("|".join(DEFERRALS), re.IGNORECASE)
_FILE_ID = re.compile(r"UX-0*(\d+)")


def _filings():
    for path in sorted(SCENARIOS.glob("UX-*.md")):
        match = _FILE_ID.match(path.name)
        if match and int(match.group(1)) >= FIRST_FILING:
            yield path


def _sentences(text):
    """Split on sentence ends, keeping enough context that an id one
    clause away still counts. A deferral and its filing id are written
    in one sentence when they are written at all."""
    return [s for s in re.split(r"(?<=[.;])\s+", text) if s.strip()]


# Where a deferral would actually be written. Reading the whole file
# instead matched `UX-237`'s own Required Fix - the sentence that
# *defines* the phrases this guard looks for - which is the same
# self-matching failure `UX-239` fixed in the context-map guard, one
# document over. A guard over prose has to say which part of the
# document is the subject and which part is the argument.
DEFERRAL_SECTIONS = ("## Out of Scope", "## Outcome")


def _sections(text):
    for heading in DEFERRAL_SECTIONS:
        if heading in text:
            yield text.split(heading, 1)[1].split("\n## ", 1)[0]


def _deferrals_without_an_id(path):
    text = "\n".join(_sections(path.read_text(encoding="utf-8")))
    own = _FILE_ID.match(path.name).group(1)
    bare = []
    for sentence in _sentences(text):
        if not _DEFERRAL.search(sentence):
            continue
        others = [n for n in re.findall(r"UX-(\d+)", sentence)
                  if n.lstrip("0") != own.lstrip("0")]
        if not others:
            bare.append(sentence.strip()[:90])
    return bare


class TestTheRuleIsWrittenDown:
    def test_the_fixing_guide_carries_the_third_door(self):
        text = FIXING_GUIDE.read_text(encoding="utf-8")
        body = text.split("## 3. Definition of Done", 1)
        assert len(body) == 2, "the guide has no Definition of Done"
        body = body[1].split("\n## ", 1)[0]
        assert "documentation you are not writing now" in body, (
            "the Definition of Done does not carry UX-237's rule")
        assert "UX-237" in body

    def test_the_style_guide_carries_the_counterpart(self):
        """From the writing side: a correction too big to be an edit is
        a filing, not a silent rewrite."""
        text = STYLE_GUIDE.read_text(encoding="utf-8")
        section = text.split("## 14. ", 1)
        assert len(section) == 2, "the style guide has no rule 14"
        body = section[1].split("\n## ", 1)[0]
        assert "fixing-guide.md" in body, (
            "rule 14 does not point at the rule it is the counterpart of")
        assert "UX-237" in body

    def test_the_definition_of_done_is_numbered_once_each(self):
        """The list is cross-referenced by number ("the same reason
        item 6 is"), and it carried two item 4s until this round - so
        every reference below the duplicate pointed one item wrong."""
        text = FIXING_GUIDE.read_text(encoding="utf-8")
        body = text.split("## 3. Definition of Done", 1)[1].split("\n## ", 1)[0]
        numbers = [int(m.group(1)) for m in
                   re.finditer(r"^(\d+)\. ", body, re.MULTILINE)]
        assert numbers == list(range(1, len(numbers) + 1)), (
            f"the Definition of Done is numbered {numbers}")


class TestADeferralNamesWhereItWent:
    def test_no_filing_defers_documentation_without_an_id(self):
        """"documented later" with no id is the parking `§12` exists to
        stop, one document over."""
        bare = {path.name: entries for path in _filings()
                if (entries := _deferrals_without_an_id(path))}
        assert bare == {}, (
            "filing(s) deferring documentation without naming where it "
            f"was filed: {bare}")

    def test_the_check_can_see_a_deferral_at_all(self):
        """The guard above passes on an empty repository and on one
        where the pattern matches nothing, and those are different
        things. This pins that the pattern fires on the shape it is
        written for - without it, retiring `DEFERRALS` to `()` would
        leave the suite green."""
        planted = ("This mechanism needs proper documentation and it is "
                   "not in this round's scope.")
        assert _DEFERRAL.search(planted)
        others = [n for n in re.findall(r"UX-(\d+)", planted)]
        assert others == [], "the fixture accidentally names an id"

    def test_the_round_28_instances_were_filed(self):
        """`UX-237`'s acceptance test: the three that motivated the
        rule are rows, not a paragraph about rows.

        The first version of this searched every filing from 237 on,
        including `UX-237` itself - which names all three mechanisms in
        its own Motivation as the evidence for the rule. Deleting a
        filing left it green. It reads every filing *except* the one
        that argues for them, which is the same subject-versus-argument
        separation `UX-239` had to make one document over.
        """
        # Both halves of the index. `UX-232` split it at 234 rows -
        # open in README.md, closed verbatim in closed.md - and this
        # check read only the open half, so the three rows reddened it
        # on the day they were *done* (round 37). "Has a row" is the
        # claim; which file the row is in is the index's business.
        index = "".join((SCENARIOS / name).read_text(encoding="utf-8")
                        for name in ("README.md", "closed.md"))
        wrong = []
        for mechanism, item in ROUND_28_INSTANCES.items():
            filings = [p for p in _filings()
                       if p.name.startswith(f"UX-0{item}")]
            if not filings:
                wrong.append(f"{mechanism}: no {item} filing")
                continue
            if mechanism not in filings[0].read_text(encoding="utf-8"):
                wrong.append(f"{mechanism}: {item} does not name it")
            if f"| UX-{item} |" not in index:
                wrong.append(f"{mechanism}: {item} has no backlog row")
        assert wrong == [], (
            f"round-28 mechanism(s) UX-237 names and nothing filed: {wrong}")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
