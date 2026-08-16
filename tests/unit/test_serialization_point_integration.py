"""UX-22 Acceptance Test #1/#2: real end-to-end large-serialization-point
detection driven through the real `bga/analyzer.py` call site (not just
direct `detect_large_serialization_points` calls - see
`tests/unit/test_serialization_points.py` for those), confirming
`Element.max_jobs`/`RunContext.host_cpu_count`/`resource_capacities`
are all correctly threaded through and surfaced in both JSON and text
output.
"""
import json

from bga import BuildEfficiencyAnalyzer
from bga.report.text import format_text


def _write_run_dir(tmp_path, name, builders, host_cpu_count, element_max_jobs):
    run_dir = tmp_path / name
    run_dir.mkdir()
    run_context = {
        "trace_epsilon_us": 100,
        "resource_capacities": {"PROCESS": builders},
        "host_cpu_count": host_cpu_count,
    }
    # 4 short filler elements + the candidates under test, so the
    # mean-duration-based "long" threshold stays realistic (same
    # reasoning as tests/unit/test_serialization_points.py's own
    # _with_filler helper).
    elements = [{"uid": f"filler_{i}.bst", "requested_target": False} for i in range(4)]
    spans = [
        {"task_key": f"filler_{i}.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 100,
         "resources": ["PROCESS"], "primary_resource": "PROCESS"}
        for i in range(4)
    ]
    for uid, max_jobs in element_max_jobs.items():
        elements.append({"uid": uid, "requested_target": True, "max_jobs": max_jobs})
        spans.append({
            "task_key": f"{uid}|BUILD|BUILD|0", "ts_us": 0, "dur_us": 10000,
            "resources": ["PROCESS"], "primary_resource": "PROCESS",
        })

    graph = {"elements": elements, "dependencies": []}
    trace = {"spans": spans, "phases": []}
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))
    return run_dir


def _analyze(tmp_path, name, builders, host_cpu_count, element_max_jobs):
    run_dir = _write_run_dir(tmp_path, name, builders, host_cpu_count, element_max_jobs)
    analyzer = BuildEfficiencyAnalyzer(run_dir)
    analyzer.load()
    return analyzer.analyze()


def test_real_llvm_style_scenario_fires_through_the_real_call_site(tmp_path):
    """Two independent, real per-element max-jobs=4 overrides (near the
    real host_cpu_count=4 ceiling), both with a real long measured
    duration, under a real builders=4 (so >=2 can genuinely dispatch
    concurrently) - the exact scenario UX-22's own Motivation describes."""
    result = _analyze(
        tmp_path, "run", builders=4, host_cpu_count=4,
        element_max_jobs={"llvm1.bst": 4, "llvm2.bst": 4},
    )

    risks = result.structural["serialization_point_risks"]
    assert len(risks) == 1
    assert set(risks[0]["elements"]) == {"llvm1.bst", "llvm2.bst"}

    output = format_text(result)
    assert "Large Serialization Point Risk" in output
    assert "llvm1.bst" in output and "llvm2.bst" in output


def test_builders_one_real_run_produces_no_risk(tmp_path):
    """Acceptance Test #2's own explicit case, driven through the real
    call site: builders=1 makes concurrent dispatch impossible
    regardless of how the elements are configured."""
    result = _analyze(
        tmp_path, "run", builders=1, host_cpu_count=4,
        element_max_jobs={"llvm1.bst": 4, "llvm2.bst": 4},
    )

    assert result.structural["serialization_point_risks"] == []


def test_only_one_override_real_run_produces_no_risk(tmp_path):
    result = _analyze(
        tmp_path, "run", builders=4, host_cpu_count=4,
        element_max_jobs={"llvm1.bst": 4},
    )

    assert result.structural["serialization_point_risks"] == []
