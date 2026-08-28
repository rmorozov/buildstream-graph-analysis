"""UX-275: the answer to the question this backlog opened with, published.

`UX-09` asked, in the first week: what should `--builders` and
`--max-jobs` be, and which constraint is the reason. `UX-116` answered
it, `UX-242` documented it - and the JSON renderer dropped it, so the
answer was reachable only by a human reading a terminal:

```text
$ bga analyze RUN --plane2 PLANE2.json -f json | jq .capacity_recommendation
null
```

**Where it went, and why here.** `analyze/v2`, beside `capacity_verdict`
("was the capacity right?"), not `correlate/v1` beside its sibling
`memory_envelope`. `correlate/v1` is the per-element join - one row per
element - and a run-level recommendation is not a row of it. The item's
own acceptance test names `bga analyze ... -f json` as the command that
must answer, which settles it from the other end.

An addition, so no version bump: `UX-190`'s rule, the same one
`UX-249`'s `producer` and `UX-215`'s `element_join` were added under.
"""
import json
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
SNAPSHOT = REPO / "tests/fixtures/macro_micro"
RUN = SNAPSHOT / "run"
PLANE2 = SNAPSHOT / "plane2.json"

KEY = "capacity_recommendation"


def _analyze(*extra):
    done = subprocess.run(
        [sys.executable, "-m", "bga.cli", "analyze", str(RUN), *extra],
        capture_output=True, text=True, cwd=REPO, timeout=300)
    assert done.returncode == 0, done.stderr[-2000:]
    return done.stdout


@pytest.fixture(scope="module")
def published():
    return json.loads(_analyze("--plane2", str(PLANE2), "--format", "json"))


@pytest.fixture(scope="module")
def printed():
    return _analyze("--plane2", str(PLANE2))


class TestTheRecommendationReachesAConsumer:

    def test_the_payload_carries_it(self, published):
        """The acceptance test's first clause, run as the command it
        names rather than through the function underneath it."""
        assert KEY in published, sorted(published)
        assert published[KEY]["binding_constraint"]
        assert published[KEY]["recommended_builders"] >= 0

    def test_the_schema_declares_it(self):
        """The acceptance test's second clause. A key in the payload
        that the schema does not declare is a key no consumer can look
        up - `UX-201`'s rule, and what `bga analyze --schema` is for."""
        from bga import schemas

        node = schemas.schema(schemas.ANALYZE)["properties"].get(KEY)
        assert node, f"{KEY} is not declared in {schemas.ANALYZE}"
        assert node.get("bga:question"), "declared with no question"

    def test_every_field_the_item_named_survived(self, published):
        """Item 2 lists what has to arrive intact. A recommendation that
        published its number and dropped its constraints would satisfy a
        key-presence check and answer nothing."""
        block = published[KEY]
        for field in ("constraints", "binding_constraint",
                      "recommended_builders", "builders_change", "caveat"):
            assert field in block, f"{field} did not survive publication"
        assert block["constraints"], "the constraint list is empty"
        for constraint in block["constraints"]:
            assert constraint["name"] and constraint["reason"], constraint
            assert isinstance(constraint["allows"], int), constraint

    def test_the_caveat_is_the_sentence_and_not_a_flag(self, published):
        """The item calls the caveat load-bearing: *a recommendation
        without it is a number a CI job would act on.* A boolean or an
        empty string would pass the presence check above."""
        caveat = published[KEY]["caveat"]
        assert isinstance(caveat, str) and len(caveat.split()) >= 20, caveat
        assert "no configuration was tried" in caveat, caveat

    def test_a_run_with_no_plane2_has_no_recommendation_rather_than_an_empty_one(
            self):
        """Absent, not zeroed - the distinction `run_instance` and
        `plane2_coverage` already keep. "Not measured" must not render
        as "no constraint".

        `UX-329`: `--no-plane2`, not a bare invocation. `RUN` sits in a
        snapshot with a Plane 2 report beside it, and a bare `analyze`
        now finds it - which is the fix, and which means the bare form
        no longer describes a run without Plane 2. The flag is how a
        reader asks for one plane, so it is how this clause asks too.
        """
        without = json.loads(_analyze("--no-plane2", "--format", "json"))
        assert KEY not in without, without.get(KEY)


class TestTheTwoRenderersCannotDisagree:
    """Item 3: the failure `UX-83` measured between two commands, one
    level down. The text report renders this block through the
    `capacity-recommendation` finding, which *copies* the fields out of
    the recommendation - so the two can drift, and only a guard that
    reads both catches it."""

    def test_the_finding_and_the_payload_name_one_binding_constraint(
            self, published):
        finding = [f for f in published["findings"]
                   if f["id"] == "capacity-recommendation"]
        assert finding, "the run published no capacity finding"
        evidence = finding[0]["evidence"]
        block = published[KEY]
        assert evidence["binding_constraint"] == block["binding_constraint"]
        assert evidence["recommended_builders"] == block["recommended_builders"]
        assert evidence["constraints"] == block["constraints"]

    def test_the_printed_report_names_the_same_one(self, published, printed):
        """And the text a human reads, which is the renderer that had
        this to itself until now. Every constraint the payload carries
        is printed with the same ceiling, and the binding one is the
        smallest in both."""
        block = published[KEY]
        for constraint in block["constraints"]:
            line = f"{constraint['name']} allows {constraint['allows']}"
            assert line in printed, (
                f"the text report does not print {line!r}")
        binding = min(block["constraints"],
                      key=lambda c: (c["allows"], c["name"]))
        assert binding["name"] == block["binding_constraint"], (
            "the payload's binding constraint is not its smallest")
        assert f"{binding['name']} binds at {block['recommended_builders']}" \
            in printed or f"{binding['name']} allows" in printed, printed[:400]

    def test_the_provenance_chain_no_longer_calls_it_unpublished(
            self, published):
        """The other half of the same disagreement. `UX-229`'s chain
        listed these fields as "computed, not published" - an honest
        label for a real gap, and a lie the moment the gap closed."""
        # `UX-344`: one published record per claim, keyed by the id the
        # finding carries.
        chain = [entry for entry in published["provenance"]
                 if entry["claim"] == "capacity-recommendation"][0]
        assert chain["unpublished_inputs"] == [], chain["unpublished_inputs"]
        cited = {entry["path"]: entry for entry in chain["evidence"]}
        assert f"{KEY}.binding_constraint" in cited, sorted(cited)
        for path, entry in cited.items():
            assert entry["resolved"], (path, "cited and unresolvable")
        assert cited[f"{KEY}.binding_constraint"]["value"] \
            == published[KEY]["binding_constraint"]
