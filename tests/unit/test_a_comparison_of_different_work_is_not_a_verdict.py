"""UX-1323: two runs that built different elements are different work, not IMPROVED.

The walk's two incremental snapshots rebuilt `apps/browser.bst` and then
`apps/shell.bst`; `bga compare` called the pair IMPROVED (-56.3%) while
saying no element present in both runs shrank.
"""

import json
import subprocess
import sys
from types import SimpleNamespace

from bga import schemas
from bga.compare import regression_gate_failed

EXIT_OK = 0
EXIT_REGRESSION = 4
EXIT_MISMATCHED_RUNS = 6
UIDS = ["common.bst", "other.bst", "browser.bst", "shell.bst"]


def _bga(*args):
    return subprocess.run([sys.executable, "-m", "bga.cli", *args], capture_output=True, text=True)


def _run(tmp_path, name, built, run_mode=None, gap_us=0):
    """One run of the same three-element project; `built` is `[(uid, dur_us)]`, laid end to end `gap_us` apart."""
    run_dir = tmp_path / name
    run_dir.mkdir()
    identity = {"manifest_hash": "fixture-project", "targets": ["common.bst"]}
    spans, at = [], 0
    for uid, dur in built:
        spans.append(
            {
                "task_key": f"{uid}|BUILD|BUILD|0",
                "ts_us": at,
                "dur_us": dur,
                "resources": ["PROCESS"],
                "primary_resource": "PROCESS",
            }
        )
        at += dur + gap_us
    context = {
        "trace_epsilon_us": 1000,
        "resource_capacities": {"PROCESS": 2},
        "run_identity": identity,
        "wall_clock": {"start_us": 0, "end_us": at},
    }
    if run_mode is not None:
        built_count = len(UIDS) if run_mode == "full" else 1
        context["queue_summary"] = {"build": {"processed": built_count, "skipped": len(UIDS) - built_count}}
    (run_dir / "run-context.json").write_text(json.dumps(context))
    (run_dir / "graph.json").write_text(
        json.dumps(
            {
                "elements": [{"uid": uid, "requested_target": uid == "common.bst"} for uid in UIDS],
                "dependencies": [],
                "run_identity_hash": identity["manifest_hash"],
            }
        )
    )
    (run_dir / "trace.json").write_text(
        json.dumps({"run_identity_hash": identity["manifest_hash"], "spans": spans, "phases": []})
    )
    return run_dir


def _pair(tmp_path, common_after=1_010_000, candidate_other="shell.bst"):
    baseline = _run(tmp_path, "browser", [("common.bst", 1_000_000), ("browser.bst", 6_300_000)])
    candidate = _run(tmp_path, "shell", [("common.bst", common_after), (candidate_other, 1_200_000)])
    return str(baseline), str(candidate)


def _json(baseline, candidate):
    result = _bga("compare", baseline, candidate, "--format", "json")
    assert result.returncode == EXIT_OK, result.stderr
    return json.loads(result.stdout)


class TestDifferentBuiltSetsAreDifferentWork:
    def test_the_text_says_different_work_and_names_each_sides_elements(self, tmp_path):
        result = _bga("compare", *_pair(tmp_path))
        assert result.returncode == EXIT_OK, result.stderr
        assert "Verdict: DIFFERENT WORK" in result.stdout, result.stdout
        assert "Verdict: IMPROVED" not in result.stdout
        assert "only the baseline built browser.bst; only the candidate built shell.bst" in result.stdout

    def test_the_ci_comment_heads_with_it_and_names_the_elements(self, tmp_path):
        result = _bga("compare", *_pair(tmp_path), "--format", "ci-comment")
        assert result.returncode == EXIT_OK, result.stderr
        assert "**DIFFERENT WORK**" in result.stdout, result.stdout
        assert "only the baseline built browser.bst; only the candidate built shell.bst" in result.stdout

    def test_the_json_carries_the_kind_from_the_published_enum(self, tmp_path):
        document = _json(*_pair(tmp_path))
        assert (document["verdict"], document["verdict_kind"]) == ("different work", "different_work")
        assert "different_work" in schemas.VERDICT_KINDS
        rows = {row["element_uid"]: row["verdict_kind"] for row in document["element_deltas"]["rows"]}
        assert rows["common.bst"] == "no_significant_change", rows

    def test_a_common_element_that_moved_keeps_the_directional_verdict(self, tmp_path):
        document = _json(*_pair(tmp_path, common_after=4_000_000))
        assert document["verdict_kind"] == "improved", document["verdict"]

    def test_common_elements_that_moved_and_netted_to_zero_keep_the_directional_verdict(self, tmp_path):
        """+0.5 s and -0.5 s sum to 0 signed but 1 s absolute, past 1% of the 8.3 s baseline."""
        baseline = _run(
            tmp_path, "b", [("common.bst", 1_000_000), ("other.bst", 1_000_000), ("browser.bst", 6_300_000)]
        )
        candidate = _run(tmp_path, "c", [("common.bst", 1_500_000), ("other.bst", 500_000), ("shell.bst", 1_200_000)])
        document = _json(str(baseline), str(candidate))
        assert document["verdict_kind"] == "improved", document["verdict"]

    def test_the_same_built_set_keeps_the_directional_verdict(self, tmp_path):
        built = [("common.bst", 1_000_000), ("browser.bst", 6_300_000)]
        baseline = _run(tmp_path, "before", built)
        candidate = _run(tmp_path, "after", built, gap_us=2_000_000)
        document = _json(str(baseline), str(candidate))
        assert document["verdict_kind"] == "regressed", document["verdict"]


class TestTheGatesKeepTheirBehaviour:
    def test_the_band_gate_still_fails_a_slower_different_work_pair(self):
        comparison = SimpleNamespace(
            baseline_band={"low_us": 0, "high_us": 1}, verdict_kind="different_work", deltas={"total_duration_us": 5}
        )
        assert regression_gate_failed(comparison, against_band=True)
        comparison.deltas = {"total_duration_us": -5}
        assert not regression_gate_failed(comparison, against_band=True)

    def test_fail_on_regression_still_reads_the_total_on_a_slower_different_work_pair(self, tmp_path):
        """The verdict says different work; the duration gate reads the total delta (cli.md), and exits 4."""
        baseline = _run(tmp_path, "shell", [("common.bst", 1_000_000), ("shell.bst", 1_200_000)])
        candidate = _run(tmp_path, "browser", [("common.bst", 1_000_000), ("browser.bst", 6_300_000)])
        result = _bga("compare", str(baseline), str(candidate), "--fail-on-regression")
        assert "Verdict: DIFFERENT WORK" in result.stdout, result.stdout
        assert result.returncode == EXIT_REGRESSION, (result.returncode, result.stderr)


class TestTheRunModeRefusalNamesTheNextStep:
    def test_the_refusal_says_what_to_run(self, tmp_path):
        cold = _run(tmp_path, "cold", [(uid, 1_000_000) for uid in UIDS], run_mode="full")
        warm = _run(tmp_path, "warm", [("shell.bst", 1_000_000)], run_mode="incremental")
        result = _bga("compare", str(cold), str(warm))
        assert result.returncode == EXIT_MISMATCHED_RUNS
        assert "Next: the next snapshot compares incremental against incremental" in result.stderr, result.stderr
        assert "XDG_CACHE_HOME=$(mktemp -d) bga snapshot -- bst build" in result.stderr
