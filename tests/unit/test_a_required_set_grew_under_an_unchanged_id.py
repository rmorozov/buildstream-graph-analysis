"""UX-629: a key entering `required` under a live id is a break.

`UX-610` took `_COMPARE_REQUIRED` from 13 keys to 14, so
`schema('compare/v2')['required']` went 14 -> 15 with the id unmoved. A
`compare/v2` document written before that no longer validated against
`compare/v2`, and the rule called it an addition because it named only
rename and removal.

Two choices were open. Bumping to `compare/v3` is honest and does not
help the already-written document; declaring the key *permitted and
always written* restores it at the cost of the schema-level guarantee,
which the emitter then has to carry. This holds the second, and holds
the rule that stops the first case recurring.

holds: rules.md#a-key-entering-required-under-a-live-id-bumps-it-too
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
GOLDEN = REPO / "tests/fixtures/golden/mixed_task_kinds"

# The 14 required keys `compare/v2` had at `147a49c`, before `UX-610`.
# A document a consumer wrote in that window, written down rather than
# derived: deriving it from today's schema would move with the defect.
A_DOCUMENT_WRITTEN_BEFORE_UX_610 = {
    "schema": "compare/v2",
    "baseline_run_id": "a", "candidate_run_id": "b",
    "baseline": {}, "candidate": {}, "deltas": {},
    "verdict": "improved", "verdict_kind": "improved",
    "low_confidence": False, "mismatches": [], "failed_runs": [],
    "attribution_deltas": {}, "element_deltas": {},
    "candidate_diagnosis": {},
}

try:
    import jsonschema
except ImportError:                      # pragma: no cover
    jsonschema = None

# Round 21's seam, held by `test_six_seams_round_21_found.py`: a
# module-scope `importorskip` skips every guard in the file, and only
# two of these need a validator.
needs_jsonschema = pytest.mark.skipif(
    jsonschema is None,
    reason="jsonschema is not installed - `pip install -e '.[dev]'`")


def _schema(name):
    from bga import schemas

    return schemas.schema(name)


def _always_written(name):
    return tuple(_schema(name).get("bga:always_written", ()))


def _every_declaration():
    from bga import contracts

    return {name: _always_written(name) for name in contracts.printable()}


class TestTheChoiceIsDeclaredAndNotInferred:
    """Which of the two shapes was taken, said in the document itself
    rather than in a comment. `--schema` prints this, so a consumer
    reads the decision off the contract."""

    def test_the_key_is_declared_permitted_rather_than_required(self):
        schema = _schema("compare/v2")
        assert "verdict_provenance" in schema["properties"], (
            "verdict_provenance is not declared at all - permitted means "
            "declared-and-not-required, not absent")
        assert "verdict_provenance" not in schema["required"], (
            "verdict_provenance is required again; a compare/v2 document "
            "written before UX-610 stops validating against compare/v2, "
            "which is the break this item is about")
        assert "verdict_provenance" in _always_written("compare/v2"), (
            "verdict_provenance is permitted but nothing says the emitter "
            "guarantees it - that is the certainty this choice cost a "
            "reader, and the annotation is what pays it back")

    def test_a_declaration_is_never_also_required(self):
        """The annotation's only content is *not required*. A key in
        both says nothing, and would read as a guarantee while being
        the very thing that breaks an old document."""
        for name, keys in _every_declaration().items():
            required = set(_schema(name)["required"])
            assert not set(keys) & required, (
                f"{name}: {sorted(set(keys) & required)} is required and "
                f"declared always-written")

    def test_a_declaration_names_a_key_the_schema_declares(self):
        for name, keys in _every_declaration().items():
            properties = _schema(name)["properties"]
            missing = sorted(key for key in keys if key not in properties)
            assert missing == [], f"{name}: undeclared {missing}"

    def test_something_is_declared(self):
        """Non-vacuity. The three clauses above quantify over the
        declarations, so an empty set passes all of them while the
        decision this item made has silently disappeared.

        While `compare/v2` is the only contract declaring anything,
        emptying the set and un-declaring that key are the same world,
        so a mutation reddens this and the first clause together. That
        is the tree's shape, not a duplicated claim: the second
        declaration separates them.
        """
        declared = {key for keys in _every_declaration().values()
                    for key in keys}
        assert declared, (
            "no contract declares an always-written key; UX-629's choice "
            "is gone and the clauses above are quantifying over nothing")

    def test_the_builder_refuses_a_declaration_that_says_nothing(self):
        """The annotation's whole content is *permitted, and yet always
        there*. A required key makes it a tautology and an undeclared
        one makes it a dangling name, so `_document` refuses both
        rather than publishing a claim a consumer would act on."""
        from bga import schemas

        with pytest.raises(ValueError):
            schemas._document("x/v1", "t", {"k": ""}, "d",
                              always_written=("k",))
        with pytest.raises(KeyError):
            schemas._document("x/v1", "t", {}, "d",
                              always_written=("nope",))


class TestTheOldDocumentValidatesAgain:
    """The consumer's own experience, which is the whole argument. The
    week-old document is the measurement; everything else is the
    mechanism that produced it."""

    @needs_jsonschema
    def test_a_document_written_before_ux_610_validates(self):
        jsonschema.validate(A_DOCUMENT_WRITTEN_BEFORE_UX_610,
                            _schema("compare/v2"))

    def test_that_document_is_the_pre_ux_610_required_set(self):
        """Non-vacuity for the clause above, and only that: a fixture
        someone topped up with today's keys would validate whatever the
        schema said. 14 keys is what `147a49c` required, measured. It
        does *not* restate `required <= document` - that is the clause
        above, and a mutation reddening both falsifies one."""
        assert len(A_DOCUMENT_WRITTEN_BEFORE_UX_610) == 14
        assert "verdict_provenance" not in A_DOCUMENT_WRITTEN_BEFORE_UX_610

    @needs_jsonschema
    def test_a_key_still_missing_from_required_reddens(self):
        """And the schema has not simply been emptied: dropping a key
        the id has always required must still fail, or the clause above
        is passing because nothing is checked."""
        broken = dict(A_DOCUMENT_WRITTEN_BEFORE_UX_610)
        del broken["verdict"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(broken, _schema("compare/v2"))


class TestTheEmitterCarriesTheGuarantee:
    """`required` was the guarantee and is gone, so this is what
    replaces it: the real payload, not the schema, and not a claim in a
    docstring."""

    def test_a_real_comparison_writes_every_declared_key(self, comparison):
        payload = comparison
        for name, keys in _every_declaration().items():
            if name != "compare/v2":
                continue
            missing = sorted(key for key in keys if key not in payload)
            assert missing == [], (
                f"compare/v2 declares {missing} always written and `bga "
                f"compare` did not write {missing}. Permitted-and-always-"
                f"written is only worth the guarantee, and the guarantee "
                f"is here")

    def test_the_payload_is_a_real_comparison(self, comparison):
        """Non-vacuity: an empty or refused payload carries no keys, so
        the clause above would pass on it having proven nothing."""
        payload = comparison
        assert payload.get("schema") == "compare/v2"
        assert len(payload) > 14, f"{len(payload)} keys is not a comparison"


class TestTheRuleSaysWhichChoiceWasMade:
    """`UX-629`'s Required Fix asks for the rule *or* the shape, with a
    guard saying which. Both landed, so both are read - and from the
    documents a session is actually pointed at."""

    DOCUMENTS = {
        "docs/spec/specification.md": "## 32.5 The published output schemas",
        "docs/design/architecture.md": "## The published contracts",
        "docs/guides/cli.md": "## The JSON outputs, and their schemas",
    }

    @pytest.mark.parametrize("relative,heading", sorted(DOCUMENTS.items()))
    def test_the_versioning_rule_carries_the_third_clause(self, relative,
                                                          heading):
        """Read from the section that states the rule, not the file: a
        document arguing about `required` elsewhere would otherwise
        satisfy this without the rule having moved."""
        text = (REPO / relative).read_text(encoding="utf-8")
        parts = text.split(heading, 1)
        assert len(parts) == 2, f"{relative} has no {heading!r} section"
        body = parts[1].split("\n## ", 1)[0]
        assert "`required`" in body, (
            f"{relative}'s versioning rule does not mention `required` - "
            f"it still names only rename and removal, and UX-610's growth "
            f"reads as an addition")
        assert "UX-629" in body, (
            f"{relative} states the clause without saying what settled it")

    def test_the_rules_card_carries_its_own_row(self):
        """The card is one line per rule and cites no ids in its rows,
        so it is read for the row rather than for the argument - and
        the row must name *this* file, which is the link
        `test_the_agent_configuration_holds.py` walks the other way."""
        text = (REPO / "docs/contributing/rules.md").read_text(
            encoding="utf-8")
        row = [line for line in text.splitlines()
               if line.startswith("|") and "`required`" in line
               and "under a live id" in line]
        assert len(row) == 1, f"expected one row, found {row}"
        assert pathlib.Path(__file__).name in row[0], (
            f"the row does not name this guard: {row[0]}")


@pytest.fixture(scope="module")
def comparison(tmp_path_factory):
    """`bga compare` over two copies of the golden run - a real payload.

    Two copies rather than the directory twice, which `bga compare`
    refuses as the same run. The verdict is uninteresting; the *key
    set* is the subject.
    """
    root = tmp_path_factory.mktemp("compare")
    runs = []
    for name in ("a", "b"):
        run = root / name
        shutil.copytree(GOLDEN, run)
        os.remove(run / "expected_output.json")
        runs.append(str(run))
    done = subprocess.run(
        [sys.executable, "-c",
         "from bga.cli import main; raise SystemExit(main(%r))"
         % (["compare", runs[0], runs[1], "--format", "json"],)],
        capture_output=True, text=True, cwd=REPO, timeout=300)
    assert done.returncode == 0, done.stderr[-2000:]
    return json.loads(done.stdout)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
