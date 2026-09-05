"""UX-610: the verdict's evidence chain is a `compare/v2` key.

`UX-593` built `bga.compare.verdict_provenance(comparison)` and left it
outside the payload, because a new top-level key had to be declared in
`bga/schemas.py` and that was another track's file. Re-measured on this
tree at `5343bd6`:

```text
$ bga compare a b --format json | keys        29   (28 + `schema`)
  of those, carrying a verdict record          0
$ verdict_provenance(comparison)
  document compare/v2 · 4 evidence paths · 0 unresolved
```

So the chain resolved against a document it was not in: every consumer
that reads `compare/v2` - the CI gatekeeper this serves - had no way to
reach it.

The rule under test is that the record travels *in* the payload its
paths walk, and that the schema requires the key rather than merely
permitting it: a key the payload always carries but the contract only
permits is one a consumer could lose without any test noticing.
"""
import json
import subprocess
import sys

import pytest

from bga import provenance, schemas
from bga.compare import compare_runs, verdict_provenance

try:
    import jsonschema
except ImportError:  # pragma: no cover - dev extra
    jsonschema = None

needs_jsonschema = pytest.mark.skipif(
    jsonschema is None, reason="jsonschema is not installed - `pip install -e '.[dev]'`")


def _span(uid, ts, dur):
    return {"task_key": f"{uid}|BUILD|BUILD|0", "ts_us": ts, "dur_us": dur,
            "resources": ["PROCESS"], "primary_resource": "PROCESS"}


def _run(directory, durations, end):
    directory.mkdir(parents=True)
    (directory / "run-context.json").write_text(json.dumps({
        "trace_epsilon_us": 1000, "max_jobs": 2,
        "resource_capacities": {"PROCESS": 2},
        "wall_clock": {"start_us": 0, "end_us": end}}))
    (directory / "graph.json").write_text(json.dumps({
        "elements": [{"uid": uid} for uid in durations], "dependencies": []}))
    (directory / "trace.json").write_text(json.dumps({
        "spans": [_span(uid, i * 100_000, dur)
                  for i, (uid, dur) in enumerate(durations.items())],
        "phases": []}))
    return directory


BEFORE = {"big.bst": 10_000, "mid.bst": 10_000, "small.bst": 10_000,
          "saver.bst": 40_000, "tiny.bst": 20_000}
AFTER = {"big.bst": 70_000, "mid.bst": 40_000, "small.bst": 20_000,
         "saver.bst": 10_000, "tiny.bst": 60_000}


@pytest.fixture
def regressed(tmp_path):
    """+9.5% on the wall clock - a verdict somebody would argue with."""
    return compare_runs(_run(tmp_path / "baseline", BEFORE, 420_000),
                        _run(tmp_path / "candidate", AFTER, 460_000))


@pytest.fixture
def payload(regressed):
    return regressed.to_dict()


@pytest.fixture
def emitted(tmp_path):
    """What `bga compare --format json` actually writes - the only
    surface a consumer reads, and the one the CLI stamps `schema` on."""
    baseline = _run(tmp_path / "baseline", BEFORE, 420_000)
    candidate = _run(tmp_path / "candidate", AFTER, 460_000)
    args = ["compare", str(baseline), str(candidate), "--format", "json"]
    result = subprocess.run(
        [sys.executable, "-c",
         f"from bga.cli import main; raise SystemExit(main({args!r}))"],
        capture_output=True, text=True)
    return json.loads(result.stdout)


class TestTheAcceptanceTest:
    def test_the_schema_declares_the_key(self):
        """`bga compare --schema` is the contract a consumer reads
        before it writes any code against the payload."""
        document = schemas.schema(schemas.COMPARE)

        assert "verdict_provenance" in document["properties"], sorted(
            document["properties"])
        # `UX-629` moved this from `required` to `bga:always_written`:
        # required under a live id broke every compare/v2 written before
        # this item. The guarantee is unchanged, its holder is not.
        assert "verdict_provenance" in document.get("bga:always_written", ()), (
            "a key the payload always carries and the schema only "
            "permits is one a consumer could lose unnoticed")
        assert "verdict_provenance" not in document["required"], (
            "required under an unmoved id is UX-629's break")

    def test_the_key_is_in_the_payload_at_the_top_level(self, payload):
        assert payload["verdict_provenance"] is not None
        assert payload["verdict_provenance"]["kind"] == "verdict"


class TestThePathsWalkThePayloadTheyShipIn:
    def test_every_evidence_path_resolves_in_this_document(self, payload):
        """The whole point of publishing it here: a reader follows a
        reference into the payload already in front of them. Re-resolved
        against the emitted document, not against the one the record was
        built from."""
        record = payload["verdict_provenance"]
        unresolved = [entry["path"] for entry in record["evidence"]
                      if provenance.resolve(payload, entry["path"])
                      is provenance.UNRESOLVED]
        assert not unresolved, unresolved
        # And the record's own view agrees with the payload's. Without
        # this the clause passes on a record built against some *other*
        # document whose paths happen to spell the same keys - which is
        # exactly the state this item found the chain in.
        disagreed = [entry["path"] for entry in record["evidence"]
                     if entry["resolved"] is not True]
        assert not disagreed, disagreed
        assert len(record["evidence"]) >= 6, (
            "a regression cites the crossing count and its culprits too - "
            "too few paths to be the record this is about")

    def test_each_quoted_value_is_what_the_payload_holds(self, payload):
        """A resolve-only check cannot see a record quoting a stale
        number, which is the half that makes this evidence."""
        for entry in payload["verdict_provenance"]["evidence"]:
            if not entry["resolved"]:
                continue
            assert provenance.resolve(payload, entry["path"]) == entry["value"], (
                entry["path"])

    def test_the_record_names_the_document_it_travels_in(self, emitted):
        """`document` was already `compare/v2` and there was no
        `compare/v2` around it. Read off the *emitted* payload, where
        the CLI stamps `schema`, so the two are the same object."""
        assert emitted["verdict_provenance"]["document"] == emitted["schema"]
        assert emitted["schema"] == schemas.COMPARE


