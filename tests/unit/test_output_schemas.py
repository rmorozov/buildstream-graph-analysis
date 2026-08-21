"""UX-190: the outputs say what shape they are, and mean it.

Field feedback: *"our analyze schema and other schemas evolved
considerably — maybe it's good idea to update them and have a command
line switch [to] output schemas [the] tool support[s] and produce[s] —
this can be later used to visualize json report."*

The guard that matters is the **round trip**: the golden run's real
`--format json` output validated against the schema `bga <cmd>
--schema` prints. A schema written beside a payload and never checked
against it is documentation, and documentation drifts - which is the
whole finding (`runs_outside_band` → `edges_outside_band` was renamed
in a published payload one round before this item was filed, with
nothing to signal it).
"""
import json
import os
import shutil
import subprocess
import sys

import pytest

from bga import schemas

# `UX-197`: this was `pytest.importorskip("jsonschema")` at module
# scope, which skips the *module*. Without dev extras that renders all
# 25 guards as a single "1 skipped" line - measured in a clean venv:
#
#     collected 0 items / 1 skipped
#
# In CI the extras are installed, so it was real there and silent
# everywhere else, which is the wrong way round for a guard whose whole
# job is to catch a schema drifting from its payload. The module now
# always collects, and `test_the_dev_extras_are_actually_here` below
# *fails* rather than skips wherever `BGA_EXPECT_DEV` is set - CI sets
# it; a contributor's bare venv does not, and still gets the honest skip.
try:
    import jsonschema
except ImportError:                      # pragma: no cover - the point
    jsonschema = None

needs_jsonschema = pytest.mark.skipif(
    jsonschema is None,
    reason="jsonschema is not installed - `pip install -e '.[dev]'`")

GOLDEN = "tests/fixtures/golden/mixed_task_kinds"


def test_the_dev_extras_are_actually_here():
    """The one test in this file that runs without `jsonschema`.

    An environment that claims to be a dev environment and cannot
    validate a schema is a broken dev environment, and it should say so
    in the one place anybody reads - a red test - rather than in a
    skip line nobody counts.
    """
    if not os.environ.get("BGA_EXPECT_DEV"):
        pytest.skip("not a dev environment by its own account "
                    "(BGA_EXPECT_DEV is unset)")
    assert jsonschema is not None, (
        "BGA_EXPECT_DEV is set, so this environment claims the dev extras, "
        "but `jsonschema` is missing and every schema guard in this module "
        "just skipped. `pip install -e '.[dev]'`.")


def _bga(args):
    return subprocess.run(
        [sys.executable, "-c",
         "from bga.cli import main; raise SystemExit(main(%r))" % (args,)],
        capture_output=True, text=True, cwd=os.getcwd())


def _two_runs(tmp_path):
    for name in ("a", "b"):
        run = tmp_path / name
        shutil.copytree(GOLDEN, run)
        os.remove(run / "expected_output.json")
    return str(tmp_path / "a"), str(tmp_path / "b")


@needs_jsonschema
class TestEveryPayloadDeclaresItsShape:
    def test_analyze(self):
        payload = json.loads(_bga(["analyze", GOLDEN, "--format", "json"]).stdout)
        assert payload["schema"] == schemas.ANALYZE

    def test_compare(self, tmp_path):
        baseline, candidate = _two_runs(tmp_path)
        payload = json.loads(
            _bga(["compare", baseline, candidate, "--format", "json"]).stdout)
        assert payload["schema"] == schemas.COMPARE

    def test_blast(self):
        payload = json.loads(_bga(
            ["blast", "base.bst", GOLDEN, "--format", "json", "--no-cost"]).stdout)
        assert payload["schema"] == schemas.BLAST

    def test_the_version_is_the_first_key(self):
        """A consumer reading the head of a streamed or truncated
        document should learn what it is before it reads anything it
        would have to interpret."""
        raw = _bga(["analyze", GOLDEN, "--format", "json"]).stdout
        assert json.loads(raw, object_pairs_hook=lambda pairs: pairs)[0][0] == "schema"


