"""P1-37: run identity (I8) - captured at extraction time
(tools/bst_extract_run.py's run_identity/run_identity_hash fields) and
enforced by bga's own loader/confidence computation.

Full pipeline tests (BuildEfficiencyAnalyzer against a hand-built run
directory), matching tests/unit/test_confidence_gates.py's own pattern -
run identity affects confidence (provenance_score, a new
run_identity_consistent hard gate), not a separate enforcement layer.
"""
import json

from bga import BuildEfficiencyAnalyzer


def _write_run_dir(tmp_path, name="run", run_context_extra=None, graph_extra=None, trace_extra=None):
    run_dir = tmp_path / name
    run_dir.mkdir()
    run_context = {
        "trace_epsilon_us": 1000,
        "wall_clock": {"start_us": 0, "end_us": 50000},
        "max_jobs": 2, "resource_capacities": {"PROCESS": 2},
        **(run_context_extra or {}),
    }
    graph = {
        "elements": [{"uid": "a.bst", "requested_target": True}],
        "dependencies": [],
        **(graph_extra or {}),
    }
    trace = {
        "spans": [{"task_key": "a.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 50000,
                    "resources": ["PROCESS"], "primary_resource": "PROCESS"}],
        "phases": [],
        **(trace_extra or {}),
    }
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))
    return run_dir


def _analyze(run_dir):
    analyzer = BuildEfficiencyAnalyzer(run_dir)
    analyzer.load()
    return analyzer.analyze()


def test_matching_run_identity_across_all_three_no_penalty(tmp_path):
    run_dir = _write_run_dir(
        tmp_path,
        run_context_extra={"run_identity": {"manifest_hash": "abc123"}},
        graph_extra={"run_identity_hash": "abc123"},
        trace_extra={"run_identity_hash": "abc123"},
    )
    result = _analyze(run_dir)

    assert result.confidence["hard_gates"]["run_identity_consistent"] is True
    assert result.confidence["run_identity_available"] is True
    assert result.confidence["provenance_score"] == 1.0
    assert result.run_id == "abc123"
    assert not any(v.get("type") == "run_identity_mismatch" for v in result.violations)


def test_missing_run_identity_is_backward_compatible_not_a_hard_failure(tmp_path):
    """An older-style/hand-built run directory with no identity fields at
    all - bga analyze must still work, with a real, visible reduced-
    provenance signal (not a false claim of full confidence), but never
    a hard failure."""
    run_dir = _write_run_dir(tmp_path)  # no run_identity/run_identity_hash anywhere
    result = _analyze(run_dir)

    assert result.confidence["hard_gates"]["run_identity_consistent"] is True
    assert result.confidence["run_identity_available"] is False
    assert result.confidence["provenance_score"] < 1.0
    assert not any(v.get("type") == "run_identity_mismatch" for v in result.violations)
    assert result.run_id == ""


def test_partially_present_run_identity_is_also_reduced_provenance_not_a_conflict(tmp_path):
    """Only run-context.json has identity data; graph.json/trace.json
    don't (e.g. extracted with an older tool version) - reduced
    provenance, same as fully absent, not treated as a conflict."""
    run_dir = _write_run_dir(
        tmp_path,
        run_context_extra={"run_identity": {"manifest_hash": "abc123"}},
    )
    result = _analyze(run_dir)

    assert result.confidence["hard_gates"]["run_identity_consistent"] is True
    assert result.confidence["run_identity_available"] is False
    assert not any(v.get("type") == "run_identity_mismatch" for v in result.violations)


def test_conflicting_run_identity_is_a_violation_and_hard_gate_failure(tmp_path):
    """trace.json's run_identity_hash disagrees with run-context.json/
    graph.json's - the exact "trace.json swapped in from an unrelated
    extraction" scenario I8 exists to catch. Must report a clear
    identity-conflict violation, not silently analyze the mismatched
    inputs as if they were consistent."""
    run_dir = _write_run_dir(
        tmp_path,
        run_context_extra={"run_identity": {"manifest_hash": "abc123"}},
        graph_extra={"run_identity_hash": "abc123"},
        trace_extra={"run_identity_hash": "xyz789-from-a-different-run"},
    )
    result = _analyze(run_dir)

    assert result.confidence["hard_gates"]["run_identity_consistent"] is False
    assert result.confidence["provenance_score"] == 0.0
    mismatches = [v for v in result.violations if v.get("type") == "run_identity_mismatch"]
    assert len(mismatches) == 1
    assert mismatches[0]["run_context_hash"] == "abc123"
    assert mismatches[0]["graph_hash"] == "abc123"
    assert mismatches[0]["trace_hash"] == "xyz789-from-a-different-run"


def test_analysis_still_proceeds_despite_identity_conflict(tmp_path):
    """A conflict is reported (see above), but does not block analysis
    from running - I8 gets a violation entry + confidence penalty, not a
    hard crash/refusal, consistent with this codebase's general "no
    silent correction, but don't stop working either" discipline."""
    run_dir = _write_run_dir(
        tmp_path,
        run_context_extra={"run_identity": {"manifest_hash": "abc123"}},
        graph_extra={"run_identity_hash": "abc123"},
        trace_extra={"run_identity_hash": "different"},
    )
    result = _analyze(run_dir)

    assert result.attribution
    assert result.total_duration_us == 50000
