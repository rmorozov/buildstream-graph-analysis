"""Tests for UX-04: the wait-category line (the Key Findings block's
single largest non-EXECUTION_ON_CHAIN attribution category, P4-02) names
a category but, before this fix, gave no way to know from the report
itself what that category means or what to do about it - RESOURCE_WAIT/
SCHEDULER_WAIT/IDLE look superficially similar ("the critical path
wasn't running") but have three completely different real fixes, each
precisely defined in spec Part 11 but never surfaced in the report.
"""
import json

import pytest

from bga import BuildEfficiencyAnalyzer
from bga.ingest.models import AttributionCategory
from bga.report._shared import ATTRIBUTION_CATEGORY_HINTS, ATTRIBUTION_CATEGORY_HINTS_BY_KEY
from bga.report.json import format_json
from bga.report.text import format_text


def test_every_attribution_category_has_a_non_empty_hint():
    """A real guard against a future new AttributionCategory silently
    lacking a hint - the acceptance test's own required check."""
    for category in AttributionCategory:
        hint = ATTRIBUTION_CATEGORY_HINTS.get(category)
        assert hint, f"{category} has no hint"
        assert isinstance(hint, str) and hint.strip()


def test_hints_by_key_covers_every_real_attribution_dict_key():
    """The lowercase `<category>_us` keys result.attribution/--format
    json actually use (confirmed against bga/analyzer.py's
    _compute_attribution) must all resolve to a hint."""
    real_keys = {
        'execution_on_chain_us', 'dependency_wait_us', 'resource_wait_us',
        'scheduler_wait_us', 'idle_us', 'retry_wait_us',
        'untracked_head_us', 'untracked_tail_us',
    }
    assert real_keys == set(ATTRIBUTION_CATEGORY_HINTS_BY_KEY.keys())


def _write_run_dir(tmp_path, run_context, elements, dependencies, spans):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    graph = {
        "elements": [{"uid": uid, "requested_target": is_target} for uid, is_target in elements],
        "dependencies": [{"predecessor": pred, "successor": succ} for pred, succ in dependencies],
    }
    trace = {"spans": spans, "phases": []}
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))
    return run_dir


@pytest.fixture
def dependency_wait_dominant_result(tmp_path):
    """Same fixture shape as test_report_key_findings.py's own
    analyzed_result - a.bst has a large, deliberate DEPENDENCY_WAIT gap,
    the clear dominant non-execution category."""
    run_dir = _write_run_dir(
        tmp_path,
        run_context={"trace_epsilon_us": 1000, "wall_start_us": 0, "wall_end_us": 110000},
        elements=[("root.bst", False), ("a.bst", True), ("b.bst", True), ("c.bst", True)],
        dependencies=[("root.bst", "a.bst"), ("root.bst", "b.bst"), ("root.bst", "c.bst")],
        spans=[
            {"task_key": "root.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 10000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "b.bst|BUILD|BUILD|0", "ts_us": 10000, "dur_us": 5000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "c.bst|BUILD|BUILD|0", "ts_us": 10000, "dur_us": 5000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "a.bst|BUILD|BUILD|0", "ts_us": 100000, "dur_us": 10000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
        ],
    )
    analyzer = BuildEfficiencyAnalyzer(run_dir)
    analyzer.load()
    return analyzer.analyze()


def test_text_report_shows_the_hint_for_the_named_biggest_opportunity(dependency_wait_dominant_result):
    output = format_text(dependency_wait_dominant_result)
    key_findings_section = output.split("Certified Floors:")[0]
    # `UX-365` re-scoped this label: it was "Biggest Opportunity",
    # a claim over every finding, and names its own population now.
    assert "Biggest wait category" in key_findings_section
    assert "DEPENDENCY WAIT" in key_findings_section
    assert ATTRIBUTION_CATEGORY_HINTS_BY_KEY["dependency_wait_us"] in key_findings_section
    # The hint line must actually follow the wait-category line,
    # not just appear anywhere in the report by coincidence.
    opportunity_idx = key_findings_section.index("Biggest wait category")
    hint_idx = key_findings_section.index(ATTRIBUTION_CATEGORY_HINTS_BY_KEY["dependency_wait_us"])
    assert hint_idx > opportunity_idx


def test_json_attribution_hints_present_without_changing_attribution_field(dependency_wait_dominant_result):
    data = json.loads(format_json(dependency_wait_dominant_result))
    # Existing field untouched - same keys/values as before this fix.
    assert set(data["attribution"].keys()) == {
        'execution_on_chain_us', 'dependency_wait_us', 'resource_wait_us',
        'scheduler_wait_us', 'idle_us', 'retry_wait_us',
        'untracked_head_us', 'untracked_tail_us',
    }
    assert all(isinstance(v, int) for v in data["attribution"].values())
    # New, additive sibling key.
    assert data["attribution_hints"]["dependency_wait_us"] == (
        ATTRIBUTION_CATEGORY_HINTS_BY_KEY["dependency_wait_us"]
    )
