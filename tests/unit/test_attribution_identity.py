"""Unit-level regression tests for invariant I4 (Sigma attribution == H).

Covers the P1-03 fix: a linear, single-task-kind-per-element dependency
chain (no TRACK/FETCH/BUILD split, so no intra-element sequencing gap -
that residual is P1-19's scope) must produce exact attribution identity.
"""
import json

from bga import analyze_run


def _write_run_dir(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    run_context = {
        "trace_epsilon_us": 50000,
        "wall_start_us": 0,
        "wall_end_us": 450000,
        "max_jobs": 1,
        "resource_capacities": {"PROCESS": 1},
    }
    graph = {
        "elements": [
            {"uid": "a.bst", "cache_key": "k1", "requested_target": True},
            {"uid": "b.bst", "cache_key": "k2", "requested_target": True},
            {"uid": "c.bst", "cache_key": "k3", "requested_target": True},
        ],
        "dependencies": [
            {"predecessor": "a.bst", "successor": "b.bst", "dependency_type": "build"},
            {"predecessor": "b.bst", "successor": "c.bst", "dependency_type": "build"},
        ],
    }
    trace = {
        "spans": [
            {"task_key": "a.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 150000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "b.bst|BUILD|BUILD|0", "ts_us": 150000, "dur_us": 150000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "c.bst|BUILD|BUILD|0", "ts_us": 300000, "dur_us": 150000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
        ],
        "phases": [],
    }
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))
    return run_dir


def test_zero_wait_serialized_chain_attribution_is_exact(tmp_path):
    """Regression guard for the P1-03 root cause found in the simplest
    possible reproduction: three tasks serialized back-to-back on a single-
    capacity resource, zero gap between them. The blame-chain walk used to
    stop dead after the first (terminal) task whenever the wait to its
    predecessor was exactly zero, silently dropping the other two tasks
    from the flattened timeline entirely (Sigma attribution was 150000us -
    33% of H - instead of the correct 450000us).
    """
    run_dir = _write_run_dir(tmp_path)
    result = analyze_run(run_dir)

    h = result.occupancy["horizon_us"]
    assert h == 450000

    total = sum(
        result.attribution.get(k, 0)
        for k in (
            "execution_on_chain_us", "dependency_wait_us", "resource_wait_us",
            "scheduler_wait_us", "idle_us", "retry_wait_us",
        )
    )
    assert total == h
    assert result.attribution["execution_on_chain_us"] == 450000
    assert result.attribution["dependency_wait_us"] == 0
