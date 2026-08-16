"""UX-22/UX-31 Acceptance Test: real end-to-end parallelism-pinning
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
    for uid, spec in element_max_jobs.items():
        max_jobs, notparallel = spec if isinstance(spec, tuple) else (spec, None)
        elements.append({
            "uid": uid, "requested_target": True,
            "max_jobs": max_jobs, "notparallel": notparallel,
        })
        spans.append({
            "task_key": f"{uid}|BUILD|BUILD|0", "ts_us": 0, "dur_us": 10000,
            "resources": ["PROCESS"], "primary_resource": "PROCESS",
        })

    graph = {
        "elements": elements,
        # UX-31: a pinned element only matters if something waits behind
        # it, so every candidate gets one real downstream dependent.
        "dependencies": [
            {"predecessor": uid, "successor": "filler_0.bst"} for uid in element_max_jobs
        ],
    }
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


def test_a_pinned_element_fires_through_the_real_call_site(tmp_path):
    """UX-31's real scenario, end to end: one element pinned to a single
    job by `notparallel` while the rest of the build runs at 4, with a
    real long measured duration and real downstream dependents.
    Confirms `Element.max_jobs`/`Element.notparallel` are threaded from
    graph.json through the analyzer into both JSON and text output."""
    result = _analyze(
        tmp_path, "run", builders=4, host_cpu_count=4,
        element_max_jobs={"core.bst": (1, True), "lib-a.bst": (4, None)},
    )

    risks = result.structural["serialization_point_risks"]
    assert len(risks) == 1
    assert risks[0]["elements"] == ["core.bst"]
    assert risks[0]["notparallel"] is True
    assert risks[0]["typical_max_jobs"] == 4

    output = format_text(result)
    assert "Parallelism-Pinned Elements" in output
    assert "core.bst" in output


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
