"""UX-535: a fact the analyze document publishes, published once.

Two halves of one census, and they end differently.

`graph_summary` carried `total_elements`, `critical_path_length` and
`max_parallelism` assigned from the same `StructuralMetrics` object
`graph_metrics` publishes - equal by construction, not by luck, and two
of them under a second spelling. `analyze/v5` removes them.

The `producer` half the census also filed is **not** a duplicate, and
the clauses below are what says so: the top-level stamp records the
build that *analyzed*, `run_instance.producer` the build that
*captured*, and they agree only when one build did both. Removing
either loses a fact, so this pins the difference rather than the
sameness.
"""
import json
import pathlib
import shutil
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import producer, schemas

FIXTURES = {
    "golden": REPO / "tests/fixtures/golden/mixed_task_kinds/expected_output.json",
    "with_timeline": REPO / "tests/fixtures/with_timeline/analyze.json",
}

#: The three the summary took from the metrics, and the name each one
#: is read under now.
MOVED = (("total_elements", "num_elements"),
         ("critical_path_length", "critical_path_length"),
         ("max_parallelism", "max_parallelism"))


def _document(label):
    return json.loads(FIXTURES[label].read_text(encoding="utf-8"))


@pytest.mark.parametrize("label", sorted(FIXTURES))
class TestTheTwoGraphSectionsShareNoFact:

    def test_they_share_no_key(self, label):
        document = _document(label)
        summary = document.get("graph_summary") or {}
        metrics = document.get("graph_metrics") or {}
        assert set(summary) & set(metrics) == set(), (
            f"{label}: graph_summary and graph_metrics both publish "
            f"{sorted(set(summary) & set(metrics))}")

    def test_the_summary_republishes_no_metric_under_a_second_name(self, label):
        """The rename half. A key check alone would pass
        `total_elements`, which is `num_elements` spelled differently."""
        document = _document(label)
        summary = document.get("graph_summary") or {}
        metrics = document.get("graph_metrics") or {}
        back = [(quoted, source) for quoted, source in MOVED
                if quoted in summary]
        assert back == [], (
            f"{label}: graph_summary republishes {back}, which "
            f"graph_metrics already publishes")
        # Removed from one section, not from the document: each of the
        # three is still readable, under one name, in the other.
        gone = [source for _, source in MOVED if source not in metrics]
        assert gone == [], (
            f"{label}: graph_metrics no longer publishes {gone}, so the "
            f"removal dropped the fact instead of moving the reader")

    def test_the_scan_read_two_populated_sections(self, label):
        """A document with neither section would pass both clauses
        above by having nothing to compare."""
        document = _document(label)
        summary = document.get("graph_summary") or {}
        metrics = document.get("graph_metrics") or {}
        assert len(summary) >= 3 and len(metrics) >= 8, (
            f"{label}: read {len(summary)} summary and {len(metrics)} "
            f"metric keys; the scan had nothing to judge")

    def test_the_removal_bumped_the_contract(self, label):
        """`UX-190`'s rule: a removed published key moves the version,
        and the document carries the one this build emits."""
        assert _document(label)["schema"] == schemas.ANALYZE
        assert "analyze/v4" in schemas.SUPERSEDED


class TestTheTwoProducerStampsAreTwoFacts:
    """Why the census's third row is not closed the way it was filed.

    Filed as `run_instance.producer == producer`, measured True - on one
    sample, where the same build captured and analyzed. That equality is
    the sample, not the contract.
    """

    OLD_CAPTURE = {"tool": "bga", "version": "0.1.0",
                   "contracts": ["analyze/v2", "compare/v1", "host/v1"]}

    def test_the_two_stamps_differ_when_two_builds_did_the_work(self, tmp_path):
        """The one that decides it: a run captured by an older build,
        analyzed by this one, carries two different stamps."""
        run = tmp_path / "run"
        run.mkdir()
        source = REPO / "tests/fixtures/golden/mixed_task_kinds"
        for name in ("run-context.json", "graph.json", "trace.json"):
            shutil.copy(source / name, run / name)
        context = json.loads((run / "run-context.json").read_text())
        context["producer"] = self.OLD_CAPTURE
        (run / "run-context.json").write_text(json.dumps(context))

        done = subprocess.run(
            [sys.executable, "-m", "bga.cli", "analyze", str(run),
             "--format", "json"],
            capture_output=True, text=True, cwd=REPO, timeout=300)
        assert done.returncode == 0, done.stderr[-2000:]
        document = json.loads(done.stdout)

        captured = (document.get("run_instance") or {}).get("producer")
        analyzed = document.get("producer")
        assert captured == self.OLD_CAPTURE, captured
        assert analyzed and analyzed != captured, (
            "the top-level stamp is the build that analyzed and "
            "run_instance.producer the build that captured; they read "
            f"as one fact here: {analyzed!r}")

    def test_the_comparison_refusal_reads_the_capture_stamp(self):
        """`UX-250`'s refusal is handed `run_instance`, so removing that
        copy would leave it reading a key nothing writes."""
        moved = producer.comparison_movement(
            {"producer": self.OLD_CAPTURE},
            {"producer": producer.stamp()})
        assert moved, "contract movement between two capture stamps is silent"

    def test_the_top_level_stamp_cannot_stand_in_for_it(self):
        """Two runs analyzed by one build carry one top-level stamp, so
        substituting it silences the refusal above."""
        mine = producer.stamp()
        assert producer.comparison_movement(
            {"producer": mine}, {"producer": mine}) == []
