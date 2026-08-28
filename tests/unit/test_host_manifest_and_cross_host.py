"""UX-186: comparing comparable, when "comparable" includes the machine.

Field feedback: *"generally we can compare builds only built on current
host — maybe we need some kind of sbom capture with information to
enable comparison of runs from different build hosts, to compare
comparable."*

Before this, `run-context.json` recorded `host_cpu_count` and
`host_memory_bytes` - two numbers that call a laptop and a build runner
with the same core count the same machine - and `bga compare` performed
**no host check of any kind**. `UX-92` had already measured a 33%
spread across five captures of one unchanged commit on nominally
identical runners.

The three behaviours, in the order a user meets them: the capture
records the machine, the comparison says when they differ, and the
gates refuse.
"""
import json
import os
import shutil
import subprocess
import sys

import pytest

from bga import hostinfo
from bga.compare import compare_runs

GOLDEN = "tests/fixtures/golden/mixed_task_kinds"

_XEON = {
    "schema": "host/v2",
    "cpu_model": "Intel(R) Xeon(R) Processor @ 2.80GHz",
    "cpu_count": 4,
    "memory_bytes": 16075 * 1024 * 1024,
    "kernel_release": "6.18.44-fc-v21",
    "distro_id": "ubuntu 24.04",
}
_RYZEN = dict(_XEON, cpu_model="AMD Ryzen 9 7950X", cpu_count=32,
              memory_bytes=64000 * 1024 * 1024)


def _run(tmp_path, name, manifest):
    run = tmp_path / name
    shutil.copytree(GOLDEN, run)
    os.remove(run / "expected_output.json")
    context = json.loads((run / "run-context.json").read_text())
    if manifest is not None:
        context["host_manifest"] = manifest
    (run / "run-context.json").write_text(json.dumps(context, indent=2))
    return run


class TestTheManifestDescribesThisMachine:
    def test_it_records_what_it_can_read(self):
        manifest = hostinfo.collect(with_toolchain=False)
        assert manifest["schema"] == "host/v2"
        # Plausible rather than exact: this runs on whatever machine CI
        # gave us, and a test that pins the CPU model pins the runner.
        assert manifest["cpu_count"] and manifest["cpu_count"] >= 1
        assert manifest["memory_bytes"] and manifest["memory_bytes"] > 128 * 1024 ** 2
        assert manifest["kernel_release"]

    def test_the_cpu_model_is_not_the_architecture(self):
        """`platform.processor()` returns `x86_64` on Linux - true of
        every x86 machine ever built, and therefore useless for telling
        two of them apart. That is the mistake this field exists to not
        make."""
        model = hostinfo.collect(with_toolchain=False)["cpu_model"]
        if model is not None:      # a machine with no /proc/cpuinfo
            assert model not in ("x86_64", "aarch64", "arm64")

    def test_the_toolchain_versions_are_collected(self):
        toolchain = hostinfo.collect()["toolchain"]
        assert set(toolchain) == {"bst", "bwrap", "buildbox-run", "cc"}
        # Each is a version line or None - never a guess.
        for value in toolchain.values():
            assert value is None or isinstance(value, str)

    def test_a_capture_records_it(self, tmp_path):
        """End to end through the producer, not by calling the helper:
        `UX-179`'s lesson about wiring nobody tests."""
        from tools._run_context_common import add_host_manifest

        context = {}
        add_host_manifest(context)
        assert context["host_manifest"]["schema"] == "host/v2"

    def test_it_does_not_take_the_operator_supplied_host_field(self):
        """`--host ci-runner-1` has published an *identifier* under
        `host` since UX-12. Redefining a field consumers already read is
        the drift UX-190 was filed about."""
        from tools._run_context_common import add_host_manifest

        context = {"host": "ci-runner-1"}
        add_host_manifest(context)
        assert context["host"] == "ci-runner-1"
        assert "host_manifest" in context


class TestClassification:
    def test_two_manifests_from_one_machine_are_the_same_host(self):
        assert hostinfo.classify(_XEON, dict(_XEON))["status"] == "same"

    def test_a_different_cpu_is_a_different_host(self):
        answer = hostinfo.classify(_XEON, _RYZEN)
        assert answer["status"] == "different"
        assert "cpu_model" in answer["differing"]

    def test_a_missing_manifest_is_unknown_not_different(self):
        """Every capture taken before this field existed. A tool that
        refused each one would be telling users to throw away the
        baselines they came with."""
        answer = hostinfo.classify(None, _XEON)
        assert answer["status"] == "unknown"
        assert answer["missing"] == ["baseline"]

    def test_a_field_neither_side_could_read_is_not_a_difference(self):
        """Two captures from a machine with no readable `/proc/cpuinfo`
        are as comparable as they ever were."""
        blind = dict(_XEON, cpu_model=None)
        assert hostinfo.classify(blind, dict(blind))["status"] == "same"

    def test_present_on_one_side_only_is_a_difference(self):
        """An absence is not evidence of a match."""
        assert hostinfo.differing_fields(
            _XEON, dict(_XEON, cpu_model=None)) == ["cpu_model"]

    def test_a_kernel_bump_alone_is_not_a_different_host(self):
        """Recorded, but not compared: refusing on a point release would
        make the check noise, and noise gets switched off."""
        assert hostinfo.classify(
            _XEON, dict(_XEON, kernel_release="6.19.0"))["status"] == "same"

    def test_the_sentence_names_the_fields_and_their_values(self):
        text = hostinfo.describe(hostinfo.classify(_XEON, _RYZEN), _XEON, _RYZEN)
        assert "Xeon" in text and "Ryzen" in text
        assert "CPU model" in text

    def test_matching_hosts_produce_no_sentence(self):
        assert hostinfo.describe(
            hostinfo.classify(_XEON, dict(_XEON)), _XEON, _XEON) is None