@needs_jsonschema
class TestTheSwitchPrintsTheSchema:
    @pytest.mark.parametrize("command,name", [
        ("analyze", schemas.ANALYZE),
        ("compare", schemas.COMPARE),
        ("blast", schemas.BLAST),
        ("floors", schemas.ANALYZE),
    ])
    def test_it_prints_and_exits_zero(self, command, name):
        result = _bga([command, "--schema"])
        assert result.returncode == 0, result.stderr
        printed = json.loads(result.stdout)
        assert printed["properties"]["schema"]["const"] == name

    def test_it_needs_no_run_directory(self):
        """`--schema` answers about a shape, not about a run. Requiring
        a run directory to ask what the output looks like would be the
        kind of papercut this item is made of."""
        assert _bga(["analyze", "--schema"]).returncode == 0

    def test_a_command_with_no_versioned_output_says_so(self):
        result = _bga(["doctor", "--schema"])
        assert result.returncode == 2
        assert "produces no versioned JSON output" in result.stderr


@needs_jsonschema
class TestTheRoundTrip:
    """The acceptance: real output, real schema, real validator."""

    def test_analyze_output_validates_against_its_own_schema(self):
        payload = json.loads(_bga(["analyze", GOLDEN, "--format", "json"]).stdout)
        jsonschema.validate(payload, json.loads(_bga(["analyze", "--schema"]).stdout))

    def test_compare_output_validates_against_its_own_schema(self, tmp_path):
        baseline, candidate = _two_runs(tmp_path)
        payload = json.loads(
            _bga(["compare", baseline, candidate, "--format", "json"]).stdout)
        jsonschema.validate(payload, json.loads(_bga(["compare", "--schema"]).stdout))

    def test_blast_output_validates_against_its_own_schema(self):
        payload = json.loads(_bga(
            ["blast", "base.bst", GOLDEN, "--format", "json", "--no-cost"]).stdout)
        jsonschema.validate(payload, json.loads(_bga(["blast", "--schema"]).stdout))

    def test_a_section_projection_validates_too(self):
        """`bga floors --format json` is the same document restricted to
        its own keys. It must not be a second, undeclared shape."""
        payload = json.loads(_bga(["floors", GOLDEN, "--format", "json"]).stdout)
        assert payload["section"] == "floors"
        jsonschema.validate(payload, schemas.schema(schemas.ANALYZE))

    def test_removing_a_field_from_the_payload_reddens(self):
        """The mutation the acceptance names, run here rather than by
        hand: the schema is a claim about the payload, so a payload that
        stops honouring it must fail."""
        payload = json.loads(_bga(["analyze", GOLDEN, "--format", "json"]).stdout)
        del payload["run_id"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(payload, schemas.schema(schemas.ANALYZE))

    def test_a_renamed_required_field_reddens(self):
        """The finding's own case. `runs_outside_band` →
        `edges_outside_band` shipped in a published payload with nothing
        to notice it."""
        payload = json.loads(_bga(["analyze", GOLDEN, "--format", "json"]).stdout)
        payload["run_id_renamed"] = payload.pop("run_id")
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(payload, schemas.schema(schemas.ANALYZE))

    def test_a_renamed_optional_field_is_caught_by_the_key_pin_instead(self):
        """`analyze`'s section-restricted keys cannot be `required` - a
        projection would fail - so the schema alone does not see them
        move. `ANALYZE_FULL_KEYS` is what covers them, and this pins
        *which* guard catches what, so neither is mistaken for the
        other."""
        payload = json.loads(_bga(["analyze", GOLDEN, "--format", "json"]).stdout)
        payload["floors_renamed"] = payload.pop("floors")

        jsonschema.validate(payload, schemas.schema(schemas.ANALYZE))
        assert "floors" in schemas.ANALYZE_FULL_KEYS
        assert "floors" not in payload, "the key pin is the guard that fires here"

    def test_an_added_field_does_not(self):
        """The other half of the contract: an addition is not a breaking
        change, and a schema that rejected one would turn every new
        signal into a version bump."""
        payload = json.loads(_bga(["analyze", GOLDEN, "--format", "json"]).stdout)
        payload["a_signal_from_the_future"] = {"measured": True}
        jsonschema.validate(payload, schemas.schema(schemas.ANALYZE))


@needs_jsonschema
class TestTheSchemaCannotBeLoosenedToPass:
    """The round trip only checks the payload against the schema, so a
    `required` entry *deleted* to make a failing test pass loosens the
    contract and nothing notices. This is the mirror: every key the real
    payload emits must be required.

    `analyze` is exempt by design - its section-restricted keys cannot
    be required - and `ANALYZE_FULL_KEYS` covers it instead.
    """

    def test_compares_schema_requires_every_key_it_emits(self, tmp_path):
        baseline, candidate = _two_runs(tmp_path)
        payload = json.loads(
            _bga(["compare", baseline, candidate, "--format", "json"]).stdout)
        required = set(schemas.schema(schemas.COMPARE)["required"])
        # Keys that are genuinely conditional are listed here, named, so
        # the exemption is a decision rather than an omission.
        conditional = {
            "host_comparison", "baseline_run_instance", "candidate_run_instance",
            "memory_envelope_delta", "comparability_warning", "baseline_band",
            "baseline_band_shortfall", "element_diff", "marginal_efficiency",
            "cache_churn", "failed_run_details", "efficiency_gate_evaluated",
            "efficiency_gate_signal", "baseline_confidence", "candidate_confidence",
        }
        unguarded = sorted(set(payload) - required - conditional)
        assert not unguarded, (
            f"compare emits {unguarded}, which the schema neither requires nor "
            f"names as conditional - so removing one would break a consumer "
            f"and pass every test here.")

    def test_blasts_schema_requires_every_key_it_emits(self):
        payload = json.loads(_bga(
            ["blast", "base.bst", GOLDEN, "--format", "json", "--no-cost"]).stdout)
        required = set(schemas.schema(schemas.BLAST)["required"])
        assert not sorted(set(payload) - required), (
            "every key `bga blast` emits is unconditional and should be required")


@needs_jsonschema
class TestTheFullReportKeepsItsKeys:
    """`required` cannot cover `analyze`'s optional keys - a section
    projection would fail it - so the full key set is pinned separately
    and checked against the real golden output. This is the list a
    rename silently shortens."""

    def test_every_pinned_key_is_present(self):
        payload = json.loads(_bga(["analyze", GOLDEN, "--format", "json"]).stdout)
        missing = [key for key in schemas.ANALYZE_FULL_KEYS if key not in payload]
        assert not missing, (
            f"`bga analyze --format json` no longer emits {missing}. If that is "
            f"deliberate, bump the schema version and update ANALYZE_FULL_KEYS.")

    def test_the_pin_describes_the_real_output(self):
        """And the other direction, so the pin cannot rot into a list of
        keys the tool stopped producing years ago."""
        payload = json.loads(_bga(["analyze", GOLDEN, "--format", "json"]).stdout)
        unpinned = sorted(set(payload) - set(schemas.ANALYZE_FULL_KEYS))
        assert not unpinned, (
            f"new top-level key(s) {unpinned} - add them to ANALYZE_FULL_KEYS "
            f"(an addition does not bump the version) and to _ANALYZE_OPTIONAL "
            f"so the schema types them.")


@needs_jsonschema
class TestTheSchemasThemselves:
    def test_every_name_resolves(self):
        for name in schemas.names():
            assert schemas.schema(name)["properties"]["schema"]["const"] == name

    def test_an_unknown_name_names_the_ones_that_exist(self):
        with pytest.raises(KeyError) as caught:
            schemas.schema("analyze/v99")
        assert "analyze/v1" in str(caught.value)

    def test_stamp_does_not_mutate_its_argument(self):
        payload = {"run_id": "x"}
        stamped = schemas.stamp(payload, schemas.ANALYZE)
        assert "schema" not in payload
        assert list(stamped)[0] == "schema"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
