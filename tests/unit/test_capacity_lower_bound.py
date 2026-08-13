"""Regression tests for P1-08: capacity lower bound (LB) generalized
beyond a single hardcoded PROCESS pool.

`bga/analyzer.py::_compute_floors` used to compute `W_p/C_p` only for a
hardcoded PROCESS resource, with `# TODO: Add DOWNLOAD/UPLOAD work
bounds` / `# TODO: Add exclusive serialization bounds` marking the gap -
LB was an under-approximation whenever a non-PROCESS resource was the
real bottleneck. Fixed to iterate over every resource type actually used
by any task, plus a hard serialization floor for resources declared
`exclusive_resources` in run-context (Part 31.3).

Generalizing LB exposed a second, previously-latent bug: replay's
`_get_task_resources` was hardcoded to `{'PROCESS': 1}` regardless of a
task's actual resources, so the replay makespan T_C never modeled
DOWNLOAD/UPLOAD contention either - meaning a correctly higher LB could
end up exceeding T_C, violating invariant I2 (LB <= T_C). Fixed
alongside this task since leaving it broken would mean the "fix" itself
produced an invariant-violating result; the fix only changes the
resource-requirement lookup, not replay's scheduling algorithm/heuristics.
"""
import json

from bga import BuildEfficiencyAnalyzer


def _write_run_dir(tmp_path, run_context, elements, spans):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    graph = {
        "elements": [{"uid": uid, "requested_target": is_target} for uid, is_target in elements],
        "dependencies": [],
    }
    trace = {"spans": spans, "phases": []}
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))
    return run_dir


def test_lb_reflects_download_bottleneck_not_just_process(tmp_path):
    """5 elements, each with an 80000us DOWNLOAD-only FETCH task sharing a
    single DOWNLOAD slot (capacity 1) - a hard 400000us serialization
    floor - plus a cheap 10000us PROCESS-only BUILD task each (capacity
    4, negligible bound). PROCESS-only LB would be far smaller than the
    real DOWNLOAD bound.
    """
    run_context = {
        "trace_epsilon_us": 50000, "wall_start_us": 0, "wall_end_us": 500000,
        "max_jobs": 4, "resource_capacities": {"PROCESS": 4, "DOWNLOAD": 1},
    }
    elements = [(f"e{i}.bst", i == 0) for i in range(5)]
    spans = []
    for i in range(5):
        spans.append({
            "task_key": f"e{i}.bst|FETCH|FETCH|0", "ts_us": i * 20000, "dur_us": 80000,
            "resources": ["DOWNLOAD"], "primary_resource": "DOWNLOAD",
        })
        spans.append({
            "task_key": f"e{i}.bst|BUILD|BUILD|0", "ts_us": 400000 + i * 10000, "dur_us": 10000,
            "resources": ["PROCESS"], "primary_resource": "PROCESS",
        })
    run_dir = _write_run_dir(tmp_path, run_context, elements, spans)

    analyzer = BuildEfficiencyAnalyzer(run_dir)
    analyzer.load()
    result = analyzer.analyze()

    floors = result.floors
    horizon_us = result.occupancy["horizon_us"]

    process_work_us = 5 * 10000
    process_only_lb = process_work_us // 4  # what the old PROCESS-only formula would give

    assert floors["lb"] > process_only_lb
    assert floors["lb"] == 400000  # W_DOWNLOAD / C_DOWNLOAD = 400000 / 1

    # I1/I2: H >= LB, LB <= T_C.
    assert horizon_us >= floors["lb"]
    assert floors["lb"] <= floors["t_c"]


def test_exclusive_resource_forces_full_serialization_floor(tmp_path):
    """CACHE declared exclusive: even with capacity 2 declared, exclusive
    resources cannot overlap at all, so LB must reflect the full summed
    duration, not work_us // 2."""
    run_context = {
        "trace_epsilon_us": 50000, "wall_start_us": 0, "wall_end_us": 300000,
        "max_jobs": 4, "resource_capacities": {"PROCESS": 4, "CACHE": 2},
        "exclusive_resources": ["CACHE"],
    }
    elements = [("a.bst", True), ("b.bst", False)]
    spans = [
        {"task_key": "a.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 100000,
         "resources": ["CACHE"], "primary_resource": "CACHE"},
        {"task_key": "b.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 100000,
         "resources": ["CACHE"], "primary_resource": "CACHE"},
    ]
    run_dir = _write_run_dir(tmp_path, run_context, elements, spans)

    analyzer = BuildEfficiencyAnalyzer(run_dir)
    analyzer.load()
    result = analyzer.analyze()

    # Non-exclusive treatment would give 200000 // 2 = 100000; exclusive
    # treatment must give the full 200000us serialization floor.
    assert result.floors["lb"] == 200000


def test_single_process_fixture_unchanged(tmp_path):
    """Regression guard: a fixture using only PROCESS must produce the
    same LB the old PROCESS-only formula would give."""
    run_context = {
        "trace_epsilon_us": 50000, "wall_start_us": 0, "wall_end_us": 200000,
        "max_jobs": 2, "resource_capacities": {"PROCESS": 2},
    }
    elements = [("a.bst", True), ("b.bst", False)]
    spans = [
        {"task_key": "a.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 100000,
         "resources": ["PROCESS"], "primary_resource": "PROCESS"},
        {"task_key": "b.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 100000,
         "resources": ["PROCESS"], "primary_resource": "PROCESS"},
    ]
    run_dir = _write_run_dir(tmp_path, run_context, elements, spans)

    analyzer = BuildEfficiencyAnalyzer(run_dir)
    analyzer.load()
    result = analyzer.analyze()

    assert result.floors["lb"] == 100000  # 200000 // 2
