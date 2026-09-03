"""UX-567: I6 (Part 34) is a hard gate, not a finding.

Observed resource occupancy above a capacity the run *declared* is a
broken capture - every capacity-derived bound divides by that C_p - so
it fails a Part 33.1 hard gate and carries the excursion as evidence.
A resource whose capacity is simply unknown is never gated: a default
would make the gate report the default rather than the run.
"""
import json
from pathlib import Path

import pytest

from bga import BuildEfficiencyAnalyzer
from bga.occupancy.sweep import (
    compute_capacity_excursions,
    compute_occupancy_segments,
    compute_peak_occupancy,
)

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures/golden/mixed_task_kinds"
EPSILON_US = 1000
DURATION_US = 10000


def _write_run(tmp_path, name, run_context, concurrent=3, resource="PROCESS"):
    """`concurrent` independent elements, all running over the same
    interval, so occupancy on `resource` is exactly `concurrent`."""
    uids = [f"e{i}.bst" for i in range(concurrent)]
    graph = {
        "elements": [{"uid": u, "requested_target": True} for u in uids],
        "dependencies": [],
    }
    trace = {
        "spans": [
            {"task_key": f"{u}|BUILD|BUILD|0", "ts_us": 0, "dur_us": DURATION_US,
             "resources": [resource], "primary_resource": resource}
            for u in uids
        ],
        "phases": [],
    }
    run_dir = tmp_path / name
    run_dir.mkdir()
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))
    return run_dir


def _analyze(tmp_path, name, run_context, concurrent=3, resource="PROCESS"):
    run_dir = _write_run(tmp_path, name, run_context, concurrent, resource)
    analyzer = BuildEfficiencyAnalyzer(run_dir)
    analyzer.load()
    return analyzer, analyzer.analyze()


def _base_context(**extra):
    context = {"trace_epsilon_us": EPSILON_US,
               "wall_clock": {"start_us": 0, "end_us": DURATION_US}}
    context.update(extra)
    return context


def _i6_violations(result):
    return [v for v in (result.violations or []) if v.get("invariant") == "I6"]


class TestTheGateFires:
    """Occupancy above a declared capacity is a hard-gate failure."""

    def test_three_concurrent_against_a_declared_two_fails_the_gate(self, tmp_path):
        _, result = _analyze(
            tmp_path, "over",
            _base_context(resource_capacities={"PROCESS": 2}), concurrent=3)
        assert result.confidence["hard_gates"]["occupancy_within_capacity"] is False

    def test_the_failure_carries_the_excursion_as_evidence(self, tmp_path):
        _, result = _analyze(
            tmp_path, "over",
            _base_context(resource_capacities={"PROCESS": 2}), concurrent=3)
        violations = _i6_violations(result)
        assert len(violations) == 1, result.violations
        assert violations[0]["gate"] == "occupancy_within_capacity"
        excursion, = violations[0]["detail"]
        assert excursion["resource"] == "PROCESS"
        assert excursion["capacity"] == 2
        assert excursion["peak_occupancy"] == 3
        assert excursion["over_capacity_us"] == DURATION_US

    def test_max_jobs_alone_is_a_declaration_the_gate_reads(self, tmp_path):
        """`max_jobs` is run-context/v9's own `builders` field, which is
        what `compute_default_capacities` already treats as PROCESS's
        C_p - a declaration, unlike that function's literal fallbacks."""
        _, result = _analyze(
            tmp_path, "over", _base_context(max_jobs=2), concurrent=3)
        assert result.confidence["hard_gates"]["occupancy_within_capacity"] is False

    def test_the_gate_is_hard_not_a_soft_caveat(self, tmp_path):
        """Part 33.1: it sits in `hard_gates`, so `all(...)` - which the
        suite uses as the healthy-run assertion - is False."""
        _, result = _analyze(
            tmp_path, "over",
            _base_context(resource_capacities={"PROCESS": 2}), concurrent=3)
        assert not all(result.confidence["hard_gates"].values())


