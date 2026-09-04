"""UX-250: a comparison refuses on contract movement, not on a version.

`bga compare` already refuses two runs from different hosts (`UX-186`)
and a caches-off run against a caches-on one, with an exit code of its
own, because "not comparable" and "comparable and equal" must not look
alike. Producer identity was the same kind of axis with nothing
watching it.

The wrong policy is "refuse when the versions differ". It would fire on
every upgrade — including the twenty-eight rounds that moved no
contract at all — and a refusal that fires constantly gets switched
off, which is worth less than none.

So the rule is: **refuse when a contract the comparison reads moved.**
Two runs from `0.1.0` and `0.9.0` compare if nothing they touch
changed; two runs one patch apart refuse if something did. No contract
has moved yet, so every case below is fabricated — which is the point
of building this before the first bump rather than after.
"""
import json
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
EXIT_MISMATCHED = 6


def _stamp(version, contracts):
    return {"producer": {"tool": "bga", "version": version,
                         "contracts": list(contracts)}}


BASE = ["analyze/v2", "compare/v1", "host/v1", "store/v1", "whatif/v1"]


class TestThePolicyIsAboutContractsNotVersions:
    def test_a_version_gap_with_no_contract_movement_still_compares(self):
        """The case that makes this usable. Seven releases apart and
        every contract identical is not a reason to refuse."""
        from bga import producer

        assert producer.comparison_movement(
            _stamp("0.1.0", BASE), _stamp("0.9.0", BASE)) == []

    def test_one_patch_apart_with_a_moved_contract_refuses(self):
        from bga import producer

        moved = ["analyze/v3"] + BASE[1:]
        assert producer.comparison_movement(
            _stamp("0.2.0", BASE), _stamp("0.2.1", moved)) == [
                "analyze/v2 → analyze/v3"]

    def test_a_contract_a_comparison_never_reads_does_not_refuse(self):
        """`whatif/v1` moving does not make two durations incomparable.
        Refusing on every contract is the over-firing this item names."""
        from bga import producer

        elsewhere = BASE[:-1] + ["whatif/v2"]
        assert producer.comparison_movement(
            _stamp("0.2.0", BASE), _stamp("0.3.0", elsewhere)) == []

    def test_the_read_set_is_named_rather_than_everything(self):
        from bga import producer

        assert "analyze/v2" in producer.COMPARISON_CONTRACTS
        assert "whatif/v1" not in producer.COMPARISON_CONTRACTS

    def test_several_moved_contracts_are_all_named(self):
        """A refusal that names one of three sends the reader back for
        the other two."""
        from bga import producer

        moved = ["analyze/v3", "compare/v3", "host/v1", "store/v1", "whatif/v1"]
        assert producer.comparison_movement(
            _stamp("0.2.0", BASE), _stamp("1.0.0", moved)) == [
                "analyze/v2 → analyze/v3", "compare/v1 → compare/v3"]


class TestAMissingStampIsNamedNotRefused:
    def test_an_unstamped_run_does_not_refuse(self):
        """Every artifact written before `UX-249` is unstamped.
        Refusing them would make the stamp's arrival delete the history
        it was built to protect."""
        from bga import producer

        assert producer.comparison_movement({}, _stamp("0.2.0", BASE)) == []
        assert producer.comparison_movement(_stamp("0.2.0", BASE), {}) == []
        assert producer.comparison_movement({}, {}) == []

    def test_but_the_absence_is_said_out_loud(self):
        from bga import producer

        note = producer.comparison_note({}, _stamp("0.2.0", BASE))
        assert note and "baseline" in note and "does not record" in note
        both = producer.comparison_note({}, {})
        assert both and "neither" in both

    def test_two_identical_producers_get_no_note(self):
        """A line every comparison carries is a line nobody reads."""
        from bga import producer

        assert producer.comparison_note(
            _stamp("0.2.0", BASE), _stamp("0.2.0", BASE)) is None

    def test_a_version_gap_with_no_movement_says_so(self):
        from bga import producer

        note = producer.comparison_note(
            _stamp("0.1.0", BASE), _stamp("0.9.0", BASE))
        assert note and "0.1.0" in note and "0.9.0" in note
        assert "no contract a comparison reads moved" in note


class TestTheRefusalReachesTheCommandLine:
    """The policy is worth nothing if `bga compare` does not act on it.
    This drives the real CLI on two real run directories."""

    @pytest.fixture
    def pair(self, tmp_path):
        runs = []
        for name in ("baseline", "candidate"):
            target = tmp_path / name
            out = subprocess.run(
                [sys.executable, "-m", "tools.gen_synthetic_scale_run",
                 str(target), "--seed", "1", "--layers", "2", "--width", "3"],
                capture_output=True, text=True, cwd=REPO)
            assert out.returncode == 0, out.stderr
            runs.append(target)
        return runs

    def _compare(self, baseline, candidate, *extra):
        return subprocess.run(
            [sys.executable, "-m", "bga.cli", "compare",
             str(baseline), str(candidate), *extra],
            capture_output=True, text=True, cwd=REPO)

    def test_matching_producers_compare(self, pair):
        assert self._compare(*pair).returncode == 0

    def test_a_moved_contract_refuses_with_the_mismatch_exit_code(self, pair):
        baseline, candidate = pair
        context = candidate / "run-context.json"
        data = json.loads(context.read_text())
        data["producer"]["version"] = "0.2.1"
        data["producer"]["contracts"] = [
            # `UX-641` made `analyze/v6` the id both runs carry, so
            # the movement this drives has to be to one nothing writes.
            name.replace("analyze/v6", "analyze/v7")
            for name in data["producer"]["contracts"]]
        context.write_text(json.dumps(data, indent=1))

        out = self._compare(baseline, candidate)
        assert out.returncode == EXIT_MISMATCHED, out.stdout
        # The refusal goes to stderr, where every other `UX-78` refusal
        # goes: a caller piping stdout to a JSON parser gets an empty
        # document and a non-zero exit, not a half-parsed report.
        assert "analyze/v6 → analyze/v7" in out.stderr, (
            f"the refusal does not name the contract that moved: {out.stderr}")
        assert "producer_contracts" in out.stderr

    def test_allow_mismatch_still_opts_back_in(self, pair):
        """The same escape every other refusal has. A new refusal with
        no way past it is a new way to be stuck."""
        baseline, candidate = pair
        context = candidate / "run-context.json"
        data = json.loads(context.read_text())
        data["producer"]["contracts"] = [
            # `UX-641` made `analyze/v6` the id both runs carry, so
            # the movement this drives has to be to one nothing writes.
            name.replace("analyze/v6", "analyze/v7")
            for name in data["producer"]["contracts"]]
        context.write_text(json.dumps(data, indent=1))

        out = self._compare(baseline, candidate, "--allow-mismatch")
        assert out.returncode == 0, out.stdout


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
