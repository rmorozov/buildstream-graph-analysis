"""Regression tests for P1-09: genuine Monte-Carlo criticality probability.

`DiagnosticsAnalyzer._compute_perturbed_critical_path` (the per-sample
resampling itself) was already a real implementation, not the
`return self.critical_path` stub the original task diagnosis described -
apparently fixed in an earlier, undocumented round (a stale-tracker
pattern that's shown up more than once this session). The actual live
bug was a key-format mismatch in `compute_criticality_probability`:
`critical_counts` is populated with element UIDs (the critical path is
defined on the element graph, Part 24.1/5.3), but the aggregation step
looked values up by the full `task_key` string, so `probability` always
collapsed to 0.0 regardless of what the resampling actually found. The
same mismatch made `observed_critical` always False too (`self.critical_path`
is also a set of element UIDs). Both fixed to key by `elem_uid`.
"""
import json

from bga import BuildEfficiencyAnalyzer


def _write_diamond_run_dir(tmp_path):
    """root -> {a, b} -> merge, with a/b near-equal length (50000 vs
    49000us) so which one lands on the critical path is genuinely
    sensitive to the +/-10% perturbation - the key case the old 0/1
    collapse could never produce.
    """
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    run_context = {
        "trace_epsilon_us": 1000, "wall_start_us": 0, "wall_end_us": 200000,
        "max_jobs": 2, "resource_capacities": {"PROCESS": 2},
    }
    graph = {
        "elements": [
            {"uid": "root.bst"}, {"uid": "a.bst"}, {"uid": "b.bst"},
            {"uid": "merge.bst", "requested_target": True},
        ],
        "dependencies": [
            {"predecessor": "root.bst", "successor": "a.bst"},
            {"predecessor": "root.bst", "successor": "b.bst"},
            {"predecessor": "a.bst", "successor": "merge.bst"},
            {"predecessor": "b.bst", "successor": "merge.bst"},
        ],
    }
    trace = {
        "spans": [
            {"task_key": "root.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 10000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "a.bst|BUILD|BUILD|0", "ts_us": 10000, "dur_us": 50000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "b.bst|BUILD|BUILD|0", "ts_us": 10000, "dur_us": 49000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "merge.bst|BUILD|BUILD|0", "ts_us": 60000, "dur_us": 10000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
        ],
        "phases": [],
    }
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))
    return run_dir


def _criticality(run_dir):
    analyzer = BuildEfficiencyAnalyzer(run_dir, run_diagnostics=True)
    analyzer.load()
    result = analyzer.analyze()
    return result.signals["criticality_probability"]


def test_near_tie_element_has_genuine_intermediate_probability(tmp_path):
    run_dir = _write_diamond_run_dir(tmp_path)
    crit = _criticality(run_dir)

    # The old bug collapsed every probability to 0.0 - this proves
    # genuine per-sample resampling is both running and being counted.
    assert 0 < crit["a.bst"]["probability"] < 1
    assert 0 < crit["b.bst"]["probability"] < 1
    # Exactly one of {a, b} is critical per sample in this diamond.
    assert crit["a.bst"]["probability"] + crit["b.bst"]["probability"] == 1.0


def test_observed_critical_matches_actual_critical_path(tmp_path):
    run_dir = _write_diamond_run_dir(tmp_path)
    crit = _criticality(run_dir)

    # a.bst (50000us) is longer than b.bst (49000us) in the observed
    # (unperturbed) trace, so it - not b.bst - is the real critical one.
    assert crit["a.bst"]["observed_critical"] is True
    assert crit["b.bst"]["observed_critical"] is False
    assert crit["root.bst"]["observed_critical"] is True
    assert crit["merge.bst"]["observed_critical"] is True


def test_same_seed_is_deterministic(tmp_path):
    run_dir = _write_diamond_run_dir(tmp_path)
    assert _criticality(run_dir) == _criticality(run_dir)


def test_probabilities_are_bounded(tmp_path):
    run_dir = _write_diamond_run_dir(tmp_path)
    for data in _criticality(run_dir).values():
        assert 0.0 <= data["probability"] <= 1.0


def test_graph_topology_built_once_not_per_sample(tmp_path, monkeypatch):
    """Regression guard for P1-28 (Part 41.2: "reuse the graph topology
    and avoid rebuilding graph structures" across Monte-Carlo samples).
    _compute_perturbed_critical_path used to call build_element_graph/
    compute_in_out_degree fresh on every one of num_samples (default
    200) calls, rebuilding the same static topology 200x over - an
    independent audit found this as a direct, literal deviation from
    the spec's explicit instruction (not asymptotically wrong, since
    each rebuild is still O(N+E), but wasteful). Both are now built
    once by the caller and passed in."""
    import bga.diagnostics.analyzer as diagnostics_module

    run_dir = _write_diamond_run_dir(tmp_path)
    call_counts = {"build_element_graph": 0, "compute_in_out_degree": 0}
    real_build_element_graph = diagnostics_module.build_element_graph
    real_compute_in_out_degree = diagnostics_module.compute_in_out_degree

    def counting_build_element_graph(*args, **kwargs):
        call_counts["build_element_graph"] += 1
        return real_build_element_graph(*args, **kwargs)

    def counting_compute_in_out_degree(*args, **kwargs):
        call_counts["compute_in_out_degree"] += 1
        return real_compute_in_out_degree(*args, **kwargs)

    monkeypatch.setattr(diagnostics_module, "build_element_graph", counting_build_element_graph)
    monkeypatch.setattr(diagnostics_module, "compute_in_out_degree", counting_compute_in_out_degree)

    analyzer = BuildEfficiencyAnalyzer(run_dir, run_diagnostics=True)
    analyzer.load()
    analyzer.analyze()

    assert call_counts["build_element_graph"] == 1
    assert call_counts["compute_in_out_degree"] == 1


def test_the_element_mapping_is_derived_once_not_per_sample(tmp_path, monkeypatch):
    """UX-542: Part 41.2's second clause - "only durations and dynamic
    programming values vary". The topology was already hoisted (P1-28
    above); the task->element mapping was not, and was re-split inside
    every sample: 4,002 tasks x 200 samples = 800,400 splits on the
    largest measured run. The bound is the call count, not seconds."""
    import bga.diagnostics.analyzer as diagnostics_module

    run_dir = _write_diamond_run_dir(tmp_path)
    calls = []
    real = diagnostics_module.element_uids_of

    def counting(task_durations):
        calls.append(len(task_durations))
        return real(task_durations)

    monkeypatch.setattr(diagnostics_module, "element_uids_of", counting)

    analyzer = BuildEfficiencyAnalyzer(run_dir, run_diagnostics=True)
    analyzer.load()
    analyzer.analyze()

    samples = diagnostics_module.DiagnosticsAnalyzer.DEFAULT_MC_SAMPLES
    assert calls, "the mapping was never derived - the seam is not on the path"
    assert len(calls) == 1, (
        f"the task->element mapping was derived {len(calls)} times for "
        f"{samples} samples; Part 41.2 asks for once")