class TestOneRecordAndNotASecondComputation:
    def test_the_published_record_is_the_function_that_built_it(
            self, regressed, payload):
        """A payload that recomputed the chain its own way would be a
        second answer to drift from the first."""
        assert payload["verdict_provenance"] == verdict_provenance(regressed)

    def test_it_is_not_nested_inside_an_object_the_verdict_cites(self, payload):
        """The alternative available to `UX-593` and refused: nesting it
        under `element_deltas` puts the verdict's record inside one of
        the objects the verdict cites."""
        assert "provenance" not in (payload.get("element_deltas") or {})
        assert any(path.startswith("element_deltas.")
                   for path in [entry["path"] for entry
                                in payload["verdict_provenance"]["evidence"]]), (
            "the record does not cite element_deltas, so this says nothing")


class TestARefusalCarriesTheKeyAndNoRecord:
    def test_not_comparable_publishes_null_rather_than_dropping_the_key(
            self, tmp_path):
        """`not_comparable` states its own reason and no band arithmetic
        ran behind it. The key stays so a consumer reads one shape."""
        comparison = compare_runs(_run(tmp_path / "baseline", BEFORE, 420_000),
                                  _run(tmp_path / "candidate", AFTER, 460_000))
        comparison.verdict_kind = "not_comparable"
        refused = comparison.to_dict()

        assert "verdict_provenance" in refused
        assert refused["verdict_provenance"] is None

    @needs_jsonschema
    def test_a_refusal_still_validates_against_the_contract(self, tmp_path):
        """Required *and* nullable - a required non-nullable key would
        make every refusal an invalid document."""
        comparison = compare_runs(_run(tmp_path / "baseline", BEFORE, 420_000),
                                  _run(tmp_path / "candidate", AFTER, 460_000))
        comparison.verdict_kind = "not_comparable"
        document = dict(comparison.to_dict(), schema=schemas.COMPARE)

        jsonschema.validate(document, schemas.schema(schemas.COMPARE))


class TestTheCensusesSeeIt:
    @needs_jsonschema
    def test_the_real_payload_validates_against_the_declared_shape(
            self, payload):
        jsonschema.validate(dict(payload, schema=schemas.COMPARE),
                            schemas.schema(schemas.COMPARE))

    def test_the_declared_shape_is_the_one_every_chain_uses(self):
        """One shape, so a consumer that learned to read `analyze/v5`'s
        chain has learned to read this."""
        node = schemas.schema(schemas.COMPARE)["properties"]["verdict_provenance"]
        assert node["required"] == ["claim", "kind", "document"]
        assert set(node["properties"]) >= {"claim", "kind", "document",
                                           "evidence", "rule", "trace_query",
                                           "unpublished_inputs"}

    def test_the_evidence_quantity_is_declared_from_the_closed_set(
            self, payload):
        """The unit census's rule, on the rows this key adds: a quantity
        a renderer could not act on prints a raw number that looks
        plausible."""
        node = (schemas.schema(schemas.COMPARE)["properties"]
                ["verdict_provenance"]["properties"]["evidence"]["items"]
                ["properties"]["quantity"])
        assert node["enum"] == list(schemas.QUANTITIES)
        declared = [entry["quantity"] for entry
                    in payload["verdict_provenance"]["evidence"]
                    if "quantity" in entry]
        assert declared, "no row declared a quantity - the clause is vacuous"
        assert set(declared) <= set(schemas.QUANTITIES), declared

    def test_every_key_the_payload_emits_stays_required_or_named(self, payload):
        """`UX-190`'s own mirror, re-run over the key this item adds:
        the schema must not have been loosened to admit it."""
        conditional = {
            "host_comparison", "baseline_run_instance", "candidate_run_instance",
            "memory_envelope_delta", "comparability_warning", "baseline_band",
            "baseline_band_shortfall", "element_diff", "marginal_efficiency",
            "cache_churn", "failed_run_details", "efficiency_gate_evaluated",
            "efficiency_gate_signal", "baseline_confidence",
            "candidate_confidence",
        }
        schema = schemas.schema(schemas.COMPARE)
        required = set(schema["required"])
        # `UX-629`'s third state: declared, permitted, and guaranteed by
        # the emitter rather than by `required`. Read off the schema so
        # this cannot drift from what a consumer sees.
        always_written = set(schema.get("bga:always_written", ()))
        unguarded = sorted(set(payload) - required - conditional
                           - always_written - {"schema"})
        assert not unguarded, unguarded


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
