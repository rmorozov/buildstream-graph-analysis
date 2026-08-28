"""UX-291: a finding carries its numbers three times, and they agree.

Found by `UX-288`'s guard, which sweeps the payload for two fields
carrying one element set and had to be told that `findings[...]` is
derived narrative. That exclusion is right, and it hid this - the same
question one level down. Measured on the committed `macro_micro` run:

```text
finding                    evidence  prov  both  in copy_text
cache-hit-ratio                   4     4     4             4
confidence                        3     3     1             3
wait-category                     4     2     0             4
...
TOTAL                            23          10            20
```

**The decision, recorded in the contract and checked here.** The
finding's own `evidence` is the carrier a consumer should believe.
`provenance.evidence[].value` is a *quotation* of the document at a
path - `UX-229`'s "what we read, where we read it" - and `copy_text` is
`UX-224`'s rendering for a human in a ticket, self-contained by
definition.

**Why `evidence` is not a projection over `provenance.evidence`**, which
was the item's other candidate: measured below, 14 of the finding
evidence entries on the `macro_micro` run have a citation at all, and
the rest are derived ratios with no published path. A projection would
have to drop numbers a consumer reads or invent paths for them.

So: three carriers, one authority, and the agreement is guarded rather
than assumed - which is the gap the item names. Nothing was wrong when
it was filed; what was missing was the rule saying it has to stay that
way.
"""
import json
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import provenance, schemas  # noqa: E402

GOLDEN = REPO / "tests/fixtures/golden/mixed_task_kinds"
SNAPSHOT = REPO / "tests/fixtures/macro_micro"


def _analyze(*args):
    done = subprocess.run(
        [sys.executable, "-m", "bga.cli", "analyze", *args],
        capture_output=True, text=True, cwd=REPO, timeout=300)
    assert done.returncode == 0, done.stderr[-2000:]
    return json.loads(done.stdout)


@pytest.fixture(scope="module")
def measured():
    """The run with both planes - the one the item measured."""
    return _analyze(str(SNAPSHOT / "run"), "--plane2",
                    str(SNAPSHOT / "plane2.json"), "--format", "json")


@pytest.fixture(scope="module")
def golden():
    return _analyze(str(GOLDEN), "--format", "json")


def _pairs(document):
    """`(finding id, leaf, evidence value, quoted value)` for every
    quantity both carriers name.

    Matched by the citation path's leaf, which is the name the finding's
    own evidence uses: `capacity_recommendation.binding_constraint` and
    `evidence["binding_constraint"]` are the same number by two routes.
    """
    found = []
    # `UX-344`: one published list keyed by claim, rather than a record
    # written into each finding.
    chains = {entry.get("claim"): entry
              for entry in document.get("provenance") or []}
    for finding in document.get("findings") or []:
        evidence = finding.get("evidence") or {}
        for cite in (chains.get(finding.get("id")) or {}).get("evidence") or []:
            leaf = cite["path"].split(".")[-1].split("[")[0]
            if leaf in evidence:
                found.append((finding["id"], leaf, evidence[leaf],
                              cite["value"]))
    return found


class TestTheCarriersAgree:

    @pytest.mark.parametrize("run", ["measured", "golden"])
    def test_the_finding_and_its_citation_carry_one_number(self, run, request):
        document = request.getfixturevalue(run)
        disagree = [row for row in _pairs(document) if row[2] != row[3]]
        assert disagree == [], (
            "a finding's evidence and its provenance citation disagree: "
            f"{disagree}")

    def test_the_run_actually_has_pairs_to_check(self, measured, golden):
        """The number that makes the check above mean something. A
        release that stopped citing anything would leave it green over
        an empty list - and this is exactly the shape `UX-288`'s
        populations had to grow after M1 passed on nothing."""
        assert len(_pairs(measured)) >= 10, _pairs(measured)
        assert len(_pairs(golden)) >= 2, _pairs(golden)

    @pytest.mark.parametrize("run", ["measured", "golden"])
    def test_every_citation_still_quotes_the_live_document(self, run, request):
        """`UX-229`'s rule, re-run over the two-plane document - it was
        guarded on the golden fixture and the synthetic one, neither of
        which carries a Plane 2 report, so the claims that only exist
        with one had never been through it."""
        document = request.getfixturevalue(run)
        wrong = []
        quoted = 0
        chains = {entry.get("claim"): entry
                  for entry in document.get("provenance") or []}
        for finding in document["findings"]:
            for cite in (chains.get(finding.get("id")) or {}).get("evidence") or []:
                if not cite["resolved"]:
                    continue
                quoted += 1
                live = provenance.resolve(document, cite["path"])
                if live is provenance.UNRESOLVED or live != cite["value"]:
                    wrong.append((finding["id"], cite["path"], cite["value"],
                                  live))
        assert quoted >= 5, f"only {quoted} citations resolved; nothing checked"
        assert wrong == [], wrong


class TestTheContractSaysWhichOneToBelieve:
    """The item's first clause: *write the decision down where a reader
    of the contract meets it.* That is the published schema, which is
    what `bga analyze --schema` prints and what every consumer reads -
    not a task file."""

    def test_the_finding_evidence_node_claims_the_authority(self):
        # `UX-344`: the chain is published once, so its schema is the
        # item schema of `provenance` rather than a node inside
        # `findings[]`.
        node = schemas.schema(schemas.ANALYZE)["properties"]["provenance"]
        cited = node["items"]["properties"]["evidence"]["description"]
        assert "quotation" in cited.lower(), cited
        assert "believe" in cited.lower(), (
            "the contract does not say which carrier wins when two name "
            "one number")

    def test_the_rendering_is_still_declared_a_rendering(self):
        """Item 2: `copy_text` stays what `UX-224` made it. A guard that
        let it become a third source of truth would have closed this
        item by breaking that one."""
        node = schemas.schema(schemas.ANALYZE)["properties"]["findings"]
        copy_text = node["items"]["properties"]["copy_text"]["description"]
        assert "plain text" in copy_text, copy_text


class TestTheDerivedFindingDoesNotOutliveItsSource:
    """The item's other example: `joint-saving` restates a whole signal.

    `findings.py` derives it *from* `joint_saving`, so the
    direction is right and the signal is the source. What was unguarded
    is that the derived copy still equals it.
    """

    def test_the_finding_and_the_signal_carry_one_set_of_numbers(
            self, measured):
        signal = (measured.get("signals") or {}).get("joint_saving")
        finding = [f for f in measured["findings"] if f["id"] == "joint-saving"]
        if not signal or not finding:
            pytest.skip("this run published no joint-saving signal")
        evidence = finding[0]["evidence"]
        for key in ("joint_saving_us", "sum_of_individual_us", "savings_add"):
            assert evidence[key] == signal[key], (key, evidence[key],
                                                  signal[key])
        assert sorted(finding[0]["elements"]) == sorted(signal["elements"])
