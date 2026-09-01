"""UX-331: the README's pasted report is a real run's, and says what it elides.

The block under *Quick start* introduced itself as **"small enough to
read in full, which is the point"** and then showed 15 lines of an
86-line report - with no marker, and three of its own lines already
drifted from what the tool prints:

```text
README said                        the tool prints
Key Findings:                      Key Findings:
  Confidence: 0.88 (high)            This build is scheduler-bound, ...
                                     Confidence: 0.88 (high)
  ... not the scheduler)             ... not the scheduler (see Dispatch
                                     Occupancy and Critical Path))
```

The missing first line is the report's own headline diagnosis, and the
dropped clause is a cross-reference. `UX-192` is the precedent: an
elision nobody declared is what reopened the round-trip that item was
filed for, and the rule it left behind is that pasted output either is
the output or says where it was cut.

So this reads the block, splits it on the elision markers, and asserts
every remaining line appears **verbatim and in order** in a fresh run
of the command the README itself prints two lines above. It is a diff,
not a spot-check: a clause quietly rewritten anywhere in those lines
reddens.
"""
import pathlib
import re
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
README = REPO / "README.md"

#: The marker the block uses to declare a cut. Anything between two of
#: these is *not* claimed to be contiguous with what follows.
ELISION = re.compile(r"^\[\.\.\. elided: .+ \.\.\.\]$")

_WORDS = {"eighty-six": 86}


def _quick_start_block():
    """The `text` fence under *Quick start*, and the prose around it."""
    text = README.read_text(encoding="utf-8")
    start = text.index("## Quick start")
    section = text[start:text.index("\n## ", start + 4)]
    fences = re.findall(r"```text\n(.*?)```", section, re.S)
    assert len(fences) == 1, (
        f"the Quick start section has {len(fences)} `text` fences; this "
        f"guard reads the one holding the pasted report")
    return section, fences[0].splitlines()


def _where(fresh, line):
    """`line`'s position in the real output, or a failure that says so.

    `list.index` raises `ValueError` here, and a guard whose failure is
    a traceback rather than a sentence makes the reader do the work the
    message should have done - so the two clauses that need a position
    ask through this.
    """
    assert line in fresh, (
        f"the README pastes a line the tool does not print:\n  {line!r}")
    return fresh.index(line)


@pytest.fixture(scope="module")
def fresh():
    """The command the README prints, run from the repository root."""
    done = subprocess.run(
        [sys.executable, "-m", "bga.cli", "analyze",
         "tests/fixtures/golden/mixed_task_kinds", "--diagnostics"],
        capture_output=True, text=True, cwd=str(REPO), timeout=180)
    assert done.returncode == 0, done.stderr
    return done.stdout.splitlines()


class TestThePastedBlockIsTheRealOutput:
    def test_the_command_in_the_block_is_the_one_this_guard_runs(self):
        """The fence above the paste says which command produced it. If
        that drifts, this guard is diffing against the wrong thing and
        would go on passing."""
        text = README.read_text(encoding="utf-8")
        start = text.index("## Quick start")
        section = text[start:text.index("\n## ", start + 4)]
        assert ("bga analyze tests/fixtures/golden/mixed_task_kinds "
                "--diagnostics") in section, (
            "the Quick start command is not the one this guard runs")

    def test_every_pasted_line_is_a_real_line_of_a_fresh_run(self, fresh):
        pasted = [line for line in _quick_start_block()[1]
                  if line.strip() and not ELISION.match(line)]
        missing = [line for line in pasted if line not in fresh]
        assert missing == [], (
            "the README pastes lines the tool does not print - the block "
            "has drifted from its own command", missing)

    def test_the_pasted_lines_appear_in_the_order_they_are_pasted(self, fresh):
        """Order matters as much as membership: a block that reshuffles
        the report's sections is as misleading as one that invents a
        line, and membership alone cannot see it."""
        pasted = [line for line in _quick_start_block()[1]
                  if line.strip() and not ELISION.match(line)]
        where = [_where(fresh, line) for line in pasted]
        assert where == sorted(where), (
            "the pasted lines are not in the order the report prints them",
            [pasted[i] for i in range(1, len(where))
             if where[i] < where[i - 1]])

    def test_the_block_declares_its_cuts(self, fresh):
        """The `UX-192` rule. Two consecutive pasted lines that are not
        adjacent in the real output are an undeclared elision."""
        lines = [line for line in _quick_start_block()[1] if line.strip()]
        undeclared = []
        previous = None
        for line in lines:
            if ELISION.match(line):
                previous = None
                continue
            here = _where(fresh, line)
            if previous is not None and here != previous + 1:
                undeclared.append(fresh[previous + 1:here])
            previous = here
        assert undeclared == [], (
            "the block jumps over report lines without an "
            "`[... elided: ... ...]` marker between them", undeclared)

    def test_the_stated_length_is_the_real_length(self, fresh):
        """It said "small enough to read in full" over a sixth of the
        report. A count nobody derives is a count that drifts."""
        section = _quick_start_block()[0]
        claimed = re.search(r"\*\*(\d+|" + "|".join(_WORDS) + r") lines\*\*",
                            section)
        assert claimed, (
            "the Quick start prose no longer states the report's length; "
            "without it the reader cannot tell how much was cut")
        stated = _WORDS.get(claimed.group(1)) or int(claimed.group(1))
        assert stated == len(fresh), (
            f"the README says the report is {stated} lines; it is "
            f"{len(fresh)}")

    def test_it_does_not_claim_to_be_the_whole_report(self):
        """The sentence this item was filed for."""
        section = _quick_start_block()[0]
        assert "read in full" not in section, (
            "the Quick start still claims the pasted block is the full "
            "report while eliding five of its sections")


