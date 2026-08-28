"""UX-249: an artifact records which build of `bga` produced it.

The tool reads its own past output as input — `@last`/`@prev`, the
baseline set, `cache-trend`, `store-aggregate`. Measured when this was
filed, `__version__` was read in two places, both the `--version`
string, and written into nothing: a `run-context.json` from round 3 and
one from round 29 were indistinguishable to the tool reading them both.

This file holds the *recording*. It deliberately asserts no refusal —
`UX-250` owns the policy, and separating them is what lets the record
land first, so the policy has something to read on the day it arrives.

It also carries the assertion `tests/test_golden.py` gave up: the
golden snapshot drops `producer` for the same reason it drops
`run_instance`, and a dropped field with nothing else checking it is a
field that silently stops being written.
"""
import json
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]


@pytest.fixture
def synthetic_run(tmp_path):
    """A real run directory, from the real generator."""
    import sys

    sys.argv = ["gen-synthetic", str(tmp_path / "run"), "--seed", "1"]
    from tools import gen_synthetic_scale_run

    gen_synthetic_scale_run.main()
    return tmp_path / "run"


class TestTheStampIsWritten:
    def test_a_run_directory_records_its_producer(self, synthetic_run):
        from bga import __version__, contracts, producer

        context = json.loads((synthetic_run / "run-context.json").read_text())
        stamp = producer.read(context)
        assert stamp is not None, "a fresh run directory carries no producer stamp"
        assert stamp["tool"] == "bga"
        assert stamp["version"] == __version__
        assert stamp["contracts"] == contracts.ids()

    def test_the_recorded_contract_set_is_the_real_one(self, synthetic_run):
        """Not a subset chosen at write time. Direction 10's reason: a
        writer that guesses its own dependencies freezes the guess into
        every artifact, where it cannot be corrected."""
        from bga import producer

        context = json.loads((synthetic_run / "run-context.json").read_text())
        recorded = producer.contracts_of(context)
        assert "sources/v1" in recorded, (
            "the run directory's own on-disk contract is missing from the "
            "set it recorded")
        assert "analyze/v3" in recorded

    def test_the_published_document_records_it_too(self):
        """A payload archived by a CI job is re-read like a stored run."""
        import subprocess
        import sys

        fixture = REPO / "tests/fixtures/golden/mixed_task_kinds"
        out = subprocess.run(
            [sys.executable, "-m", "bga.cli", "analyze", str(fixture),
             "--format", "json"],
            capture_output=True, text=True, cwd=REPO)
        assert out.returncode == 0, out.stderr
        from bga import producer

        assert producer.read(json.loads(out.stdout)) is not None

    def test_the_stamp_the_golden_file_drops_is_asserted_here(self):
        """`tests/test_golden.py` pops `producer` so the snapshot does
        not fail on the first release. That is correct and it is also a
        hole: a dropped field nothing else checks is a field that can
        stop being written unnoticed. This is the other half."""
        golden = (REPO / "tests/test_golden.py").read_text(encoding="utf-8")
        assert 'payload.pop("producer", None)' in golden, (
            "the golden harness no longer drops the stamp - if that is "
            "deliberate this test is what should change, not this comment")


class TestTheAbsenceHasAName:
    def test_an_unstamped_artifact_is_not_a_match(self):
        """Every artifact in every store today predates this. Reading a
        missing stamp as agreement would make the feature's arrival a
        silent claim about a year of history."""
        from bga import producer

        assert producer.read({}) is None
        assert producer.version_of({}) == producer.UNSTAMPED
        assert producer.contracts_of({}) is None
        assert "before" in producer.describe({})

    def test_no_stamp_and_an_empty_set_are_different_answers(self):
        """Both occur - an old artifact, versus one whose enumeration
        failed - and collapsing them would let the second agree with
        anything."""
        from bga import producer

        absent = producer.contracts_of({})
        empty = producer.contracts_of(
            {"producer": {"tool": "bga", "version": "9.9.9", "contracts": []}})
        assert absent is None
        assert empty == []
        assert absent != empty

    def test_a_malformed_stamp_reads_as_absent_rather_than_as_data(self):
        from bga import producer

        for junk in ({"producer": "0.1.0"}, {"producer": []},
                     {"producer": None}, None, "not a dict"):
            assert producer.read(junk) is None, junk


class TestProvenanceNeverBreaksACapture:
    def test_a_failure_to_enumerate_leaves_the_artifact_usable(self,
                                                               monkeypatch):
        """The same rule `add_host_manifest` follows: a run directory
        that could not describe itself is still a run directory."""
        from bga import producer

        def explode():
            raise RuntimeError("no package to walk")

        monkeypatch.setattr(producer, "stamp", explode)
        artifact = {"wall_clock": {"start_us": 0}}
        producer.add(artifact)
        assert artifact == {"wall_clock": {"start_us": 0}}, (
            "a failed stamp left debris in the artifact")

    def test_the_stamp_goes_in_beside_the_host_manifest(self):
        """Both are provenance about the same capture, added by the
        same helper, at the same point - so a run directory that has one
        has the other."""
        common = (REPO / "tools/_run_context_common.py").read_text(
            encoding="utf-8")
        assert "def add_producer(" in common
        for name in ("tools/bst_extract_run.py", "tools/bst_run_context.py"):
            text = (REPO / name).read_text(encoding="utf-8")
            assert "add_producer(run_context)" in text, name
            assert "add_host_manifest(run_context)" in text, name


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
