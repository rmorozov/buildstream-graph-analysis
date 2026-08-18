"""Tests for UX-10: `Total Duration` (AnalysisResult.total_duration_us)
must prefer the run's real wall-clock window (run_context.wall_start_us/
wall_end_us) over the tracked-task horizon, per spec Part 4.3's own
stated preference - the horizon-only calculation is explicitly marked
"reduced provenance", a fallback for when wall-clock bounds aren't
available, not the primary definition.

Found via a real run of examples/05-cmake-cpp-toolchain (see
docs/backlog/scenarios/UX-10-total-duration-excludes-pre-task-overhead.md):
`bga analyze` reported `Total Duration: 4.0s` while the real BuildStream
session (run-context.json's own wall_clock field) was 7.6s - a real
~3.6s gap (BuildStream startup + real sandbox-staging cost for a large
import dependency) invisible to the headline number, and consequently to
`bga compare`'s verdict too.
"""
import json

from bga import BuildEfficiencyAnalyzer
from bga.compare import compare_runs


def _write_run_dir(tmp_path, name, run_context, elements, dependencies, spans):
    run_dir = tmp_path / name
    run_dir.mkdir()
    graph = {
        "elements": [{"uid": uid, "requested_target": is_target} for uid, is_target in elements],
        "dependencies": [
            {"predecessor": pred, "successor": succ} for pred, succ in dependencies
        ],
    }
    trace = {"spans": spans, "phases": []}
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))
    return run_dir


# A single a.bst task running from t=3000 to t=8000 (5000us of real work) -
# but the run's real wall clock spans 0 to 10000 (10000us), i.e. 3000us of
# real pre-task overhead (BuildStream startup, sandbox staging) and 2000us
# of real post-task overhead, neither of which the tracked-task horizon
# (5000us, min_start to max_finish) reflects at all.
_ELEMENTS = [("a.bst", True)]
_DEPENDENCIES: list = []
_SPANS = [
    {"task_key": "a.bst|BUILD|BUILD|0", "ts_us": 3000, "dur_us": 5000,
     "resources": ["PROCESS"], "primary_resource": "PROCESS"},
]


def _run_context(wall_start_us, wall_end_us):
    # run-context/v9's real schema (bga/ingest/loader.py:load_run_context)
    # nests these under "wall_clock", not flat "wall_start_us"/
    # "wall_end_us" keys.
    run_context = {"trace_epsilon_us": 100}
    if wall_start_us is not None or wall_end_us is not None:
        run_context["wall_clock"] = {"start_us": wall_start_us, "end_us": wall_end_us}
    return run_context


def _analyze(tmp_path, name, wall_start_us, wall_end_us):
    run_dir = _write_run_dir(
        tmp_path, name, _run_context(wall_start_us, wall_end_us),
        _ELEMENTS, _DEPENDENCIES, _SPANS,
    )
    analyzer = BuildEfficiencyAnalyzer(run_dir)
    analyzer.load()
    return analyzer.analyze()


def test_total_duration_uses_real_wall_clock_when_available(tmp_path):
    result = _analyze(tmp_path, "run", wall_start_us=0, wall_end_us=10000)
    assert result.total_duration_us == 10000
    # Not the narrower tracked-task horizon (max_finish - min_start = 5000).
    assert result.total_duration_us != 5000


def test_total_duration_falls_back_to_horizon_without_wall_clock_bounds(tmp_path):
    result = _analyze(tmp_path, "run", wall_start_us=None, wall_end_us=None)
    assert result.total_duration_us == 5000


def test_attribution_categories_sum_to_total_duration_with_wall_clock(tmp_path):
    """Part 12's exact identity: UNTRACKED_HEAD + task-horizon attribution
    + UNTRACKED_TAIL == wall_clock. Before this fix, total_duration_us was
    the (narrower) horizon while UNTRACKED_HEAD/TAIL were already
    wall-clock-relative, so this sum structurally could not equal
    total_duration_us whenever real pre/post-task overhead existed."""
    result = _analyze(tmp_path, "run", wall_start_us=0, wall_end_us=10000)
    assert sum(result.attribution.values()) == result.total_duration_us
    assert result.attribution["untracked_head_us"] == 3000
    assert result.attribution["untracked_tail_us"] == 2000


def test_wall_clock_less_than_horizon_is_flagged_as_a_violation(tmp_path):
    """A real, meaningful data-quality signal (Part 13: "wall_clock >= H
    is a provenance/containment relationship") - exactly the symptom a
    corrupted timestamp reconstruction produces (see UX-06), so it must
    be reported, not silently absorbed."""
    # wall_clock span (2000us) is narrower than the task horizon (5000us,
    # min_start=3000 to max_finish=8000) - an impossible/corrupt case.
    result = _analyze(tmp_path, "run", wall_start_us=0, wall_end_us=2000)
    violation_types = [v.get("type") for v in (result.violations or [])]
    assert "wall_clock_containment" in violation_types


def test_compare_verdict_reflects_a_real_wall_clock_only_regression(tmp_path):
    """The real UX-10 scenario: two runs with an *identical* tracked-task
    horizon (same task, same duration) but genuinely different real
    wall-clock time (different pre-task overhead) - before this fix,
    `bga compare` reported "no significant change" here since it only
    ever saw the identical horizon."""
    baseline_dir = _write_run_dir(
        tmp_path, "baseline", _run_context(0, 6000), _ELEMENTS, _DEPENDENCIES, _SPANS,
    )
    candidate_dir = _write_run_dir(
        tmp_path, "candidate", _run_context(0, 10000), _ELEMENTS, _DEPENDENCIES, _SPANS,
    )
    comparison = compare_runs(baseline_dir, candidate_dir)
    assert comparison.deltas["total_duration_us"] == 4000
    assert comparison.verdict != "no significant change"