class TestTheGateDoesNotFireOnAGuess:
    """A capacity nobody declared is unknown, and unknown is not a breach."""

    def test_no_declared_capacity_and_no_max_jobs_never_fires(self, tmp_path):
        """Eight concurrent PROCESS tasks and nothing declared: the
        defaults in `bga/floors/capacity.py` would call this a breach of
        4, which would be the default speaking, not the capture."""
        _, result = _analyze(tmp_path, "unknown", _base_context(), concurrent=8)
        assert result.confidence["hard_gates"]["occupancy_within_capacity"] is True
        assert _i6_violations(result) == []

    def test_a_resource_declared_for_another_resource_is_not_borrowed(self, tmp_path):
        """DOWNLOAD occupancy of 3 with only PROCESS declared: the
        PROCESS number must not be applied to DOWNLOAD."""
        _, result = _analyze(
            tmp_path, "other",
            _base_context(resource_capacities={"PROCESS": 1}),
            concurrent=3, resource="DOWNLOAD")
        assert result.confidence["hard_gates"]["occupancy_within_capacity"] is True

    def test_occupancy_exactly_at_capacity_passes(self, tmp_path):
        _, result = _analyze(
            tmp_path, "at",
            _base_context(resource_capacities={"PROCESS": 3}), concurrent=3)
        assert result.confidence["hard_gates"]["occupancy_within_capacity"] is True


class TestTheGateReadsThePublishedOccupancy:
    """Not a second, independent count of the same thing."""

    @pytest.mark.parametrize("concurrent,capacity", [(3, 2), (5, 1), (8, 4)])
    def test_the_peak_is_the_sweeps_own_peak(self, tmp_path, concurrent, capacity):
        analyzer, _ = _analyze(
            tmp_path, "run",
            _base_context(resource_capacities={"PROCESS": capacity}),
            concurrent=concurrent)
        segments = compute_occupancy_segments(analyzer.normalized_tasks)
        _, peak_resources = compute_peak_occupancy(segments)
        published_peak = {r.value: c for r, c in peak_resources.items()}

        excursion, = compute_capacity_excursions(
            analyzer.normalized_tasks, {"PROCESS": capacity})
        assert excursion["peak_occupancy"] == published_peak["PROCESS"]

    def test_the_over_capacity_time_is_measured_not_the_whole_horizon(self, tmp_path):
        """Two tasks over a declared one, overlapping for a quarter of
        the horizon: `over_capacity_us` is that quarter."""
        run_dir = tmp_path / "partial"
        run_dir.mkdir()
        (run_dir / "run-context.json").write_text(json.dumps(_base_context(
            resource_capacities={"PROCESS": 1})))
        (run_dir / "graph.json").write_text(json.dumps({
            "elements": [{"uid": "a.bst", "requested_target": True},
                         {"uid": "b.bst", "requested_target": True}],
            "dependencies": []}))
        (run_dir / "trace.json").write_text(json.dumps({"spans": [
            {"task_key": "a.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 20000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "b.bst|BUILD|BUILD|0", "ts_us": 15000, "dur_us": 20000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
        ], "phases": []}))
        analyzer = BuildEfficiencyAnalyzer(run_dir)
        analyzer.load()
        analyzer.analyze()

        excursion, = compute_capacity_excursions(
            analyzer.normalized_tasks, {"PROCESS": 1})
        assert excursion["over_capacity_us"] == 5000
        assert excursion["first_start_us"] == 15000
        assert excursion["first_end_us"] == 20000


class TestTheFixturesThisRepositoryShips:
    """The gate must not fire on any capture already committed."""

    def test_the_golden_run_is_within_its_declared_capacity(self):
        analyzer = BuildEfficiencyAnalyzer(GOLDEN)
        analyzer.load()
        result = analyzer.analyze()
        assert result.confidence["hard_gates"]["occupancy_within_capacity"] is True