class TestTheBoundSentenceNamesItsThreshold:
    """The other half of `UX-331`, and the reason the diagnosis line was
    worth pasting at all: **88% sounds chain-bound.** Nine-tenths of the
    build is on the critical path and the sentence says the chain is not
    the constraint, which reads as a contradiction until you know the
    threshold - and nothing in the sentence could get you there."""

    def test_the_sentence_names_the_line_the_ratio_fell_on(self, fresh):
        from bga import findings

        headline = next(line for line in fresh if "bound, not" in line)
        assert f"{findings.CHAIN_BOUND_RATIO:.0%} chain-bound line" in headline, (
            "the diagnosis sentence does not name the threshold that "
            "decided it", headline)

    def test_both_bound_wordings_carry_it_not_just_the_one_on_the_fixture(self):
        """The fixture exercises one branch. A threshold added to the
        sentence that happens to be printed, and not to its opposite, is
        half a fix that no committed run would catch."""
        from bga import findings

        for name in (findings.DIAGNOSIS_CHAIN_BOUND,
                     findings.DIAGNOSIS_SCHEDULER_BOUND):
            assert "{bound:" in findings.DIAGNOSIS_SENTENCES[name], (
                f"the {name} sentence does not carry the threshold")

    def test_the_number_is_formatted_from_the_constant_not_written_out(self):
        """One copy. `UX-229`'s rule: a rule whose threshold has no name
        cannot be published as one - and one written out beside the
        constant is a second copy waiting to drift."""
        from bga import findings

        for name in (findings.DIAGNOSIS_CHAIN_BOUND,
                     findings.DIAGNOSIS_SCHEDULER_BOUND):
            sentence = findings.DIAGNOSIS_SENTENCES[name]
            assert "90%" not in sentence, (
                f"the {name} sentence writes the threshold out as a "
                f"literal instead of formatting `CHAIN_BOUND_RATIO`")

    def test_explain_quotes_the_same_constant(self):
        """`--explain`'s record and the headline are two surfaces of one
        rule (`UX-229`), so they cannot disagree about the number - and
        the reader sent from the sentence to the record must land on the
        threshold they were just shown."""
        from bga import findings

        rule = _headline_rule()
        assert rule["name"] == "CHAIN_BOUND_RATIO", rule
        assert rule["threshold"] == findings.CHAIN_BOUND_RATIO
        assert f"{findings.CHAIN_BOUND_RATIO:.0%}" in rule["sentence"], (
            "the record's sentence does not quote the threshold the "
            "headline now names", rule["sentence"])

    def test_every_rule_carrying_this_constant_carries_its_value(self):
        """Two findings gate on `CHAIN_BOUND_RATIO` - the headline and
        the blast-radius ranking - and only one of them spells the
        number in prose. That is fine, and this says why it is fine:
        the record carries `threshold` as a **field** on every rule, so
        a sentence saying "above the threshold" is still reachable. The
        clause exists so a future rule that carries neither reddens.

        Read across two runs since `UX-477`. The two rules are on
        opposite sides of the same branch - the ranking fires only when
        the run is *not* chain-bound - so no single capture publishes
        both, and the golden run used to publish both only because its
        verdict came from BuildStream's startup rather than its graph.
        `shared_base_wide` is scheduler-bound by shape."""
        from bga import findings

        rules = [rule for rule in
                 _rules_for_the_fixture()
                 + _rules_for_the_fixture("tests/fixtures/shared_base_wide/run")
                 if rule.get("name") == "CHAIN_BOUND_RATIO"]
        assert len(rules) >= 2, ("the fixture no longer exercises both "
                                 "rules that gate on this constant", rules)
        for rule in rules:
            assert rule["threshold"] == findings.CHAIN_BOUND_RATIO, rule


def _headline_rule():
    """The rule behind `headline.sentence` - the one the README's first
    pasted line comes from."""
    import json

    done = subprocess.run(
        [sys.executable, "-m", "bga.cli", "analyze",
         "tests/fixtures/golden/mixed_task_kinds", "--format", "json",
         "--diagnostics", "--explain"],
        capture_output=True, text=True, cwd=str(REPO), timeout=180)
    assert done.returncode == 0, done.stderr
    # `UX-344`: the chain is published once per claim, at the top level.
    document = json.loads(done.stdout)
    return next(entry for entry in document["provenance"]
                if entry["claim"] == "diagnosis")["rule"]


def _rules_for_the_fixture(run="tests/fixtures/golden/mixed_task_kinds"):
    """Every provenance rule one run publishes."""
    import json

    done = subprocess.run(
        [sys.executable, "-m", "bga.cli", "analyze",
         run, "--format", "json",
         "--diagnostics", "--explain"],
        capture_output=True, text=True, cwd=str(REPO), timeout=180)
    assert done.returncode == 0, done.stderr
    document = json.loads(done.stdout)
    found = []

    def walk(node):
        if isinstance(node, dict):
            if "name" in node and "threshold" in node and "sentence" in node:
                found.append(node)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(document)
    return found


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