class TestWhatCompareDoes:
    def test_a_cross_host_pair_still_compares_and_says_so(self, tmp_path):
        """Looking is fine; gating is not. The numbers render, with the
        caveat attached."""
        result = compare_runs(_run(tmp_path, "a", _XEON), _run(tmp_path, "b", _RYZEN))
        assert result.host_comparison["status"] == "different"
        assert "different machines" in (result.comparability_warning or "")
        assert result.verdict, "the comparison itself was refused"

    def test_the_confidence_is_capped(self, tmp_path):
        """Two machines' durations are not one measurement, whatever
        each run's own analysis thought of its own coverage."""
        result = compare_runs(_run(tmp_path, "a", _XEON), _run(tmp_path, "b", _RYZEN))
        assert result.low_confidence

    def test_a_same_host_pair_is_untouched(self, tmp_path):
        result = compare_runs(_run(tmp_path, "a", _XEON), _run(tmp_path, "b", dict(_XEON)))
        assert result.host_comparison["status"] == "same"
        assert "different machines" not in (result.comparability_warning or "")

    def test_a_manifest_less_run_says_host_unknown_and_still_compares(self, tmp_path):
        result = compare_runs(_run(tmp_path, "old", None), _run(tmp_path, "a", _XEON))
        assert result.host_comparison["status"] == "unknown"
        assert "Host unknown" in (result.comparability_warning or "")
        assert result.verdict

    def test_it_is_published_in_the_json(self, tmp_path):
        result = compare_runs(_run(tmp_path, "a", _XEON), _run(tmp_path, "b", _RYZEN))
        assert result.to_dict()["host_comparison"]["differing"]


def _compare(args):
    return subprocess.run(
        [sys.executable, "-c",
         "from bga.cli import main; raise SystemExit(main(%r))" % (args,)],
        capture_output=True, text=True, cwd=os.getcwd())


class TestWhatTheGateDoes:
    """Exit codes, through the real CLI - the surface a pipeline sees."""

    def test_a_cross_host_gate_refuses_with_exit_6(self, tmp_path):
        baseline = str(_run(tmp_path, "a", _XEON))
        candidate = str(_run(tmp_path, "b", _RYZEN))
        result = _compare(["compare", baseline, candidate, "--fail-on-regression"])
        assert result.returncode == 6, result.stderr
        assert "Cross-host gate FAILED" in result.stderr
        assert "cpu_model" in result.stderr, "the refusal must name what differs"

    def test_allow_cross_host_opts_back_in(self, tmp_path):
        baseline = str(_run(tmp_path, "a", _XEON))
        candidate = str(_run(tmp_path, "b", _RYZEN))
        result = _compare(["compare", baseline, candidate, "--fail-on-regression",
                           "--allow-cross-host"])
        assert result.returncode == 0, result.stderr

    def test_without_a_gate_a_cross_host_pair_exits_zero(self, tmp_path):
        """`bga compare` on its own is a question, and the answer here is
        "these are different machines" - printed, not refused."""
        baseline = str(_run(tmp_path, "a", _XEON))
        candidate = str(_run(tmp_path, "b", _RYZEN))
        result = _compare(["compare", baseline, candidate])
        assert result.returncode == 0, result.stderr
        assert "different machines" in result.stdout

    def test_an_unknown_host_does_not_refuse(self, tmp_path):
        baseline = str(_run(tmp_path, "old", None))
        candidate = str(_run(tmp_path, "a", _XEON))
        result = _compare(["compare", baseline, candidate, "--fail-on-regression"])
        assert result.returncode == 0, result.stderr


class TestTheBaselineSetWarns:
    def test_a_mixed_host_set_is_named(self, tmp_path):
        from tools.bst_baseline_set import check_homogeneity

        members = []
        for name, manifest in (("a", _XEON), ("b", _RYZEN)):
            run = _run(tmp_path, name, manifest)
            members.append({
                "ref": {"ref": f"captures/x-{name}", "run_id": name},
                "run_dir": str(run),
                "context": {},
            })
        drift = check_homogeneity(members)["host_drift"]
        assert drift and "different machines" in drift["message"]
        assert len(drift["cpu_models"]) == 2

    def test_a_single_host_set_is_silent(self, tmp_path):
        from tools.bst_baseline_set import check_homogeneity

        members = [{
            "ref": {"ref": f"captures/x-{name}", "run_id": name},
            "run_dir": str(_run(tmp_path, name, dict(_XEON))),
            "context": {},
        } for name in ("a", "b")]
        assert check_homogeneity(members)["host_drift"] is None

    def test_it_warns_rather_than_refuses(self, tmp_path):
        """A band across machines is a real object somebody may want to
        look at; it is not the object the band's arithmetic claims to
        be. Warning, not `mismatches`."""
        from tools.bst_baseline_set import check_homogeneity

        members = [{
            "ref": {"ref": f"captures/x-{name}", "run_id": name},
            "run_dir": str(_run(tmp_path, name, manifest)),
            "context": {},
        } for name, manifest in (("a", _XEON), ("b", _RYZEN))]
        homogeneity = check_homogeneity(members)
        assert homogeneity["host_drift"]
        assert not homogeneity["mismatches"], (
            "a mixed-host set exits 6 from `bga baseline` if this becomes a "
            "mismatch, which is a stronger claim than the item asked for")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
